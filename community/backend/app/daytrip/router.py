from fastapi import APIRouter, Depends

from ..security import authenticated
from .schemas import (
    AcceptInput,
    BenefitInput,
    CancelInput,
    ClaimInput,
    ConfirmInput,
    LeaderInput,
    OutingInput,
    ProviderConfirmInput,
    ReserveInput,
    RouteInput,
    VersionInput,
)
from .service import Daytrip


def create_router(database):
    router = APIRouter(prefix='/api', dependencies=[Depends(authenticated)])
    service = Daytrip(database)

    @router.get('/daytrip/catalog')
    def catalog():
        return service.catalog()

    @router.get('/daytrip/me')
    def me(session=Depends(authenticated)):
        return service.me(session['user_id'])

    @router.get('/daytrip/provider')
    def provider(session=Depends(authenticated)):
        return service.provider(session['user_id'])

    @router.get('/circles/{cid}/outings')
    def outings(cid: str, session=Depends(authenticated)):
        return service.outings(session['user_id'], cid)

    @router.post('/circles/{cid}/outings')
    def create(cid: str, body: OutingInput, session=Depends(authenticated)):
        return service.create(session['user_id'], cid, body.model_dump(mode='json'))

    @router.get('/daytrip/outings/{oid}')
    def get(oid: str, session=Depends(authenticated)):
        return service.get(session['user_id'], oid)

    @router.post('/daytrip/outings/{oid}/leader')
    def leader(oid: str, body: LeaderInput, session=Depends(authenticated)):
        return service.leader(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/accept')
    def accept(oid: str, body: AcceptInput, session=Depends(authenticated)):
        return service.accept(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/claim')
    def claim(oid: str, body: ClaimInput, session=Depends(authenticated)):
        return service.claim(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/confirm')
    def confirm(oid: str, body: ConfirmInput, session=Depends(authenticated)):
        return service.confirm(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/provider-confirm')
    def provider_confirm(oid: str, body: ProviderConfirmInput, session=Depends(authenticated)):
        return service.provider_confirm(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/cancel')
    def cancel(oid: str, body: CancelInput, session=Depends(authenticated)):
        return service.cancel(session['user_id'], oid, body.model_dump())

    @router.post('/daytrip/outings/{oid}/participants/{uid}/cancel')
    def cancel_participant(oid: str, uid: str, body: CancelInput, session=Depends(authenticated)):
        return service.cancel(session['user_id'], oid, body.model_dump(), uid)

    @router.put('/daytrip/plan-routes/{pid}')
    def link(pid: str, body: RouteInput, session=Depends(authenticated)):
        return service.link(session['user_id'], pid, body.route_id)

    @router.post('/daytrip/benefits')
    def benefit(body: BenefitInput, session=Depends(authenticated)):
        return service.create_benefit(session['user_id'], body.model_dump(mode='json'))

    @router.post('/daytrip/benefits/{bid}/close')
    def close(bid: str, body: VersionInput, session=Depends(authenticated)):
        return service.close_benefit(session['user_id'], bid, body.version)

    @router.post('/daytrip/benefits/{bid}/reserve')
    def reserve(bid: str, body: ReserveInput, session=Depends(authenticated)):
        return service.reserve(session['user_id'], bid, body.model_dump())

    @router.post('/daytrip/redemptions/{rid}/redeem')
    def redeem(rid: str, body: VersionInput, session=Depends(authenticated)):
        return service.redemption(session['user_id'], rid, body.version)

    @router.post('/daytrip/redemptions/{rid}/cancel')
    def cancel_redemption(rid: str, body: VersionInput, session=Depends(authenticated)):
        return service.redemption(session['user_id'], rid, body.version, True)

    return router
