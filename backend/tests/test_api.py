import asyncio
from datetime import datetime, timedelta
import json
import sqlite3

import httpx
import pytest

from app.clock import JST
from app.config import Settings
from app.main import create_app
from conftest import Client


def test_catalog_has_four_seasons_distinct_difficulties_and_no_secrets(harness):
    response = harness.client.get("/catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["season"] == "autumn"
    assert len(catalog["games"]) == 8
    assert {item["kind"] for item in catalog["spots"]} == {"gate", "shrine", "coast", "conference"}
    assert {item["season"] for item in catalog["games"]} == {"spring", "summer", "autumn", "winter"}
    assert "GATE-314" not in response.text
    assert "answer_json" not in response.text and "code_hash" not in response.text
    assert "csrf_token" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_full_journey_and_server_scoring(harness):
    assert harness.start().status_code == 409
    assert harness.visit().status_code == 200
    attempt = harness.start().json()
    wrong = harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [0, 0, 0]})
    assert wrong.json()["correct"] is False
    assert wrong.json()["score"] is None
    hinted = harness.client.post(f"/attempts/{attempt['id']}/hint").json()
    assert hinted["hints_used"] == 1
    assert harness.client.post(f"/attempts/{attempt['id']}/hint").json() == hinted
    answer = harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]})
    assert answer.status_code == 200, answer.text
    assert answer.json()["score"] == 75
    assert answer.json()["achievement"]["season"] == "autumn"
    saved = harness.client.post("/plans", {"experience_id": "gate-winter", "reason": "冬の灯りの水路を歩く"})
    assert saved.status_code == 200
    journal = harness.client.get("/journal").json()
    assert len(journal["visits"]) == 1
    assert len(journal["achievements"]) == 2
    assert journal["attempts"][0]["status"] == "completed"
    assert journal["plans"][0]["reason"] == "冬の灯りの水路を歩く"


def test_duplicate_and_concurrent_submission_are_atomic(harness):
    initial_visit = harness.visit().json()
    assert harness.visit().json() == initial_visit
    attempt = harness.start().json()
    assert harness.start().json()["id"] == attempt["id"]

    async def submit_concurrently():
        return await asyncio.gather(*[harness.client.client.post(f"/api/attempts/{attempt['id']}/answer", json={"values": [1, 2, 3]}) for _ in range(6)])

    results = harness.runner.run(submit_concurrently())
    assert all(response.status_code == 200 for response in results)
    assert len({response.json()["achievement"]["id"] for response in results}) == 1
    original = results[0].json()
    assert harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [5, 5, 5]}).json() == original
    journal = harness.client.get("/journal").json()
    assert len(journal["attempts"]) == 1
    assert len(journal["achievements"]) == 2


def test_ownership_and_authentication_boundaries(harness):
    harness.visit()
    attempt = harness.start().json()
    plan = harness.client.post("/plans", {"experience_id": "gate-winter", "reason": "冬に歩く"}).json()
    other = harness.another()
    assert other.get("/journal").json() == {"visits": [], "attempts": [], "achievements": [], "plans": []}
    assert other.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]}).status_code == 404
    assert other.post(f"/attempts/{attempt['id']}/hint").status_code == 404
    assert other.request("DELETE", f"/plans/{plan['id']}", headers={"Content-Type": "application/json"}).status_code == 404
    assert other.post("/attempts", {"game_id": attempt["game_id"]}).status_code == 409
    anonymous = Client(harness.runner, harness.app)
    try:
        assert anonymous.get("/journal").status_code == 401
        assert anonymous.post("/plans", {"experience_id": "gate-winter", "reason": "冬"}).status_code == 401
    finally:
        anonymous.close()


@pytest.mark.parametrize("body", [
    {"values": [1, 2, 3], "score": 999},
    {"values": [1, 2, 3], "user_id": "someone"},
    {"values": [True, 2, 3]}, {"values": [1.0, 2, 3]},
    {"values": ["1", 2, 3]}, {"values": [6, 2, 3]}, {"values": [1, 2]},
])
def test_forged_or_invalid_answer_rejected(harness, body):
    harness.visit()
    attempt = harness.start().json()
    response = harness.client.post(f"/attempts/{attempt['id']}/answer", body)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert harness.client.get("/journal").json()["attempts"][0]["status"] == "active"


