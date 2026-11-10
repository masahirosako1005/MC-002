from typing import Annotated

from fastapi import APIRouter, Depends

from ..schemas import Id
from ..security import authenticated
from .schemas import CancelInput, Catalogue, EnrollInput, Enrollment, LinkInput, Outings
from .service import Programs


def create_router(database):
    router = APIRouter(prefix='/api/daytrip/programs', tags=['programs'])
    service = Programs(database)

    @router.get('')
    def catalogue(session: Annotated[dict, Depends(authenticated)]) -> Catalogue:
        return service.catalogue(session['user_id'])

    @router.get('/{pid}/outings')
    def outings(pid: Id, session: Annotated[dict, Depends(authenticated)]) -> Outings:
        return service.outings(session['user_id'], pid)

    @router.post('/{pid}/enroll')
    def enroll(pid: Id, body: EnrollInput, session: Annotated[dict, Depends(authenticated)]) -> Enrollment:
        return service.enroll(session['user_id'], pid, body.model_dump())

    @router.post('/{pid}/cancel')
    def cancel(pid: Id, body: CancelInput, session: Annotated[dict, Depends(authenticated)]) -> Enrollment:
        return service.cancel(session['user_id'], pid, body.model_dump())

    @router.put('/{pid}/steps/{sid}')
    def link(pid: Id, sid: Id, body: LinkInput, session: Annotated[dict, Depends(authenticated)]) -> Enrollment:
        return service.link(session['user_id'], pid, sid, body.model_dump())

    return router
