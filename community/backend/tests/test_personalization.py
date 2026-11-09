import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.circles.discovery import Discovery
from app.database import Database
from app.main import create_app
from app.personalization import schema
from app.personalization.router import create_router
from app.personalization.service import Personalization
from conftest import Client
from fastapi import HTTPException
from test_circles import circle
from test_discovery import discover, set_preferences


@pytest.fixture
def personal(harness):
    schema.migrate(harness.app.state.database)
    if not any(
        getattr(route, "path", None) == "/api/me/resume-state" for route in harness.app.routes
    ):
        existing = len(harness.app.router.routes)
        harness.app.include_router(create_router(harness.app.state.database))
        # The standalone fixture wires the not-yet-integrated router before the
        # production SPA catch-all, just as main must do during integration.
        routes = harness.app.router.routes
        routes[:] = routes[existing:] + routes[:existing]
    return harness


def state(client, **changes):
    response = client.get("/me/resume-state")
    assert response.status_code == 200
    return response.json() | changes


def save(client, **changes):
    response = client.write("PUT", "/me/resume-state", state(client, **changes))
    assert response.status_code == 200, response.text
    return response.json()


def filters(**changes):
    return dict(query="", category="", duration="all", schedule="all", area="") | changes


def test_personal_values_survive_new_connection_without_cross_account_leak(personal):
    aoi, ren = personal.client("aoi"), personal.client("ren")
    chosen = circle(aoi)
    first = state(aoi)
    assert first == dict(
        version=0, page="market", community_id=None, circle_id=None, filters=filters()
    )
    own = save(
        aoi,
        page="circles",
        community_id="peers",
        circle_id=chosen["id"],
        filters=filters(query="本人専用の検索", category="cafe", area="軽井沢周辺"),
    )
    other = save(ren, page="journal", community_id="peers", filters=filters(query="別の検索"))
    assert own["version"] == other["version"] == 1
    fresh = Personalization(Database(personal.settings.db_path))
    assert fresh.resume("u-aoi") == own
    assert fresh.resume("u-ren") == other
    assert "本人専用の検索" not in ren.get("/me/resume-state").text
    assert "本人専用の検索" not in aoi.get("/bootstrap").text
    assert "user_id" not in own
    assert aoi.write("PUT", "/me/resume-state", own | {"user_id": "u-ren"}).status_code == 422
    assert personal.client().get("/me/resume-state").status_code == 401
    assert (
        aoi.write("PUT", "/me/resume-state", own, headers={"X-CSRF-Token": "wrong"}).status_code
        == 403
    )
    assert aoi.get("/me/resume-state").json() == own


def test_explicit_personal_interests_change_ranking_and_permission_off_removes_only_own_signal(
    personal,
):
    aoi, ren = personal.client("aoi"), personal.client("ren")
    set_preferences(aoi, ["coast"])
    set_preferences(ren, ["cafe"])
    own, other = discover(aoi), discover(ren)
    assert own["items"][0]["plan"]["id"] == "shore-school"
    assert other["items"][0]["plan"]["id"].startswith("forest-")
    assert own["context"]["profile_used"] and other["context"]["profile_used"]
    fresh = Discovery(Database(personal.settings.db_path))
    assert fresh.discover("u-aoi", "peers") == own
    set_preferences(ren, ["food"])
    assert discover(aoi) == own
    set_preferences(aoi, ["coast"], allowed=False)
    revoked = fresh.discover("u-aoi", "peers")
    assert not revoked["context"]["profile_used"]
    assert all(item["score"] == 0 for item in revoked["items"])


def test_full_application_lifecycle_reopens_saved_state_with_new_login(personal):
    aoi = personal.client("aoi")
    room = circle(aoi)
    expected = save(
        aoi,
        community_id="peers",
        circle_id=room["id"],
        filters=filters(query="再開する旅", duration="day"),
    )
    app = create_app(personal.settings)
    lifecycle = app.router.lifespan_context(app)
    personal.runner.run(lifecycle.__aenter__())
    client = Client(personal.runner, app)
    try:
        client.login("aoi")
        assert client.get("/me/resume-state").json() == expected
        client.login("ren")
        assert client.get("/me/resume-state").json()["version"] == 0
        assert "再開する旅" not in client.get("/me/resume-state").text
    finally:
        client.close()
        personal.runner.run(lifecycle.__aexit__(None, None, None))


