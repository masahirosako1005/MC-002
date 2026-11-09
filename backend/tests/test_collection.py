from datetime import datetime, timedelta
import json

import pytest

from app.clock import JST, season_at
from app.collection import derive_collection
from app.config import Settings
from app.main import create_app
from app.seed import SOLUTIONS
from conftest import Client


CODES = {"watergate": "GATE-314", "sakura": "SAKURA-428", "coast": "COAST-582", "conference": "MEET-763"}


def collection(client):
    response = client.get("/collection")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def by_id(value):
    return {item["id"]: item for item in value["trophies"]}


def visit(harness, spot):
    response = harness.client.post("/visits", {"spot_id": spot, "code": CODES[spot]})
    assert response.status_code == 200, response.text
    return response.json()


def solve(harness, difficulty="beginner"):
    visit(harness, "watergate")
    season = season_at(harness.current[0])
    games = harness.client.get("/catalog").json()["games"]
    game = next(item for item in games if item["season"] == season and item["difficulty"] == difficulty)
    attempt = harness.client.post("/attempts", {"game_id": game["id"]}).json()
    response = harness.client.post(f"/attempts/{attempt['id']}/answer", {"values": SOLUTIONS[season][difficulty]})
    assert response.status_code == 200 and response.json()["correct"], response.text
    return attempt


def put_target(client, target, **kwargs):
    return client.request("PUT", "/collection/target", json={"trophy_id": target}, **kwargs)


def recover(client, code):
    response = client.post("/session/recover", {"recovery_code": code})
    assert response.status_code == 200, response.text
    client.client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def database_dump(harness):
    connection = harness.app.state.database.connect()
    try:
        return list(connection.iterdump())
    finally:
        connection.close()


def test_empty_collection_is_private_read_only_and_has_twelve_complete_definitions(harness):
    before = database_dump(harness)
    value = collection(harness.client)
    assert value["summary"] == {"earned": 0, "total": 12, "completed_sets": 0}
    assert len(value["sets"]) == 3 and all(item["total"] == 4 for item in value["sets"])
    assert value["target_id"] is None and value["definition_version"] == "1"
    assert len({item["id"] for item in value["trophies"]}) == 12
    assert all(item["status"] == "locked" and item["next_action"] for item in value["trophies"])
    assert all(item["missing_conditions"] and not item["completed"] for item in value["trophies"])
    assert collection(harness.client) == value
    assert database_dump(harness) == before
    text = json.dumps(value)
    assert all(secret not in text for secret in ["user_id", "answer_json", "csrf_token", *CODES.values()])
    harness.client.client.cookies.clear()
    assert harness.client.get("/collection").status_code == 401


def test_places_complete_set_without_same_day_returns_or_duplicate_awards(harness):
    for spot in CODES:
        first = visit(harness, spot)
        assert visit(harness, spot) == first
        harness.current[0] += timedelta(minutes=1)
    value = collection(harness.client)
    places = next(item for item in value["sets"] if item["id"] == "places")
    assert places["completed"] and places["earned"] == 4 and places["reward_label"] == "水都を歩く人"
    assert places["earned_at"] == first["visited_at"]
    assert by_id(value)["return-path"]["progress"] == {"current": 1, "target": 2, "unit": "日"}
    assert by_id(value)["conference-detour"]["earned_at"] is None
    assert len(harness.client.get("/journal").json()["visits"]) == 4


def test_plans_and_active_games_do_not_create_completion_or_revisit_progress(harness):
    response = harness.client.post("/plans", {"experience_id": "shrine-birth", "reason": "希望する日に"})
    assert response.status_code == 200
    assert collection(harness.client)["summary"]["earned"] == 0
    visit(harness, "watergate")
    assert harness.start().status_code == 200
    trophies = by_id(collection(harness.client))
    assert trophies["season-autumn"]["status"] == "locked"
    assert trophies["watergate-mastery"]["progress"]["current"] == 0
    assert trophies["return-path"]["earned_at"] is None


