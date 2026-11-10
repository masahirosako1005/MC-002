"""Create a small public welcome image from the existing fictional source asset."""
from pathlib import Path
import hashlib
import json
from io import BytesIO
from PIL import Image, ImageOps

frontend = Path(__file__).resolve().parents[1]
source = frontend.parent / "assets" / "woodland.png"
before = hashlib.sha256(source.read_bytes()).hexdigest()
with Image.open(source) as original:
    picture = ImageOps.fit(original.convert("RGB"), (640, 320), Image.Resampling.LANCZOS, centering=(0.5, 0.72))
    buffer = BytesIO()
    picture.save(buffer, "WEBP", quality=68, method=6)
payload = buffer.getvalue()
output_hash = hashlib.sha256(payload).hexdigest()
destination = frontend / "public" / f"welcome-woodland-{output_hash[:12]}.webp"
destination.parent.mkdir(exist_ok=True)
destination.write_bytes(payload)
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
report = {"source": "assets/woodland.png", "source_sha256": before, "output": "frontend/public/" + destination.name, "width": 640, "height": 320, "quality": 68, "bytes": destination.stat().st_size, "sha256": output_hash, "fictional_source": True, "metadata_retained": False}
(frontend / "scripts" / "welcome-image-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"bytes": report["bytes"], "width": 640, "height": 320}))
