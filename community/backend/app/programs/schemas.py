from typing import Literal

from pydantic import BaseModel, Field

from ..schemas import Id, Input


class EnrollInput(Input):
    client_request_id: Id


class LinkInput(Input):
    version: int = Field(ge=1)
    outing_id: Id | None


class CancelInput(EnrollInput):
    version: int = Field(ge=1)


class ProgressStep(BaseModel):
    step_id: str
    status: Literal['unplanned', 'planned', 'awaiting_confirmation', 'completed', 'invalid']
    outing_id: str | None
    has_link: bool
    reason: str | None


class Enrollment(BaseModel):
    version: int
    status: Literal['active', 'completed', 'cancelled']
    completed_count: int
    total_steps: int
    steps: list[ProgressStep]


class Step(BaseModel):
    id: str
    order: int
    title: str
    purpose: str
    plan_id: str
    plan_title: str
    price_yen: int
    route_id: str


class Provider(BaseModel):
    id: str
    name: str


class Program(BaseModel):
    id: str
    title: str
    goal: str
    area: str
    provider: Provider
    recommended_interval: str
    price_basis: Literal['per_person'] = 'per_person'
    price_scope: Literal['plan_only'] = 'plan_only'
    total_price_yen: int
    price_note: str
    steps: list[Step]
    enrollment: Enrollment | None
    available: bool = True
    unavailable_reason: str | None = None


class Catalogue(BaseModel):
    items: list[Program]
    notice: str


class Outing(BaseModel):
    id: str
    title: str
    starts_at: str
    ends_at: str
    plan_id: str
    status: str


class Outings(BaseModel):
    items: list[Outing]
