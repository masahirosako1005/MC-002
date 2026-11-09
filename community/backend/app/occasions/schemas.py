from typing import Annotated,Literal
from pydantic import Field,StringConstraints,model_validator
from ..schemas import Input,Id
from .dates import validate_occasion_date

Version=Annotated[int,Field(strict=True,ge=1)]


class Fields(Input):
    kind:Literal['birthday','anniversary']
    name:Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=60)]
    month:Annotated[int,Field(strict=True,ge=1,le=12)]
    day:Annotated[int,Field(strict=True,ge=1,le=31)]
    repeats_annually:Annotated[bool,Field(strict=True)]
    year:Annotated[int,Field(strict=True,ge=1900,le=9999)]|None=None

    @model_validator(mode='after')
    def valid_date(self):
        if self.kind=='birthday' and (self.name!='誕生日' or not self.repeats_annually or self.year is not None):
            raise ValueError('Birthday stores only recurring month/day')
        if self.repeats_annually and self.year is not None:
            raise ValueError('Recurring occasion does not store a year')
        validate_occasion_date(self.month,self.day,repeats_annually=self.repeats_annually,year=self.year)
        return self


class CreateInput(Fields):
    client_request_id:Id


class VersionInput(Input):
    version:Version


class EditInput(Fields,VersionInput):
    pass


class Share(Input):
    circle_id:Id
    share_date:Annotated[bool,Field(strict=True)]
    suggest:Annotated[bool,Field(strict=True)]

    @model_validator(mode='after')
    def shared(self):
        if self.suggest and not self.share_date:
            raise ValueError('Suggestions require date sharing')
        return self


class SharingInput(VersionInput):
    sharing:Annotated[list[Share],Field(max_length=100)]

    @model_validator(mode='after')
    def unique(self):
        if len({s.circle_id for s in self.sharing})!=len(self.sharing):
            raise ValueError('Duplicate circle')
        return self


class StateInput(Input):
    state:Literal['new','later','dismissed']
    version:Annotated[int,Field(strict=True,ge=0)]


class CandidateInput(Input):
    plan_id:Id
    plan_version:Version
    occasion_version:Version
    client_request_id:Id
