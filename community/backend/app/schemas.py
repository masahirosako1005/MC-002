from datetime import date as Date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from .database import TAGS

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Id = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]
TagList = Annotated[list[Id], Field(max_length=9)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("tags", check_fields=False)
    @classmethod
    def valid_tags(cls, values):
        if values is not None and (len(values) != len(set(values)) or any(value not in TAGS for value in values)):
            raise ValueError("Unknown or duplicate tag")
        return values


class Empty(Input):
    pass


class Login(Input):
    username: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class CommunityInput(Input):
    name: Short
    description: Annotated[str, StringConstraints(max_length=500)] = ""


class JoinInput(Input):
    invite_code: Annotated[str, StringConstraints(min_length=1, max_length=100)]


class PostInput(Input):
    community_id: Id
    body: Annotated[str, StringConstraints(max_length=2000)] = ""
    media_ids: Annotated[list[Id], Field(min_length=1, max_length=5)]
    tags: TagList = []
    place_label: Annotated[str, StringConstraints(max_length=100)] = ""
    taken_on: Date | None = None


class PostPatch(Input):
    body: Annotated[str, StringConstraints(max_length=2000)] | None = None
    tags: TagList | None = None
    status: Literal["draft", "published"] | None = None
    place_label: Annotated[str, StringConstraints(max_length=100)] | None = None
    taken_on: Date | None = None


class GrantInput(Input):
    community_id: Id
    use_for_matching: bool
    display_in_matches: bool
    participate: bool


class PreferencesInput(Input):
    tags: TagList
    learn_from_posts: bool
    grants: Annotated[list[GrantInput], Field(max_length=100)]


class ProposalInput(Input):
    purpose: Short
    tags: Annotated[list[Id], Field(min_length=1, max_length=9)]
    size: Annotated[int, Field(strict=True, ge=3, le=6)]
    trip_id: Id
    date: Date | None = None


class ResponseInput(Input):
    decision: Literal["accepted", "declined"]
    version: Annotated[int, Field(strict=True, ge=1)]


class ContributionInput(Input):
    role: Literal["none", "research", "schedule", "food", "photos"]
    note: Annotated[str, StringConstraints(max_length=300)] = ""


class PlanInput(Input):
    date: Date | None
    meeting_point: Annotated[str, StringConstraints(max_length=200)]
    notes: Annotated[str, StringConstraints(max_length=2000)]
    version: Annotated[int, Field(strict=True, ge=1)]
