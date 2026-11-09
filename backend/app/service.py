import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from .clock import SEASON_NAMES, catalog_year, season_at, season_year
from .database import Database
from .collection import TROPHY_IDS, derive_collection
from .seed import CITY, fingerprint, seed_games


SPOT_FIELDS = ("id", "name", "area", "kind", "description", "walk_minutes", "dwell_minutes")
EXPERIENCE_FIELDS = ("id", "spot_id", "title", "season", "description", "month_label", "duration_minutes", "kind")
GAME_FIELDS = ("id", "spot_id", "title", "season", "difficulty", "description", "version")
VISIT_FIELDS = ("id", "spot_id", "spot_name", "visited_at")
ATTEMPT_FIELDS = ("id", "game_id", "title", "season", "status", "score", "hints_used", "created_at", "completed_at")
ACHIEVEMENT_FIELDS = ("id", "title", "description", "earned_at", "season")
PLAN_FIELDS = ("id", "experience_id", "title", "spot_name", "season", "month_label", "reason", "created_at")


def project(row: sqlite3.Row, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: row[field] for field in fields}


def identifier() -> str:
    return uuid4().hex


def require_row(row: sqlite3.Row | None, message: str = "記録が見つかりません。") -> sqlite3.Row:
    if row is None:
        raise HTTPException(404, message)
    return row


def award(connection: sqlite3.Connection, user_id: str, scope: str, title: str,
          description: str, current: datetime, season: str,
          visit_id: str | None = None, attempt_id: str | None = None) -> dict[str, Any]:
    connection.execute(
        "INSERT INTO achievements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(user_id, scope) DO NOTHING",
        (identifier(), user_id, scope, title, description, current.isoformat(), season, visit_id, attempt_id),
    )
    row = connection.execute("SELECT * FROM achievements WHERE user_id=? AND scope=?", (user_id, scope)).fetchone()
    return project(row, ACHIEVEMENT_FIELDS)


