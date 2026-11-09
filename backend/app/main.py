from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging
from pathlib import Path
import secrets
import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import clock
from .config import Settings
from .database import Database
from .models import (
    AnswerInput, AnswerOut, AttemptInput, CatalogOut, DeletedOut, EmptyInput, HealthOut,
    HintOut, JournalOut, LeaderboardOut, PlanInput, PlanOut, RecommendationsOut, RecoveryInput, RecoveryOut,
    Season, SessionOut, StartedAttemptOut, VisitInput, VisitOut,
)
from .security import COOKIE_NAME, SecurityMiddleware, authenticated, check_csrf, find_session, request_time, response_security_headers
from .seed import fingerprint
from .service import JourneyService, identifier


logger = logging.getLogger("journey")


def create_app(settings: Settings | None = None, now_provider: Callable[[], datetime] = clock.now) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings.db_path)
    service = JourneyService(database)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database.initialize(clock.local_time(application.state.clock()))
        yield

    application = FastAPI(title="旅の手帳", debug=False, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    application.state.database = database
    application.state.clock = now_provider
    application.add_middleware(SecurityMiddleware, settings=settings)

    @application.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "入力内容を確認してください。項目や値の形式が正しくありません。"}, status_code=422)

    @application.exception_handler(sqlite3.Error)
    async def database_error(request: Request, exc: sqlite3.Error) -> JSONResponse:
        logger.error("Database operation failed (%s)", type(exc).__name__)
        return JSONResponse({"detail": "記録を読み書きできませんでした。少し待ってからもう一度試してください。"}, status_code=503)

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = {404: "ページや記録が見つかりません。", 405: "この操作には対応していません。"}.get(exc.status_code, "操作を完了できませんでした。")
        if isinstance(exc, HTTPException):
            detail = str(exc.detail)
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unexpected operation failure (%s)", type(exc).__name__)
        return JSONResponse({"detail": "操作を完了できませんでした。画面を開き直してください。"}, status_code=500, headers=response_security_headers(request.url.path))

    public = APIRouter(prefix="/api")
    protected = APIRouter(prefix="/api", dependencies=[Depends(authenticated)])

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.secure_cookie, samesite="strict", path="/", max_age=settings.session_days * 86_400)

    @public.get("/health", response_model=HealthOut)
    def health() -> dict[str, str]:
        with database.transaction() as connection:
            connection.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return {"status": "ok"}

    @public.post("/session", response_model=SessionOut)
    def open_session(body: EmptyInput, request: Request, response: Response,
                     current: datetime = Depends(request_time)) -> dict[str, str]:
        existing = find_session(request, current)
        if existing is not None:
            check_csrf(request, existing)
            return {"nickname": existing["nickname"], "csrf_token": existing["csrf_token"]}
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        user_id = identifier()
        with database.transaction(write=True) as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at<=?", (current.isoformat(),))
            connection.execute("INSERT INTO users VALUES (?, '旅人', ?)", (user_id, current.isoformat()))
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?)", (fingerprint(token), user_id, csrf_token, (current + timedelta(days=settings.session_days)).isoformat()))
        set_session_cookie(response, token)
        return {"nickname": "旅人", "csrf_token": csrf_token}

    @protected.post("/recovery", response_model=RecoveryOut)
    def create_recovery(body: EmptyInput, session: sqlite3.Row = Depends(authenticated),
                        current: datetime = Depends(request_time)) -> dict[str, str]:
        recovery_code = "TC-" + secrets.token_urlsafe(32)
        with database.transaction(write=True) as connection:
            connection.execute(
                "INSERT INTO recovery_codes VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET code_hash=excluded.code_hash,created_at=excluded.created_at",
                (session["user_id"], fingerprint(recovery_code), current.isoformat()),
            )
        return {"recovery_code": recovery_code}

    @public.post("/session/recover", response_model=SessionOut)
    def recover_session(body: RecoveryInput, request: Request, response: Response,
                        current: datetime = Depends(request_time)) -> dict[str, str]:
        existing = find_session(request, current)
        if existing is not None:
            check_csrf(request, existing)
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        with database.transaction(write=True) as connection:
            owner = connection.execute("SELECT r.user_id,u.nickname FROM recovery_codes r JOIN users u ON u.id=r.user_id WHERE r.code_hash=?", (fingerprint(body.recovery_code),)).fetchone()
            if owner is None:
                raise HTTPException(401, "手帳を復旧できませんでした。保存した復旧コードを確認してください。")
            connection.execute("DELETE FROM sessions WHERE user_id=?", (owner["user_id"],))
            connection.execute("INSERT INTO sessions VALUES (?,?,?,?)", (fingerprint(token), owner["user_id"], csrf_token, (current + timedelta(days=settings.session_days)).isoformat()))
        set_session_cookie(response, token)
        return {"nickname": owner["nickname"], "csrf_token": csrf_token}

    @protected.get("/session", response_model=SessionOut)
    def current_session(session: sqlite3.Row = Depends(authenticated)) -> dict[str, str]:
        return {"nickname": session["nickname"], "csrf_token": session["csrf_token"]}

    @public.get("/catalog", response_model=CatalogOut)
    def catalog(current: datetime = Depends(request_time)) -> dict:
        return service.catalog(current)

    @protected.get("/journal", response_model=JournalOut)
    def journal(session: sqlite3.Row = Depends(authenticated)) -> dict:
        return service.journal(session["user_id"])

    @protected.post("/visits", response_model=VisitOut)
    def visit(body: VisitInput, session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.visit(session["user_id"], body.spot_id, body.code, current)

    @protected.post("/attempts", response_model=StartedAttemptOut)
    def start_attempt(body: AttemptInput, session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.start_attempt(session["user_id"], body.game_id, current)

    @protected.post("/attempts/{attempt_id}/hint", response_model=HintOut)
    def hint(attempt_id: str, body: EmptyInput, session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.hint(session["user_id"], attempt_id, current)

    @protected.post("/attempts/{attempt_id}/answer", response_model=AnswerOut)
    def answer(attempt_id: str, body: AnswerInput, session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.answer(session["user_id"], attempt_id, body.values, current)

    @public.get("/leaderboard", response_model=LeaderboardOut)
    def leaderboard(game_id: Annotated[str, Query(min_length=1, max_length=100)]) -> dict:
        return service.leaderboard(game_id)

    @protected.get("/recommendations", response_model=RecommendationsOut)
    def recommendations(minutes: Annotated[int, Query(ge=15, le=240)] = 90,
                        season: Season | None = None, interest: Literal["all", "shrine", "coast"] = "all",
                        session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.recommendations(session["user_id"], minutes, season or clock.season_at(current), interest, current)

    @protected.post("/plans", response_model=PlanOut)
    def save_plan(body: PlanInput, session: sqlite3.Row = Depends(authenticated), current: datetime = Depends(request_time)) -> dict:
        return service.save_plan(session["user_id"], body.experience_id, body.reason, current)

    @protected.delete("/plans/{plan_id}", response_model=DeletedOut)
    def delete_plan(plan_id: str, session: sqlite3.Row = Depends(authenticated)) -> dict:
        return service.delete_plan(session["user_id"], plan_id)

    application.include_router(public)
    application.include_router(protected)

    @application.api_route("/api", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"])
    @application.api_route("/api/{unknown:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"])
    def missing_api(unknown: str = "") -> None:
        raise HTTPException(404, "この操作は見つかりません。")

    if settings.static_dir is not None:
        static_root = settings.static_dir.resolve()

        @application.get("/{path:path}", response_model=None)
        def static_file(path: str) -> FileResponse:
            candidate = (static_root / path).resolve()
            if not candidate.is_relative_to(static_root) or any(part.startswith(".") for part in Path(path).parts):
                raise HTTPException(404, "ページが見つかりません。")
            if candidate.is_file():
                return FileResponse(candidate)
            if Path(path).suffix or not (static_root / "index.html").is_file():
                raise HTTPException(404, "ページが見つかりません。")
            return FileResponse(static_root / "index.html")

    return application


app = create_app()
