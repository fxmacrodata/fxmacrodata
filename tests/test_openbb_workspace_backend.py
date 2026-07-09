"""Tests for the FXMacroData OpenBB Workspace backend."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from fastapi import FastAPI

from fxmacrodata.openbb import workspace_backend as backend


def test_workspace_backend_does_not_expose_docs_by_default():
    """The public Workspace backend should not expose exploratory API docs."""
    client = TestClient(backend.app)

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_workspace_metadata_endpoints():
    """The backend should expose OpenBB Workspace metadata documents."""
    client = TestClient(backend.app)

    health = client.get("/health")
    widgets = client.get("/widgets.json")
    apps = client.get("/apps.json")

    assert health.status_code == 200
    assert health.json() == {"ok": True}
    assert widgets.status_code == 200
    widget_payload = widgets.json()
    forex_params = {
        param["paramName"]: param.get("value")
        for param in widget_payload["fxmacrodata_forex"]["params"]
    }
    cot_params = {
        param["paramName"]: param.get("value")
        for param in widget_payload["fxmacrodata_cot"]["params"]
    }

    assert "fxmacrodata_catalogue" in widget_payload
    assert "fxmacrodata_release_calendar" in widget_payload
    assert widget_payload["fxmacrodata_release_timeline"]["type"] == "chart"
    assert forex_params["base"] == "USD"
    assert forex_params["quote"] == "JPY"
    assert cot_params["currency"] == "USD"
    assert apps.status_code == 200
    app_payload = apps.json()
    assert {app["name"] for app in app_payload} == {
        "FXMacroData Macro Event Radar",
        "FXMacroData USD Macro Monitor",
        "FXMacroData Pro FX Board",
    }
    assert all(
        app["img"].startswith("http://testserver/assets/openbb-apps/")
        for app in app_payload
    )

    for app in app_payload:
        image_response = client.get(app["img"].replace("http://testserver", ""))
        assert image_response.status_code == 200
        assert image_response.headers["content-type"].startswith("image/svg+xml")
        assert "<svg" in image_response.text


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
            "frequency": "monthly",
            "source": None,
            "latest": None,
            "observations": 12,
            "coverage": "good",
            "access": "Free",
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
        return {
            "data": [
                {
                    "release": "inflation",
                    "announcement_datetime_utc": "2026-07-14T12:30:00+00:00",
                    "currency": "USD",
                    "source": "BLS",
                    "release_date_confirmed": True,
                }
            ]
        }

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get(
        "/release_calendar?currency=USD&indicator=inflation",
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "announcement_datetime": "2026-07-14 12:30 UTC",
            "event": "inflation",
            "name": "Inflation",
            "source": "BLS",
            "status": "Confirmed",
        }
    ]
    assert calls == [
        {
            "path": "/v1/calendar/usd",
            "params": {"indicator": "inflation"},
            "api_key": "test-key",
            "auth_mode": "header",
        }
    ]


def test_release_calendar_timeline_returns_plotly_figure(
    monkeypatch: pytest.MonkeyPatch,
):
    """The timeline endpoint should return a chart payload for Workspace."""

    async def fake_get_json(
        path,
        params=None,
        api_key=None,
        auth_mode="query",
        **kwargs,
    ):
        return {
            "data": [
                {
                    "release": "inflation",
                    "announcement_datetime_utc": "2026-07-14T12:30:00+00:00",
                },
                {
                    "release": "ppi",
                    "announcement_datetime_utc": "2026-07-15T12:30:00+00:00",
                },
            ]
        }

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get("/release_calendar_timeline?currency=USD")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["type"] == "bar"
    assert payload["data"][0]["x"] == ["2026-07-14", "2026-07-15"]
    assert payload["data"][0]["name"] == "Prices"
    assert payload["layout"]["barmode"] == "stack"
    assert payload["layout"]["title"]["text"] == "USD macro release radar"


def test_macro_indicator_retries_today_only_window(
    monkeypatch: pytest.MonkeyPatch,
):
    """Workspace's default same-day date window should fall back gracefully."""
    calls = []

    async def fake_get_json(
        path,
        params=None,
        api_key=None,
        auth_mode="query",
        **kwargs,
    ):
        calls.append({"path": path, "params": params})
        if len(calls) == 1:
            response = type("Response", (), {})()
            response.status_code = 404
            response.json = lambda: {
                "detail": {
                    "error_code": "NO_DATA_IN_REQUESTED_WINDOW",
                    "recommended_start_date": "2026-05-31",
                    "latest_available_date": "2026-05-31",
                }
            }
            response.text = "No observations"
            raise backend.HTTPError(response=response)
        return {
            "data": [
                {
                    "date": "2026-05-31",
                    "announcement_datetime": 1781094600,
                    "value": 2.4,
                }
            ]
        }

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get(
        "/macro_indicator?currency=USD&indicator=inflation"
        "&start_date=2026-07-08&end_date=2026-07-08"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "announcement_datetime": "2026-06-10 12:30 UTC",
            "observation_date": "2026-05-31",
            "value": 2.4,
        }
    ]
    assert calls == [
        {
            "path": "/v1/announcements/usd/inflation",
            "params": {"start_date": "2026-07-08", "end_date": "2026-07-08"},
        },
        {
            "path": "/v1/announcements/usd/inflation",
            "params": {"start_date": "2026-05-31", "end_date": "2026-05-31"},
        },
    ]


def test_cot_endpoint_formats_announcement_datetime(monkeypatch: pytest.MonkeyPatch):
    """COT rows should show readable publication datetimes, not epoch seconds."""

    async def fake_get_json(
        path,
        params=None,
        api_key=None,
        auth_mode="query",
        **kwargs,
    ):
        return {
            "data": [
                {
                    "date": "2026-06-30",
                    "announcement_datetime": 1783366200,
                    "nonreportable_long": 4753,
                    "report_date": "2026-06-30",
                    "release_date": "2026-07-06",
                    "release_datetime": "2026-07-07T05:30:00+10:00",
                    "release_source": "CFTC Commitment of Traders Release Schedule",
                }
            ]
        }

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get("/cot?currency=USD&start_date=2025-01-01")

    assert response.status_code == 200
    assert response.json() == [
        {
            "announcement_datetime": "2026-07-06 19:30 UTC",
            "report_date": "2026-06-30",
            "nonreportable_long": 4753,
            "release_source": "CFTC Commitment of Traders Release Schedule",
        }
    ]


def test_openbb_platform_api_can_import_workspace_backend():
    """OpenBB's API launcher should be able to load the Workspace backend."""
    api_utils = pytest.importorskip("openbb_platform_api.utils.api")

    imported_app = api_utils.import_app(
        "fxmacrodata/openbb/workspace_backend.py",
        "app",
        False,
    )

    route_paths = {route.path for route in imported_app.routes}

    assert isinstance(imported_app, FastAPI)
    assert {"/widgets.json", "/apps.json", "/catalogue"}.issubset(route_paths)
