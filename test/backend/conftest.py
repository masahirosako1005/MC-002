import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys
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


@pytest.fixture
def harness(tmp_path):
    settings = Settings(db_path=tmp_path / "community.db", media_dir=tmp_path / "media", model_dir=tmp_path / "no-model", worker_enabled=False)
    app = create_app(settings)
    with asyncio.Runner() as runner:
        lifecycle = app.router.lifespan_context(app)
        runner.run(lifecycle.__aenter__())
        harness = Harness(app, settings, runner, [])
        yield harness
        for client in harness.clients:
            client.close()
        runner.run(lifecycle.__aexit__(None, None, None))
