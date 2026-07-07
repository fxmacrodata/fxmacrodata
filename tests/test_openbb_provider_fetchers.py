"""Unit tests for FXMacroData OpenBB provider fetchers."""

from __future__ import annotations

from datetime import date

import pytest

pytest.importorskip("openbb_core")

from fxmacrodata.openbb import fxmacrodata_provider
from fxmacrodata.openbb.models.data_catalogue import FXMacroDataDataCatalogueFetcher
from fxmacrodata.openbb.models.forex import FXMacroDataFxHistoricalFetcher
from fxmacrodata.openbb.models.release_calendar import FXMacroDataReleaseCalendarFetcher
from fxmacrodata.openbb.utils import helpers


def test_provider_registers_expected_fetchers():
    """The provider entry point should expose every router model."""
    assert fxmacrodata_provider is not None
    assert fxmacrodata_provider.name == "fxmacrodata"
    assert set(fxmacrodata_provider.fetcher_dict) == {
        "FXMacroDataCommodity",
        "FXMacroDataCot",
        "FXMacroDataDataCatalogue",
        "FXMacroDataFxHistorical",
        "FXMacroDataMacroIndicators",
        "FXMacroDataReleaseCalendar",
    }


@pytest.mark.asyncio
async def test_fx_fetcher_extracts_data_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
):
    """FX fetcher should lowercase pair codes and pass OpenBB credentials."""
    calls = []

    async def fake_get_data(path, params, api_key, **kwargs):
        calls.append({"path": path, "params": params, "api_key": api_key})
        return [{"date": "2026-01-02", "val": 1.0832}]

    monkeypatch.setattr(helpers, "get_data", fake_get_data)

    query = FXMacroDataFxHistoricalFetcher.transform_query(
        {
            "base": "EUR",
            "quote": "USD",
            "start_date": date(2026, 1, 1),
        }
    )
    raw_data = await FXMacroDataFxHistoricalFetcher.aextract_data(
        query,
        {"fxmacrodata_api_key": "credential-key"},
    )
    rows = FXMacroDataFxHistoricalFetcher.transform_data(query, raw_data)

    assert calls == [
        {
            "path": "/v1/forex/eur/usd",
            "params": {"start_date": "2026-01-01", "end_date": None},
            "api_key": "credential-key",
        }
    ]
    assert rows[0].date == date(2026, 1, 2)
    assert rows[0].close == 1.0832


@pytest.mark.asyncio
async def test_data_catalogue_fetcher_flattens_catalogue(
    monkeypatch: pytest.MonkeyPatch,
):
    """Catalogue fetcher should request coverage metadata and flatten rows."""
    calls = []

    async def fake_get_json(path, params=None, api_key=None, **kwargs):
        calls.append({"path": path, "params": params, "api_key": api_key})
        return {
            "catalogue": {
                "inflation": {
                    "name": "Inflation",
                    "frequency": "monthly",
                    "coverage": {"available": True, "row_count": 12},
                }
            }
        }

    monkeypatch.setattr(helpers, "get_json", fake_get_json)

    query = FXMacroDataDataCatalogueFetcher.transform_query(
        {"currency": "USD", "indicator": "Inflation"}
    )
    raw_rows = await FXMacroDataDataCatalogueFetcher.aextract_data(
        query,
        {"api_key": "credential-key"},
    )
    rows = FXMacroDataDataCatalogueFetcher.transform_data(query, raw_rows)

    assert calls == [
        {
            "path": "/v1/data_catalogue/usd",
            "params": {
                "include_coverage": True,
                "include_capabilities": False,
                "indicator": "inflation",
            },
            "api_key": "credential-key",
        }
    ]
    assert rows[0].indicator == "inflation"
    assert rows[0].available is True
    assert rows[0].row_count == 12


@pytest.mark.asyncio
async def test_release_calendar_fetcher_filters_indicator(
    monkeypatch: pytest.MonkeyPatch,
):
    """Release-calendar fetcher should preserve indicator filtering."""
    calls = []
    monkeypatch.delenv("FXMACRODATA_API_KEY", raising=False)
    monkeypatch.delenv("FXMD_API_KEY", raising=False)

    async def fake_get_data(path, params, api_key, **kwargs):
        calls.append({"path": path, "params": params, "api_key": api_key})
        return [{"announcement_datetime": 1767261600, "release": "inflation"}]

    monkeypatch.setattr(helpers, "get_data", fake_get_data)

    query = FXMacroDataReleaseCalendarFetcher.transform_query(
        {"currency": "USD", "indicator": "Inflation"}
    )
    raw_data = await FXMacroDataReleaseCalendarFetcher.aextract_data(query, None)
    rows = FXMacroDataReleaseCalendarFetcher.transform_data(query, raw_data)

    assert calls == [
        {
            "path": "/v1/calendar/usd",
            "params": {"indicator": "inflation"},
            "api_key": None,
        }
    ]
    assert rows[0].release == "inflation"
    assert rows[0].announcement_datetime == 1767261600
