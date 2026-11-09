from fastapi import APIRouter, Depends

from ..security import authenticated
from .schemas import (
    CompletionInput,
    ConsentInput,
    CreateInput,
    EditInput,
    MessageInput,
    ParticipationInput,
    ReviewInput,
    VersionInput,
)
from .service import Reflections


def create_router(database):
    router=APIRouter(prefix='/api',dependencies=[Depends(authenticated)])
    service=Reflections(database)

    @router.get('/circles/{pid}/reflection-options')
    def options(pid:str,session=Depends(authenticated)):
        return service.options(session['user_id'],pid)

    @router.get('/circles/{pid}/reflections')
    def listing(pid:str,session=Depends(authenticated)):
        return service.list(session['user_id'],pid)

    @router.post('/circles/{pid}/reflections')
    def create(pid:str,body:CreateInput,session=Depends(authenticated)):
        return service.create(session['user_id'],pid,body.model_dump(mode='json'))

    @router.get('/reflections/{rid}')
    def detail(rid:str,session=Depends(authenticated)):
        return service.get(session['user_id'],rid)

    @router.put('/reflections/{rid}/participation')
    def participation(rid:str,body:ParticipationInput,session=Depends(authenticated)):
        return service.participant(session['user_id'],rid,body.model_dump())

    @router.put('/reflections/{rid}/consent')
    def consent(rid:str,body:ConsentInput,session=Depends(authenticated)):
        return service.participant(session['user_id'],rid,body.model_dump(),True)

    @router.post('/reflections/{rid}/participants-refresh')
    def refresh(rid:str,body:VersionInput,session=Depends(authenticated)):
        return service.refresh(session['user_id'],rid,body.version)

    @router.put('/reflections/{rid}/completion')
    def completion(rid:str,body:CompletionInput,session=Depends(authenticated)):
        return service.completion(session['user_id'],rid,body.model_dump())

    @router.post('/reflections/{rid}/messages')
    def post(rid:str,body:MessageInput,session=Depends(authenticated)):
        return service.post(session['user_id'],rid,body.model_dump())

    @router.put('/reflection-messages/{mid}')
    def edit(mid:str,body:EditInput,session=Depends(authenticated)):
        return service.edit(session['user_id'],mid,body.model_dump())

    @router.delete('/reflection-messages/{mid}')
    def delete(mid:str,body:VersionInput,session=Depends(authenticated)):
        return service.edit(session['user_id'],mid,body.model_dump(),delete=True)

    @router.put('/reflection-messages/{mid}/review')
    def review(mid:str,body:ReviewInput,session=Depends(authenticated)):
        return service.edit(session['user_id'],mid,body.model_dump(),review=True)

    @router.get('/providers/{provider_id}/experience-summary')
    def public(provider_id:str):
        return service.public(provider_id)

    return router