def test_csrf_origin_json_host_and_cookie(harness):
    session = harness.client.get("/session")
    assert session.status_code == 200
    assert harness.client.post("/session").status_code == 200
    bad_csrf = {"X-CSRF-Token": "wrong"}
    assert harness.client.post("/session", headers=bad_csrf).status_code == 403
    assert harness.client.post("/visits", {"spot_id": "watergate", "code": "GATE-314"}, headers=bad_csrf).status_code == 403
    assert harness.client.post("/session", headers={"Origin": "https://evil.example"}).status_code == 403
    assert harness.client.post("/session", headers={"Origin": "null"}).status_code == 403
    assert harness.client.post("/session", headers={"Content-Type": "text/plain"}).status_code == 415
    assert harness.client.get("/catalog", headers={"Host": "evil.example"}).status_code == 400
    assert harness.client.get("/catalog", headers={"Host": "localhost:9999"}).status_code == 400
    assert harness.client.post("/session", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    new_client = Client(harness.runner, harness.app)
    try:
        response = new_client.login()
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie
        assert "secure" not in cookie
        assert "csrf_token" not in cookie
    finally:
        new_client.close()


def test_payload_limit_and_rate_limit(harness):
    response = harness.client.post("/session", {"padding": "a" * 17000})
    assert response.status_code == 413
    responses = [harness.client.post("/session") for _ in range(21)]
    assert responses[-1].status_code == 429
    assert responses[-1].headers["Retry-After"] == "60"
    assert harness.client.get("/health").status_code == 200


def test_transaction_failure_rolls_back_completion_and_can_retry(harness):
    harness.visit()
    attempt = harness.start().json()
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("CREATE TRIGGER fail_award BEFORE INSERT ON achievements WHEN NEW.attempt_id IS NOT NULL BEGIN SELECT RAISE(ABORT, 'private storage failure'); END")
    response = harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]})
    assert response.status_code == 503
    assert "private storage failure" not in response.text
    journal = harness.client.get("/journal").json()
    assert journal["attempts"][0]["status"] == "active"
    assert journal["attempts"][0]["score"] is None
    assert len(journal["achievements"]) == 1
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("DROP TRIGGER fail_award")
    assert harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]}).json()["correct"]


def test_visit_and_trophy_fail_together(harness):
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("CREATE TRIGGER fail_visit_award BEFORE INSERT ON achievements BEGIN SELECT RAISE(ABORT, 'failure'); END")
    assert harness.visit().status_code == 503
    assert harness.client.get("/journal").json()["visits"] == []


def test_backup_restore_and_restart_keep_history_and_session(harness, tmp_path):
    harness.visit()
    attempt = harness.start().json()
    harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]})
    harness.client.post("/plans", {"experience_id": "gate-winter", "reason": "冬の謎"})
    before = harness.client.get("/journal").json()
    backup = tmp_path / "restored.sqlite3"
    harness.app.state.database.backup(backup)
    application = create_app(Settings(db_path=backup), now_provider=lambda: harness.current[0])
    lifecycle = application.router.lifespan_context(application)
    harness.runner.run(lifecycle.__aenter__())
    restored = Client(harness.runner, application)
    restored.client.cookies.update(harness.client.client.cookies)
    try:
        assert restored.get("/journal").json() == before
        assert restored.get("/session").status_code == 200
        with application.state.database.transaction() as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        restored.close()
        harness.runner.run(lifecycle.__aexit__(None, None, None))


def test_season_year_and_daily_visit_boundaries(harness):
    harness.visit()
    attempt = harness.start().json()
    harness.current[0] += timedelta(days=1)
    assert harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]}).status_code == 409
    harness.visit()
    completed = harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]}).json()
    active = harness.start("advanced").json()
    harness.current[0] = datetime(2026, 12, 1, 10, tzinfo=JST)
    assert harness.client.post(f"/attempts/{active['id']}/answer", {"values": [3, 1, 4]}).status_code == 409
    assert harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [0, 0, 0]}).json() == completed
    winter = next(game for game in harness.client.get("/catalog").json()["games"] if game["season"] == "winter" and game["difficulty"] == "beginner")
    assert "2026" in winter["version"]
    harness.current[0] = datetime(2027, 1, 3, 10, tzinfo=JST)
    harness.visit()
    assert harness.client.post("/attempts", {"game_id": winter["id"]}).status_code == 200
    assert len(harness.client.get("/journal").json()["visits"]) == 3


