"""Read-only audit of the running local database; outputs counts/booleans only.

Run inside the application container via stdin. Never changes accounts, sessions,
preferences, fixtures, WAL settings, or volumes. This is an inspection, not a
restart/persistence test.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import Settings
from app.circles.discovery import Discovery


class ReadOnlyDatabase:
    def __init__(self, path):
        self.path = path

    @contextmanager
    def transaction(self, write=False):
        if write:
            raise AssertionError("Audit forbids writes")
        conn = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        try:
            yield conn
        finally:
            conn.rollback()
            conn.close()


db = ReadOnlyDatabase(Settings().db_path.resolve())
discovery = Discovery(db)
with db.transaction() as conn:
    schema = conn.execute("PRAGMA user_version").fetchone()[0]
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    durable_categories = {
        "accounts": "users", "preferences": "preferences", "permissions": "grants",
        "circles": "travel_parties", "saved_candidates": "circle_candidate_cards",
        "media": "media", "posts": "posts", "visits": "journal_visits",
        "anniversaries": "occasions", "reflections": "reflection_sessions",
    }
    counts = {name: conn.execute('SELECT COUNT(*) FROM "' + table + '"').fetchone()[0]
              for name, table in durable_categories.items() if table in tables}
    users = [dict(row) for row in conn.execute(
        "SELECT DISTINCT u.id FROM users u JOIN memberships m ON m.user_id=u.id "
        "WHERE u.login_enabled=1 AND m.status='active' ORDER BY u.id")]
    groups = {}
    personal_sets = set()
    for user in users:
        uid = user["id"]
        pref = conn.execute("SELECT tags FROM preferences WHERE user_id=?", (uid,)).fetchone()
        if pref:
            personal_sets.add(tuple(sorted(json.loads(pref[0]))))
        for row in conn.execute("SELECT community_id FROM memberships WHERE user_id=? AND status='active'", (uid,)):
            groups.setdefault(row[0], []).append(uid)
    context_tables = [name for name in tables if any(token in name for token in ("navigation", "resume", "home_state"))]

comparisons = []
for cid, members in groups.items():
    if len(members) < 2:
        continue
    results = [discovery.discover(uid, cid) for uid in members]
    orders = [tuple(item["plan"]["id"] for item in result["items"]) for result in results]
    scores = [tuple((item["plan"]["id"], item["score"]) for item in result["items"]) for result in results]
    comparisons.append({
        "account_count": len(members),
        "profiles_used_count": sum(result["context"]["profile_used"] for result in results),
        "distinct_candidate_orders": len(set(orders)),
        "distinct_candidate_score_sets": len(set(scores)),
        "candidate_counts": [len(order) for order in orders],
        "same_order_is_not_permission_failure": True,
    })

print(json.dumps({
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "mode": "sqlite-read-only-service-inspection",
    "schema_version": schema,
    "journal_mode": journal_mode,
    "database_file_present": db.path.is_file(),
    "durable_row_counts": counts,
    "active_login_accounts_with_community": len(users),
    "distinct_confirmed_preference_sets": len(personal_sets),
    "same_community_comparisons": comparisons,
    "navigation_state_table_count": len(context_tables),
    "limitations": ["No private text, tag values, identifiers, or credentials exported", "No restart performed", "Identical current preferences may legitimately produce identical rankings"],
}, ensure_ascii=False, indent=2))
