from dataclasses import dataclass, field
from pathlib import Path
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    db_path: Path = field(default_factory=lambda: Path(os.environ.get(
        "APP_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "journal.sqlite3")
    )))
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        value.strip().rstrip("/") for value in os.environ.get(
            "APP_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
        ).split(",") if value.strip()
    ))
    static_dir: Path | None = field(default_factory=lambda: (
        Path(os.environ["STATIC_DIR"]) if os.environ.get("STATIC_DIR") else None
    ))
    secure_cookie: bool = field(default_factory=lambda: os.environ.get("APP_COOKIE_SECURE") == "1")
    session_days: int = 180
    max_body_bytes: int = 16_384
    writes_per_minute: int = 120
    sessions_per_minute: int = 20
    recoveries_per_minute: int = 5

    def __post_init__(self) -> None:
        if not self.allowed_origins:
            raise ValueError("At least one allowed origin is required")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("Allowed origins must be complete HTTP origins without paths")

    @property
    def allowed_hosts(self) -> set[str]:
        return {urlsplit(origin).netloc.lower() for origin in self.allowed_origins}
