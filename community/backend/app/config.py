import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.getenv("APP_DB_PATH", str(ROOT / "data/community.db"))))
    media_dir: Path = field(default_factory=lambda: Path(os.getenv("MEDIA_DIR", str(ROOT / "data/media"))))
    model_dir: Path = field(default_factory=lambda: Path(os.getenv("MODEL_DIR", str(ROOT.parent / "models"))))
    seed_asset_dir: Path | None = field(default_factory=lambda: Path(os.environ["SEED_ASSET_DIR"]) if os.getenv("SEED_ASSET_DIR") else None)
    static_dir: Path | None = field(default_factory=lambda: Path(os.environ["STATIC_DIR"]) if os.getenv("STATIC_DIR") else None)
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: tuple(value.strip().rstrip("/") for value in os.getenv("APP_ALLOWED_ORIGINS", "http://localhost:8001,http://127.0.0.1:8001").split(",")))
    secure_cookie: bool = field(default_factory=lambda: os.getenv("APP_COOKIE_SECURE") == "1")
    worker_enabled: bool = False
    max_image_bytes: int = 12 * 1024 * 1024
    max_pixels: int = 20_000_000

    def __post_init__(self):
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("Origin must be an HTTP origin without a path")

    @property
    def allowed_hosts(self):
        return {urlsplit(origin).netloc.lower() for origin in self.allowed_origins}
