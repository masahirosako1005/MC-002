from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ..security import COOKIE, authenticated
from .schemas import PasswordChange, PasswordChanged
from .service import AccountService


def create_router(database, settings):
    router = APIRouter(prefix="/api/account", tags=["account"])
    service = AccountService(database)

    @router.post("/password")
    def change_password(
        body: PasswordChange, request: Request, response: Response,
        session: Annotated[dict, Depends(authenticated)],
    ) -> PasswordChanged:
        stage = request.headers.get("authorization") is not None
        result = service.change_password(
            session, body.current_password.get_secret_value(), body.new_password.get_secret_value(), stage=stage,
        )
        # An explicit Stage credential may coexist with a different user's cookie.
        if not stage:
            response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict", secure=settings.secure_cookie)
        return result

    return router
