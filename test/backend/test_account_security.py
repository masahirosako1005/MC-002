"""Isolated credential-change, race, rollback, policy, and real-route checks."""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from app import password_policy
from app.account import service as account_module
from app.account.service import AccountService
from app.database import SCHEMA, Database, password_hash, password_matches
from fastapi import HTTPException

OLD = "桜を見にゆく 2026!"
NEW = "森と川を歩こう 2031!"


@pytest.fixture(scope="module")
def initial_hash():
    return password_hash(OLD, "ab" * 16)


@pytest.fixture
def account_db(tmp_path, initial_hash):
    database = Database(tmp_path / "isolated-account.db")
    conn = database.connect()
    try:
        conn.executescript(SCHEMA)
        conn.execute("CREATE TABLE stage_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),csrf_token TEXT,expires_at TEXT)")
    finally:
        conn.close()
    with database.transaction(True) as conn:
        for uid in ("owner", "other"):
            conn.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?,1)",
                         (uid, uid, uid, uid[0], "#123456", "ab" * 16, initial_hash))
            for table in ("sessions", "stage_sessions"):
                for index in (1, 2):
                    conn.execute(f"INSERT INTO {table} VALUES(?,?,?,?)",
                                 (f"{uid}-{table}-{index}", uid, "csrf", "2999-01-01T00:00:00+00:00"))
    return database


def session(database, *, stage=False):
    table = "stage_sessions" if stage else "sessions"
    with database.transaction() as conn:
        return conn.execute(f"SELECT * FROM {table} WHERE user_id='owner' ORDER BY token_hash").fetchone()


