import { useCallback, useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { ErrorBox } from "./ui";
import "./jizo-camera.css";

function JizoFigure() {
  const [imageFailed, setImageFailed] = useState(false);
  return imageFailed ? (
    <svg
      className="jizo-figure"
      viewBox="0 0 180 240"
      aria-label="現地の印から現れたお地蔵さん"
    >
      <ellipse cx="90" cy="225" rx="66" ry="12" fill="#393a2c38" />
      <path
        d="M44 204q3-96 46-96t46 96q-46 31-92 0"
        fill="#9d9f8e"
        stroke="#535d50"
        strokeWidth="3"
      />
      <circle
        cx="90"
        cy="68"
        r="44"
        fill="#bbbcaa"
        stroke="#535d50"
        strokeWidth="3"
      />
      <path
        d="M67 67q8 8 15 0m16 0q8 8 15 0m-31 20q8 7 16 0"
        fill="none"
        stroke="#535d50"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="m51 112 39 17 39-17-12 49H64Z"
        fill="#a64432"
        stroke="#773b30"
        strokeWidth="2"
      />
      <path
        d="M90 143q-23 30-10 42l10-10 10 10q13-12-10-42"
        fill="#c8c6af"
        stroke="#535d50"
        strokeWidth="2"
      />
    </svg>
  ) : (
    <img
      className="jizo-figure"
      src="/assets/jizo-ar.png"
      alt="現地の印から現れたお地蔵さん"
      onError={() => setImageFailed(true)}
      width={180}
      height={240}
    />
  );
}

export default function JizoCamera({
  onScanned,
  disabled,
}: {
  onScanned: (code: string) => void;
  disabled: boolean;
}) {
  const [active, setActive] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [found, setFound] = useState(false);
  const [photo, setPhoto] = useState("");
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const live = useRef(true);
  const foundRef = useRef(false);
  const scanCallback = useRef(onScanned);
  const captureGeneration = useRef(0);
  useEffect(() => {
    scanCallback.current = onScanned;
  }, [onScanned]);
  const stop = useCallback(() => {
    captureGeneration.current++;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    if (video.current) video.current.srcObject = null;
    if (live.current) {
      setActive(false);
      setStarting(false);
    }
  }, []);
  useEffect(() => {
    live.current = true;
    const hide = () => {
      if (document.hidden) stop();
    };
    document.addEventListener("visibilitychange", hide);
    window.addEventListener("pagehide", stop);
    return () => {
      live.current = false;
      stop();
      document.removeEventListener("visibilitychange", hide);
      window.removeEventListener("pagehide", stop);
    };
  }, [stop]);
  const scan = useCallback(
    (source: CanvasImageSource, width: number, height: number) => {
      if (!width || !height || foundRef.current) return false;
      const surface = canvas.current ?? document.createElement("canvas");
      canvas.current = surface;
      const scale = Math.min(1, 720 / Math.max(width, height));
      surface.width = Math.max(1, Math.round(width * scale));
      surface.height = Math.max(1, Math.round(height * scale));
      const context = surface.getContext("2d", { willReadFrequently: true });
      if (!context) return false;
      context.drawImage(source, 0, 0, surface.width, surface.height);
      const pixels = context.getImageData(0, 0, surface.width, surface.height);
      const decoded = jsQR(pixels.data, pixels.width, pixels.height, {
        inversionAttempts: "dontInvert",
      });
      const match = decoded?.data.match(/^KOU-OMIKUJI:([0-9]{6})$/);
      if (!match) return false;
      foundRef.current = true;
      const liveCamera = source === video.current;
      if (!liveCamera) setPhoto(surface.toDataURL("image/jpeg", 0.82));
      setFound(true);
      setError("");
      if (!liveCamera) stop();
      scanCallback.current(match[1]);
      return true;
    },
    [stop],
  );
  useEffect(() => {
    if (!active || disabled || found) return undefined;
    const timer = window.setInterval(() => {
      if (document.hidden || !video.current || video.current.readyState < 2)
        return;
      try {
        scan(
          video.current,
          video.current.videoWidth,
          video.current.videoHeight,
        );
      } catch {
        setError(
          "カメラ画像を読み取れません。写真を選んで読み取ることもできます。",
        );
        stop();
      }
    }, 300);
    return () => window.clearInterval(timer);
  }, [active, disabled, found, scan, stop]);
  useEffect(() => {
    if (disabled) stop();
  }, [disabled, stop]);
  async function start() {
    if (starting || disabled) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "この環境ではカメラを開けません。QRの写真を選んでください。カメラにはHTTPSまたはlocalhostが必要です。",
      );
      return;
    }
    stop();
    const generation = captureGeneration.current;
    setStarting(true);
    setError("");
    setFound(false);
    setPhoto("");
    foundRef.current = false;
    scanCallback.current("");
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (
        !live.current ||
        generation !== captureGeneration.current ||
        document.hidden
      ) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = media;
      if (video.current) {
        video.current.srcObject = media;
        await video.current.play();
      }
      if (live.current && generation === captureGeneration.current)
        setActive(true);
    } catch {
      if (live.current && generation === captureGeneration.current) {
        stop();
        setError(
          "カメラを使えません。ブラウザーのカメラ許可を確認するか、QRの写真を選んでください。",
        );
      }
    } finally {
      if (live.current && generation === captureGeneration.current)
        setStarting(false);
    }
  }
  async function readPhoto(file: File | undefined) {
    if (!file || disabled) return;
    stop();
    const generation = captureGeneration.current;
    if (!file.type.startsWith("image/") || file.size > 12 * 1024 * 1024) {
      setError("12MB以下の画像を選んでください。");
      return;
    }
    setError("");
    setFound(false);
    setPhoto("");
    foundRef.current = false;
    scanCallback.current("");
    try {
      const bitmap = await createImageBitmap(file);
      try {
        if (!live.current || generation !== captureGeneration.current) return;
        if (!scan(bitmap, bitmap.width, bitmap.height))
          setError(
            "この写真では現地おみくじのQRを読み取れません。印を大きく、明るく写してください。",
          );
      } finally {
        bitmap.close();
      }
    } catch {
      if (live.current && generation === captureGeneration.current)
        setError("画像を開けません。JPEGやPNGで撮り直してください。");
    }
  }
  return (
    <section className="jizo-camera" aria-label="現地の印を読み取る">
      <div className="jizo-view">
        <video
          ref={video}
          autoPlay
          muted
          playsInline
          aria-label="現地QRを読み取るカメラ映像"
        />
        {photo && (
          <img
            className="jizo-scanned-photo"
            src={photo}
            alt="読み取った現地の印"
          />
        )}
        {!active && !photo && (
          <div className="jizo-camera-idle">
            <span aria-hidden="true">⌗</span>
            <p>現地の印にカメラを向ける</p>
          </div>
        )}
        {active && !found && (
          <div className="jizo-scan-guide" aria-hidden="true" />
        )}
        {found && (
          <div className="jizo-overlay">
            <JizoFigure />
            <strong>お地蔵さんが現れました</strong>
          </div>
        )}
      </div>
      <div className="jizo-camera-actions">
        <button
          type="button"
          className="button primary"
          disabled={starting || disabled}
          onClick={() => {
            if (active) stop();
            else void start();
          }}
        >
          {starting
            ? "カメラを準備中…"
            : active
              ? "カメラを止める"
              : "カメラで現地の印を読む"}
        </button>
        <label className="jizo-photo-input">
          QRの写真を読み取る
          <input
            type="file"
            accept="image/*"
            capture="environment"
            disabled={disabled || starting}
            onChange={(event) => {
              void readPhoto(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </label>
      </div>
      <p className="omikuji-help">
        映像と写真は端末内だけで読み取ります。保存・送信しません。読み取り後に「お地蔵さんをスキャン」を押すと今月の結果が確定します。
      </p>
      <ErrorBox message={error} />
    </section>
  );
}
