from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from ..schemas import Id, Input, Short

Version = Annotated[int, Field(strict=True, ge=1)]
PositiveYen = Annotated[int, Field(strict=True, ge=1, le=100_000_000)]


class VersionInput(Input):
    version: Version


class RouteInput(Input):
    route_id: Id


class OutingInput(RouteInput):
    title: Short
    starts_at: datetime
    ends_at: datetime
    participant_ids: Annotated[list[Id], Field(min_length=2, max_length=20)]
    leader_id: Id
    plan_id: Id | None = None
    client_request_id: Id

    @field_validator('starts_at', 'ends_at', mode='before')
    @classmethod
    def iso_datetime(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError('Use an offset-aware ISO datetime')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if any(value.tzinfo is None or value.utcoffset() is None for value in (self.starts_at, self.ends_at)):
            raise ValueError('Timezone required')
        if self.ends_at <= self.starts_at:
            raise ValueError('End must follow start')
        if len(set(self.participant_ids)) != len(self.participant_ids) or self.leader_id not in self.participant_ids:
            raise ValueError('Choose a participating leader and unique people')
        return self


class LeaderInput(VersionInput):
    leader_id: Id


class AcceptInput(VersionInput):
    accept_leader: bool = False


class ClaimInput(VersionInput):
    full_route: bool


class ConfirmInput(VersionInput):
    participant_id: Id


class ProviderConfirmInput(VersionInput):
    participant_ids: Annotated[list[Id], Field(min_length=1, max_length=20)]

    @field_validator('participant_ids')
    @classmethod
    def unique(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Duplicate participant')
        return values


class CancelInput(VersionInput):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class BenefitInput(Input):
    plan_id: Id
    title: Short
    min_rank: Annotated[int, Field(strict=True, ge=1, le=10)]
    rank_policy_version: Literal['D1', 'R2'] = 'D1'
    discount_type: Literal['amount', 'percent']
    discount_value: PositiveYen
    max_discount_yen: PositiveYen
    max_redemptions: Annotated[int, Field(strict=True, ge=1, le=10000)]
    starts_on: date
    ends_on: date

    @model_validator(mode='after')
    def coherent(self):
        if self.ends_on < self.starts_on or (self.discount_type == 'percent' and self.discount_value > 100):
            raise ValueError('Invalid benefit conditions')
        if self.rank_policy_version == 'D1' and self.min_rank > 4:
            raise ValueError('Use R2 for the ten-rank policy')
        return self


class ReserveInput(Input):
    outing_id: Id
    client_request_id: Id
