import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .analytics.router import create_router as analytics_router
from .circles.discovery_schema import migrate as migrate_discovery
from .circles.router import create_router as circles_router
from .circles.schema import migrate as migrate_circles
from .city_registry import migrate as migrate_city_registry
from .config import Settings
from .database import TAGS, Database, digest
from .daytrip.router import create_router as daytrip_router
from .daytrip.schema import migrate as migrate_daytrip
from .image_guidance import IMAGE_PROCESSING, ImageGuidance
from .images import AnalysisWorker
from .journal.router import create_router as journal_router
from .journal.schema import migrate as migrate_journal
from .marketplace.router import create_router as marketplace_router
from .marketplace.schema import migrate
from .occasions.router import create_router as occasions_router
from .occasions.schema import migrate as migrate_occasions
from .personalization.router import create_router as personalization_router
from .personalization.schema import migrate as migrate_personalization
from .programs.router import create_router as programs_router
from .programs.schema import migrate as migrate_programs
from .reflections.router import create_router as reflections_router
from .reflections.schema import migrate as migrate_reflections
from .residence.router import create_router as residence_router
from .residence.schema import migrate as migrate_residence
from .schemas import (
    CommunityInput,
    ContributionInput,
    Empty,
    Id,
    JoinInput,
    Login,
    PhotoAnalysis,
    PlanInput,
    PostFeed,
    PostInput,
    PostOutput,
    PostPatch,
    PreferencesInput,
    ProposalInput,
    Removed,
    ResponseInput,
    UploadedMedia,
)
from .security import COOKIE, HEADERS, SecurityMiddleware, authenticated, csrf, current_session
from .service import COVER_KEYS, TRIP_BY_ID, Service, user_out

logger = logging.getLogger("ko")
CurrentSession = Annotated[sqlite3.Row, Depends(authenticated)]


def discard_media(mid: Id, body: Empty, request: Request, session: CurrentSession):
    return request.app.state.service.delete_unused_media(session["user_id"], mid)


