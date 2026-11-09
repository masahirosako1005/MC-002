from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import secrets
import sqlite3
from uuid import uuid4


TAGS = {"mountain": "山の景色", "coast": "海辺", "food": "食事", "cafe": "カフェ", "walk": "街歩き", "fashion": "服・小物", "games": "ボードゲーム", "stay": "宿で過ごす", "nature": "自然"}
ACCOUNTS = (("aoi", "藤沢 葵", "葵", "#A05C42"), ("ren", "高橋 蓮", "蓮", "#436D68"), ("mio", "小野 美緒", "美緒", "#806483"))
TRIPS = (
    {"id": "karuizawa", "title": "軽井沢で森とカフェをめぐる", "area": "軽井沢", "description": "木立を歩き、カフェで旅の続きを話す。", "tags": ["mountain", "nature", "cafe", "walk"], "duration": "day", "budget": 12000, "season_label": "春から秋", "cover_key": "mountain"},
    {"id": "coast-day", "title": "海辺を歩いて昼ごはん", "area": "海辺のまち", "description": "浜を歩いてから、まちの食堂へ。", "tags": ["coast", "food", "walk"], "duration": "day", "budget": 8000, "season_label": "春・秋", "cover_key": "coast"},
    {"id": "town-weekend", "title": "商店街と喫茶店の週末", "area": "街歩きのまち", "description": "小さな店をのぞき、好きな場所を持ち寄る。", "tags": ["walk", "cafe", "fashion", "food"], "duration": "day", "budget": 6000, "season_label": "通年", "cover_key": "cafe"},
    {"id": "lodge-games", "title": "宿でボードゲームを囲む", "area": "森の宿", "description": "散策の後、宿のテーブルに集まる。", "tags": ["games", "stay", "nature", "food"], "duration": "overnight", "budget": 18000, "season_label": "通年", "cover_key": "games"},
)
for trip in TRIPS:
    trip["source_note"] = "ローカルの企画素材。料金は概算で、営業・交通・空席は未確認。"


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return uuid4().hex


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(value, salt):
    return hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,initials TEXT NOT NULL,color TEXT NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL,login_enabled INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf_token TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS communities(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,invite_hash TEXT NOT NULL UNIQUE,invite_code TEXT NOT NULL,cover_key TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memberships(community_id TEXT REFERENCES communities(id),user_id TEXT REFERENCES users(id),role TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('active','left')),PRIMARY KEY(community_id,user_id));
CREATE TABLE IF NOT EXISTS preferences(user_id TEXT PRIMARY KEY REFERENCES users(id),tags TEXT NOT NULL,learn_from_posts INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS grants(user_id TEXT REFERENCES users(id),community_id TEXT REFERENCES communities(id),use_matching INTEGER NOT NULL,display_matching INTEGER NOT NULL,participate INTEGER NOT NULL,PRIMARY KEY(user_id,community_id));
CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),storage_key TEXT NOT NULL UNIQUE,width INTEGER NOT NULL,height INTEGER NOT NULL,sha256 TEXT NOT NULL,deleted INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(media_id TEXT PRIMARY KEY REFERENCES media(id),status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,lease_until TEXT,tags TEXT NOT NULL DEFAULT '[]',message TEXT NOT NULL DEFAULT '',model_version TEXT);
CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),community_id TEXT NOT NULL REFERENCES communities(id),body TEXT NOT NULL,tags TEXT NOT NULL,status TEXT NOT NULL,place_label TEXT NOT NULL,taken_on TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS post_media(post_id TEXT REFERENCES posts(id),media_id TEXT UNIQUE REFERENCES media(id),position INTEGER NOT NULL,PRIMARY KEY(post_id,media_id));
CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY,community_id TEXT NOT NULL REFERENCES communities(id),created_by TEXT NOT NULL REFERENCES users(id),purpose TEXT NOT NULL,trip_id TEXT NOT NULL,tags TEXT NOT NULL,date TEXT,status TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,group_id TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS responses(proposal_id TEXT REFERENCES proposals(id),user_id TEXT REFERENCES users(id),decision TEXT NOT NULL DEFAULT 'pending',PRIMARY KEY(proposal_id,user_id));
CREATE TABLE IF NOT EXISTS ko_groups(id TEXT PRIMARY KEY,proposal_id TEXT UNIQUE NOT NULL REFERENCES proposals(id),community_id TEXT NOT NULL REFERENCES communities(id),purpose TEXT NOT NULL,trip_id TEXT NOT NULL,date TEXT,meeting_point TEXT NOT NULL DEFAULT '',notes TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS group_members(group_id TEXT REFERENCES ko_groups(id),user_id TEXT REFERENCES users(id),role TEXT NOT NULL DEFAULT 'none',note TEXT NOT NULL DEFAULT '',PRIMARY KEY(group_id,user_id));
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    @contextmanager
    def transaction(self, write=False):
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self.connect()
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3, 4, 5):
                raise RuntimeError("Unknown database version")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            if version == 0:
                conn.execute("PRAGMA user_version=1")
        finally:
            conn.close()
        with self.transaction(True) as conn:
            if conn.execute("SELECT 1 FROM settings WHERE key='seeded'").fetchone():
                return
            for username, name, initials, color in ACCOUNTS:
                salt = secrets.token_hex(16)
                password = os.getenv(f"KO_PASSWORD_{username.upper()}", username + "-local-2026")
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?,1)", ("u-" + username, username, name, initials, color, salt, password_hash(password, salt)))
            for number in range(197):
                uid = f"member-{number:03}"
                conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?,0)", (uid, uid, f"旅の会員 {number + 1:03}", "旅", "#748075", "", ""))
            for cid, name, description, code, cover in [("peers", "同期の旅じたく", "同じ時期に入社した仲間と、次の休日を考える。", "KO-PEERS-2026", "mountain"), ("campus", "大学さんぽ部", "学生時代に歩いたまちと、旅の写真。", "KO-CAMPUS-2026", "coast")]:
                conn.execute("INSERT INTO communities VALUES(?,?,?,?,?,?)", (cid, name, description, digest(code), code, cover))
            all_users = [row["id"] for row in conn.execute("SELECT id FROM users ORDER BY login_enabled DESC,id")]
            for index, uid in enumerate(all_users):
                conn.execute("INSERT INTO memberships VALUES('peers',?,?, 'active')", (uid, "owner" if uid == "u-aoi" else "member"))
                tags = ["mountain", "cafe", "walk"] if uid.startswith("u-") else [["mountain", "nature"], ["coast", "food"], ["games", "stay"], ["fashion", "cafe"]][index % 4]
                conn.execute("INSERT INTO preferences(user_id,tags,learn_from_posts) VALUES(?,?,0)", (uid, json.dumps(tags)))
                enabled = int(uid.startswith("u-"))
                conn.execute("INSERT INTO grants VALUES(?,'peers',?,?,?)", (uid, enabled, enabled, enabled))
            conn.execute("INSERT INTO memberships VALUES('campus','u-aoi','owner','active')")
            conn.execute("INSERT INTO grants VALUES('u-aoi','campus',0,0,0)")
            conn.execute("INSERT INTO settings VALUES('seeded','1')")