def snapshot(database):
    with database.transaction() as conn:
        return {
            table: [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1")]
            for table in ("users", "sessions", "stage_sessions")
        }


@pytest.mark.parametrize("stage", [False, True])
def test_change_invalidates_both_kinds_for_owner_only(account_db, stage):
    before = snapshot(account_db)
    result = AccountService(account_db).change_password(session(account_db, stage=stage), OLD, NEW, stage=stage)
    assert result.model_dump() == {"ok": True, "reauthentication_required": True}
    with account_db.transaction() as conn:
        user = conn.execute("SELECT * FROM users WHERE id='owner'").fetchone()
        assert user["salt"] != "ab" * 16
        assert password_matches(NEW, user["salt"], user["password_hash"])
        assert not password_matches(OLD, user["salt"], user["password_hash"])
        for table in ("sessions", "stage_sessions"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id='owner'").fetchone()[0] == 0
    after = snapshot(account_db)
    for table in before:
        # The unrelated user's credential and all four sessions are unchanged.
        assert [row for row in before[table] if row[0].startswith("other")] == [
            row for row in after[table] if row[0].startswith("other")
        ]


@pytest.mark.parametrize("current,new", [("incorrect", NEW), (OLD, OLD), (OLD, "123456789012"), (OLD, "owner-local-2026")])
def test_rejected_password_does_not_change_or_logout(account_db, current, new):
    before = snapshot(account_db)
    with pytest.raises(HTTPException) as raised:
        AccountService(account_db).change_password(session(account_db), current, new)
    assert raised.value.status_code == 422
    assert snapshot(account_db) == before
    assert current not in raised.value.detail and new not in raised.value.detail


@pytest.mark.parametrize("race", ["logout", "expiry", "disabled", "password", "csrf"])
def test_concurrent_changes_win_over_password_update(account_db, monkeypatch, race):
    active = session(account_db)
    real_hash = account_module.password_hash

    def change_during_hash(value, salt):
        hashed = real_hash(value, salt)
        # This write would fail if the KDF were holding a database transaction.
        with account_db.transaction(True) as conn:
            if race == "logout":
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (active["token_hash"],))
            elif race == "expiry":
                conn.execute("UPDATE sessions SET expires_at='2000-01-01' WHERE token_hash=?", (active["token_hash"],))
            elif race == "disabled":
                conn.execute("UPDATE users SET login_enabled=0 WHERE id='owner'")
            elif race == "password":
                conn.execute("UPDATE users SET password_hash='changed-by-another-request' WHERE id='owner'")
            else:
                conn.execute("UPDATE sessions SET csrf_token='changed' WHERE token_hash=?", (active["token_hash"],))
        return hashed

    monkeypatch.setattr(account_module, "password_hash", change_during_hash)
    with pytest.raises(HTTPException) as raised:
        AccountService(account_db).change_password(active, OLD, NEW)
    assert raised.value.status_code == 401
    with account_db.transaction() as conn:
        assert conn.execute("SELECT salt FROM users WHERE id='owner'").fetchone()[0] == "ab" * 16
        assert conn.execute("SELECT COUNT(*) FROM stage_sessions WHERE user_id='owner'").fetchone()[0] == 2


def test_revocation_failure_rolls_back_password_and_other_deletions(account_db):
    before = snapshot(account_db)
    with account_db.transaction(True) as conn:
        conn.execute("CREATE TRIGGER fail_revoke BEFORE DELETE ON stage_sessions BEGIN SELECT RAISE(ABORT,'test revocation failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        AccountService(account_db).change_password(session(account_db), OLD, NEW)
    assert snapshot(account_db) == before


def test_session_cannot_cross_normal_and_stage_tables(account_db):
    before = snapshot(account_db)
    with pytest.raises(HTTPException) as raised:
        AccountService(account_db).change_password(session(account_db), OLD, NEW, stage=True)
    assert raised.value.status_code == 401
    assert snapshot(account_db) == before


@pytest.mark.parametrize("password,username", [
    ("123456789012", "owner"), ("PASSWORD123456", "owner"),
    ("owner-local-2026", "owner"), ("traveltester2026!", "traveltester"),
    ("ko-no-tabi-jitaku-2026", "owner"), ("nishicity2026", "owner"),
    ("a" * 11, "owner"), ("a" * 129, "owner"),
])
def test_local_policy_rejects_common_contextual_and_out_of_bounds(password, username):
    with pytest.raises(HTTPException) as raised:
        password_policy.validate_new_password(password, username)
    assert raised.value.status_code == 422
    assert password not in raised.value.detail


@pytest.mark.parametrize("password", ["Hazel!River93", "Q" + "x" * 126 + "!", " 前後の空白も含めた長い言葉 ", "owner and a completely different journey"])
def test_policy_accepts_long_phrases_unicode_and_boundary_lengths(password):
    password_policy.validate_new_password(password, "owner")


def test_blocklist_integrity_and_provenance_are_fixed(monkeypatch):
    folder = Path(password_policy.__file__).parent / "account" / "data"
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["derived_entries"] == len(password_policy._COMMON_PASSWORDS) == 46825
    assert hashlib.sha256((folder / provenance["derived_file"]).read_bytes()).hexdigest() == provenance["derived_sha256"]
    assert hashlib.sha256((folder / "LICENSE-SecLists.txt").read_bytes()).hexdigest() == provenance["license_sha256"]
    assert provenance["runtime_network"] is False
    monkeypatch.setattr(Path, "read_bytes", lambda self: b"corrupt")
    with pytest.raises(RuntimeError, match="integrity"):
        password_policy._load_blocklist()


def stage_login(client, username):
    response = client.write("POST", "/stage/login", {"username": username, "password": username + "-local-2026"})
    assert response.status_code == 200, response.text
    data = response.json()
    client.client.headers["Authorization"] = "Bearer " + data["access_token"]
    client.client.headers["X-CSRF-Token"] = data["csrf_token"]
    return data


def test_real_normal_route_reauthenticates_revokes_all_and_preserves_other_user(harness):
    normal = harness.client("aoi")
    other = harness.client("ren")
    stage = harness.client()
    stage_login(stage, "aoi")
    payload = {"current_password": "aoi-local-2026", "new_password": NEW}
    wrong = normal.write("POST", "/account/password", payload | {"current_password": "incorrect"})
    assert wrong.status_code == 422 and normal.get("/me").status_code == 200
    assert normal.write("POST", "/account/password", payload | {"new_password": "123456789012"}).status_code == 422
    assert normal.write("POST", "/account/password", payload | {"new_password": "aoi-local-2026"}).status_code == 422
    response = normal.write("POST", "/account/password", payload)
    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True, "reauthentication_required": True}
    assert "ko_session=" in response.headers["set-cookie"]
    assert normal.get("/me").status_code == stage.get("/me").status_code == 401
    assert other.get("/me").status_code == 200
    assert normal.write("POST", "/login", {"username": "aoi", "password": "aoi-local-2026"}).status_code == 401
    assert normal.write("POST", "/login", {"username": "aoi", "password": NEW}).status_code == 200


def test_real_stage_route_keeps_unrelated_cookie_and_enforces_origin_csrf_schema(harness):
    shared = harness.client("aoi")
    auth = stage_login(shared, "forest")
    cookie_before = dict(shared.client.cookies)
    payload = {"current_password": "forest-local-2026", "new_password": NEW}
    assert shared.write("POST", "/account/password", payload, headers={"Origin": "https://invalid.test"}).status_code == 403
    assert shared.write("POST", "/account/password", payload, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    bad = shared.write("POST", "/account/password", payload | {"user_id": "aoi"})
    assert bad.status_code == 422 and payload["current_password"] not in bad.text and NEW not in bad.text
    shared.client.headers["X-CSRF-Token"] = auth["csrf_token"]
    changed = shared.write("POST", "/account/password", payload)
    assert changed.status_code == 200, changed.text
    assert "set-cookie" not in changed.headers
    assert dict(shared.client.cookies) == cookie_before
    assert shared.get("/me").status_code == 401
    del shared.client.headers["Authorization"]
    assert shared.get("/me").json()["user"]["username"] == "aoi"


def test_registration_uses_same_local_policy_and_password_route_is_rate_bounded(harness):
    client = harness.client()
    for password in ("123456789012", "policy-user2026"):
        response = client.write("POST", "/register", {"username": "policy-user", "password": password, "name": "登録確認"})
        assert response.status_code == 422 and password not in response.text
    registration = client.write("POST", "/register", {"username": "policy-user", "password": NEW, "name": "登録確認"})
    assert registration.status_code == 201, registration.text
    owner = harness.client("aoi")  # Existing fixed seed credentials still work.
    for _ in range(5):
        assert owner.write("POST", "/account/password", {"current_password": "incorrect", "new_password": NEW}).status_code == 422
    limited = owner.write("POST", "/account/password", {"current_password": "incorrect", "new_password": NEW})
    assert limited.status_code == 429 and limited.headers["retry-after"] == "60"
    assert owner.get("/me").status_code == 200
