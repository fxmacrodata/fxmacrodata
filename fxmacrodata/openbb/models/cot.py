"""FXMacroData CFTC Commitment of Traders model and fetcher for OpenBB.

Endpoint: GET /v1/cot/{currency}

Supported currencies: AUD, CAD, CHF, EUR, GBP, HUF, JPY, MXN, NZD, TRY,
USD, XAU.

The COT report is published weekly by the CFTC and covers non-commercial
(speculative) and commercial (hedger) positioning in FX futures contracts
traded on the Chicago Mercantile Exchange.
"""

from __future__ import annotations

from datetime import date as dateType
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from pydantic import Field

from fxmacrodata.openbb.utils.datetimes import with_human_announcement_datetime


class FXMacroDataCotQueryParams(QueryParams):
    """Query parameters for FXMacroData CFTC COT positioning data."""

    currency: str = Field(
        description=(
            "Currency code for the FX futures contract "
            "(AUD, CAD, CHF, EUR, GBP, HUF, JPY, MXN, NZD, TRY, USD, XAU)."
        )
    )
    start_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive start date (YYYY-MM-DD).",
    )
    end_date: Optional[dateType] = Field(
        default=None,
        description="Inclusive end date (YYYY-MM-DD).",
    )


class FXMacroDataCotData(Data):
    """A single weekly COT positioning record from FXMacroData."""

    announcement_datetime: Optional[str] = Field(
        default=None,
        description="CFTC publication datetime formatted as YYYY-MM-DD HH:MM UTC.",
    )
    date: dateType = Field(description="Report date (Tuesday of the reference week).")
    open_interest: Optional[int] = Field(
        default=None,
        description="Total open interest across all trader categories.",
    )
    noncommercial_long: Optional[int] = Field(
        default=None,
        description="Non-commercial (speculative) long positions.",
    )
    noncommercial_short: Optional[int] = Field(
        default=None,
        description="Non-commercial (speculative) short positions.",
    )
    noncommercial_net: Optional[int] = Field(
        default=None,
        description="Non-commercial net positions (long minus short).",
    )
    noncommercial_spread: Optional[int] = Field(
        default=None,
        description="Non-commercial spread positions.",
    )
    commercial_long: Optional[int] = Field(
        default=None,
        description="Commercial (hedger) long positions.",
    )
    commercial_short: Optional[int] = Field(
        default=None,
        description="Commercial (hedger) short positions.",
    )
    commercial_net: Optional[int] = Field(
        default=None,
        description="Commercial net positions (long minus short).",
    )
    total_reportable_long: Optional[int] = Field(
        default=None,
        description="Total reportable long positions.",
    )
    total_reportable_short: Optional[int] = Field(
        default=None,
        description="Total reportable short positions.",
    )
    nonreportable_long: Optional[int] = Field(
        default=None,
        description="Non-reportable (small trader) long positions.",
    )
    nonreportable_short: Optional[int] = Field(
        default=None,
        description="Non-reportable (small trader) short positions.",
    )


class FXMacroDataCotFetcher(
    Fetcher[
        FXMacroDataCotQueryParams,
        List[FXMacroDataCotData],
    ]
):
    """Fetch CFTC Commitment of Traders positioning data from FXMacroData."""

    require_credentials = False

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> FXMacroDataCotQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataCotQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataCotQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract raw COT data from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_data, resolve_api_key

        api_key = resolve_api_key(credentials)
        return await get_data(
            f"/v1/cot/{query.currency.lower()}",
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
        query: FXMacroDataCotQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataCotData]:
        """Transform raw API records into validated data models."""
        return [
            FXMacroDataCotData.model_validate(
                with_human_announcement_datetime(row, drop_source_fields=True)
            )
            for row in data
        ]
