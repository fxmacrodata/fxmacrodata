"""FXMacroData economic release-calendar model and fetcher for OpenBB.

Endpoint: GET /v1/calendar/{currency}

Returns upcoming scheduled release dates for a currency's economic data.
Supported currencies: AUD, BRL, CAD, CHF, CNY, COMM, DKK, EUR, GBP, HKD,
JPY, KRW, MXN, NOK, NZD, PLN, SEK, SGD, USD.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import Field


class FXMacroDataReleaseCalendarQueryParams(QueryParams):
    """Query parameters for FXMacroData economic release calendar."""

    currency: str = Field(
        description=(
            "Currency code whose release schedule to fetch "
            "(e.g. USD, EUR, AUD, COMM)."
        )
    )
    indicator: Optional[str] = Field(
        default=None,
        description=(
            "Optional indicator filter "
            "(e.g. inflation, gdp, non_farm_payrolls). "
            "When omitted, all upcoming releases for the currency are returned."
        ),
    )


class FXMacroDataReleaseCalendarData(Data):
    """A single upcoming release entry from the FXMacroData release calendar."""

    announcement_datetime: int = Field(
        description="Unix epoch (UTC seconds) of the scheduled announcement.",
    )
    release: str = Field(
        description="Indicator name for the scheduled release (e.g. inflation).",
    )


class FXMacroDataReleaseCalendarFetcher(
    Fetcher[
        FXMacroDataReleaseCalendarQueryParams,
        List[FXMacroDataReleaseCalendarData],
    ]
):
    """Fetch economic release-calendar entries from FXMacroData."""

    require_credentials = False

    @staticmethod
    def transform_query(
        params: Dict[str, Any],
    ) -> FXMacroDataReleaseCalendarQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataReleaseCalendarQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataReleaseCalendarQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract raw calendar data from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_data, resolve_api_key

        api_key = resolve_api_key(credentials)
        params: Dict[str, Any] = {}
        if query.indicator:
            params["indicator"] = query.indicator.lower()
        return await get_data(
            f"/v1/calendar/{query.currency.lower()}",
            params=params,
            api_key=api_key,
        )

    @staticmethod
    def transform_data(
        query: FXMacroDataReleaseCalendarQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataReleaseCalendarData]:
        """Transform raw API records into validated data models."""
        return [FXMacroDataReleaseCalendarData.model_validate(row) for row in data]
