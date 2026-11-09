import asyncio
from collections import defaultdict, deque
import secrets
import sqlite3
import threading
import time
from datetime import datetime

from fastapi import Depends, HTTPException, Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .clock import local_time
from .config import Settings
from .seed import fingerprint


COOKIE_NAME = "journey_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def request_time(request: Request) -> datetime:
    return local_time(request.app.state.clock())


def find_session(request: Request, current: datetime) -> sqlite3.Row | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        return None
    with request.app.state.database.transaction() as connection:
        return connection.execute(
            "SELECT s.user_id, s.csrf_token, u.nickname FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>?", (fingerprint(token), current.isoformat()),
        ).fetchone()


def check_csrf(request: Request, session: sqlite3.Row) -> None:
    supplied = request.headers.get("x-csrf-token", "")
    if len(supplied) > 128 or not secrets.compare_digest(supplied.encode("utf-8"), session["csrf_token"].encode("utf-8")):
        raise HTTPException(403, "操作の確認情報が一致しません。画面を開き直してください。")


def authenticated(request: Request, current: datetime = Depends(request_time)) -> sqlite3.Row:
    session = find_session(request, current)
    if session is None:
        raise HTTPException(401, "旅の手帳を開き直してください。")
    if request.method not in SAFE_METHODS:
        check_csrf(request, session)
    return session


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.settings = settings
        self.windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def rate_allowed(self, key: tuple[str, str], limit: int) -> bool:
        current = time.monotonic()
        with self.lock:
            for stale in [item for item, times in self.windows.items() if not times or times[-1] <= current - 60]:
                del self.windows[stale]
            if key not in self.windows and len(self.windows) >= 1000:
                return False
            window = self.windows[key]
            while window and window[0] <= current - 60:
                window.popleft()
            if len(window) >= limit:
                return False
            window.append(current)
            return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)

        async def secure_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                output = MutableHeaders(scope=message)
                output["X-Content-Type-Options"] = "nosniff"
                output["X-Frame-Options"] = "DENY"
                output["Referrer-Policy"] = "no-referrer"
                output["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                output["Content-Security-Policy"] = (
                    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                    "font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
                    "base-uri 'none'; form-action 'self'"
                )
                if scope["path"].startswith("/api"):
                    output["Cache-Control"] = "no-store"
            await send(message)

        async def reject(status: int, detail: str) -> None:
            response = JSONResponse({"detail": detail}, status_code=status)
            if status == 429:
                response.headers["Retry-After"] = "60"
            await response(scope, receive, secure_send)

        host = headers.get("host", "").lower()
        if host not in self.settings.allowed_hosts:
            await reject(400, "この接続先からは利用できません。")
            return
        if scope["method"] not in SAFE_METHODS:
            if headers.get("origin") not in self.settings.allowed_origins or headers.get("sec-fetch-site") == "cross-site":
                await reject(403, "この画面からの操作を確認できません。")
                return
            if headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                await reject(415, "送信形式が正しくありません。")
                return
            group = "recovery" if scope["path"] == "/api/session/recover" else "session" if scope["path"] == "/api/session" else "write"
            address = scope.get("client") or ("local", 0)
            limit = self.settings.recoveries_per_minute if group == "recovery" else self.settings.sessions_per_minute if group == "session" else self.settings.writes_per_minute
            if not self.rate_allowed((address[0], group), limit):
                await reject(429, "操作が続いています。1分待ってから試してください。")
                return
            body = bytearray()
            while True:
                try:
                    incoming = await asyncio.wait_for(receive(), timeout=10)
                except TimeoutError:
                    await reject(408, "送信に時間がかかりました。もう一度試してください。")
                    return
                if incoming["type"] == "http.disconnect":
                    return
                body.extend(incoming.get("body", b""))
                if len(body) > self.settings.max_body_bytes:
                    await reject(413, "入力が長すぎます。内容を短くしてください。")
                    return
                if not incoming.get("more_body", False):
                    break
            delivered = False

            async def limited_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, limited_receive, secure_send)
            return
        await self.app(scope, receive, secure_send)
