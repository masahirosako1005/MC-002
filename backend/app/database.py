from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from collections.abc import Iterator

from .seed import seed_games, seed_static


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, nickname TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
    csrf_token TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recovery_codes (
    user_id TEXT PRIMARY KEY REFERENCES users(id), code_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS spots (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, area TEXT NOT NULL, kind TEXT NOT NULL,
    description TEXT NOT NULL, walk_minutes INTEGER NOT NULL CHECK(walk_minutes >= 0),
    dwell_minutes INTEGER NOT NULL CHECK(dwell_minutes > 0), code_hash TEXT NOT NULL,
    open_hour INTEGER NOT NULL, close_hour INTEGER NOT NULL, closed_weekdays TEXT NOT NULL,
    CHECK(open_hour < close_hour)
);
CREATE TABLE IF NOT EXISTS experiences (
    id TEXT PRIMARY KEY, spot_id TEXT NOT NULL REFERENCES spots(id), title TEXT NOT NULL,
    season TEXT NOT NULL, description TEXT NOT NULL, month_label TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0), kind TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1))
);
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY, spot_id TEXT NOT NULL REFERENCES spots(id), title TEXT NOT NULL,
    season TEXT NOT NULL, difficulty TEXT NOT NULL, description TEXT NOT NULL,
    version TEXT NOT NULL, season_year INTEGER NOT NULL, puzzle_json TEXT NOT NULL,
    answer_json TEXT NOT NULL, hint TEXT NOT NULL,
    UNIQUE(spot_id, season, difficulty, version)
);
CREATE TABLE IF NOT EXISTS visits (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
    spot_id TEXT NOT NULL REFERENCES spots(id), spot_name TEXT NOT NULL,
    visited_at TEXT NOT NULL, visit_day TEXT NOT NULL, evidence TEXT NOT NULL,
    UNIQUE(user_id, spot_id, visit_day)
);
CREATE TABLE IF NOT EXISTS attempts (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
    game_id TEXT NOT NULL REFERENCES games(id), visit_id TEXT NOT NULL REFERENCES visits(id),
    title TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','completed')),
    hints_used INTEGER NOT NULL DEFAULT 0 CHECK(hints_used IN (0,1)),
    wrong_answers INTEGER NOT NULL DEFAULT 0 CHECK(wrong_answers >= 0),
    score INTEGER CHECK(score BETWEEN 0 AND 200), created_at TEXT NOT NULL,
    completed_at TEXT, answer_json TEXT,
    CHECK((status='active' AND score IS NULL AND completed_at IS NULL) OR
          (status='completed' AND score IS NOT NULL AND completed_at IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_attempt ON attempts(user_id, game_id) WHERE status='active';
CREATE INDEX IF NOT EXISTS attempts_ranking ON attempts(game_id, status, score);
CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), scope TEXT NOT NULL,
    title TEXT NOT NULL, description TEXT NOT NULL, earned_at TEXT NOT NULL, season TEXT NOT NULL,
    visit_id TEXT REFERENCES visits(id), attempt_id TEXT REFERENCES attempts(id),
    CHECK((visit_id IS NOT NULL) != (attempt_id IS NOT NULL)), UNIQUE(user_id, scope)
);
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
    experience_id TEXT NOT NULL REFERENCES experiences(id), title TEXT NOT NULL,
    spot_name TEXT NOT NULL, season TEXT NOT NULL, month_label TEXT NOT NULL,
    reason TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id, experience_id)
);
PRAGMA user_version = 2;
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.execute("PRAGMA synchronous = FULL")
        except BaseException:
            connection.close()
            raise
        return connection

    def initialize(self, current: datetime) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = self.connect()
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] not in (0, 1, 2):
                raise RuntimeError("Unsupported database schema version")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA)
            connection.execute("BEGIN IMMEDIATE")
            seed_static(connection)
            seed_games(connection, current)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def backup(self, destination: Path) -> None:
        if destination.resolve() == self.path.resolve():
            raise ValueError("Backup must use a different destination")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise sqlite3.DatabaseError("Backup integrity check failed")
            if target.execute("PRAGMA foreign_key_check").fetchall():
                raise sqlite3.DatabaseError("Backup foreign key check failed")
        finally:
            target.close()
            source.close()