def test_same_season_different_days_grow_stages_and_preserve_first_dates(harness):
    dates = []
    for index in range(5):
        result = visit(harness, "sakura")
        dates.append(result["visited_at"])
        trophy = by_id(collection(harness.client))["return-path"]
        if index == 1:
            assert trophy["status"] == "earned" and not trophy["completed"]
            assert trophy["progress"] == {"current": 2, "target": 3, "unit": "日"}
            assert trophy["next_action"]["available_from"] == (harness.current[0].date() + timedelta(days=1)).isoformat()
        harness.current[0] += timedelta(days=1)
    final = by_id(collection(harness.client))["return-path"]
    assert final["earned_at"] == dates[1]
    assert [item["earned_at"] for item in final["stages"]] == [dates[1], dates[2], dates[4]]
    assert all(item["completed"] for item in final["stages"])
    assert final["completed"] and final["next_action"] is None and final["missing_conditions"] == []
    assert final["progress"] == {"current": 5, "target": 5, "unit": "日"}
    journal = harness.client.get("/journal").json()
    assert len(journal["visits"]) == 5 and len(journal["achievements"]) == 1


def test_seasons_and_mastery_survive_old_catalog_and_never_count_repeated_games(harness):
    code = harness.client.post("/recovery").json()["recovery_code"]
    completion_dates = []
    for month, year in [(11, 2026), (12, 2026), (3, 2027), (6, 2027)]:
        harness.current[0] = datetime(year, month, 9, 10, tzinfo=JST)
        recover(harness.client, code)
        visit(harness, "coast")
        solve(harness)
        before_mastery = by_id(collection(harness.client))["watergate-mastery"]["progress"]["current"]
        solve(harness, "advanced")
        completion_dates.append(harness.current[0].isoformat())
        once = by_id(collection(harness.client))["watergate-mastery"]
        solve(harness, "advanced")
        assert by_id(collection(harness.client))["watergate-mastery"] == once
        assert once["progress"]["current"] == before_mastery + 1
    value = collection(harness.client)
    trophies = by_id(value)
    assert trophies["coast-seasons"]["completed"] and trophies["watergate-mastery"]["completed"]
    assert [stage["earned_at"] for stage in trophies["coast-seasons"]["stages"]] == completion_dates[1:]
    assert [stage["earned_at"] for stage in trophies["watergate-mastery"]["stages"]] == [completion_dates[0], completion_dates[1], completion_dates[3]]
    assert next(item for item in value["sets"] if item["id"] == "seasons")["completed"]
    earned_before = {key: [(stage["id"], stage["earned_at"]) for stage in item["stages"]] for key, item in trophies.items()}
    harness.current[0] = datetime(2028, 11, 9, 10, tzinfo=JST)
    recover(harness.client, code)
    assert all("2026" not in game["id"] for game in harness.client.get("/catalog").json()["games"])
    assert {key: [(stage["id"], stage["earned_at"]) for stage in item["stages"]] for key, item in by_id(collection(harness.client)).items()} == earned_before


def test_conference_requires_later_days_and_counts_each_day_once(harness):
    visit(harness, "sakura")
    harness.current[0] += timedelta(days=1)
    visit(harness, "conference")
    visit(harness, "coast")
    assert by_id(collection(harness.client))["conference-detour"]["progress"]["current"] == 0
    dates = []
    for _ in range(3):
        harness.current[0] += timedelta(days=1)
        dates.append(visit(harness, "watergate")["visited_at"])
        visit(harness, "sakura")
    result = by_id(collection(harness.client))["conference-detour"]
    assert result["completed"] and result["progress"]["current"] == 3
    assert [stage["earned_at"] for stage in result["stages"]] == dates


@pytest.mark.parametrize("body", [
    {"trophy_id": "not-a-trophy"}, {"trophy_id": "https://example.com"},
    {"trophy_id": "place-coast", "user_id": "someone-else"}, {"trophy_id": 12}, {},
])
def test_target_rejects_unknown_url_extra_owner_and_invalid_types(harness, body):
    response = harness.client.request("PUT", "/collection/target", json=body)
    assert response.status_code == 422
    assert collection(harness.client)["target_id"] is None


