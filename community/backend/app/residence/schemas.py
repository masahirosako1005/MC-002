from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from ..schemas import Input, PostAuthor

AreaId = Annotated[str, StringConstraints(pattern=r'^\d{5}$')]


class Area(BaseModel):
    id: str
    prefecture: str
    city: str
    label: str
    latitude: float
    longitude: float


class Destination(BaseModel):
    id: str
    name: str
    prefecture: str
    latitude: float
    longitude: float
    fictional: Literal[True]


class AreaCatalogue(BaseModel):
    items: list[Area]
    destination: Destination
    precision: Literal['municipality_representative'] = 'municipality_representative'


class Residence(BaseModel):
    area: Area | None
    share_area_analytics: bool
    version: int
    updated_at: str | None


class Registration(Input):
    username: Annotated[str, StringConstraints(min_length=3, max_length=40, pattern=r'^[a-z0-9_-]+$')]
    password: Annotated[SecretStr, Field(min_length=12, max_length=128)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    residence_area_id: AreaId | None = None
    share_area_analytics: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode='after')
    def consent_needs_area(self):
        if self.residence_area_id is None and self.share_area_analytics:
            raise ValueError('A municipality is required before sharing')
        return self

    @field_validator('name')
    @classmethod
    def no_controls(cls, value):
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError('Control characters are not allowed')
        return value


class RegistrationResult(BaseModel):
    user: PostAuthor
    residence: Residence
    login_required: Literal[True] = True


class ResidenceUpdate(Input):
    residence_area_id: AreaId | None
    share_area_analytics: Annotated[bool, Field(strict=True)]
    version: Annotated[int, Field(strict=True, ge=0)]

    @model_validator(mode='after')
    def consent_needs_area(self):
        if self.residence_area_id is None and self.share_area_analytics:
            raise ValueError('A municipality is required before sharing')
        return self
