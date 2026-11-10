from fastapi import APIRouter, Depends, Query

from ..schemas import Empty
from ..security import authenticated
from .schemas import (
    DraftInput,
    MessageInput,
    PartyInput,
    PlanReference,
    ProviderPlanInput,
    RequirementsInput,
    SelectionInput,
    VersionInput,
)
from .service import Marketplace


def create_router(database):
    router = APIRouter(prefix='/api', dependencies=[Depends(authenticated)])
    service = Marketplace(database)

    @router.get('/marketplace/capabilities')
    def capabilities(session=Depends(authenticated)):
        return service.capabilities(session['user_id'])

    @router.get('/providers')
    def providers(session=Depends(authenticated)):
        return service.providers(session['user_id'])

    @router.get('/providers/{pid}')
    def provider(pid:str,session=Depends(authenticated)):
        return service.providers(session['user_id'],pid)

    @router.get('/provider-plans')
    def plans(provider_id:str|None=Query(None,max_length=100),mine:bool=False,session=Depends(authenticated)):
        return service.plans(session['user_id'],provider_id=provider_id,mine=mine)

    @router.get('/provider-plans/{pid}')
    def plan(pid:str,session=Depends(authenticated)):
        return service.plans(session['user_id'],plan_id=pid)

    @router.post('/providers/{pid}/plans')
    def create_plan(pid:str,body:ProviderPlanInput,session=Depends(authenticated)):
        return service.save_plan(session['user_id'],pid,body.model_dump(mode='json'))

    @router.patch('/provider-plans/{pid}')
    def update_plan(pid:str,body:ProviderPlanInput,session=Depends(authenticated)):
        return service.save_plan(session['user_id'],None,body.model_dump(mode='json'),pid)

    @router.get('/travel-parties')
    def parties(session=Depends(authenticated)):
        return service.parties(session['user_id'])

    @router.get('/travel-parties/{pid}')
    def party(pid:str,session=Depends(authenticated)):
        return service.parties(session['user_id'],pid)

    @router.post('/communities/{cid}/travel-parties')
    def create_party(cid:str,body:PartyInput,session=Depends(authenticated)):
        return service.create_party(session['user_id'],cid,body.model_dump())

    @router.put('/travel-parties/{pid}/requirements')
    def requirements(pid:str,body:RequirementsInput,session=Depends(authenticated)):
        return service.requirements(session['user_id'],pid,body.model_dump(mode='json'))

    @router.post('/travel-parties/{pid}/close')
    def close_party(pid:str,body:Empty,session=Depends(authenticated)):
        return service.close_party(session['user_id'],pid)

    @router.get('/travel-parties/{pid}/messages')
    def party_messages(pid:str,session=Depends(authenticated)):
        return service.messages(session['user_id'],'party',pid)

    @router.post('/travel-parties/{pid}/messages')
    def party_message(pid:str,body:MessageInput,session=Depends(authenticated)):
        return service.messages(session['user_id'],'party',pid,body.model_dump())

    @router.post('/travel-parties/{pid}/condition-drafts')
    def condition_drafts(pid:str,body:DraftInput,session=Depends(authenticated)):
        return service.draft(session['user_id'],pid,body.model_dump())

    @router.post('/travel-parties/{pid}/recommendations')
    def recommendations(pid:str,body:VersionInput,session=Depends(authenticated)):
        return service.recommendations(session['user_id'],pid,body.version)

    @router.post('/travel-parties/{pid}/selection-preview')
    def preview(pid:str,body:PlanReference,session=Depends(authenticated)):
        return service.selection_preview(session['user_id'],pid,body.model_dump())

    @router.post('/travel-parties/{pid}/selections')
    def select(pid:str,body:SelectionInput,session=Depends(authenticated)):
        return service.select(session['user_id'],pid,body.model_dump())

    @router.get('/consultations')
    def consultations(session=Depends(authenticated)):
        return service.consultations(session['user_id'])

    @router.get('/consultations/{cid}')
    def consultation(cid:str,session=Depends(authenticated)):
        return service.consultations(session['user_id'],cid)

    @router.get('/consultations/{cid}/messages')
    def consultation_messages(cid:str,session=Depends(authenticated)):
        return service.messages(session['user_id'],'consultation',cid)

    @router.post('/consultations/{cid}/messages')
    def consultation_message(cid:str,body:MessageInput,session=Depends(authenticated)):
        return service.messages(session['user_id'],'consultation',cid,body.model_dump())

    @router.post('/consultations/{cid}/close')
    def close(cid:str,body:VersionInput,session=Depends(authenticated)):
        return service.close(session['user_id'],cid,body.version)

    return router
