from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from ..schemas import Id, Input, Short
from .catalog import PREFECTURE_BY_ID

Key = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')]
Version = Annotated[int, Field(ge=1, strict=True)]


class JourneyCreate(Input):
    title: Short
    request_key: Key


class JourneyUpdate(Input):
    title: Short
    version: Version


class VersionInput(Input):
    version: Version


class ProfileInput(Input):
    share_achievements: bool
    version: Version


class VisitInput(Input):
    journey_id: Id
    prefecture_id: str
    visited_on: date
    place_label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)] | None = None
    longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)] | None = None
    media_id: Id | None = None
    source: Literal['manual', 'exif'] = 'manual'
    visibility: Literal['private', 'community'] = 'private'
    community_id: Id | None = None
    confirmed: Literal[True]

    @field_validator('prefecture_id')
    @classmethod
    def prefecture_known(cls, value):
        if value not in PREFECTURE_BY_ID:
            raise ValueError('Unknown prefecture')
        return value

    @field_validator('visited_on')
    @classmethod
    def past_or_today(cls, value):
        if value > datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError('Future visit')
        return value

    @model_validator(mode='after')
    def consistent(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('Both coordinates required')
        if (self.visibility == 'community') != (self.community_id is not None):
            raise ValueError('Choose exactly one audience')
        if self.source == 'exif' and (self.media_id is None or self.latitude is None):
            raise ValueError('EXIF needs a photo and coordinates')
        return self


class VisitCreate(VisitInput):
    request_key: Key


class VisitUpdate(VisitInput):
    version: Version
