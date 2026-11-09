from fastapi import APIRouter, Depends, Query

from ..security import authenticated
from .assistant import HELP
from .discovery import Discovery
from .schemas import (
    ActionInput,
    CandidateCardInput,
    CandidateInput,
    CircleCreate,
    CirclePreferencesInput,
    ConfirmationInput,
    GroupInput,
    InviteInput,
    ProposalInput,
    ProviderInvitationInput,
    ResponseInput,
    TurnInput,
    VersionInput,
)
from .service import Circles


def create_router(database):
    router = APIRouter(prefix='/api',dependencies=[Depends(authenticated)])
    service = Circles(database)
    discovery = Discovery(database)

    @router.get('/plan-discovery')
    def discover(community_id:str=Query(min_length=1,max_length=100),circle_id:str|None=Query(None,max_length=100),session=Depends(authenticated)):
        return discovery.discover(session['user_id'],community_id,circle_id)

    @router.get('/circles/{pid}/candidate-cards')
    def candidate_cards(pid:str,session=Depends(authenticated)):
        return discovery.cards(session['user_id'],pid)

    @router.post('/circles/{pid}/candidate-cards')
    def save_candidate(pid:str,body:CandidateCardInput,session=Depends(authenticated)):
        return discovery.cards(session['user_id'],pid,body.model_dump())

    @router.get('/circles/help')
    def help():
        return HELP

    @router.post('/circles/candidates')
    def candidates(body:CandidateInput,session=Depends(authenticated)):
        return service.candidates(session['user_id'],body.model_dump())

    @router.post('/circles')
    def create(body:CircleCreate,session=Depends(authenticated)):
        return service.create(session['user_id'],body.model_dump())

    @router.get('/circles')
    def circles(session=Depends(authenticated)):
        return service.list(session['user_id'])

    @router.post('/circles/from-group')
    def from_group(body:GroupInput,session=Depends(authenticated)):
        return service.from_group(session['user_id'],body.model_dump())

    @router.get('/circles/{pid}')
    def circle(pid:str,session=Depends(authenticated)):
        return service.get(session['user_id'],pid)

    @router.put('/circles/{pid}/preferences')
    def preferences(pid:str,body:CirclePreferencesInput,session=Depends(authenticated)):
        return service.preferences(session['user_id'],pid,body.model_dump())

    @router.post('/circles/{pid}/invitations')
    def invite(pid:str,body:InviteInput,session=Depends(authenticated)):
        return service.invite(session['user_id'],pid,body.model_dump())

    @router.post('/circle-invitations/{iid}/respond')
    def respond(iid:str,body:ResponseInput,session=Depends(authenticated)):
        return service.respond(session['user_id'],iid,body.model_dump())

    @router.post('/circle-invitations/{iid}/cancel')
    def cancel(iid:str,body:ActionInput,session=Depends(authenticated)):
        return service.respond(session['user_id'],iid,body.model_dump(),True)

    @router.post('/circles/{pid}/leave')
    def leave(pid:str,body:VersionInput,session=Depends(authenticated)):
        return service.leave(session['user_id'],pid,body.version)

    @router.post('/circles/{pid}/close')
    def close(pid:str,body:VersionInput,session=Depends(authenticated)):
        return service.close(session['user_id'],pid,body.version)

    @router.get('/circles/{pid}/assistant-turns')
    def turns(pid:str,session=Depends(authenticated)):
        return service.turns(session['user_id'],pid)

    @router.post('/circles/{pid}/assistant-turns')
    def turn(pid:str,body:TurnInput,session=Depends(authenticated)):
        return service.turns(session['user_id'],pid,body.model_dump())

    @router.post('/circles/{pid}/provider-invitations')
    def invite_provider(pid:str,body:ProviderInvitationInput,session=Depends(authenticated)):
        return service.invite_provider(session['user_id'],pid,body.model_dump())

    @router.get('/circle-provider-invitations')
    def provider_invitations(session=Depends(authenticated)):
        return service.provider_invitations(session['user_id'])

    @router.post('/circle-provider-invitations/{iid}/respond')
    def provider_response(iid:str,body:ResponseInput,session=Depends(authenticated)):
        return service.provider_response(session['user_id'],iid,body.model_dump())

    @router.post('/circle-provider-invitations/{iid}/cancel')
    def cancel_provider(iid:str,body:ActionInput,session=Depends(authenticated)):
        return service.provider_response(session['user_id'],iid,body.model_dump(),True)

    @router.get('/circle-provider-invitations/{iid}/room')
    def shared_room(iid:str,session=Depends(authenticated)):
        return service.shared_room(session['user_id'],iid)

    @router.post('/circle-provider-invitations/{iid}/messages')
    def shared_message(iid:str,body:TurnInput,session=Depends(authenticated)):
        return service.shared_message(session['user_id'],iid,body.model_dump())

    @router.post('/circle-provider-invitations/{iid}/proposals')
    def proposal(iid:str,body:ProposalInput,session=Depends(authenticated)):
        return service.propose_agreement(session['user_id'],iid,body.model_dump(mode='json'))

    @router.post('/circle-provider-invitations/{iid}/confirmations')
    def confirm(iid:str,body:ConfirmationInput,session=Depends(authenticated)):
        return service.confirm_agreement(session['user_id'],iid,body.model_dump())

    return router