def test_target_and_collection_are_owner_scoped_and_require_write_protections(harness):
    visit(harness, "sakura")
    assert put_target(harness.client, "place-sakura").json() == {"target_id": "place-sakura"}
    assert put_target(harness.client, "place-sakura").status_code == 200
    other = harness.another()
    assert collection(other)["target_id"] is None and collection(other)["summary"]["earned"] == 0
    assert put_target(other, "season-winter").status_code == 200
    assert collection(harness.client)["target_id"] == "place-sakura"
    assert put_target(harness.client, "return-path", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert put_target(harness.client, "return-path", headers={"Origin": "https://example.com"}).status_code == 403
    assert harness.client.request("PUT", "/collection/target", content='{"trophy_id":null}', headers={"Content-Type": "text/plain"}).status_code == 415
    assert collection(harness.client)["target_id"] == "place-sakura"
    assert put_target(harness.client, None).json() == {"target_id": None}
    other.client.cookies.clear()
    assert put_target(other, "place-sakura").status_code == 401


def test_target_write_failure_is_atomic(harness):
    put_target(harness.client, "place-coast")
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("CREATE TRIGGER fail_preference BEFORE UPDATE ON collection_preferences BEGIN SELECT RAISE(ABORT,'private-db-detail'); END")
    response = put_target(harness.client, "return-path")
    assert response.status_code == 503 and "private-db-detail" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert collection(harness.client)["target_id"] == "place-coast"


def test_recovery_and_database_restore_keep_target_and_collection(harness, tmp_path):
    solve(harness, "advanced")
    put_target(harness.client, "watergate-mastery")
    before = collection(harness.client)
    code = harness.client.post("/recovery").json()["recovery_code"]
    other = harness.another()
    recover(other, code)
    assert collection(other) == before
    assert harness.client.get("/collection").status_code == 401
    backup = tmp_path / "restored.sqlite3"
    harness.app.state.database.backup(backup)
    application = create_app(Settings(db_path=backup), now_provider=lambda: harness.current[0])
    lifecycle = application.router.lifespan_context(application)
    harness.runner.run(lifecycle.__aenter__())
    restored = Client(harness.runner, application)
    restored.client.cookies.update(other.client.cookies)
    try:
        assert collection(restored) == before
        with application.state.database.transaction() as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        restored.close()
        harness.runner.run(lifecycle.__aexit__(None, None, None))


def test_schema_v2_upgrade_keeps_history_and_adds_preferences(harness):
    visit(harness, "coast")
    before = harness.client.get("/journal").json()
    with harness.app.state.database.transaction(write=True) as connection:
        connection.execute("DROP TABLE collection_preferences")
        connection.execute("PRAGMA user_version=2")
    harness.app.state.database.initialize(harness.current[0])
    assert harness.client.get("/journal").json() == before
    assert put_target(harness.client, "coast-seasons").status_code == 200
    with harness.app.state.database.transaction() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3


def test_return_first_earned_date_and_next_season_are_deterministic():
    visits = [
        {"spot_id": spot, "visited_at": f"2026-11-{day:02}T10:00:00+09:00", "visit_day": f"2026-11-{day:02}"}
        for spot, day in [("sakura", 1), ("sakura", 2), ("coast", 3), ("coast", 4), ("coast", 5)]
    ]
    value = derive_collection(visits, [], None, datetime(2026, 11, 9, 10, tzinfo=JST))
    trophies = by_id(value)
    assert trophies["return-path"]["earned_at"] == "2026-11-02T10:00:00+09:00"
    assert trophies["return-path"]["stages"][1]["earned_at"] == "2026-11-05T10:00:00+09:00"
    assert trophies["return-path"]["next_action"]["spot_id"] == "coast"
    assert trophies["coast-seasons"]["next_action"]["season"] == "winter"
    assert trophies["coast-seasons"]["next_action"]["available_from"] == "2026-12-01"
    assert trophies["season-spring"]["next_action"]["available_from"] == "2027-03-01"


def test_all_sets_require_final_stages_and_date_the_last_required_evidence():
    def evidence(spot, day):
        return {"spot_id": spot, "visited_at": day + "T10:00:00+09:00", "visit_day": day}

    visits = [evidence("conference", "2026-10-31"), evidence("sakura", "2026-11-01")]
    visits += [evidence("watergate", f"2026-11-{day:02}") for day in range(1, 6)]
    attempts = []
    for month, season in [(3, "spring"), (6, "summer"), (9, "autumn"), (12, "winter")]:
        day = f"2026-{month:02}-01"
        visits.append(evidence("coast", day))
        attempts.append({"status": "completed", "spot_id": "watergate", "season": season,
                         "difficulty": "advanced", "completed_at": day + "T12:00:00+09:00"})
    value = derive_collection(visits, attempts, "return-path", datetime(2027, 1, 9, 10, tzinfo=JST))
    assert value["summary"] == {"earned": 12, "total": 12, "completed_sets": 3}
    assert all(item["completed"] and item["next_action"] is None for item in value["trophies"])
    assert all(item["completed"] and item["earned"] == item["total"] == 4 for item in value["sets"])
    assert next(item for item in value["sets"] if item["id"] == "journeys")["earned_at"] == "2026-12-01T12:00:00+09:00"
