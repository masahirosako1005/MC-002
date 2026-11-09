from fastapi import APIRouter,Depends,Query
from ..security import authenticated
from .service import Occasions
from .schemas import CreateInput,EditInput,VersionInput,SharingInput,StateInput,CandidateInput


def create_router(database):
    router=APIRouter(prefix='/api',dependencies=[Depends(authenticated)])
    service=Occasions(database)

    @router.get('/me/occasions')
    def listing(session=Depends(authenticated)):
        return service.list(session['user_id'])

    @router.post('/me/occasions')
    def create(body:CreateInput,session=Depends(authenticated)):
        return service.create(session['user_id'],body.model_dump())

    @router.put('/me/occasions/{oid}')
    def edit(oid:str,body:EditInput,session=Depends(authenticated)):
        return service.edit(session['user_id'],oid,body.model_dump())

    @router.delete('/me/occasions/{oid}')
    def delete(oid:str,body:VersionInput,session=Depends(authenticated)):
        return service.edit(session['user_id'],oid,body.model_dump(),True)

    @router.put('/me/occasions/{oid}/sharing')
    def sharing(oid:str,body:SharingInput,session=Depends(authenticated)):
        return service.sharing(session['user_id'],oid,body.model_dump())

    @router.get('/me/occasions/{oid}/preview')
    def preview(oid:str,circle_id:str=Query(min_length=1,max_length=100),session=Depends(authenticated)):
        return service.preview(session['user_id'],oid,circle_id)

    @router.get('/circles/{pid}/occasions')
    def shared_dates(pid:str,session=Depends(authenticated)):
        return service.shared_dates(session['user_id'],pid)

    @router.get('/occasion-suggestions')
    def suggestions(circle_id:str=Query(min_length=1,max_length=100),session=Depends(authenticated)):
        return service.suggestions(session['user_id'],circle_id)

    @router.put('/occasion-suggestions/{sid}/state')
    def state(sid:str,body:StateInput,session=Depends(authenticated)):
        return service.state(session['user_id'],sid,body.model_dump())

    @router.post('/occasion-suggestions/{sid}/candidate-cards')
    def save(sid:str,body:CandidateInput,session=Depends(authenticated)):
        return service.save(session['user_id'],sid,body.model_dump())

    return router
