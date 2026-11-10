from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StringConstraints

from ..schemas import Id, Input
from ..security import authenticated
from .service import Omikuji


class PolicyInput(Input):
    provider_id: Id
    enabled: Annotated[bool, Field(strict=True)]
    monthly_budget_yen: Annotated[int, Field(strict=True, ge=0, le=10000)]
    version: Annotated[int, Field(strict=True, ge=0)]


class CodeInput(Input):
    provider_id: Id


class DrawInput(Input):
    code: Annotated[str, StringConstraints(pattern=r'^[0-9]{6}$')]
    client_request_id: Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9_-]{8,100}$')]


class RedeemInput(Input):
    purchase_yen: Annotated[int, Field(strict=True, ge=1, le=1000000)]
    no_other_discount: Literal[True]


class ProviderPolicy(BaseModel):
    id: str
    name: str
    enabled: bool
    monthly_budget_yen: int
    issued_yen: int
    remaining_yen: int
    version: int


class Reward(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    title: str
    amount_yen: int
    status: Literal['available', 'redeemed', 'expired']
    expires_at: str
    redeemed_at: str | None
    created_at: str


class Draw(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    month: str
    amount_yen: int
    rank_level: int
    created_at: str
    reward: Reward | None


class Rank(BaseModel):
    level: int
    name: str


class Chance(BaseModel):
    amount_yen: int
    probability_percent: int


class Personal(BaseModel):
    month: str
    can_draw: bool
    rank: Rank
    personal_rank: Rank
    odds: list[Chance]
    draws: list[Draw]
    terms: list[str]


class ProviderOverview(BaseModel):
    month: str
    providers: list[ProviderPolicy]
    rewards: list[Reward]


class Code(BaseModel):
    code: str
    provider_id: str
    provider_name: str
    expires_at: str


Session = Annotated[dict, Depends(authenticated)]


def create_router(database):
    router = APIRouter(prefix='/api/omikuji', tags=['omikuji'])
    service = Omikuji(database)

    @router.get('')
    def personal(session: Session) -> Personal:
        return service.me(session['user_id'])

    @router.get('/provider')
    def provider(session: Session) -> ProviderOverview:
        return service.provider(session['user_id'])

    @router.put('/provider/policy')
    def configure(body: PolicyInput, session: Session) -> ProviderPolicy:
        return service.configure(session['user_id'], body.model_dump())

    @router.post('/provider/codes')
    def code(body: CodeInput, session: Session) -> Code:
        return service.issue_code(session['user_id'], body.provider_id)

    @router.post('/draw')
    def draw(body: DrawInput, session: Session) -> Draw:
        return service.draw(session['user_id'], body.model_dump())

    @router.post('/rewards/{rid}/redeem')
    def redeem(rid: Id, body: RedeemInput, session: Session) -> Reward:
        return service.redeem(session['user_id'], rid, body.model_dump())

    return router
