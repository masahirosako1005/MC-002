from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from ..database import TAGS
from ..schemas import Id, Input


class Filters(Input):
    query: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    category: Annotated[str, StringConstraints(max_length=100)] = ""
    duration: Literal["all", "day", "overnight"] = "all"
    schedule: Literal["all", "dated", "on_request"] = "all"
    area: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ""

    @field_validator("category")
    @classmethod
    def current_tag(cls, value):
        if value and value not in TAGS:
            raise ValueError("Unknown category")
        return value


class ResumeInput(Input):
    version: Annotated[int, Field(strict=True, ge=0, le=9007199254740991)]
    page: Literal["feed", "market", "circles", "journal", "provider"]
    community_id: Id | None
    circle_id: Id | None
    filters: Filters
