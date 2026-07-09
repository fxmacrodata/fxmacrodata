"""FXMacroData commodity model and fetcher for OpenBB.

Endpoint: GET /v1/commodities/{indicator}

Supported indicators: gold, natural_gas, oil_brent, oil_wti, platinum,
silver.
"""

from __future__ import annotations

from datetime import date as dateType
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import Field

from fxmacrodata.openbb.utils.datetimes import with_human_announcement_datetime


class FXMacroDataCommodityQueryParams(QueryParams):
    """Query parameters for FXMacroData commodity price data."""

    indicator: str = Field(
        description=(
            "Commodity indicator name: gold, natural_gas, oil_brent, "
            "oil_wti, platinum, or silver."
        ),
    )
    start_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive start date for the time series (YYYY-MM-DD).",
    )
    end_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive end date for the time series (YYYY-MM-DD).",
    )


class FXMacroDataCommodityData(Data):
    """A single commodity price data point from FXMacroData."""

    date: dateType = Field(description="Price date.")
    val: Optional[float] = Field(
        default=None,
        description="Commodity price in the unit defined by FXMacroData.",
    )
    announcement_datetime: Optional[str] = Field(
        default=None,
        description="Associated publication datetime formatted as YYYY-MM-DD HH:MM UTC.",
    )
    pct_change: Optional[float] = Field(
        default=None,
        description="Period-over-period percentage change.",
    )
    pct_change_12m: Optional[float] = Field(
        default=None,
        description="12-month percentage change.",
    )


class FXMacroDataCommodityFetcher(
    Fetcher[
        FXMacroDataCommodityQueryParams,
        List[FXMacroDataCommodityData],
    ]
):
    """Fetch commodity prices from FXMacroData."""

    require_credentials = False

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> FXMacroDataCommodityQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataCommodityQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataCommodityQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract raw commodity data from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_data, resolve_api_key

        api_key = resolve_api_key(credentials)
        return await get_data(
            f"/v1/commodities/{query.indicator.lower()}",
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
        query: FXMacroDataCommodityQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataCommodityData]:
        """Transform raw API records into validated data models."""
        return [
            FXMacroDataCommodityData.model_validate(
                with_human_announcement_datetime(row, drop_source_fields=True)
            )
            for row in data
        ]
