import asyncio
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.config import Settings
from app.main import create_app


class Client:
    def __init__(self, runner, app):
        self.runner = runner
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://localhost:8001", headers={"Origin": "http://localhost:8001"})
        runner.run(self.client.__aenter__())

    def request(self, method, path, **kwargs):
        return self.runner.run(self.client.request(method, "/api" + path, **kwargs))

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def write(self, method, path, body=None, **kwargs):
        return self.request(method, path, json={} if body is None else body, **kwargs)

    def login(self, username):
        response = self.write("POST", "/login", {"username": username, "password": username + "-local-2026"})
        assert response.status_code == 200, response.text
        self.client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return response

    def close(self):
        self.runner.run(self.client.aclose())


@dataclass
class Harness:
    app: object
    settings: object
    runner: object
    clients: list

    def client(self, username=None):
        client = Client(self.runner, self.app)
        self.clients.append(client)
        if username:
            client.login(username)
        return client


@pytest.fixture(scope="session")
def database_template(tmp_path_factory):
    """Seed using the real application/KDF; snapshot the closed database."""
    root = tmp_path_factory.mktemp("seed-template")
    settings = Settings(db_path=root / "seed.db", media_dir=root / "media", model_dir=root / "no-model", worker_enabled=False)
    app = create_app(settings)
    with asyncio.Runner() as runner:
        lifecycle = app.router.lifespan_context(app)
        runner.run(lifecycle.__aenter__())
        runner.run(lifecycle.__aexit__(None, None, None))
    target = root / "template.db"
    with sqlite3.connect(settings.db_path) as source, sqlite3.connect(target) as snapshot:
        source.backup(snapshot)
    return target


@pytest.fixture
def harness(tmp_path, database_template):
    settings = Settings(db_path=tmp_path / "community.db", media_dir=tmp_path / "media", model_dir=tmp_path / "no-model", worker_enabled=False)
    shutil.copyfile(database_template, settings.db_path)
    app = create_app(settings)
    with asyncio.Runner() as runner:
        lifecycle = app.router.lifespan_context(app)
        runner.run(lifecycle.__aenter__())
        harness = Harness(app, settings, runner, [])
        yield harness
        for client in harness.clients:
            client.close()
        runner.run(lifecycle.__aexit__(None, None, None))
