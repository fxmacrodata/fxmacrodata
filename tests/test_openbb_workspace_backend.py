"""Tests for the FXMacroData OpenBB Workspace backend."""

from __future__ import annotations

import traceback

import pytest
import requests

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient

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


@pytest.mark.parametrize("status_code", [401, 429])
@pytest.mark.parametrize("error_origin", ["sanitized", "response"])
def test_workspace_preserves_safe_upstream_status_without_error_details(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_origin: str,
):
    """Safe status metadata must survive without exposing authenticated URLs."""
    canary = "synthetic-workspace-canary"
    authenticated_url = f"https://example.test/calendar?api_key={canary}"
    error = requests.HTTPError("FXMacroData request failed")
    if error_origin == "sanitized":
        error.status_code = status_code
        assert error.request is None
        assert error.response is None
    else:
        request = requests.Request("GET", authenticated_url).prepare()
        upstream = requests.Response()
        upstream.status_code = status_code
        upstream.url = authenticated_url
        upstream.request = request
        upstream._content = f'{{"detail": "{canary}"}}'.encode()
        error = requests.HTTPError(
            f"Request failed for {authenticated_url}",
            request=request,
            response=upstream,
        )

    async def fake_get_json(path, params=None, api_key=None, auth_mode="query"):
        assert path == "/v1/calendar/usd"
        assert api_key == canary
        assert auth_mode == "header"
        raise error

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    client = TestClient(backend.app)

    response = client.get(
        "/release_calendar?currency=USD", headers={"X-API-Key": canary}
    )

    assert response.status_code == status_code
    detail = response.json()["detail"]
    assert isinstance(detail, str)
    assert canary not in response.text
    assert authenticated_url not in response.text
    assert canary not in detail
    assert authenticated_url not in detail


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 429])
@pytest.mark.parametrize("error_origin", ["sanitized", "response"])
async def test_workspace_proxy_error_traceback_drops_authenticated_exception(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_origin: str,
):
    """Raised proxy errors must detach upstream exceptions and secret URLs."""
    canary = "synthetic-traceback-canary"
    authenticated_url = f"https://example.test/calendar?api_key={canary}"
    original = requests.HTTPError("FXMacroData request failed")
    if error_origin == "sanitized":
        original.status_code = status_code
        assert original.request is None
        assert original.response is None
    else:
        upstream_request = requests.Request("GET", authenticated_url).prepare()
        upstream_response = requests.Response()
        upstream_response.status_code = status_code
        upstream_response.url = authenticated_url
        upstream_response.request = upstream_request
        original = requests.HTTPError(
            f"Request failed for {authenticated_url}",
            request=upstream_request,
            response=upstream_response,
        )

    async def fake_get_json(path, params=None, api_key=None, auth_mode="query"):
        assert api_key == canary
        assert auth_mode == "header"
        raise original

    monkeypatch.setattr(backend, "get_json", fake_get_json)
    request = backend.Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/release_calendar",
            "headers": [(b"x-api-key", canary.encode())],
            "query_string": b"",
        }
    )

    with pytest.raises(backend.HTTPException) as raised:
        await backend._proxy_json(request, "/v1/calendar/usd")

    error = raised.value
    rendered_traceback = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    assert error.status_code == status_code
    assert error.__cause__ is None
    assert error.__context__ is None
    assert all(value is not original for value in vars(error).values())
    assert all(value is not original for value in error.args)
    assert getattr(error, "request", None) is None
    assert getattr(error, "response", None) is None
    for rendered in (str(error), str(error.detail), rendered_traceback):
        assert canary not in rendered
        assert authenticated_url not in rendered


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
