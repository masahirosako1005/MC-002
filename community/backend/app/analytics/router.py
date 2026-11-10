from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..security import authenticated
from .city_schemas import CityAnalyticsResponse
from .city_service import CityAnalytics
from .schemas import AnalyticsQuery, AnalyticsResponse
from .service import Analytics


def create_router(database):
    router = APIRouter(prefix='/api/providers', tags=['provider-analytics'])
    service = Analytics(database)
    city_service = CityAnalytics(database)

    @router.get('/{provider_id}/city-analytics')
    def city_analytics(
        provider_id: Annotated[str, Path(min_length=1, max_length=100)],
        query: Annotated[AnalyticsQuery, Query()],
        session: Annotated[dict, Depends(authenticated)],
    ) -> CityAnalyticsResponse:
        return city_service.read(session['user_id'], provider_id, query.days)

    @router.get('/{provider_id}/analytics')
    def analytics(
        provider_id: Annotated[str, Path(min_length=1, max_length=100)],
        query: Annotated[AnalyticsQuery, Query()],
        session: Annotated[dict, Depends(authenticated)],
    ) -> AnalyticsResponse:
        if query.days not in (30, 90, 365):
            raise HTTPException(422, '期間は30日・90日・365日から選んでください。')
        return service.read(session['user_id'], provider_id, query.days)

    return router
