import io
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

from PIL import Image
import pytest

from app.config import Settings
from app.main import create_app
from app.images import LocalClassifier
from conftest import Client


def photo_bytes(format="JPEG", exif=False):
    image = Image.new("RGB", (180, 120), (30, 150, 100))
    output = io.BytesIO()
    if exif:
        meta = Image.Exif()
        meta[270] = "private-camera-note"
        image.save(output, format=format, exif=meta)
    else:
        image.save(output, format=format)
    return output.getvalue()


def upload(client, raw=None):
    return client.request("POST", "/media", files={"file": ("untrusted-name.jpg", raw or photo_bytes(), "image/jpeg")})


def draft(client, cid="peers"):
    image = upload(client)
    assert image.status_code == 200, image.text
    response = client.write("POST", "/posts", {"community_id": cid, "body": "木立を歩いた日", "media_ids": [image.json()["id"]], "tags": ["mountain", "cafe"]})
    assert response.status_code == 200, response.text
    return response.json()


def propose(client, size=3):
    return client.write("POST", "/communities/peers/proposals", {"purpose": "森を歩いてカフェへ", "tags": ["mountain", "cafe"], "size": size, "trip_id": "karuizawa", "date": "2026-12-12"})


def test_real_account_login_switch_revokes_old_session_and_requires_password(harness):
    client = harness.client()
    assert client.get("/me").status_code == 401
    assert client.write("POST", "/login", {"username": "aoi", "password": "wrong"}).status_code == 401
    first = client.login("aoi")
    old_cookies = dict(client.client.cookies)
    assert client.get("/me").json()["user"]["id"] == "u-aoi"
    assert "HttpOnly" in first.headers["set-cookie"] and "SameSite=strict" in first.headers["set-cookie"]
    assert client.login("ren").json()["user"]["id"] == "u-ren"
    stale = harness.client()
    stale.client.cookies.update(old_cookies)
    assert stale.get("/me").status_code == 401
    assert client.write("POST", "/logout").status_code == 200
    assert client.get("/me").status_code == 401
    data = json.dumps(client.get("/bootstrap").json())
    assert "password" not in data and "salt" not in data


