from typing import Literal

from pydantic import BaseModel

from ..residence.schemas import Destination
from .schemas import OriginArea, Period

Status = Literal['available', 'insufficient_sample', 'no_data']


class CityMetric(BaseModel):
    count: int | None
    previous_count: int | None
    change_count: int | None
    change_percent: float | None
    unit: str
    definition: str
    status: Literal['available', 'insufficient_sample']
    reason: str | None


class CitySummary(BaseModel):
    visitors: CityMetric
    returning_visitors: CityMetric
    visit_days: CityMetric
    participations: CityMetric


class CityDay(BaseModel):
    date: str
    visitors: int | None
    returning_visitors: int | None
    visit_days: int | None
    participations: int | None


class CityDaily(BaseModel):
    status: Status
    reason: str | None
    items: list[CityDay]


class CityBucket(CityDay):
    end_date: str


class CityTrend(BaseModel):
    status: Status
    reason: str | None
    interval_days: int
    items: list[CityBucket]


class CityProvider(BaseModel):
    id: str
    name: str
    area: str
    published_plan_count: int
    visitors: int | None
    participations: int | None
    completed_outings: int | None


class CityProviders(BaseModel):
    status: Status
    reason: str | None
    items: list[CityProvider]


class CityOrigins(BaseModel):
    status: Status
    reason: str | None
    destination: Destination
    total_visitors: int | None
    consented_visitors: int | None
    missing_visitors: int | None
    withheld_visitors: int | None
    suppressed_visitors: int | None
    areas: list[OriginArea]
    privacy_threshold: int = 5
    definitions: list[str]


class PlanCategory(BaseModel):
    id: str
    label: str
    plan_count: int


class CityAnalyticsResponse(BaseModel):
    scope: Literal['city'] = 'city'
    city: Destination
    generated_at: str
    period: Period
    provider_count: int
    published_plan_count: int
    plan_categories: list[PlanCategory]
    summary: CitySummary
    daily: CityDaily
    trend: CityTrend
    providers: CityProviders
    origins: CityOrigins
    privacy_threshold: int = 5
    notes: list[str]