def test_pending_member_wrong_community_closed_circle_and_provider_page_are_rejected(personal):
    aoi, ren, forest = (personal.client(name) for name in ("aoi", "ren", "forest"))
    room = circle(aoi, invitee_ids=["u-ren"])
    payload = state(ren, community_id="peers", circle_id=room["id"])
    assert ren.write("PUT", "/me/resume-state", payload).status_code == 404
    assert (
        aoi.write(
            "PUT", "/me/resume-state", state(aoi, community_id="campus", circle_id=room["id"])
        ).status_code
        == 404
    )
    assert aoi.write("PUT", "/me/resume-state", state(aoi, circle_id=room["id"])).status_code == 404
    assert aoi.write("PUT", "/me/resume-state", state(aoi, page="provider")).status_code == 404
    assert state(forest)["page"] == "provider"
    invite = room["invitations"][0]
    assert (
        ren.write(
            "POST",
            "/circle-invitations/" + invite["id"] + "/respond",
            dict(decision="accepted", version=invite["version"], client_request_id="resume-accept"),
        ).status_code
        == 200
    )
    assert save(ren, community_id="peers", circle_id=room["id"])["circle_id"] == room["id"]
    current = aoi.get("/circles/" + room["id"]).json()
    assert (
        aoi.write(
            "POST", "/circles/" + room["id"] + "/close", {"version": current["version"]}
        ).status_code
        == 200
    )
    assert state(ren)["circle_id"] is None
    assert ren.write("PUT", "/me/resume-state", state(ren, circle_id=room["id"])).status_code == 404


def test_version_compare_exchange_serializes_concurrent_tabs(personal):
    aoi = personal.client("aoi")
    own = save(aoi, community_id="peers")
    service = Personalization(personal.app.state.database)

    def write(page):
        try:
            return service.resume("u-aoi", own | {"page": page})
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ["journal", "circles"]))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results
    latest = state(aoi)
    assert latest["version"] == own["version"] + 1
    assert aoi.write("PUT", "/me/resume-state", latest).json() == latest


@pytest.mark.parametrize(
    "kind", ["community_status", "community_delete", "party_member", "party_close", "account"]
)
def test_revocation_latches_before_rejoin_without_intermediate_get(personal, kind):
    aoi, ren = personal.client("aoi"), personal.client("ren")
    room = circle(aoi, invitee_ids=["u-ren"])
    invitation = room["invitations"][0]
    ren.write(
        "POST",
        "/circle-invitations/" + invitation["id"] + "/respond",
        dict(decision="accepted", version=invitation["version"], client_request_id="accept"),
    )
    stored = save(
        ren,
        page="circles",
        community_id="peers",
        circle_id=room["id"],
        filters=filters(query="私的検索"),
    )
    with personal.app.state.database.transaction(True) as conn:
        if kind == "community_status":
            conn.execute(
                "UPDATE memberships SET status='left' WHERE user_id='u-ren' AND community_id='peers'"
            )
            conn.execute(
                "UPDATE memberships SET status='active' WHERE user_id='u-ren' AND community_id='peers'"
            )
            conn.execute(
                "INSERT OR IGNORE INTO travel_party_members VALUES(?,'u-ren')", (room["id"],)
            )
        elif kind == "community_delete":
            conn.execute("DELETE FROM memberships WHERE user_id='u-ren' AND community_id='peers'")
            conn.execute("INSERT INTO memberships VALUES('peers','u-ren','member','active')")
        elif kind == "party_member":
            conn.execute(
                "DELETE FROM travel_party_members WHERE party_id=? AND user_id='u-ren'",
                (room["id"],),
            )
            conn.execute("INSERT INTO travel_party_members VALUES(?,'u-ren')", (room["id"],))
        elif kind == "party_close":
            conn.execute("UPDATE travel_parties SET status='closed' WHERE id=?", (room["id"],))
            conn.execute("UPDATE travel_parties SET status='open' WHERE id=?", (room["id"],))
        else:
            conn.execute("UPDATE users SET login_enabled=0 WHERE id='u-ren'")
            conn.execute("UPDATE users SET login_enabled=1 WHERE id='u-ren'")
    final = state(ren)
    assert final["circle_id"] is None and final["filters"] == filters()
    assert final["version"] > stored["version"]
    assert ren.write("PUT", "/me/resume-state", stored).status_code == 409
    if kind.startswith("community") or kind == "account":
        assert final["community_id"] is None


