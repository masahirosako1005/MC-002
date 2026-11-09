import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clock import JST
from app.config import Settings
from app.main import create_app


class Client:
    def __init__(self, runner: asyncio.Runner, application):
        self.runner = runner
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=application, raise_app_exceptions=False), base_url="http://localhost:8000", headers={"Origin": "http://localhost:8000"})
        runner.run(self.client.__aenter__())

    def request(self, method: str, path: str, **kwargs):
        return self.runner.run(self.client.request(method, "/api" + path, **kwargs))

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, body: dict | None = None, **kwargs):
        return self.request("POST", path, json={} if body is None else body, **kwargs)

    def login(self):
        response = self.post("/session")
        assert response.status_code == 200, response.text
        self.client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return response

    def close(self):
        self.runner.run(self.client.aclose())


@dataclass
class Harness:
    app: object
    client: Client
    runner: asyncio.Runner
    current: list[datetime]
    clients: list[Client]
    settings: Settings

    def another(self) -> Client:
        client = Client(self.runner, self.app)
        self.clients.append(client)
        client.login()
        return client

    def visit(self, client: Client | None = None):
        return (client or self.client).post("/visits", {"spot_id": "watergate", "code": "GATE-314"})

    def start(self, difficulty: str = "beginner", client: Client | None = None):
        client = client or self.client
        games = client.get("/catalog").json()["games"]
        game = next(game for game in games if game["season"] == "autumn" and game["difficulty"] == difficulty)
        return client.post("/attempts", {"game_id": game["id"]})


@pytest.fixture
def harness(tmp_path):
    current = [datetime(2026, 11, 9, 10, 0, tzinfo=JST)]
    settings = Settings(db_path=tmp_path / "journal.sqlite3")
    application = create_app(settings, now_provider=lambda: current[0])
    with asyncio.Runner() as runner:
        lifecycle = application.router.lifespan_context(application)
        runner.run(lifecycle.__aenter__())
        client = Client(runner, application)
        clients = [client]
        client.login()
        yield Harness(application, client, runner, current, clients, settings)
        for item in clients:
            item.close()
        runner.run(lifecycle.__aexit__(None, None, None))