def test_leaderboard_compares_only_same_version_and_best_score(harness):
    harness.visit()
    attempt = harness.start().json()
    harness.client.post(f"/attempts/{attempt['id']}/hint")
    harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": [1, 2, 3]})
    again = harness.start().json()
    harness.client.post(f"/attempts/{again['id']}/answer", {"values": [1, 2, 3]})
    advanced = harness.start("advanced").json()
    harness.client.post(f"/attempts/{advanced['id']}/answer", {"values": [3, 1, 4]})
    board = harness.client.get("/leaderboard", params={"game_id": attempt["game_id"]}).json()
    assert board["entries"] == [{"rank": 1, "nickname": "旅人", "score": 100}]
    assert len(harness.client.get("/journal").json()["achievements"]) == 3
    assert "user_id" not in json.dumps(board)


def test_recommendations_include_roundtrip_buffer_and_respect_hours(harness):
    response = harness.client.get("/recommendations", params={"minutes": 90, "season": "autumn"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["total_minutes"] == item["travel_minutes"] + item["experience"]["duration_minutes"] + item["buffer_minutes"] for item in items)
    assert all(item["travel_minutes"] == item["spot"]["walk_minutes"] * 2 for item in items)
    assert all(item["total_minutes"] <= 90 for item in items)
    assert all(item["spot"]["id"] != "coast" for item in items)
    assert harness.client.get("/recommendations", params={"minutes": 15}).json()["items"] == []
    coast = harness.client.get("/recommendations", params={"minutes": 120, "interest": "coast"}).json()["items"]
    assert coast[0]["total_minutes"] == 120
    harness.current[0] = datetime(2026, 11, 10, 10, tzinfo=JST)
    assert harness.client.get("/recommendations", params={"minutes": 120, "interest": "coast"}).json()["items"] == []
    harness.current[0] = datetime(2026, 11, 9, 17, 50, tzinfo=JST)
    assert harness.client.get("/recommendations", params={"minutes": 120, "interest": "shrine"}).json()["items"] == []


def test_future_season_and_life_events_are_optional_candidates(harness):
    response = harness.client.get("/recommendations", params={"minutes": 120, "season": "winter", "interest": "shrine"})
    items = response.json()["items"]
    assert {item["experience"]["id"] for item in items} == {"shrine-wish", "shrine-birth", "shrine-winter"}
    assert all("出発前に確認" in item["reason"] for item in items)
    before = harness.client.get("/journal").json()
    body = {"experience_id": "shrine-birth", "reason": "希望する時期に参拝する"}
    saved = harness.client.post("/plans", body).json()
    assert saved["season"] == "all"
    assert harness.client.post("/plans", body).json() == saved
    after = harness.client.get("/journal").json()
    for key in ("visits", "attempts", "achievements"):
        assert before[key] == after[key]
    assert len(after["plans"]) == 1
    assert harness.client.request("DELETE", f"/plans/{saved['id']}", headers={"Content-Type": "application/json"}).json() == {"ok": True}


@pytest.mark.parametrize("query", [{"minutes": 0}, {"minutes": 241}, {"minutes": "nan"}, {"season": "monsoon"}, {"interest": "pregnant"}])
def test_recommendation_invalid_queries(harness, query):
    assert harness.client.get("/recommendations", params=query).status_code == 422


def test_database_constraints_and_disabled_candidate(harness):
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("UPDATE experiences SET enabled=0 WHERE id='gate-winter'")
    assert harness.client.post("/plans", {"experience_id": "gate-winter", "reason": "冬"}).status_code == 404
    assert "gate-winter" not in {item["id"] for item in harness.client.get("/catalog").json()["experiences"]}
    with pytest.raises(sqlite3.IntegrityError), harness.app.state.database.transaction(write=True) as connection:
        connection.execute("INSERT INTO visits VALUES ('x','missing','watergate','水門','now','today','code')")


def test_static_serving_never_exposes_api_fallback_or_outside_files(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>旅の手帳</title>", encoding="utf-8")
    (tmp_path / "private.txt").write_text("private", encoding="utf-8")
    application = create_app(Settings(db_path=tmp_path / "db.sqlite3", static_dir=static))

    async def scenario():
        async with application.router.lifespan_context(application):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url="http://localhost:8000") as client:
                home = await client.get("/journal")
                assert home.status_code == 200
                assert "旅の手帳" in home.text
                assert "script-src 'self'" in home.headers["content-security-policy"]
                assert "base-uri 'none'" in home.headers["content-security-policy"]
                assert "'unsafe-inline'" not in home.headers["content-security-policy"]
                assert (await client.get("/api/missing")).status_code == 404
                assert (await client.get("/api")).status_code == 404
                assert (await client.get("/%2e%2e/private.txt")).status_code == 404
                assert (await client.get("/.env")).status_code == 404
                assert (await client.get("/missing.js")).status_code == 404
    asyncio.run(scenario())


def test_recovery_in_new_browser_keeps_history_after_session_expiry(harness):
    harness.visit()
    saved = harness.client.post("/plans", {"experience_id": "gate-winter", "reason": "冬の水路"})
    assert saved.status_code == 200
    before = harness.client.get("/journal").json()
    code_response = harness.client.post("/recovery")
    assert code_response.status_code == 200
    code = code_response.json()["recovery_code"]
    assert code.startswith("TC-") and len(code) >= 45
    with harness.app.state.database.transaction() as connection:
        hashes = connection.execute("SELECT code_hash FROM recovery_codes").fetchall()
        assert len(hashes) == 1 and hashes[0][0] != code and len(hashes[0][0]) == 64
    harness.current[0] += timedelta(days=400)
    assert harness.client.get("/session").status_code == 401
    other = Client(harness.runner, harness.app)
    try:
        response = other.post("/session/recover", {"recovery_code": code})
        assert response.status_code == 200, response.text
        other.client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        assert other.get("/journal").json() == before
        assert code not in other.get("/session").text
        assert code not in other.get("/journal").text
        assert code not in other.get("/catalog").text
        assert other.post("/plans", {"experience_id": "gate-spring", "reason": "次の春"}).status_code == 200
    finally:
        other.close()


def test_recovery_rotation_ownership_and_previous_sessions_invalidated(harness):
    harness.visit()
    old_code = harness.client.post("/recovery").json()["recovery_code"]
    new_code = harness.client.post("/recovery").json()["recovery_code"]
    assert new_code != old_code
    other = harness.another()
    assert other.post("/recovery", {"user_id": "someone"}).status_code == 422
    assert other.post("/session/recover", {"recovery_code": old_code}).status_code == 401
    assert other.get("/journal").json()["visits"] == []
    assert other.post("/session/recover", {"recovery_code": new_code}, headers={"X-CSRF-Token": "bad"}).status_code == 403
    recovered = other.post("/session/recover", {"recovery_code": new_code})
    assert recovered.status_code == 200
    other.client.headers["X-CSRF-Token"] = recovered.json()["csrf_token"]
    assert len(other.get("/journal").json()["visits"]) == 1
    assert harness.client.get("/session").status_code == 401
    assert harness.client.post("/recovery").status_code == 401


def test_recovery_wrong_code_is_generic_throttled_and_origin_protected(harness):
    other = Client(harness.runner, harness.app)
    try:
        assert other.post("/recovery").status_code == 401
        assert other.post("/session/recover", {"recovery_code": "fake"}, headers={"Origin": "https://evil.example"}).status_code == 403
        responses = [other.post("/session/recover", {"recovery_code": f"unknown-{index}"}) for index in range(6)]
        assert all(response.status_code == 401 for response in responses[:5])
        assert len({response.text for response in responses[:5]}) == 1
        assert responses[-1].status_code == 429
        assert "unknown" not in responses[0].text
    finally:
        other.close()


def test_schema_v1_migrates_without_losing_history(harness):
    harness.visit()
    before = harness.client.get("/journal").json()
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("DROP TABLE recovery_codes")
        connection.execute("PRAGMA user_version=1")
    harness.app.state.database.initialize(harness.current[0])
    with harness.app.state.database.transaction() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
    assert harness.client.get("/journal").json() == before
    assert harness.client.post("/recovery").status_code == 200
