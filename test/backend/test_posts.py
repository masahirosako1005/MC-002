"""Posting acceptance through authenticated APIs, with rollback and retry checks."""
import asyncio
import io
from pathlib import Path

import pytest
from PIL import Image
from test_api import photo_bytes, upload
from test_journal import add, journey


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def create(client, **changes):
    body = dict(community_id="peers", body="週末に歩いたまち", media_ids=[], tags=["walk"])
    body.update(changes)
    return client.write("POST", "/posts", body)


def shown(client, cid="peers"):
    return ok(client.get("/communities/" + cid + "/feed"))["items"]


def test_text_only_post_draft_publish_owner_tags_and_delete(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    post = ok(create(aoi, client_request_id="text-one"))
    pid = post["id"]
    assert post["status"] == "draft" and post["media"] == []
    assert any(item["id"] == pid for item in shown(aoi))
    assert all(item["id"] != pid for item in shown(ren))
    assert ren.write("PATCH", "/posts/" + pid, {"tags": ["food"]}).status_code == 404
    assert ren.write("DELETE", "/posts/" + pid).status_code == 404
    published = ok(aoi.write("PATCH", "/posts/" + pid, {"status": "published", "tags": ["cafe"]}))
    assert published["media"] == [] and published["tags"] == ["cafe"]
    peer = next(item for item in shown(ren) if item["id"] == pid)
    assert not peer["can_edit"] and peer["body"] == post["body"] and peer["tags"] == ["cafe"]
    ok(aoi.write("DELETE", "/posts/" + pid))
    ok(aoi.write("DELETE", "/posts/" + pid))
    assert all(item["id"] != pid for item in shown(aoi) + shown(ren))
    assert aoi.write("PATCH", "/posts/" + pid, {"status": "published"}).status_code == 404


@pytest.mark.parametrize("body", ["", " \n\t", "　"])
def test_empty_post_is_rejected_without_creating_rows(harness, body):
    aoi = harness.client("aoi")
    before = shown(aoi)
    assert create(aoi, body=body).status_code == 422
    assert aoi.write("POST", "/posts", {"community_id": "peers"}).status_code == 422
    assert shown(aoi) == before


def test_photo_only_post_private_preview_clean_bytes_and_shared_tags(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    photo = ok(upload(aoi, photo_bytes(exif=True)))
    mid = photo["id"]
    preview = aoi.get("/media/" + mid)
    assert preview.status_code == 200 and preview.headers["cache-control"] == "no-store"
    assert b"private-camera-note" not in preview.content
    with Image.open(io.BytesIO(preview.content)) as image:
        assert image.format == "JPEG" and not image.getexif()
    assert ren.get("/media/" + mid).status_code == 404
    assert ren.get("/media/" + mid + "/analysis").status_code == 404
    analysis = ok(aoi.get("/media/" + mid + "/analysis"))
    assert analysis == ok(aoi.write("POST", "/media/" + mid + "/analyze"))
    assert analysis["status"] == "manual" and not analysis["inference_enabled"]
    post = ok(create(aoi, body="", media_ids=[mid], tags=["nature"]))
    assert ren.get("/media/" + mid).status_code == 404
    ok(aoi.write("PATCH", "/posts/" + post["id"], {"status": "published"}))
    assert ren.get("/media/" + mid).status_code == 200
    shared = next(item for item in shown(ren) if item["id"] == post["id"])
    assert shared["tags"] == ["nature"] and shared["media"][0]["analysis"]["tags"] == []
    assert "location_candidate" not in shared["media"][0]
    ok(aoi.write("DELETE", "/posts/" + post["id"]))
    assert aoi.get("/media/" + mid).status_code == ren.get("/media/" + mid).status_code == 404
    assert not (harness.settings.media_dir / (mid + ".jpg")).exists()


def test_membership_is_required_for_create_edit_replay_and_shared_media(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    assert create(ren, community_id="campus").status_code == 404
    private = ok(create(aoi, community_id="campus"))
    ok(aoi.write("PATCH", "/posts/" + private["id"], {"status": "published"}))
    assert ren.get("/communities/campus/feed").status_code == 404
    photo = ok(upload(ren))
    own = ok(create(ren, client_request_id="before-leave", media_ids=[photo["id"]]))
    ok(ren.write("PATCH", "/posts/" + own["id"], {"status": "published"}))
    assert aoi.get("/media/" + photo["id"]).status_code == 200
    ok(ren.write("POST", "/communities/peers/leave"))
    assert aoi.get("/media/" + photo["id"]).status_code == 404
    assert ren.get("/communities/peers/feed").status_code == 404
    assert create(ren, client_request_id="before-leave").status_code == 404
    assert ren.write("PATCH", "/posts/" + own["id"], {"status": "published"}).status_code == 404
    # The former member may still erase their own retained post.
    ok(ren.write("DELETE", "/posts/" + own["id"]))


def test_retry_recovers_same_post_without_overwriting_or_changing_audience(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    first = ok(create(aoi, client_request_id="one-composer"))
    retry = ok(create(aoi, client_request_id="one-composer", body="通信後に書き直した文章"))
    assert retry == first
    latest = ok(aoi.write("PATCH", "/posts/" + first["id"], {"body": "確認して公開", "status": "published"}))
    assert ok(create(aoi, client_request_id="one-composer", body="古い送信")) == latest
    assert create(aoi, community_id="campus", client_request_id="one-composer").status_code == 409
    assert ok(create(ren, client_request_id="one-composer"))["id"] != first["id"]
    ok(aoi.write("DELETE", "/posts/" + first["id"]))
    assert create(aoi, client_request_id="one-composer").status_code == 409
    assert all(item["id"] != first["id"] for item in shown(aoi))


def test_concurrent_post_retries_create_one_draft(harness):
    aoi = harness.client("aoi")
    body = dict(community_id="peers", body="一度だけ保存", client_request_id="parallel-create")

    async def simultaneous():
        return await asyncio.gather(*(aoi.client.post("/api/posts", json=body) for _ in range(2)))

    results = harness.runner.run(simultaneous())
    ids = [ok(result)["id"] for result in results]
    assert ids[0] == ids[1]
    assert sum(item["id"] == ids[0] for item in shown(aoi)) == 1
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM operation_keys WHERE actor_id='u-aoi' AND operation='post:create' AND request_key='parallel-create'").fetchone()[0] == 1


def test_edit_replaces_and_reorders_owned_photos_without_deleting_detached_file(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    first, second, third = [ok(upload(aoi))["id"] for _ in range(3)]
    post = ok(create(aoi, media_ids=[first, second]))
    pid = post["id"]
    changed = ok(aoi.write("PATCH", "/posts/" + pid, {"media_ids": [third, second], "body": "写真を確認", "status": "published"}))
    assert [item["id"] for item in changed["media"]] == [third, second]
    assert ren.get("/media/" + first).status_code == 404
    assert ren.get("/media/" + third).status_code == 200
    assert aoi.get("/media/" + first).status_code == 200
    ok(aoi.write("DELETE", "/media/" + first))
    no_photos = ok(aoi.write("PATCH", "/posts/" + pid, {"media_ids": []}))
    assert no_photos["media"] == [] and no_photos["body"] == "写真を確認"
    assert ren.get("/media/" + third).status_code == 404
    assert aoi.write("PATCH", "/posts/" + pid, {"body": "  "}).status_code == 422
    assert next(item for item in shown(aoi) if item["id"] == pid) == no_photos


def test_photo_owner_reuse_duplicates_and_schema_fields_are_checked(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    own = ok(upload(aoi))["id"]
    foreign = ok(upload(ren))["id"]
    post = ok(create(aoi, media_ids=[own]))
    pid = post["id"]
    assert create(aoi, media_ids=[foreign]).status_code == 404
    assert create(aoi, media_ids=[own]).status_code == 409
    assert aoi.write("PATCH", "/posts/" + pid, {"media_ids": [foreign]}).status_code == 404
    assert aoi.write("PATCH", "/posts/" + pid, {"media_ids": [own, own]}).status_code == 422
    assert aoi.write("PATCH", "/posts/" + pid, {"media_ids": None}).status_code == 422
    assert create(aoi, media_ids=[own] * 6).status_code == 422
    assert create(aoi, user_id="u-ren").status_code == 422
    assert create(aoi, tags=["unlisted"]).status_code == 422
    assert create(aoi, tags=["walk", "walk"]).status_code == 422
    assert create(aoi, body="a" * 2001).status_code == 422
    assert aoi.write("PATCH", "/posts/" + pid, {"community_id": "campus"}).status_code == 422
    assert next(item for item in shown(aoi) if item["id"] == pid) == post


def test_publish_failure_rolls_back_all_content_and_media_changes_then_retry_succeeds(harness):
    aoi = harness.client("aoi")
    first, second = [ok(upload(aoi))["id"] for _ in range(2)]
    post = ok(create(aoi, media_ids=[first], client_request_id="save-retry"))
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("CREATE TRIGGER reject_post BEFORE UPDATE ON posts BEGIN SELECT RAISE(ABORT,'private-storage-error'); END")
    changes = dict(body="保存を確認した文", media_ids=[second], tags=["food"], status="published")
    failed = aoi.write("PATCH", "/posts/" + post["id"], changes)
    assert failed.status_code == 503 and "private-storage-error" not in failed.text
    assert next(item for item in shown(aoi) if item["id"] == post["id"]) == post
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("DROP TRIGGER reject_post")
    recovered = ok(create(aoi, client_request_id="save-retry", body="再送"))
    assert recovered["id"] == post["id"]
    saved = ok(aoi.write("PATCH", "/posts/" + post["id"], changes))
    assert saved["body"] == changes["body"] and saved["tags"] == ["food"]
    assert saved["status"] == "published" and saved["media"][0]["id"] == second


def test_create_failure_rolls_back_post_photo_link_and_retry_key(harness):
    aoi = harness.client("aoi")
    mid = ok(upload(aoi))["id"]
    before = shown(aoi)
    with harness.app.state.database.transaction(True) as conn:
        conn.execute("CREATE TRIGGER reject_post_key BEFORE INSERT ON operation_keys WHEN NEW.operation='post:create' BEGIN SELECT RAISE(ABORT,'private-key-error'); END")
    assert create(aoi, media_ids=[mid], client_request_id="retry-failed-create").status_code == 503
    assert shown(aoi) == before and aoi.get("/media/" + mid).status_code == 200
    with harness.app.state.database.transaction(True) as conn:
        assert conn.execute("SELECT COUNT(*) FROM post_media WHERE media_id=?", (mid,)).fetchone()[0] == 0
        conn.execute("DROP TRIGGER reject_post_key")
    assert ok(create(aoi, media_ids=[mid], client_request_id="retry-failed-create"))["media"][0]["id"] == mid


def test_unused_photo_discard_authorization_usage_guards_and_retry(harness):
    aoi, ren = harness.client("aoi"), harness.client("ren")
    mid = ok(upload(aoi))["id"]
    assert ren.write("DELETE", "/media/" + mid).status_code == 404
    assert aoi.write("DELETE", "/media/" + mid, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    post = ok(create(aoi, media_ids=[mid]))
    assert aoi.write("DELETE", "/media/" + mid).status_code == 409
    ok(aoi.write("PATCH", "/posts/" + post["id"], {"media_ids": []}))
    jid = journey(aoi)["id"]
    visit = add(aoi, jid, media_id=mid)
    assert aoi.write("DELETE", "/media/" + mid).status_code == 409
    assert aoi.get("/media/" + mid).status_code == 200
    # Guard preserves the confirmed visit rather than silently deleting it.
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT 1 FROM journal_visits WHERE id=?", (visit["id"],)).fetchone()
    spare = ok(upload(aoi))["id"]
    ok(aoi.write("DELETE", "/media/" + spare))
    ok(aoi.write("DELETE", "/media/" + spare))
    assert aoi.get("/media/" + spare).status_code == 404
    assert aoi.get("/media/" + spare + "/analysis").status_code == 404
    assert create(aoi, media_ids=[spare]).status_code == 404
    assert not (harness.settings.media_dir / (spare + ".jpg")).exists()


def test_failed_file_write_rolls_back_and_removes_partial_upload(harness, monkeypatch):
    aoi = harness.client("aoi")
    original = Path.write_bytes

    def fail_write(path, data):
        if path.parent == harness.settings.media_dir:
            original(path, data[:20])
            raise OSError("private-storage-path")
        return original(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    result = upload(aoi)
    assert result.status_code == 500 and "private-storage-path" not in result.text
    with harness.app.state.database.transaction() as conn:
        assert conn.execute("SELECT COUNT(*) FROM media WHERE user_id='u-aoi'").fetchone()[0] == 0
    assert list(harness.settings.media_dir.glob("*.jpg")) == []


def test_discard_denies_access_before_retrying_failed_file_cleanup(harness, monkeypatch):
    aoi = harness.client("aoi")
    mid = ok(upload(aoi))["id"]
    survivor = ok(upload(aoi))["id"]
    target = harness.settings.media_dir / (mid + ".jpg")
    original = Path.unlink

    def blocked(path, *args, **kwargs):
        if path == target:
            raise PermissionError("file-busy")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as locked:
        locked.setattr(Path, "unlink", blocked)
        ok(aoi.write("DELETE", "/media/" + mid))
        assert target.exists()
        assert aoi.get("/media/" + mid).status_code == 404
    ok(aoi.write("DELETE", "/media/" + mid))
    assert not target.exists()
    assert aoi.get("/media/" + survivor).status_code == 200


def test_post_response_models_filter_internal_fields(harness, monkeypatch):
    aoi = harness.client("aoi")
    original = harness.app.state.service.post_out

    def with_internal_fields(conn, row, uid):
        result = original(conn, row, uid)
        result["internal_record"] = "not-public"
        result["author"]["salt"] = "not-public"
        for media in result["media"]:
            media["storage_key"] = "not-public"
            media["location_candidate"] = {"latitude": 1, "longitude": 2}
        return result

    monkeypatch.setattr(harness.app.state.service, "post_out", with_internal_fields)
    photo = ok(upload(aoi))
    result = create(aoi, media_ids=[photo["id"]])
    assert result.status_code == 200 and "not-public" not in result.text
    assert "location_candidate" not in result.json()["media"][0]
    response = aoi.get("/communities/peers/feed")
    assert response.status_code == 200 and "not-public" not in response.text
