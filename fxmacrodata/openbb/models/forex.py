"""FXMacroData FX spot-rate model and fetcher for the OpenBB Platform.

Endpoint: GET /v1/forex/{base}/{quote}

Use the data catalogue or FXMacroData docs to discover supported currencies.
"""

from __future__ import annotations

from datetime import date as dateType
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import Field


class FXMacroDataFxHistoricalQueryParams(QueryParams):
    """Query parameters for FXMacroData FX spot-rate data."""

    base: str = Field(description="Base currency code (e.g. AUD, EUR, GBP).")
    quote: str = Field(description="Quote currency code (e.g. USD, JPY, CHF).")
    start_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive start date for the time series (YYYY-MM-DD).",
    )
    end_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive end date for the time series (YYYY-MM-DD).",
    )


class FXMacroDataFxHistoricalData(Data):
    """A single FX spot-rate data point from FXMacroData."""

    date: dateType = Field(description="Trading date.")
    close: Optional[float] = Field(
        default=None,
        description="End-of-day spot rate (base / quote).",
    )
    announcement_datetime: Optional[int] = Field(
        default=None,
        description="Unix epoch (UTC seconds) of any associated announcement.",
    )


class FXMacroDataFxHistoricalFetcher(
    Fetcher[
        FXMacroDataFxHistoricalQueryParams,
        List[FXMacroDataFxHistoricalData],
    ]
):
    """Fetch FX spot-rate history from FXMacroData."""

    require_credentials = False

    @staticmethod
    def transform_query(
        params: Dict[str, Any],
    ) -> FXMacroDataFxHistoricalQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataFxHistoricalQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataFxHistoricalQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract raw FX data from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_data, resolve_api_key

        api_key = resolve_api_key(credentials)
        return await get_data(
            f"/v1/forex/{query.base.lower()}/{query.quote.lower()}",
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
        query: FXMacroDataFxHistoricalQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataFxHistoricalData]:
        """Transform raw API records into validated data models.

        The API returns the rate as ``val``; this is renamed to ``close`` so
        that the field name is consistent with standard OHLCV conventions.
        """
        normalised = [{**row, "close": row.get("val")} for row in data]
        return [FXMacroDataFxHistoricalData.model_validate(row) for row in normalised]
