"""FXMacroData data catalogue model and fetcher for OpenBB.

Endpoint: GET /v1/data_catalogue/{currency}
"""

from __future__ import annotations

from datetime import date as dateType
from typing import Any, Dict, List, Optional

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.abstract.query_params import QueryParams
from fxmacrodata.openbb.utils.catalogue import flatten_catalogue_payload
from pydantic import Field


class FXMacroDataDataCatalogueQueryParams(QueryParams):
    """Query parameters for FXMacroData indicator discovery."""

    currency: str = Field(
        description="Currency code to inspect (e.g. USD, EUR, AUD, JPY).",
    )
    include_coverage: bool = Field(
        default=True,
        description=(
            "Include availability and freshness metadata such as row count, "
            "latest available date, and coverage quality."
        ),
    )
    include_capabilities: bool = Field(
        default=False,
        description="Include machine-readable endpoint capabilities where available.",
    )
    indicator: Optional[str] = Field(
        default=None,
        description="Optional indicator slug to limit the catalogue response.",
    )


class FXMacroDataDataCatalogueData(Data):
    """A single indicator row from the FXMacroData catalogue."""

    indicator: str = Field(description="FXMacroData indicator slug.")
    name: Optional[str] = Field(default=None, description="Human-readable name.")
    unit: Optional[str] = Field(default=None, description="Published unit.")
    frequency: Optional[str] = Field(default=None, description="Publishing frequency.")
    source: Optional[str] = Field(default=None, description="Official source.")
    source_series_id: Optional[str] = Field(
        default=None,
        description="Source system series identifier, when available.",
    )
    source_series_name: Optional[str] = Field(
        default=None,
        description="Source system series name, when available.",
    )
    seasonal_adjustment: Optional[str] = Field(
        default=None,
        description="Seasonality basis, when available.",
    )
    price_basis: Optional[str] = Field(
        default=None,
        description="Real/nominal price basis, when available.",
    )
    available: Optional[bool] = Field(
        default=None,
        description="Whether the indicator is currently available.",
    )
    requires_api_key: Optional[bool] = Field(
        default=None,
        description="Whether this row requires subscriber API access.",
    )
    earliest_available_date: Optional[dateType] = Field(
        default=None,
        description="Earliest stored observation date.",
    )
    latest_available_date: Optional[dateType] = Field(
        default=None,
        description="Latest stored observation date.",
    )
    row_count: Optional[int] = Field(
        default=None,
        description="Number of stored observations in the coverage scope.",
    )
    has_recent_data: Optional[bool] = Field(
        default=None,
        description="Whether recent observations are present.",
    )
    coverage_quality: Optional[str] = Field(
        default=None,
        description="Coverage freshness/quality label.",
    )
    recent_observation_count: Optional[int] = Field(
        default=None,
        description="Number of recent observations in the freshness window.",
    )


class FXMacroDataDataCatalogueFetcher(
    Fetcher[
        FXMacroDataDataCatalogueQueryParams,
        List[FXMacroDataDataCatalogueData],
    ]
):
    """Fetch the FXMacroData indicator catalogue for a currency."""

    require_credentials = False

    @staticmethod
    def transform_query(params: Dict[str, Any]) -> FXMacroDataDataCatalogueQueryParams:
        """Validate and transform raw query parameters."""
        return FXMacroDataDataCatalogueQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: FXMacroDataDataCatalogueQueryParams,
        credentials: Optional[Dict[str, str]],
        **kwargs: Any,
    ) -> List[Dict]:
        """Extract and flatten catalogue metadata from the FXMacroData API."""
        # pylint: disable=import-outside-toplevel
        from fxmacrodata.openbb.utils.helpers import get_json, resolve_api_key

        api_key = resolve_api_key(credentials)
        payload = await get_json(
            f"/v1/data_catalogue/{query.currency.lower()}",
            params={
                "include_coverage": query.include_coverage,
                "include_capabilities": query.include_capabilities,
                "indicator": query.indicator.lower() if query.indicator else None,
            },
            api_key=api_key,
        )
        return flatten_catalogue_payload(payload)

    @staticmethod
    def transform_data(
        query: FXMacroDataDataCatalogueQueryParams,
        data: List[Dict],
        **kwargs: Any,
    ) -> List[FXMacroDataDataCatalogueData]:
        """Transform raw API records into validated data models."""
        return [FXMacroDataDataCatalogueData.model_validate(row) for row in data]
