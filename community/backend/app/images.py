from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
import re
import threading
import warnings

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from .database import TAGS, identifier, now


def sanitize_image(raw, settings):
    if not raw or len(raw) > settings.max_image_bytes:
        raise HTTPException(413, "写真は12MB以内で選んでください。")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"} or getattr(original, "n_frames", 1) != 1:
                    raise HTTPException(415, "静止したJPEG・PNG・WebPを選んでください。")
                if original.width * original.height > settings.max_pixels or min(original.size) < 16:
                    raise HTTPException(413, "写真の大きさを確認してください。上限は2000万画素です。")
                original.verify()
            with Image.open(io.BytesIO(raw)) as original:
                converted = ImageOps.exif_transpose(original).convert("RGB")
                converted.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                clean = Image.new("RGB", converted.size)
                clean.paste(converted)
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=88, optimize=True)
                return output.getvalue(), clean.width, clean.height
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, "写真を読み取れませんでした。別のJPEG・PNG・WebPを選んでください。")


def location_candidate(raw):
    """Called only after bounded image validation and explicit upload opt-in.

    Read GPS only; never preserve a raw EXIF block, dates, device IDs or filenames.
    A candidate is unverified until its owner explicitly confirms a visit.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with Image.open(io.BytesIO(raw)) as original:
                gps = original.getexif().get_ifd(34853)
                def coordinate(value, reference, positive, negative, limit):
                    if isinstance(reference, bytes):
                        reference = reference.decode('ascii')
                    if reference not in (positive, negative) or len(value) != 3:
                        raise ValueError('Invalid GPS reference')
                    degrees, minutes, seconds = map(float, value)
                    if not all(math.isfinite(item) for item in (degrees, minutes, seconds)) or not (0 <= degrees <= limit and 0 <= minutes < 60 and 0 <= seconds < 60):
                        raise ValueError('Invalid GPS angle')
                    result = degrees + minutes / 60 + seconds / 3600
                    if result > limit:
                        raise ValueError('Invalid GPS range')
                    return round(result * (1 if reference == positive else -1), 7)
                return {'latitude': coordinate(gps[2], gps[1], 'N', 'S', 90),
                        'longitude': coordinate(gps[4], gps[3], 'E', 'W', 180)}
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError, OSError, Warning, AttributeError, IndexError):
        return None


class LocalClassifier:
    """ImageNet visual classifier; user filenames/captions are never inputs."""
    KEYWORDS = {
        "coast": ("seashore", "sandbar", "coral reef", "promontory", "cliff", "lakeside"),
        "mountain": ("mountain", "volcano", "alp", "valley"),
        "nature": ("forest", "daisy", "rapeseed", "tree", "mushroom"),
        "food": ("pizza", "food", "plate", "dish", "salad", "sandwich", "hotdog", "hot pot", "burrito", "carbonara", "soup", "ice cream", "bread", "bagel", "pretzel", "cheeseburger", "guacamole", "bakery", "dining table", "restaurant"),
        "cafe": ("coffee", "espresso", "teapot", "cup", "mug"),
        "fashion": ("shirt", "dress", "jean", "shoe", "sandal", "sneaker", "sunglass", "handbag", "backpack", "cardigan", "sweatshirt", "poncho"),
        "games": ("board game", "chess", "puzzle", "crossword"),
        "stay": ("bed", "quilt", "couch", "sofa", "pillow"),
        "walk": ("street", "palace", "castle", "bookshop", "fountain", "bridge", "pier"),
    }

    def __init__(self, folder):
        self.session = None
        self.version = None
        self.labels = []
        try:
            manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
            model = folder / "mobilenetv2-12.onnx"
            for name in ("mobilenetv2-12.onnx", "synset.txt"):
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != manifest["files"][name]["sha256"]:
                    raise ValueError("Model integrity failure")
            import onnxruntime as ort
            ort.disable_telemetry_events()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
            self.labels = (folder / "synset.txt").read_text(encoding="utf-8").splitlines()
            if len(self.labels) != 1000:
                raise ValueError("Unexpected label count")
            self.version = "mobilenetv2-12:" + manifest["revision"][:12]
        except Exception:
            self.session = None

    def classify(self, path):
        if self.session is None:
            raise RuntimeError("model_unavailable")
        import numpy as np
        import onnxruntime as ort
        with Image.open(path) as image:
            image = image.convert("RGB")
            scale = 256 / min(image.size)
            resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.BILINEAR)
            left, top = (resized.width - 224) // 2, (resized.height - 224) // 2
            array = np.asarray(resized.crop((left, top, left + 224, top + 224)), dtype=np.float32) / 255.0
        array = ((array - np.array([.485, .456, .406], dtype=np.float32)) / np.array([.229, .224, .225], dtype=np.float32)).transpose(2, 0, 1)[None]
        options = ort.RunOptions()
        timer = threading.Timer(10, lambda: setattr(options, "terminate", True))
        timer.start()
        try:
            logits = self.session.run(None, {self.session.get_inputs()[0].name: array}, options)[0].reshape(-1)
        finally:
            timer.cancel()
        probabilities = np.exp(logits - logits.max())
        probabilities /= probabilities.sum()
        scores = {}
        for tag, words in self.KEYWORDS.items():
            scores[tag] = sum(float(probabilities[index]) for index, label in enumerate(self.labels) if any(re.search(r"\b" + re.escape(word) + r"\b", label.lower()) for word in words))
        return [{"id": tag, "label": TAGS[tag], "score": round(score, 4)} for tag, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score >= .12][:3]


class AnalysisWorker:
    def __init__(self, database, settings, classifier):
        self.database, self.settings, self.classifier = database, settings, classifier
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name="local-image-analysis", daemon=True)

    def start(self):
        with self.database.transaction(True) as conn:
            self.recover_expired(conn)
        self.thread.start()

    @staticmethod
    def recover_expired(conn):
        conn.execute("UPDATE jobs SET status=CASE WHEN attempts<2 THEN 'queued' ELSE 'failed' END,lease_until=NULL,message='処理が中断されました。再試行するかタグを選んでください。' WHERE status='running' AND (lease_until IS NULL OR lease_until<=?)", (now(),))

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=12)

    def run(self):
        while not self.stop_event.is_set():
            try:
                if not self.once():
                    self.stop_event.wait(.4)
            except Exception:
                # No filenames, photo content or exception detail enters logs.
                self.stop_event.wait(1)

    def once(self):
        with self.database.transaction(True) as conn:
            for deleted in conn.execute("SELECT storage_key FROM media WHERE deleted=1"):
                try:
                    (self.settings.media_dir / deleted["storage_key"]).unlink(missing_ok=True)
                except OSError:
                    pass
            self.recover_expired(conn)
            job = conn.execute("SELECT j.*,m.storage_key FROM jobs j JOIN media m ON m.id=j.media_id WHERE j.status='queued' AND j.attempts<2 AND m.deleted=0 ORDER BY m.created_at LIMIT 1").fetchone()
            if job is None:
                return False
            lease = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
            conn.execute("UPDATE jobs SET status='running',attempts=attempts+1,lease_until=? WHERE media_id=?", (lease, job["media_id"]))
        try:
            tags = self.classifier.classify(self.settings.media_dir / job["storage_key"])
            status, message = "succeeded", "写真から候補を見つけました。内容を確かめて選んでください。" if tags else "候補を絞れませんでした。写真に合うタグを選んでください。"
        except Exception:
            tags, status = [], "failed"
            message = "画像分析を利用できませんでした。タグを自分で選んで続けられます。"
        with self.database.transaction(True) as conn:
            conn.execute("UPDATE jobs SET status=?,tags=?,message=?,model_version=?,lease_until=NULL WHERE media_id=? AND status='running' AND lease_until=? AND EXISTS(SELECT 1 FROM media WHERE id=? AND deleted=0)",
                         (status, json.dumps(tags, ensure_ascii=False), message, self.classifier.version, job["media_id"], lease, job["media_id"]))
        return True