def test_csrf_origin_host_and_extra_owner_are_rejected(harness):
    client = harness.client("aoi")
    assert client.write("POST", "/communities", {"name": "旅"}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.write("POST", "/communities", {"name": "旅"}, headers={"Origin": "https://elsewhere.invalid"}).status_code == 403
    assert client.get("/me", headers={"Host": "elsewhere.invalid"}).status_code == 400
    assert client.write("POST", "/communities", {"name": "旅", "user_id": "u-mio"}).status_code == 422
    assert client.request("POST", "/communities", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_image_formats_are_reencoded_and_exif_removed(harness, format):
    client = harness.client("aoi")
    response = upload(client, photo_bytes(format, exif=True))
    assert response.status_code == 200, response.text
    result = client.get("/media/" + response.json()["id"])
    assert result.headers["content-type"] == "image/jpeg"
    assert result.headers["cache-control"] == "no-store" and result.headers["x-content-type-options"] == "nosniff"
    assert b"private-camera-note" not in result.content
    with Image.open(io.BytesIO(result.content)) as image:
        assert not image.getexif() and image.format == "JPEG"


def test_invalid_image_and_oversized_body_are_rejected(harness):
    client = harness.client("aoi")
    assert upload(client, b"<svg><script>alert(1)</script></svg>").status_code == 422
    assert upload(client, photo_bytes("GIF")).status_code == 415
    assert client.request("POST", "/media", files={"file": ("photo.png", b"x" * (12 * 1024 * 1024 + 1), "image/png")}).status_code == 413
    image = Image.new("RGB", (5000, 4100))
    output = io.BytesIO()
    image.save(output, format="PNG")
    assert upload(client, output.getvalue()).status_code == 413


def test_draft_private_cross_group_denial_publish_unpublish_and_delete(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    post = draft(aoi)
    mid = post["media"][0]["id"]
    assert ren.get("/media/" + mid).status_code == 404
    assert ren.get("/media/" + mid + "/analysis").status_code == 404
    assert ren.write("PATCH", "/posts/" + post["id"], {"status": "published"}).status_code == 404
    assert aoi.write("PATCH", "/posts/" + post["id"], {"status": "published"}).status_code == 200
    assert ren.get("/media/" + mid).status_code == 200
    assert aoi.write("PATCH", "/posts/" + post["id"], {"status": "draft"}).status_code == 200
    assert ren.get("/media/" + mid).status_code == 404
    campus = draft(aoi, "campus")
    aoi.write("PATCH", "/posts/" + campus["id"], {"status": "published"})
    assert ren.get("/communities/campus/feed").status_code == 404
    assert ren.get(campus["media"][0]["url"][4:]).status_code == 404
    assert aoi.write("DELETE", "/posts/" + post["id"]).status_code == 200
    assert aoi.get("/media/" + mid).status_code == 404
    assert not (harness.settings.media_dir / (mid + ".jpg")).exists()


def test_model_missing_is_honest_and_manual_tags_can_publish(harness):
    client = harness.client("aoi")
    post = draft(client)
    mid = post["media"][0]["id"]
    assert harness.app.state.worker.once()
    analysis = client.get("/media/" + mid + "/analysis").json()
    assert analysis["status"] == "failed" and analysis["tags"] == [] and analysis["model_version"] is None
    assert client.write("PATCH", "/posts/" + post["id"], {"status": "published", "tags": ["nature"]}).status_code == 200
    assert client.write("POST", "/media/" + mid + "/analyze").json()["status"] == "queued"


def test_personal_evidence_permissions_and_deletion_stay_separate(harness):
    client = harness.client("aoi")
    post = draft(client, "campus")
    client.write("PATCH", "/posts/" + post["id"], {"status": "published"})
    prefs = client.get("/me/preferences").json()
    prefs.pop("evidence")
    prefs["learn_from_posts"] = True
    assert client.write("PUT", "/me/preferences", prefs).status_code == 200
    assert client.get("/me/preferences").json()["evidence"]
    ren = harness.client("ren")
    assert all(item["post_id"] != post["id"] for item in ren.get("/me/preferences").json()["evidence"])
    client.write("DELETE", "/posts/" + post["id"])
    assert client.get("/me/preferences").json()["evidence"] == []
    assert client.get("/me/preferences").json()["tags"] == prefs["tags"]


def test_three_people_accept_to_form_one_group_and_edit_optional_plan(harness):
    clients = [harness.client(name) for name in ("aoi", "ren", "mio")]
    assert clients[0].get("/communities/peers").json()["community"]["member_count"] == 200
    assert propose(clients[0], size=5).status_code == 409
    response = propose(clients[0])
    assert response.status_code == 200, response.text
    proposal = response.json()
    assert proposal["date"] == "2026-12-12"
    assert {person["id"] for person in proposal["participants"]} == {"u-aoi", "u-ren", "u-mio"}
    assert all(person["response"] == "pending" for person in proposal["participants"])
    for client in clients:
        current = client.get("/proposals/" + proposal["id"]).json()
        assert current["date"] == "2026-12-12"
        accepted = client.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": current["version"]})
        assert accepted.status_code == 200, accepted.text
        assert client.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": current["version"]}).json() == accepted.json()
    formed = accepted.json()
    assert formed["status"] == "formed"
    gid = formed["group_id"]
    group = clients[0].get("/groups/" + gid).json()
    assert len(group["members"]) == 3 and all(item["role"] == "none" for item in group["contributions"])
    assert clients[1].write("PUT", "/groups/" + gid + "/contribution", {"role": "food", "note": "喫茶店を調べる"}).status_code == 200
    updated = clients[0].write("PUT", "/groups/" + gid + "/plan", {"date": "2026-12-12", "meeting_point": "駅の改札", "notes": "歩きやすい靴で", "version": group["plan"]["version"]})
    assert updated.status_code == 200
    assert clients[0].write("PUT", "/groups/" + gid + "/plan", {"date": None, "meeting_point": "", "notes": "", "version": 1}).status_code == 409
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM ko_groups").fetchone()[0] == 1


def test_decline_is_private_and_invalidates_without_group(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    proposal = propose(aoi).json()
    response = ren.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "declined", "version": proposal["version"]})
    assert response.status_code == 200
    visible = aoi.get("/proposals/" + proposal["id"]).json()
    assert visible["status"] == "invalidated" and visible["group_id"] is None
    assert all(person["response"] == "unavailable" for person in visible["participants"])
    assert aoi.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": proposal["version"]}).status_code == 409


def test_membership_invitation_leave_and_grant_revocation_invalidate_proposals(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    group = aoi.write("POST", "/communities", {"name": "週末の仲間", "description": "近くのまちへ"}).json()
    assert ren.get("/communities/" + group["id"]).status_code == 404
    code = aoi.get("/communities/" + group["id"]).json()["invite_code"]
    assert ren.write("POST", "/communities/join", {"invite_code": code}).status_code == 200
    assert ren.get("/communities/" + group["id"]).json()["invite_code"] is None
    assert ren.write("POST", "/communities/" + group["id"] + "/leave").status_code == 200
    assert ren.get("/communities/" + group["id"] + "/feed").status_code == 404
    proposal = propose(aoi).json()
    prefs = ren.get("/me/preferences").json()
    prefs.pop("evidence")
    prefs["grants"][0]["display_in_matches"] = False
    assert ren.write("PUT", "/me/preferences", prefs).status_code == 200
    revised = aoi.get("/proposals/" + proposal["id"]).json()
    assert revised["status"] == "invalidated" and not any(person["id"] == "u-ren" for person in revised["participants"])
    assert ren.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": proposal["version"]}).status_code == 409
    assert ren.write("POST", "/communities/peers/leave").status_code == 200
    assert ren.get("/proposals/" + proposal["id"]).status_code == 404


def test_group_failure_rolls_back_last_acceptance(harness):
    clients = [harness.client(name) for name in ("aoi", "ren", "mio")]
    proposal = propose(clients[0]).json()
    for client in clients[:2]:
        current = client.get("/proposals/" + proposal["id"]).json()
        client.write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": current["version"]})
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("CREATE TRIGGER reject_group BEFORE INSERT ON ko_groups BEGIN SELECT RAISE(ABORT,'private-internal'); END")
    current = clients[2].get("/proposals/" + proposal["id"]).json()
    result = clients[2].write("POST", "/proposals/" + proposal["id"] + "/respond", {"decision": "accepted", "version": current["version"]})
    assert result.status_code == 503 and "private-internal" not in result.text
    assert clients[2].get("/proposals/" + proposal["id"]).json()["my_response"] == "pending"


def test_database_restart_keeps_posts_permissions_and_sessions(harness):
    client = harness.client("aoi")
    draft(client)
    before = client.get("/communities/peers/feed").json()
    application = create_app(harness.settings)
    lifecycle = application.router.lifespan_context(application)
    harness.runner.run(lifecycle.__aenter__())
    restarted = Client(harness.runner, application)
    restarted.client.cookies.update(client.client.cookies)
    try:
        assert restarted.get("/communities/peers/feed").json() == before
        assert restarted.get("/me").json()["user"]["id"] == "u-aoi"
        with application.state.database.transaction() as conn:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        restarted.close()
        harness.runner.run(lifecycle.__aexit__(None, None, None))


def test_public_covers_allow_only_catalog_keys_and_keep_uploads_private(harness, tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    for key in ("woodland", "coffee", "coast", "table"):
        (assets / (key + ".png")).write_bytes(photo_bytes("PNG", exif=True))
    settings = Settings(db_path=tmp_path / "seeded.db", media_dir=tmp_path / "seeded-media", model_dir=tmp_path / "no-model", seed_asset_dir=assets, worker_enabled=False)
    app = create_app(settings)
    lifecycle = app.router.lifespan_context(app)
    harness.runner.run(lifecycle.__aenter__())
    client = Client(harness.runner, app)
    try:
        response = client.get("/covers/woodland")
        assert response.status_code == 200 and response.headers["content-type"] == "image/jpeg"
        assert b"private-camera-note" not in response.content
        assert client.get("/covers/secret").status_code == 404
        assert client.get("/covers/%2e%2e%2fcommunity.db").status_code == 404
        client.login("aoi")
        posts = client.get("/communities/campus/feed").json()["items"]
        assert len(posts) == 1
        private_url = posts[0]["media"][0]["url"][4:]
        assert client.get(private_url).status_code == 200
        client.write("POST", "/logout")
        assert client.get(private_url).status_code == 401
        app.state.service.seed_assets()
        client.login("aoi")
        assert len(client.get("/communities/campus/feed").json()["items"]) == 1
    finally:
        client.close()
        harness.runner.run(lifecycle.__aexit__(None, None, None))


def test_real_model_uses_pixels(tmp_path):
    root = Path(__file__).resolve().parents[2]
    assert (root / "models/mobilenetv2-12.onnx").is_file()
    model = LocalClassifier(root / "models")
    if model.session is None:
        if sys.platform == "win32":
            pytest.skip("Native ONNX runtime unavailable on Windows; real inference must be verified inside Docker")
        pytest.fail("The supplied real model must load in the Linux runtime")
    coast = root / "assets/coast.png"
    assert coast.exists()
    tags = model.classify(coast)
    assert any(tag["id"] == "coast" for tag in tags)


def test_analysis_lease_recovery_is_bounded_and_preserves_active_work(harness):
    client = harness.client("aoi")
    mid = upload(client).json()["id"]
    future = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE jobs SET status='running',attempts=1,lease_until=? WHERE media_id=?", (future, mid))
        harness.app.state.worker.recover_expired(conn)
        assert conn.execute("SELECT status FROM jobs WHERE media_id=?", (mid,)).fetchone()[0] == "running"
    assert not harness.app.state.worker.once()
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00+00:00' WHERE media_id=?", (mid,))
    assert harness.app.state.worker.once()
    with harness.app.state.database.transaction(True) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE media_id=?", (mid,)).fetchone()
        assert row["attempts"] == 2 and row["status"] == "failed"
        conn.execute("UPDATE jobs SET status='running',lease_until='2000-01-01T00:00:00+00:00' WHERE media_id=?", (mid,))
    assert not harness.app.state.worker.once()
    assert client.get("/media/" + mid + "/analysis").json()["status"] == "failed"
