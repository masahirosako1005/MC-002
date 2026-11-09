from datetime import date as Date
from typing import Annotated, Literal
from pydantic import Field, model_validator
from ..schemas import Input, Id, Short, TagList


class PartyInput(Input):
    title: Short
    ko_group_id: Id | None = None
    member_ids: Annotated[list[Id], Field(max_length=20)] = []


class RequirementsInput(Input):
    planned_people: Annotated[int, Field(strict=True, ge=1, le=500)]
    nights: Annotated[int, Field(strict=True, ge=0, le=30)]
    budget_yen: Annotated[int, Field(strict=True, ge=1, le=100_000_000)] | None = None
    budget_basis: Literal['per_person', 'party_total'] | None = None
    budget_scope: Literal['plan_only', 'whole_trip'] | None = None
    date_start: Date | None = None
    interests: TagList = []
    departure_label: Annotated[str, Field(max_length=120)] = ''
    version: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode='after')
    def coherent_budget(self):
        from ..database import TAGS
        if len(set(self.interests)) != len(self.interests) or any(t not in TAGS for t in self.interests):
            raise ValueError('Unknown interest')
        if (self.budget_yen is None) != (self.budget_basis is None) or (self.budget_yen is None) != (self.budget_scope is None):
            raise ValueError('Budget amount, basis and scope must be specified together')
        return self


class MessageInput(Input):
    body: Annotated[str, Field(min_length=1, max_length=2000)]
    client_request_id: Id

    @model_validator(mode='after')
    def not_blank(self):
        if not self.body.strip():
            raise ValueError('Blank message')
        return self


class DraftInput(Input):
    message_ids: Annotated[list[Id], Field(min_length=1, max_length=50)]


class VersionInput(Input):
    version: Annotated[int, Field(strict=True, ge=1)]


class PlanReference(Input):
    plan_id: Id
    plan_version: Annotated[int, Field(strict=True, ge=1)]
    requirements_version: Annotated[int, Field(strict=True, ge=1)]


class SelectionInput(PlanReference):
    share_note: Annotated[str, Field(max_length=1000)] = ''
    sharing_confirmed: Literal[True]
    client_request_id: Id


class ItineraryItem(Input):
    day: Annotated[int, Field(strict=True, ge=1, le=31)]
    period: Literal['morning', 'afternoon', 'evening']
    place: Short
    description: Annotated[str, Field(max_length=400)]
    travel_minutes: Annotated[int, Field(strict=True, ge=0, le=1440)] | None = None


class ProviderPlanInput(Input):
    title: Short
    summary: Annotated[str, Field(max_length=1000)]
    area: Short
    min_people: Annotated[int, Field(strict=True, ge=1, le=500)]
    max_people: Annotated[int, Field(strict=True, ge=1, le=500)]
    nights: Annotated[int, Field(strict=True, ge=0, le=30)]
    price_yen: Annotated[int, Field(strict=True, ge=1, le=100_000_000)]
    price_basis: Literal['per_person', 'party_total']
    price_scope: Literal['plan_only', 'whole_trip']
    price_note: Annotated[str, Field(min_length=1, max_length=400)]
    tags: TagList
    itinerary: Annotated[list[ItineraryItem], Field(min_length=1, max_length=60)]
    status: Literal['draft', 'published', 'archived'] = 'draft'
    version: Annotated[int, Field(strict=True, ge=0)] = 0

    @model_validator(mode='after')
    def consistent(self):
        if self.min_people > self.max_people:
            raise ValueError('Invalid capacity')
        days = {row.day for row in self.itinerary}
        if any(day > self.nights + 1 for day in days):
            raise ValueError('Day outside trip')
        if self.status == 'published' and days != set(range(1, self.nights + 2)):
            raise ValueError('Every day needs an itinerary')
        return self
