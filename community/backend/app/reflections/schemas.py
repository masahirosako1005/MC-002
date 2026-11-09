from datetime import date,datetime,timedelta,timezone
from typing import Annotated,Literal
from pydantic import Field,StringConstraints,field_validator,model_validator
from ..schemas import Input,Id

Version=Annotated[int,Field(strict=True,ge=1)]
Body=Annotated[str,StringConstraints(strip_whitespace=True,min_length=1,max_length=1000)]


class CreateInput(Input):
    invitation_id:Id
    ended_on:date
    trip_finished:Literal[True]
    client_request_id:Id

    @field_validator('ended_on')
    @classmethod
    def no_future(cls,value):
        if value>datetime.now(timezone(timedelta(hours=9))).date():
            raise ValueError('Trip has not ended yet')
        return value


class VersionInput(Input):
    version:Version


class ParticipationInput(VersionInput):
    used_service:bool


class ConsentInput(VersionInput):
    allowed:bool


class CompletionInput(VersionInput):
    trip_finished:bool


class MessageInput(Input):
    body:Body
    client_request_id:Id


class EditInput(VersionInput):
    body:Body


class AspectInput(Input):
    aspect_id:Literal['guidance','response','experience','price']
    sentiment:Literal['positive','negative','mixed','excluded']


class ReviewInput(VersionInput):
    source_version:Version
    values:Annotated[list[AspectInput],Field(min_length=4,max_length=4)]

    @model_validator(mode='after')
    def all_aspects(self):
        if {value.aspect_id for value in self.values}!={'guidance','response','experience','price'}:
            raise ValueError('Each aspect exactly once')
        return self