class JourneyService:
    def __init__(self, database: Database):
        self.database = database

    def collection(self, user_id: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction() as connection:
            visits = [dict(row) for row in connection.execute(
                "SELECT spot_id,visited_at,visit_day FROM visits WHERE user_id=? ORDER BY visited_at,id", (user_id,))]
            attempts = [dict(row) for row in connection.execute(
                "SELECT a.status,a.completed_at,g.spot_id,g.season,g.difficulty FROM attempts a "
                "JOIN games g ON g.id=a.game_id WHERE a.user_id=? AND a.status='completed' ORDER BY a.completed_at,a.id", (user_id,))]
            preference = connection.execute("SELECT trophy_id FROM collection_preferences WHERE user_id=?", (user_id,)).fetchone()
            return derive_collection(visits, attempts, preference["trophy_id"] if preference else None, current)

    def collection_target(self, user_id: str, trophy_id: str | None, current: datetime) -> dict[str, Any]:
        if trophy_id is not None and trophy_id not in TROPHY_IDS:
            raise HTTPException(422, "次に狙うしるしを一覧から選んでください。")
        with self.database.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO collection_preferences(user_id,trophy_id,updated_at) VALUES (?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET trophy_id=excluded.trophy_id,updated_at=excluded.updated_at",
                (user_id, trophy_id, current.isoformat()),
            )
        return {"target_id": trophy_id}

    def catalog(self, current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            seed_games(connection, current)
            games = [project(row, GAME_FIELDS) for row in connection.execute("SELECT * FROM games ORDER BY season, difficulty")
                     if row["season_year"] == catalog_year(current, row["season"])]
            return {"city": CITY, "season": season_at(current),
                    "spots": [project(row, SPOT_FIELDS) for row in connection.execute("SELECT * FROM spots ORDER BY rowid")],
                    "experiences": [project(row, EXPERIENCE_FIELDS) for row in connection.execute("SELECT * FROM experiences WHERE enabled=1 ORDER BY rowid")],
                    "games": games}

    def journal(self, user_id: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            return {
                "visits": [project(row, VISIT_FIELDS) for row in connection.execute("SELECT * FROM visits WHERE user_id=? ORDER BY visited_at DESC, id", (user_id,))],
                "attempts": [project(row, ATTEMPT_FIELDS) for row in connection.execute("SELECT a.*,g.season FROM attempts a JOIN games g ON g.id=a.game_id WHERE a.user_id=? ORDER BY a.created_at DESC,a.id", (user_id,))],
                "achievements": [project(row, ACHIEVEMENT_FIELDS) for row in connection.execute("SELECT * FROM achievements WHERE user_id=? ORDER BY earned_at DESC, id", (user_id,))],
                "plans": [project(row, PLAN_FIELDS) for row in connection.execute("SELECT * FROM plans WHERE user_id=? ORDER BY created_at DESC, id", (user_id,))],
            }

    def visit(self, user_id: str, spot_id: str, code: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            spot = require_row(connection.execute("SELECT * FROM spots WHERE id=?", (spot_id,)).fetchone(), "場所が見つかりません。")
            if not secrets.compare_digest(spot["code_hash"], fingerprint(code.upper())):
                raise HTTPException(403, "訪問コードが一致しません。現地のしおりを確かめてください。")
            connection.execute(
                "INSERT INTO visits VALUES (?, ?, ?, ?, ?, ?, 'printed-code') ON CONFLICT(user_id, spot_id, visit_day) DO NOTHING",
                (identifier(), user_id, spot_id, spot["name"], current.isoformat(), current.date().isoformat()),
            )
            visit = connection.execute("SELECT * FROM visits WHERE user_id=? AND spot_id=? AND visit_day=?", (user_id, spot_id, current.date().isoformat())).fetchone()
            season = season_at(current)
            award(connection, user_id, f"visit:{spot_id}:{season}:{season_year(current)}:v1",
                  f"{SEASON_NAMES[season]}の{spot['name']}", "現地のしおりで訪問を記録した。", current, season, visit_id=visit["id"])
            return project(visit, VISIT_FIELDS)

    @staticmethod
    def validate_game(game: sqlite3.Row, current: datetime) -> None:
        if game["season"] != season_at(current) or game["season_year"] != season_year(current):
            raise HTTPException(409, "この謎の季節は終了したか、まだ始まっていません。今の季節の謎を選んでください。")

    @staticmethod
    def require_visit(connection: sqlite3.Connection, user_id: str, spot_id: str, current: datetime) -> sqlite3.Row:
        visit = connection.execute("SELECT * FROM visits WHERE user_id=? AND spot_id=? AND visit_day=?", (user_id, spot_id, current.date().isoformat())).fetchone()
        if visit is None:
            raise HTTPException(409, "今日の訪問を記録してから挑戦してください。")
        return visit

    def start_attempt(self, user_id: str, game_id: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            seed_games(connection, current)
            game = require_row(connection.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone(), "謎が見つかりません。")
            self.validate_game(game, current)
            visit = self.require_visit(connection, user_id, game["spot_id"], current)
            connection.execute(
                "INSERT INTO attempts(id,user_id,game_id,visit_id,title,status,created_at) VALUES(?,?,?,?,?,'active',?) "
                "ON CONFLICT(user_id,game_id) WHERE status='active' DO UPDATE SET visit_id=excluded.visit_id",
                (identifier(), user_id, game_id, visit["id"], game["title"], current.isoformat()),
            )
            attempt = connection.execute("SELECT * FROM attempts WHERE user_id=? AND game_id=? AND status='active'", (user_id, game_id)).fetchone()
            return {"id": attempt["id"], "game_id": game_id, "status": attempt["status"],
                    "hints_used": attempt["hints_used"], "puzzle": json.loads(game["puzzle_json"])}

    @staticmethod
    def owned_attempt(connection: sqlite3.Connection, user_id: str, attempt_id: str) -> sqlite3.Row:
        return require_row(connection.execute("SELECT * FROM attempts WHERE id=? AND user_id=?", (attempt_id, user_id)).fetchone())

    def hint(self, user_id: str, attempt_id: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            attempt = self.owned_attempt(connection, user_id, attempt_id)
            game = connection.execute("SELECT * FROM games WHERE id=?", (attempt["game_id"],)).fetchone()
            if attempt["status"] == "completed":
                raise HTTPException(409, "この謎は解き終わっています。新しく挑戦してください。")
            self.validate_game(game, current)
            self.require_visit(connection, user_id, game["spot_id"], current)
            connection.execute("UPDATE attempts SET hints_used=1 WHERE id=?", (attempt_id,))
            return {"hint": game["hint"], "hints_used": 1}

    def answer(self, user_id: str, attempt_id: str, values: list[int], current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            attempt = self.owned_attempt(connection, user_id, attempt_id)
            game = connection.execute("SELECT * FROM games WHERE id=?", (attempt["game_id"],)).fetchone()
            if attempt["status"] == "completed":
                achieved = connection.execute("SELECT * FROM achievements WHERE user_id=? AND scope=?", (user_id, f"game:{game['id']}")).fetchone()
                return {"correct": True, "score": attempt["score"], "achievement": project(achieved, ACHIEVEMENT_FIELDS), "message": "水路に水が届きました。旅の手帳に記録しました。"}
            self.validate_game(game, current)
            self.require_visit(connection, user_id, game["spot_id"], current)
            if values != json.loads(game["answer_json"]):
                connection.execute("UPDATE attempts SET wrong_answers=MIN(wrong_answers+1, 100) WHERE id=?", (attempt_id,))
                return {"correct": False, "score": None, "achievement": None, "message": "まだ水量が合いません。手掛かりの条件を一つずつ確かめてください。"}
            base_score = 100 if game["difficulty"] == "beginner" else 200
            score = max(10, base_score - attempt["hints_used"] * 20 - attempt["wrong_answers"] * 5)
            connection.execute("UPDATE attempts SET status='completed',score=?,completed_at=?,answer_json=? WHERE id=?", (score, current.isoformat(), json.dumps(values), attempt_id))
            achieved = award(connection, user_id, f"game:{game['id']}", game["title"],
                             f"{game['version']}の謎を解き、水路に水を届けた。", current, game["season"], attempt_id=attempt_id)
            return {"correct": True, "score": score, "achievement": achieved, "message": "水路に水が届きました。旅の手帳に記録しました。"}

    def leaderboard(self, game_id: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            require_row(connection.execute("SELECT id FROM games WHERE id=?", (game_id,)).fetchone(), "謎が見つかりません。")
            rows = connection.execute(
                "SELECT u.nickname, MAX(a.score) AS score FROM attempts a JOIN users u ON u.id=a.user_id "
                "WHERE a.game_id=? AND a.status='completed' GROUP BY a.user_id,u.nickname ORDER BY score DESC,u.nickname LIMIT 50", (game_id,),
            ).fetchall()
            previous_score = None
            rank = 0
            entries = []
            for position, row in enumerate(rows, start=1):
                if row["score"] != previous_score:
                    rank = position
                entries.append({"rank": rank, "nickname": row["nickname"], "score": row["score"]})
                previous_score = row["score"]
            return {"entries": entries, "game_id": game_id}

    def recommendations(self, user_id: str, minutes: int, season: str, interest: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction() as connection:
            experiences = connection.execute("SELECT * FROM experiences WHERE (season=? OR season='all') AND enabled=1 ORDER BY rowid", (season,)).fetchall()
            visited = {row[0] for row in connection.execute("SELECT DISTINCT spot_id FROM visits WHERE user_id=?", (user_id,))}
            items = []
            for experience in experiences:
                spot = connection.execute("SELECT * FROM spots WHERE id=?", (experience["spot_id"],)).fetchone()
                if interest != "all" and spot["kind"] != interest:
                    continue
                travel_minutes = spot["walk_minutes"] * 2
                buffer_minutes = 10
                total_minutes = travel_minutes + experience["duration_minutes"] + buffer_minutes
                if total_minutes > minutes:
                    continue
                is_current_season = season == season_at(current)
                if is_current_season:
                    arrival = current + timedelta(minutes=spot["walk_minutes"])
                    departure = arrival + timedelta(minutes=experience["duration_minutes"])
                    if str(current.isoweekday()) in spot["closed_weekdays"].split(",") or arrival.date() != current.date() or departure.date() != current.date():
                        continue
                    if arrival.hour < spot["open_hour"] or departure.hour * 60 + departure.minute > spot["close_hour"] * 60:
                        continue
                relationship = "前に訪れた場所を、別の体験から。" if spot["id"] in visited else "まだ訪れていない場所へ。"
                timing = "今から出発する場合。" if is_current_season else f"{SEASON_NAMES[season]}の次の旅の候補。開催日と営業時間は出発前に確認。"
                reason = f"{relationship}{timing}会議館から往復{travel_minutes}分＋体験{experience['duration_minutes']}分＋余裕{buffer_minutes}分。"
                items.append({"experience": project(experience, EXPERIENCE_FIELDS), "spot": project(spot, SPOT_FIELDS),
                              "total_minutes": total_minutes, "travel_minutes": travel_minutes, "buffer_minutes": buffer_minutes, "reason": reason})
            items.sort(key=lambda item: (item["spot"]["id"] not in visited, item["total_minutes"], item["experience"]["id"]))
            return {"items": items, "reason": f"会議館を出発して戻るまで{minutes}分以内の候補です。" if items else "この時間・季節・営業時間では往復できる候補がありません。時間や季節を変えてください。"}

    def save_plan(self, user_id: str, experience_id: str, reason: str, current: datetime) -> dict[str, Any]:
        with self.database.transaction(write=True) as connection:
            experience = require_row(connection.execute("SELECT e.*,s.name AS spot_name FROM experiences e JOIN spots s ON s.id=e.spot_id WHERE e.id=? AND e.enabled=1", (experience_id,)).fetchone(), "この体験は現在選べません。")
            connection.execute(
                "INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id, experience_id) DO NOTHING",
                (identifier(), user_id, experience_id, experience["title"], experience["spot_name"], experience["season"], experience["month_label"], reason, current.isoformat()),
            )
            return project(connection.execute("SELECT * FROM plans WHERE user_id=? AND experience_id=?", (user_id, experience_id)).fetchone(), PLAN_FIELDS)

    def delete_plan(self, user_id: str, plan_id: str) -> dict[str, bool]:
        with self.database.transaction(write=True) as connection:
            result = connection.execute("DELETE FROM plans WHERE id=? AND user_id=?", (plan_id, user_id))
            if not result.rowcount:
                raise HTTPException(404, "候補が見つかりません。")
            return {"ok": True}
