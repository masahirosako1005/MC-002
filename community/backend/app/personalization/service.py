import json

from fastapi import HTTPException
from pydantic import ValidationError

from ..marketplace.schedules import schedule_state
from .schemas import Filters, ResumeInput


def unavailable():
    raise HTTPException(404, "開ける画面や講を選んでください。")


class Personalization:
    def __init__(self, database):
        self.db = database

    @staticmethod
    def is_provider(conn, uid):
        return (
            conn.execute(
                "SELECT 1 FROM provider_staff s JOIN providers p ON p.id=s.provider_id "
                "WHERE s.user_id=? AND s.active=1 AND p.active=1",
                (uid,),
            ).fetchone()
            is not None
        )

    @staticmethod
    def community_allowed(conn, uid, cid):
        return (
            conn.execute(
                "SELECT 1 FROM memberships WHERE user_id=? AND community_id=? AND status='active'",
                (uid, cid),
            ).fetchone()
            is not None
        )

    @staticmethod
    def circle_allowed(conn, uid, cid, pid):
        return (
            conn.execute(
                "SELECT 1 FROM travel_parties p JOIN travel_party_members m ON m.party_id=p.id "
                "JOIN circle_rooms r ON r.party_id=p.id "
                "WHERE p.id=? AND m.user_id=? AND p.community_id=? AND p.status='open' "
                "AND (p.ko_group_id IS NULL OR EXISTS(SELECT 1 FROM group_members g "
                "WHERE g.group_id=p.ko_group_id AND g.user_id=?))",
                (pid, uid, cid, uid),
            ).fetchone()
            is not None
        )

    @staticmethod
    def public_areas(conn):
        areas = set()
        for row in conn.execute(
            "SELECT p.body FROM provider_plans p JOIN providers v ON v.id=p.provider_id "
            "WHERE p.status='published' AND v.active=1"
        ):
            plan = json.loads(row[0])
            if schedule_state(plan) not in ("ended", "invalid"):
                areas.add(plan["area"])
        return areas

    def default(self, conn, uid):
        return dict(
            version=0,
            page="provider" if self.is_provider(conn, uid) else "daytrip",
            community_id=None,
            circle_id=None,
            filters=Filters().model_dump(),
        )

    @staticmethod
    def persist(conn, uid, state):
        conn.execute(
            "INSERT INTO user_resume_state(user_id,page,community_id,circle_id,filters_json,version) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET page=excluded.page,"
            "community_id=excluded.community_id,circle_id=excluded.circle_id,"
            "filters_json=excluded.filters_json,version=excluded.version",
            (
                uid,
                state["page"],
                state["community_id"],
                state["circle_id"],
                json.dumps(state["filters"], ensure_ascii=False, sort_keys=True),
                state["version"],
            ),
        )

    def current(self, conn, uid, areas):
        row = conn.execute("SELECT * FROM user_resume_state WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            return self.default(conn, uid)
        raw = dict(
            version=row["version"],
            page=row["page"],
            community_id=row["community_id"],
            circle_id=row["circle_id"],
            filters=json.loads(row["filters_json"]),
        )
        try:
            state = ResumeInput(**raw).model_dump()
        except ValidationError:
            state = self.default(conn, uid) | {"version": row["version"]}
        cid, pid = state["community_id"], state["circle_id"]
        if cid and not self.community_allowed(conn, uid, cid):
            state.update(
                community_id=None, circle_id=None, filters=Filters().model_dump(), page="market"
            )
        elif pid and (not cid or not self.circle_allowed(conn, uid, cid, pid)):
            state.update(circle_id=None, filters=Filters().model_dump())
            if state["page"] == "circles":
                state["page"] = "market"
        if state["page"] == "provider" and not self.is_provider(conn, uid):
            state["page"] = "market"
        if state["filters"]["area"] and state["filters"]["area"] not in areas:
            state["filters"]["area"] = ""
        if state != raw:
            state["version"] += 1
            self.persist(conn, uid, state)
        return state

    def resume(self, uid, data=None):
        # GET may repair a stale reference, so normalization and compare/exchange
        # share a short write transaction. No activity history is stored.
        conflict = False
        with self.db.transaction(True) as conn:
            if not conn.execute(
                "SELECT 1 FROM users WHERE id=? AND login_enabled=1", (uid,)
            ).fetchone():
                raise HTTPException(401, "ログインしてください。")
            areas = self.public_areas(conn)
            current = self.current(conn, uid, areas)
            if data is None:
                return current
            if data["version"] != current["version"]:
                conflict = True
            else:
                cid, pid = data["community_id"], data["circle_id"]
                if cid and not self.community_allowed(conn, uid, cid):
                    unavailable()
                if pid and (not cid or not self.circle_allowed(conn, uid, cid, pid)):
                    unavailable()
                if data["page"] == "provider" and not self.is_provider(conn, uid):
                    unavailable()
                if data["filters"]["area"] and data["filters"]["area"] not in areas:
                    raise HTTPException(422, "公開されている開催エリアを選んでください。")
                if data == current and current["version"] > 0:
                    return current
                current = dict(data, version=current["version"] + 1)
                self.persist(conn, uid, current)
        # A repair must commit even if the caller's old version is rejected.
        if conflict:
            raise HTTPException(
                409, "保存した画面が更新されています。最新の状態を確認してください。"
            )
        return current
