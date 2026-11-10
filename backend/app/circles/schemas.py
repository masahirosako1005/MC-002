from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from ..marketplace.schemas import ItineraryItem, PlanReference
from ..schemas import Id, Input, Short, TagList

Version = Annotated[int, Field(strict=True, ge=1)]
Count = Annotated[int, Field(strict=True, ge=2, le=20)]
People = Annotated[list[Id], Field(max_length=19)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class KeyInput(Input):
    client_request_id: Id


class CandidateInput(Input):
    community_id: Id
    tags: TagList
    desired_count: Count


class CircleCreate(CandidateInput, KeyInput):
    title: Short
    mode: Literal['recommended','manual']
    invitee_ids: People

    @model_validator(mode='after')
    def selected(self):
        if len(set(self.invitee_ids)) != len(self.invitee_ids):
            raise ValueError('Duplicate invitee')
        if len(self.invitee_ids) + 1 > self.desired_count:
            raise ValueError('Too many invitees')
        if self.mode == 'recommended' and not self.tags:
            raise ValueError('Choose interests')
        return self


class GroupInput(KeyInput):
    group_id: Id


class VersionInput(Input):
    version: Version


class InviteInput(KeyInput, VersionInput):
    invitee_ids: Annotated[list[Id], Field(min_length=1, max_length=19)]

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.invitee_ids)) != len(self.invitee_ids):
            raise ValueError('Duplicate invitee')
        return self


class ActionInput(KeyInput, VersionInput):
    pass


class ResponseInput(ActionInput):
    decision: Literal['accepted','declined']


class TurnInput(KeyInput):
    body: Text


class ProviderInvitationInput(PlanReference, ActionInput):
    share_note: Annotated[str, StringConstraints(max_length=1000)] = ''
    sharing_confirmed: Literal[True]


class ProposalInput(KeyInput):
    version: Annotated[int, Field(strict=True, ge=0)]
    title: Short
    date_start: date | None = None
    itinerary: Annotated[list[ItineraryItem], Field(min_length=1, max_length=60)]
    estimated_price_yen: Annotated[int, Field(strict=True, ge=1, le=100_000_000)]
    price_basis: Literal['per_person','party_total']
    price_scope: Literal['plan_only','whole_trip']
    price_note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
    unknowns: Annotated[list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]], Field(min_length=1, max_length=12)]


class ConfirmationInput(ActionInput):
    proposal_id: Id


class CandidateCardInput(KeyInput):
    plan_id: Id
    plan_version: Version


class CirclePreferencesInput(VersionInput):
    tags: TagList
