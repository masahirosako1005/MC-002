from fastapi import APIRouter, Depends

from ..security import authenticated
from .schemas import ResumeInput
from .service import Personalization


def create_router(database):
    router = APIRouter(prefix="/api", dependencies=[Depends(authenticated)])
    service = Personalization(database)

    @router.get("/me/resume-state")
    def read(session=Depends(authenticated)):
        return service.resume(session["user_id"])

    @router.put("/me/resume-state")
    def save(body: ResumeInput, session=Depends(authenticated)):
        return service.resume(session["user_id"], body.model_dump())

    return router
