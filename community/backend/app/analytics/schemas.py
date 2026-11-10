from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..residence.schemas import Area, Destination


class AnalyticsQuery(BaseModel):
    model_config = ConfigDict(extra='forbid')
    days: int = 30


class Period(BaseModel):
    days: int
    timezone: Literal['Asia/Tokyo'] = 'Asia/Tokyo'
    start_date: str
    end_date: str
    previous_start_date: str
    previous_end_date: str
    today_partial: bool = True


class Metric(BaseModel):
    count: int
    previous_count: int
    change_count: int
    change_percent: float | None
    unit: str
    definition: str


class Summary(BaseModel):
    consultations: Metric
    confirmed_users: Metric
    confirmed_visits: Metric
    completed_outings: Metric


class Daily(BaseModel):
    date: str
    consultations: int
    confirmed_users: int
    confirmed_visits: int
    completed_outings: int


class Plan(BaseModel):
    id: str
    title: str
    status: Literal['published'] = 'published'
    consultations: int
    confirmed_users: int
    confirmed_visits: int
    completed_outings: int


class Bin(BaseModel):
    key: str
    label: str
    count: int | None


class Distribution(BaseModel):
    label: str
    status: Literal['available', 'insufficient_sample', 'no_data']
    known_count: int
    missing_count: int
    bins: list[Bin]
    reason: str | None


class Conditions(BaseModel):
    population_unit: str
    consultation_count: int
    sample_count: int
    unique_sharers: int
    people: Distribution
    nights: Distribution
    budget_per_person: Distribution


class Uncollected(BaseModel):
    status: Literal['not_collected'] = 'not_collected'
    reason: str
    known_count: int = 0
    missing_count: int


class Demographics(BaseModel):
    age: Uncollected
    gender: Uncollected
    interests: Uncollected


class OriginArea(Area):
    visitors: int
    returning_visitors: int | None
    visits: int | None
    returning_status: Literal['available', 'insufficient_sample']


class Origins(BaseModel):
    status: Literal['available', 'insufficient_sample', 'no_data']
    destination: Destination
    total_visitors: int
    consented_visitors: int
    missing_visitors: int
    withheld_visitors: int
    suppressed_visitors: int
    areas: list[OriginArea]
    privacy_threshold: int = 5
    definitions: list[str]


class AnalyticsResponse(BaseModel):
    provider_id: str
    generated_at: str
    period: Period
    summary: Summary
    daily: list[Daily]
    plans: list[Plan]
    conditions: Conditions
    demographics: Demographics
    origins: Origins
    privacy_threshold: int = Field(default=5)
    notes: list[str]
