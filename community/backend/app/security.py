import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
import secrets
import threading
import time

from fastapi import HTTPException, Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from .database import digest

COOKIE = "ko_session"
SAFE = {"GET", "HEAD", "OPTIONS"}
HEADERS = {
    "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(),microphone=(),geolocation=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
}


def current_session(request: Request):
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 128:
        return None
    with request.app.state.database.transaction() as conn:
        return conn.execute("SELECT s.*,u.username,u.name,u.initials,u.color FROM sessions s JOIN users u ON u.id=s.user_id WHERE token_hash=? AND expires_at>?", (digest(token), datetime.now(timezone.utc).isoformat())).fetchone()


def csrf(request, session):
    supplied = request.headers.get("x-csrf-token", "")
    if len(supplied) > 128 or not secrets.compare_digest(supplied.encode(), session["csrf_token"].encode()):
        raise HTTPException(403, "接続が切り替わりました。画面を開き直してください。", headers={"X-Session-Invalid": "true"})


def authenticated(request: Request):
    session = current_session(request)
    if session is None:
        raise HTTPException(401, "ログインしてください。")
    if request.method not in SAFE:
        csrf(request, session)
    return session


class SecurityMiddleware:
    def __init__(self, app, settings):
        self.app, self.settings = app, settings
        self.windows = defaultdict(deque)
        self.lock = threading.Lock()

    def rate_allowed(self, address, kind):
        moment = time.monotonic()
        with self.lock:
            for key in list(self.windows):
                if not self.windows[key] or self.windows[key][-1] < moment - 60:
                    del self.windows[key]
            if (address, kind) not in self.windows and len(self.windows) >= 1000:
                return False
            window = self.windows[(address, kind)]
            while window and window[0] < moment - 60:
                window.popleft()
            if len(window) >= (20 if kind == "login" else 30 if kind == "upload" else 120):
                return False
            window.append(moment)
            return True

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).update(HEADERS)
            await send(message)

        async def reject(code, detail):
            await JSONResponse({"detail": detail}, status_code=code, headers={"Retry-After": "60"} if code == 429 else None)(scope, receive, secure_send)

        if headers.get("host", "").lower() not in self.settings.allowed_hosts:
            return await reject(400, "接続先を確認してください。")
        if scope["method"] not in SAFE:
            if headers.get("origin") not in self.settings.allowed_origins or headers.get("sec-fetch-site") == "cross-site":
                return await reject(403, "この画面からの操作を確認できません。")
            upload = scope["path"] == "/api/media" and scope["method"] == "POST"
            expected = "multipart/form-data" if upload else "application/json"
            if headers.get("content-type", "").split(";", 1)[0].lower().strip() != expected:
                return await reject(415, "送信形式を確認してください。")
            kind = "login" if scope["path"] == "/api/login" else "upload" if upload else "write"
            if not self.rate_allowed((scope.get("client") or ("local",))[0], kind):
                return await reject(429, "操作が続いています。少し待って試してください。")
            limit = self.settings.max_image_bytes + 65536 if upload else 65536
            body = bytearray()
            while True:
                try:
                    incoming = await asyncio.wait_for(receive(), timeout=15)
                except TimeoutError:
                    return await reject(408, "送信に時間がかかりました。")
                if incoming["type"] == "http.disconnect":
                    return
                body.extend(incoming.get("body", b""))
                if len(body) > limit:
                    return await reject(413, "画像または入力が大きすぎます。")
                if not incoming.get("more_body", False):
                    break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()
            return await self.app(scope, bounded_receive, secure_send)
        await self.app(scope, receive, secure_send)
