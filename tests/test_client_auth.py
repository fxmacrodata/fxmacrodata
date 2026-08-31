"""Unit tests for SDK auth and request construction."""

from __future__ import annotations

import pytest

from fxmacrodata.client import Client
from fxmacrodata.exceptions import FXMacroDataError


def test_non_usd_indicator_uses_api_key_header(monkeypatch: pytest.MonkeyPatch):
    """Subscriber macro endpoints should send API keys as headers."""
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {"data": []}

    def fake_get(url, headers=None, params=None):
        calls.append({"url": url, "headers": headers, "params": params})
        return FakeResponse()

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    Client(api_key="test-key").get_indicator(
        "aud",
        "gdp",
        start_date="2024-01-01",
    )

    assert calls == [
        {
            "url": "https://api.fxmacrodata.com/v1/announcements/aud/gdp",
            "headers": {"X-API-Key": "test-key"},
            "params": {"start_date": "2024-01-01"},
        }
    ]


def test_fx_price_requires_api_key_before_request(monkeypatch: pytest.MonkeyPatch):
    """FX spot history should fail locally before making a keyless request."""
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    with pytest.raises(FXMacroDataError, match="API key required"):
        Client().get_fx_price("eur", "usd")

    assert called is False


def test_fx_price_uses_api_key_header(monkeypatch: pytest.MonkeyPatch):
    """FX spot history should authenticate with the documented header."""
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self) -> dict:
            return {"data": []}

    def fake_get(url, headers=None, params=None):
        calls.append({"url": url, "headers": headers, "params": params})
        return FakeResponse()

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    Client(api_key="test-key").get_fx_price(
        "eur",
        "usd",
        start_date="2026-01-01",
        indicators="sma_20",
    )

    assert calls == [
        {
            "url": "https://api.fxmacrodata.com/v1/forex/eur/usd",
            "headers": {"X-API-Key": "test-key"},
            "params": {"start_date": "2026-01-01", "indicators": "sma_20"},
        }
    ]


def test_commodities_require_api_key_before_request(monkeypatch: pytest.MonkeyPatch):
    """Commodity history should fail locally before making a keyless request."""
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    with pytest.raises(FXMacroDataError, match="API key required"):
        Client().get_commodities("gold")

    assert called is False
