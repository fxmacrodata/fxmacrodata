"""FXMacroData macro-indicator model and fetcher for the OpenBB Platform.

Endpoint: GET /v1/announcements/{currency}/{indicator}

Use the data catalogue fetcher to discover supported currencies and indicators.
"""

from __future__ import annotations

from datetime import date as dateType
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import Field


class FXMacroDataMacroIndicatorsQueryParams(QueryParams):
    """Query parameters for FXMacroData macro-indicator data."""

    currency: str = Field(
        description=(
            "Currency code for the country of interest "
            "(e.g. USD, EUR, GBP, AUD, JPY)."
        )
    )
    indicator: str = Field(
        description=(
            "Indicator name (e.g. inflation, gdp, unemployment, policy_rate). "
            "See https://fxmacrodata.com/documentation for the full list."
        )
    )
    start_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive start date for the time series (YYYY-MM-DD).",
    )
    end_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive end date for the time series (YYYY-MM-DD).",
    )


class FXMacroDataMacroIndicatorsData(Data):
    """A single macro-indicator data point from FXMacroData."""

    date: dateType = Field(description="Data publication date.")
    val: Optional[float] = Field(
        default=None,
        description="Indicator value in the unit defined by the catalogue.",
    )
    announcement_datetime: Optional[int] = Field(
        default=None,
        description="Unix epoch (UTC seconds) of the official announcement.",
    )
    pct_change: Optional[float] = Field(
        default=None,
        description="Period-over-period percentage change.",
    )
    pct_change_12m: Optional[float] = Field(
        default=None,
        description="12-month percentage change.",
    )


class FXMacroDataMacroIndicatorsFetcher(
    Fetcher[
        FXMacroDataMacroIndicatorsQueryParams,
        List[FXMacroDataMacroIndicatorsData],
    ]
):
    """Fetch macroeconomic indicator time series from FXMacroData."""

    require_credentials = False

    @staticmethod
    def transform_query(
        params: Dict[str, Any],
    ) -> FXMacroDataMacroIndicatorsQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataMacroIndicatorsQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataMacroIndicatorsQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract raw indicator data from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_data, resolve_api_key

        api_key = resolve_api_key(credentials)
        return await get_data(
            f"/v1/announcements/{query.currency.lower()}/{query.indicator.lower()}",
            params={
                "start_date": (
                    query.start_date.isoformat() if query.start_date else None
                ),
                "end_date": query.end_date.isoformat() if query.end_date else None,
            },
            api_key=api_key,
        )

    @staticmethod
    def transform_data(
        query: FXMacroDataMacroIndicatorsQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataMacroIndicatorsData]:
        """Transform raw API records into validated data models."""
        return [FXMacroDataMacroIndicatorsData.model_validate(row) for row in data]
