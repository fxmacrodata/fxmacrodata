"""Tests for shared FXMacroData OpenBB HTTP helpers."""

from __future__ import annotations

import pytest

from fxmacrodata.openbb.utils import helpers


def test_resolve_api_key_prefers_openbb_credentials(monkeypatch: pytest.MonkeyPatch):
    """OpenBB credential values should take precedence over environment vars."""
    monkeypatch.setenv("FXMACRODATA_API_KEY", "env-key")

    assert (
        helpers.resolve_api_key(
            {"fxmacrodata_api_key": "credential-key", "api_key": "generic-key"}
        )
        == "credential-key"
    )


def test_resolve_api_key_accepts_env_fallback(monkeypatch: pytest.MonkeyPatch):
    """Local developer env vars should work when OpenBB credentials are absent."""
    monkeypatch.delenv("FXMACRODATA_API_KEY", raising=False)
    monkeypatch.setenv("FXMD_API_KEY", "local-env-key")

    assert helpers.resolve_api_key({}) == "local-env-key"
    assert helpers.resolve_api_key(None) == "local-env-key"


def test_sync_request_sends_header_auth_and_filters_null_params(
    monkeypatch: pytest.MonkeyPatch,
):
    """Workspace proxy mode should send API keys as headers, not URL params."""
    calls = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"ok": True}]}

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(helpers.requests, "get", fake_get)

    payload = helpers._sync_request(
        "https://fxmacrodata.com/api/v1/calendar/usd",
        {"indicator": None, "limit": 10},
        api_key="test-key",
        auth_mode="header",
        retry_count=1,
    )

    assert payload == {"data": [{"ok": True}]}
    assert calls == [
        {
            "url": "https://fxmacrodata.com/api/v1/calendar/usd",
            "params": {"limit": 10},
            "headers": {"X-API-Key": "test-key"},
            "timeout": 30,
        }
    ]


@pytest.mark.asyncio
async def test_get_data_returns_top_level_data(monkeypatch: pytest.MonkeyPatch):
    """Provider fetchers consume the top-level FXMacroData data array."""

    def fake_sync_request(
        url,
        params,
        api_key=None,
        auth_mode="query",
        retry_count=3,
        pause=0.1,
        timeout=30,
    ):
        return {"data": [{"release": "inflation"}], "meta": {"url": url}}

    monkeypatch.setattr(helpers, "_sync_request", fake_sync_request)

    data = await helpers.get_data(
        "/v1/calendar/usd",
        params={"indicator": "inflation"},
        api_key="test-key",
    )

    assert data == [{"release": "inflation"}]
