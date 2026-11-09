from fastapi import APIRouter, Depends
from ..security import authenticated
from ..schemas import Empty
from .catalog import PREFECTURES, BADGES, EVIDENCE_NOTE
from .schemas import JourneyCreate, JourneyUpdate, VersionInput, VisitCreate, VisitUpdate, ProfileInput
from .service import JournalService


def create_router(database):
    router = APIRouter(prefix='/api/journal', dependencies=[Depends(authenticated)])
    service = JournalService(database)

    @router.get('/catalog')
    def catalog():
        return dict(prefectures=PREFECTURES, badges=BADGES, evidence_note=EVIDENCE_NOTE)

    @router.get('/journeys')
    def journeys(session=Depends(authenticated)):
        return service.journeys(session['user_id'])

    @router.post('/journeys')
    def create_journey(body: JourneyCreate, session=Depends(authenticated)):
        return service.create_journey(session['user_id'], body.model_dump())

    @router.get('/journeys/{jid}')
    def journey(jid: str, session=Depends(authenticated)):
        return service.journey(session['user_id'], jid)

    @router.put('/journeys/{jid}')
    def update_journey(jid: str, body: JourneyUpdate, session=Depends(authenticated)):
        return service.change_journey(session['user_id'], jid, body.model_dump())

    @router.delete('/journeys/{jid}')
    def delete_journey(jid: str, body: VersionInput, session=Depends(authenticated)):
        return service.change_journey(session['user_id'], jid, body.model_dump(), True)

    @router.post('/visits')
    def create_visit(body: VisitCreate, session=Depends(authenticated)):
        return service.create_visit(session['user_id'], body.model_dump(mode='json'))

    @router.put('/visits/{vid}')
    def update_visit(vid: str, body: VisitUpdate, session=Depends(authenticated)):
        return service.change_visit(session['user_id'], vid, body.model_dump(mode='json'))

    @router.delete('/visits/{vid}')
    def delete_visit(vid: str, body: VersionInput, session=Depends(authenticated)):
        return service.change_visit(session['user_id'], vid, body.model_dump(), True)

    @router.get('/media')
    def media(session=Depends(authenticated)):
        return service.media(session['user_id'])

    @router.get('/media/{mid}/location-candidate')
    def candidate(mid: str, session=Depends(authenticated)):
        return service.location_candidate(session['user_id'], mid)

    @router.delete('/media/{mid}/location-candidate')
    def discard_candidate(mid: str, body: Empty, session=Depends(authenticated)):
        return service.location_candidate(session['user_id'], mid, True)

    @router.get('/people')
    def people(community_id: str, session=Depends(authenticated)):
        return service.people(session['user_id'], community_id)

    @router.get('/profile/{uid}')
    def profile(uid: str, session=Depends(authenticated)):
        return service.profile(session['user_id'], uid)

    @router.put('/profile')
    def update_profile(body: ProfileInput, session=Depends(authenticated)):
        return service.profile(session['user_id'], data=body.model_dump())

    return router