@pytest.mark.parametrize("kind", ["staff", "provider", "delete"])
def test_provider_role_revocation_does_not_restore_private_workspace(personal, kind):
    forest = personal.client("forest")
    original = save(forest, page="provider")
    with personal.app.state.database.transaction(True) as conn:
        if kind == "staff":
            conn.execute("UPDATE provider_staff SET active=0 WHERE user_id='provider-forest'")
            conn.execute("UPDATE provider_staff SET active=1 WHERE user_id='provider-forest'")
        elif kind == "provider":
            conn.execute("UPDATE providers SET active=0 WHERE id='forest-house'")
            conn.execute("UPDATE providers SET active=1 WHERE id='forest-house'")
        else:
            conn.execute("DELETE FROM provider_staff WHERE user_id='provider-forest'")
            conn.execute("INSERT INTO provider_staff VALUES('forest-house','provider-forest',1)")
    assert state(forest)["page"] == "market"
    assert state(forest)["version"] > original["version"]


def test_public_area_only_and_removed_area_normalization_commit_before_conflict(personal):
    aoi = personal.client("aoi")
    original = save(aoi, community_id="peers", filters=filters(area="軽井沢周辺"))
    with personal.app.state.database.transaction(True) as conn:
        rows = list(
            conn.execute("SELECT id,body FROM provider_plans WHERE provider_id='forest-house'")
        )
        for row in rows:
            body = json.loads(row["body"]) | {"area": "非公開の専用エリア"}
            conn.execute(
                "UPDATE provider_plans SET body=?,status='draft' WHERE id=?",
                (json.dumps(body), row["id"]),
            )
    assert aoi.write("PUT", "/me/resume-state", original).status_code == 409
    current = state(aoi)
    assert current["version"] == original["version"] + 1 and current["filters"]["area"] == ""
    private = current | {"filters": filters(area="非公開の専用エリア")}
    response = aoi.write("PUT", "/me/resume-state", private)
    assert response.status_code == 422 and "非公開の専用エリア" not in response.text
    assert (
        aoi.write(
            "PUT", "/me/resume-state", current | {"filters": filters(category="unknown")}
        ).status_code
        == 422
    )
    assert aoi.write("PUT", "/me/resume-state", current | {"version": True}).status_code == 422
    assert (
        aoi.write(
            "PUT", "/me/resume-state", current | {"filters": filters(query="a" * 121)}
        ).status_code
        == 422
    )


def test_additive_schema_migration_preserves_all_existing_rows_and_rolls_back(harness, monkeypatch):
    db = harness.app.state.database
    author = harness.client("aoi")
    room = circle(author)
    assert (
        author.write(
            "POST",
            "/travel-parties/" + room["id"] + "/messages",
            dict(body="移行後も残す私的な会話", client_request_id="migration-message"),
        ).status_code
        == 200
    )
    assert (
        author.write(
            "POST",
            "/circles/" + room["id"] + "/candidate-cards",
            dict(plan_id="forest-day", plan_version=1, client_request_id="migration-card"),
        ).status_code
        == 200
    )
    with db.transaction(True) as conn:
        # After root wires schema 8 into startup, recreate its source version in
        # this isolated temporary fixture only. Never operate on the real volume.
        for row in list(
            conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'resume_%'"
            )
        ):
            conn.execute('DROP TRIGGER "' + row[0] + '"')
        conn.execute("DROP TABLE IF EXISTS user_resume_state")
        conn.execute("PRAGMA user_version=7")
        names = [
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        before = {
            name: [
                tuple(row) for row in conn.execute('SELECT * FROM "' + name + '" ORDER BY rowid')
            ]
            for name in names
        }
    original = schema.DDL
    monkeypatch.setattr(schema, "DDL", original + ("INVALID SQL",))
    with pytest.raises(sqlite3.OperationalError):
        schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='user_resume_state'"
        ).fetchone()
    monkeypatch.setattr(schema, "DDL", original)
    schema.migrate(db)
    schema.migrate(db)
    with db.transaction() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 8
        assert {
            name: [
                tuple(row) for row in conn.execute('SELECT * FROM "' + name + '" ORDER BY rowid')
            ]
            for name in names
        } == before
