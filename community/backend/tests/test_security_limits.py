import logging
import sqlite3
from types import SimpleNamespace

import pytest
from app import security
from fastapi import Depends, Request


def fixed_clock(monkeypatch):
    clock = [10000.0]
    # Replace this module's dependency rather than the process-wide monotonic
    # clock, so ASGI event-loop timeout behavior remains unchanged.
    monkeypatch.setattr(security, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    return clock


def test_login_bucket_rejects_21st_attempt_and_recovers_after_window(harness, monkeypatch):
    clock = fixed_clock(monkeypatch)
    client = harness.client()
    body = {"username": "aoi", "password": "incorrect-local-fixture-password"}
    for index in range(20):
        endpoint = "/login" if index % 2 else "/stage/login"
        assert client.write("POST", endpoint, body).status_code == 401
    blocked = client.write("POST", "/stage/login", body)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    # Read-only recovery/help endpoints remain accessible.
    assert client.get("/bootstrap").status_code == 200
    clock[0] += 61
    assert client.write("POST", "/login", body).status_code == 401
    assert (
        client.write(
            "POST", "/login", {"username": "aoi", "password": "aoi-local-2026"}
        ).status_code
        == 200
    )


def test_write_bucket_rejects_121st_attempt_and_recovers_without_data_mutation(
    harness, monkeypatch
):
    clock = fixed_clock(monkeypatch)
    client = harness.client("aoi")
    before = client.get("/communities").json()
    invalid = {"name": "", "description": ""}
    for _ in range(120):
        assert client.write("POST", "/communities", invalid).status_code == 422
    blocked = client.write("POST", "/communities", invalid)
    assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "60"
    assert client.get("/communities").json() == before
    clock[0] += 61
    assert client.write("POST", "/communities", invalid).status_code == 422
    assert client.get("/communities").json() == before


@pytest.mark.parametrize("failure,status", [("database", 503), ("unexpected", 500)])
def test_exception_logs_and_responses_do_not_echo_private_values(harness, caplog, failure, status):
    # Test-only endpoint exercises the actual application's exception handlers,
    # authentication, CSRF and bounded-body middleware. It never stores input.
    async def failing_route(request: Request, session=Depends(security.authenticated)):
        body = await request.json()
        if failure == "database":
            raise sqlite3.OperationalError(str(body))
        raise RuntimeError(str(body))

    before = len(harness.app.router.routes)
    harness.app.add_api_route("/api/security-test-failure", failing_route, methods=["POST"])
    routes = harness.app.router.routes
    routes[:] = routes[before:] + routes[:before]
    client = harness.client("aoi")
    sentinels = {
        "password": "PRIVATE-PASSWORD-SENTINEL-CP14",
        "access_token": "PRIVATE-TOKEN-SENTINEL-CP14",
        "body": "PRIVATE-MESSAGE-SENTINEL-CP14",
    }
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        response = client.write("POST", "/security-test-failure", sentinels)
    assert response.status_code == status
    assert any(record.name == "ko" and record.levelno == logging.ERROR for record in caplog.records)
    assert all(
        value not in response.text and value not in caplog.text for value in sentinels.values()
    )
    assert "Traceback" not in response.text


def test_validation_and_login_errors_do_not_echo_private_values(harness, caplog):
    client = harness.client("aoi")
    private = "PRIVATE-VALIDATION-SENTINEL-CP14"
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        invalid = client.write("PUT", "/me/preferences", {"unknown_private_field": private})
        login = client.write("POST", "/login", {"username": "aoi", "password": private})
    assert invalid.status_code == 422 and login.status_code == 401
    assert private not in invalid.text and private not in login.text and private not in caplog.text
