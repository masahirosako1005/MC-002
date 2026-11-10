from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ..security import authenticated, csrf, current_session
from .catalog import AREAS, DESTINATION
from .schemas import AreaCatalogue, Registration, RegistrationResult, Residence, ResidenceUpdate
from .service import ResidenceService


def create_router(database):
    router = APIRouter(prefix='/api', tags=['residence'])
    service = ResidenceService(database)

    @router.get('/residence/areas')
    def areas() -> AreaCatalogue:
        return AreaCatalogue(items=AREAS, destination=DESTINATION)

    @router.post('/register', status_code=201)
    def register(body: Registration, request: Request) -> RegistrationResult:
        session = current_session(request)
        if session is not None:
            csrf(request, session)
        return service.register(body)

    @router.get('/residence/me')
    def me(session: Annotated[dict, Depends(authenticated)]) -> Residence:
        return service.me(session['user_id'])

    @router.put('/residence/me')
    def update(body: ResidenceUpdate, session: Annotated[dict, Depends(authenticated)]) -> Residence:
        return service.me(session['user_id'], body)

    return router
