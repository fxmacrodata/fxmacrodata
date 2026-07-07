"""Tests for the FXMacroData OpenBB Workspace backend."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from fxmacrodata.openbb import workspace_backend as backend


def test_workspace_metadata_endpoints():
    """The backend should expose OpenBB Workspace metadata documents."""
    client = TestClient(backend.app)

    health = client.get("/health")
    widgets = client.get("/widgets.json")
    apps = client.get("/apps.json")

    assert health.status_code == 200
    assert health.json() == {"ok": True}
    assert widgets.status_code == 200
    assert "fxmacrodata_catalogue" in widgets.json()
    assert "fxmacrodata_release_calendar" in widgets.json()
    assert apps.status_code == 200
    assert {app["name"] for app in apps.json()} == {
        "FXMacroData Macro Event Radar",
        "FXMacroData FX Research Board",
    }


def test_catalogue_endpoint_flattens_rows_and_uses_header_auth(
    monkeypatch: pytest.MonkeyPatch,
):
    """Catalogue proxy responses should become table rows for OpenBB Workspace."""
    calls = []

    async def fake_get_json(
        path,
        params=None,
        api_key=None,
        auth_mode="query",
        **kwargs,
    ):
        calls.append(
            {
                "path": path,
                "params": params,
                "api_key": api_key,
                "auth_mode": auth_mode,
            }
        )
        return {
            "catalogue": {
                "inflation": {
                    "name": "Inflation",
                    "unit": "%",
                    "frequency": "monthly",
                    "coverage": {
                        "available": True,
                        "row_count": 12,
                        "coverage_quality": "good",
                    },
                }
            },
            "coverage": [],
        }

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get("/catalogue?currency=USD", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "indicator": "inflation",
            "name": "Inflation",
            "unit": "%",
            "frequency": "monthly",
            "source": None,
            "source_series_id": None,
            "source_series_name": None,
            "seasonal_adjustment": None,
            "price_basis": None,
            "available": True,
            "requires_api_key": None,
            "earliest_available_date": None,
            "latest_available_date": None,
            "row_count": 12,
            "has_recent_data": None,
            "coverage_quality": "good",
            "recent_observation_count": None,
        }
    ]
    assert calls == [
        {
            "path": "/v1/data_catalogue/usd",
            "params": {
                "include_coverage": True,
                "include_capabilities": False,
                "indicator": None,
            },
            "api_key": "test-key",
            "auth_mode": "header",
        }
    ]


def test_release_calendar_endpoint_proxies_data_rows(monkeypatch: pytest.MonkeyPatch):
    """The release calendar endpoint should return top-level data rows."""
    calls = []

    async def fake_get_json(
        path,
        params=None,
        api_key=None,
        auth_mode="query",
        **kwargs,
    ):
        calls.append(
            {
                "path": path,
                "params": params,
                "api_key": api_key,
                "auth_mode": auth_mode,
            }
        )
        return {"data": [{"release": "inflation", "announcement_datetime": 123}]}

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get(
        "/release_calendar?currency=USD&indicator=inflation",
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    assert response.json() == [{"release": "inflation", "announcement_datetime": 123}]
    assert calls == [
        {
            "path": "/v1/calendar/usd",
            "params": {"indicator": "inflation"},
            "api_key": "test-key",
            "auth_mode": "header",
        }
    ]