def create_app(settings=None):
    settings = settings or Settings()
    database = Database(settings.db_path)
    classifier = ImageGuidance()
    service = Service(database, settings, classifier)
    worker = AnalysisWorker(database, settings, classifier)

    @asynccontextmanager
    async def lifespan(application):
        database.initialize()
        migrate(database)
        migrate_journal(database)
        migrate_circles(database)
        migrate_discovery(database)
        migrate_reflections(database)
        migrate_occasions(database)
        migrate_personalization(database)
        migrate_daytrip(database)
        migrate_residence(database)
        migrate_programs(database)
        migrate_city_registry(database)
        settings.media_dir.mkdir(parents=True, exist_ok=True)
        worker.cleanup_deleted()
        service.seed_assets()
        if settings.worker_enabled:
            worker.start()
        yield
        if settings.worker_enabled:
            worker.close()

    app = FastAPI(title="講の旅じたく", debug=False, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.database, app.state.service, app.state.worker, app.state.classifier = database, service, worker, classifier
    app.add_middleware(SecurityMiddleware, settings=settings)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exception):
        return JSONResponse({"detail": "入力の項目や値を確認してください。"}, status_code=422, headers=HEADERS)

    @app.exception_handler(sqlite3.Error)
    async def db_error(request, exception):
        logger.error("Database operation failed (%s)", type(exception).__name__)
        return JSONResponse({"detail": "記録を保存・読込できませんでした。もう一度試してください。"}, status_code=503, headers=HEADERS)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exception):
        detail = str(exception.detail) if isinstance(exception, HTTPException) else "ページまたは操作が見つかりません。"
        return JSONResponse({"detail": detail}, status_code=exception.status_code, headers={**HEADERS, **(exception.headers or {})})

    @app.exception_handler(Exception)
    async def unexpected(request, exception):
        logger.error("Operation failed (%s)", type(exception).__name__)
        return JSONResponse({"detail": "操作を完了できませんでした。画面を開き直してください。"}, status_code=500, headers=HEADERS)

    public = APIRouter(prefix="/api")
    private = APIRouter(prefix="/api", dependencies=[Depends(authenticated)])

    @public.get("/health")
    def health():
        with database.transaction() as conn:
            conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return {"status": "ok"}

    @public.get("/bootstrap")
    def bootstrap():
        return {"tags": [{"id": key, "label": label} for key, label in TAGS.items()],
                "model": dict(IMAGE_PROCESSING)}

    @public.get("/covers/{key}")
    def cover(key: str):
        if key not in COVER_KEYS:
            raise HTTPException(404, "写真が見つかりません。")
        path = settings.media_dir / "covers" / (key + ".jpg")
        if not path.is_file():
            raise HTTPException(404, "写真が見つかりません。")
        return FileResponse(path, media_type="image/jpeg")

    @public.post("/login")
    def login(body: Login, request: Request, response: Response):
        old = current_session(request)
        if old is not None:
            csrf(request, old)
        result, token = service.login(body.username, body.password, old["token_hash"] if old else None)
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=settings.secure_cookie, path="/", max_age=30 * 86400)
        return result

    @private.get("/me")
    def me(session=Depends(authenticated)):
        return {"user": user_out(session), "csrf_token": session["csrf_token"]}

    @public.post('/stage/login')
    def stage_login(body: Login):
        # Password authentication is shared; stage tokens never become cookies.
        result, token = service.login(body.username, body.password, None)
        expires_at = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
        with database.transaction(True) as conn:
            row = conn.execute('SELECT * FROM sessions WHERE token_hash=?', (digest(token),)).fetchone()
            conn.execute('INSERT INTO stage_sessions VALUES(?,?,?,?)', (row['token_hash'],row['user_id'],row['csrf_token'],expires_at))
            conn.execute('DELETE FROM sessions WHERE token_hash=?', (row['token_hash'],))
            conn.execute('DELETE FROM stage_sessions WHERE expires_at<=?', (datetime.now(UTC).isoformat(),))
        return {**result,'access_token':token,'expires_at':expires_at}

    @private.post("/logout")
    def logout(body: Empty, request: Request, response: Response, session=Depends(authenticated)):
        with database.transaction(True) as conn:
            table = 'stage_sessions' if request.headers.get('authorization') is not None else 'sessions'
            conn.execute(f"DELETE FROM {table} WHERE token_hash=?", (session["token_hash"],))
        if request.headers.get('authorization') is None:
            response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=settings.secure_cookie)
        return {"ok": True}

    @private.get("/communities")
    def communities(session=Depends(authenticated)):
        return service.communities(session["user_id"])

    @private.post("/communities")
    def create_community(body: CommunityInput, session=Depends(authenticated)):
        return service.create_community(session["user_id"], body.model_dump())

    @private.post("/communities/join")
    def join(body: JoinInput, session=Depends(authenticated)):
        return service.join(session["user_id"], body.invite_code)

    @private.get("/communities/{cid}")
    def community(cid: str, session=Depends(authenticated)):
        return service.community(session["user_id"], cid)

    @private.post("/communities/{cid}/leave")
    def leave(cid: str, body: Empty, session=Depends(authenticated)):
        return service.leave(session["user_id"], cid)

    @private.get("/communities/{cid}/feed", response_model=PostFeed)
    def feed(cid: Id, session: CurrentSession, before: Id | None = None,
             limit: Annotated[int, Query(ge=1, le=100)] = 24):
        return service.feed(session["user_id"], cid, before, limit)

    @private.post("/media", response_model=UploadedMedia)
    async def upload(request: Request, session: CurrentSession, read_location: bool = False):
        async with request.form(max_files=1, max_fields=0, max_part_size=settings.max_image_bytes) as form:
            file = form.get("file")
            if len(form) != 1 or file is None or not hasattr(file, "read"):
                raise HTTPException(422, "写真を1枚選んでください。")
            raw = await file.read(settings.max_image_bytes + 1)
        return await asyncio.to_thread(service.upload, session["user_id"], raw, read_location)

    @private.get("/media/{mid}/analysis", response_model=PhotoAnalysis)
    def analysis(mid: Id, session: CurrentSession):
        return service.analysis(session["user_id"], mid)

    @private.post("/media/{mid}/analyze", response_model=PhotoAnalysis)
    def analyze(mid: Id, body: Empty, session: CurrentSession):
        return service.analysis(session["user_id"], mid, True)

    @private.get("/media/{mid}")
    def media(mid: Id, session: CurrentSession):
        path = service.media_path(session["user_id"], mid)
        if not path.is_file():
            raise HTTPException(404, "写真が見つかりません。")
        return FileResponse(path, media_type="image/jpeg")

    private.add_api_route("/media/{mid}", discard_media, methods=["DELETE"], response_model=Removed)

    @private.post("/posts", response_model=PostOutput)
    def post(body: PostInput, session: CurrentSession):
        return service.create_post(session["user_id"], body.model_dump(mode="json"))

    @private.patch("/posts/{pid}", response_model=PostOutput)
    def patch(pid: Id, body: PostPatch, session: CurrentSession):
        return service.patch_post(session["user_id"], pid, body.model_dump(mode="json", exclude_unset=True))

    @private.delete("/posts/{pid}", response_model=Removed)
    def delete(pid: Id, body: Empty, session: CurrentSession):
        return service.delete_post(session["user_id"], pid)

    @private.get("/me/preferences")
    def preferences(session=Depends(authenticated)):
        return service.preferences(session["user_id"])

    @private.put("/me/preferences")
    def update_preferences(body: PreferencesInput, session=Depends(authenticated)):
        return service.preferences(session["user_id"], body.model_dump())

    @private.get("/trips")
    def trips():
        return {"items": list(TRIP_BY_ID.values())}

    @private.post("/communities/{cid}/proposals")
    def propose(cid: str, body: ProposalInput, session=Depends(authenticated)):
        return service.propose(session["user_id"], cid, body.model_dump(mode="json"))

    @private.get("/proposals")
    def proposals(session=Depends(authenticated)):
        return service.proposals(session["user_id"])

    @private.get("/proposals/{pid}")
    def proposal(pid: str, session=Depends(authenticated)):
        return service.proposals(session["user_id"], pid)

    @private.post("/proposals/{pid}/respond")
    def respond(pid: str, body: ResponseInput, session=Depends(authenticated)):
        return service.respond(session["user_id"], pid, body.model_dump())

    @private.get("/groups")
    def groups(session=Depends(authenticated)):
        return service.groups(session["user_id"])

    @private.get("/groups/{gid}")
    def group(gid: str, session=Depends(authenticated)):
        return service.groups(session["user_id"], gid)

    @private.put("/groups/{gid}/contribution")
    def contribution(gid: str, body: ContributionInput, session=Depends(authenticated)):
        return service.update_group(session["user_id"], gid, body.model_dump(), True)

    @private.put("/groups/{gid}/plan")
    def plan(gid: str, body: PlanInput, session=Depends(authenticated)):
        return service.update_group(session["user_id"], gid, body.model_dump(mode="json"))

    app.include_router(public)
    app.include_router(private)
    app.include_router(marketplace_router(database))
    app.include_router(journal_router(database))
    app.include_router(circles_router(database))
    app.include_router(reflections_router(database))
    app.include_router(occasions_router(database))
    app.include_router(personalization_router(database))
    app.include_router(daytrip_router(database))
    app.include_router(analytics_router(database))
    app.include_router(residence_router(database))
    app.include_router(programs_router(database))

    @app.api_route("/api", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def unknown(path: str = ""):
        raise HTTPException(404, "操作が見つかりません。")

    if settings.static_dir:
        root = settings.static_dir.resolve()

        @app.get("/{path:path}")
        def static(path: str):
            candidate = (root / path).resolve()
            if not candidate.is_relative_to(root) or any(part.startswith(".") for part in Path(path).parts):
                raise HTTPException(404, "ページが見つかりません。")
            if candidate.is_file():
                return FileResponse(candidate, media_type="image/webp" if candidate.suffix.lower() == ".webp" else None)
            if Path(path).suffix or not (root / "index.html").is_file():
                raise HTTPException(404, "ページが見つかりません。")
            return FileResponse(root / "index.html", media_type="text/html")
    return app


app = create_app()
