"""Tests for shared FXMacroData OpenBB HTTP helpers."""

from __future__ import annotations

import logging
import traceback

import pytest
import requests

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


def _authenticated_failure(error_type, canary, status_code=401):
    request = requests.Request(
        "GET",
        "https://example.test/calendar",
        params={"api_key": canary},
        headers={"X-API-Key": canary},
    ).prepare()
    response = requests.Response()
    response.status_code = status_code
    response.url = request.url
    response.request = request
    error = error_type(
        f"Request failed for {request.url}", request=request, response=response
    )
    return error, request.url


def _assert_sanitized_failure(error, caplog, canary, authenticated_url):
    rendered_traceback = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    for rendered in (caplog.text, str(error), rendered_traceback, repr(error.args)):
        assert canary not in rendered
        assert authenticated_url not in rendered
    assert error.request is None
    assert error.response is None
    assert error.__cause__ is None
    assert error.__context__ is None
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("auth_mode", ["query", "header"])
@pytest.mark.parametrize("status_code", [401, 429])
def test_sync_request_redacts_http_errors_and_tracebacks(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    auth_mode: str,
    status_code: int,
):
    """Failed retries must not expose credentials through logs or error objects."""
    canary = "synthetic-redaction-canary"
    original, authenticated_url = _authenticated_failure(
        requests.HTTPError, canary, status_code=status_code
    )
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, dict(params), dict(headers or {}), timeout))
        raise original

    monkeypatch.setattr(helpers.requests, "get", fake_get)
    monkeypatch.setattr(helpers.time, "sleep", lambda pause: None)
    caplog.set_level(logging.WARNING, logger=helpers.logger.name)

    with pytest.raises(requests.HTTPError) as raised:
        helpers._sync_request(
            "https://example.test/calendar",
            {"limit": 7},
            api_key=canary,
            auth_mode=auth_mode,
            retry_count=2,
            pause=0,
        )

    assert raised.value is not original
    assert type(raised.value.status_code) is int
    assert raised.value.status_code == status_code
    assert len(calls) == 2
    assert len(caplog.records) == 2
    expected_params = {"limit": 7}
    expected_headers = {}
    if auth_mode == "query":
        expected_params["api_key"] = canary
    else:
        expected_headers["X-API-Key"] = canary
    assert all(
        call
        == (
            "https://example.test/calendar",
            expected_params,
            expected_headers,
            30,
        )
        for call in calls
    )
    _assert_sanitized_failure(raised.value, caplog, canary, authenticated_url)


@pytest.mark.parametrize("auth_mode", ["query", "header"])
def test_sync_request_retry_success_preserves_authentication(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    auth_mode: str,
):
    """A sanitized failed attempt must retain retry and authentication behavior."""
    canary = "synthetic-retry-canary"
    original, authenticated_url = _authenticated_failure(requests.HTTPError, canary)
    calls = []
    pauses = []
    params = {"indicator": None, "limit": 7}
    expected_payload = {"data": [{"ok": True}]}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return expected_payload

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append((url, dict(params), dict(headers or {}), timeout))
        if len(calls) == 1:
            raise original
        return FakeResponse()

    monkeypatch.setattr(helpers.requests, "get", fake_get)
    monkeypatch.setattr(helpers.time, "sleep", pauses.append)
    caplog.set_level(logging.WARNING, logger=helpers.logger.name)

    result = helpers._sync_request(
        "https://example.test/calendar",
        params,
        api_key=canary,
        auth_mode=auth_mode,
        retry_count=3,
        pause=0.25,
        timeout=9,
    )

    assert result is expected_payload
    assert params == {"indicator": None, "limit": 7}
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert calls[0][0] == "https://example.test/calendar"
    assert calls[0][3] == 9
    assert pauses == [0.25]
    if auth_mode == "query":
        assert calls[0][1] == {"limit": 7, "api_key": canary}
        assert calls[0][2] == {}
    else:
        assert calls[0][1] == {"limit": 7}
        assert calls[0][2] == {"X-API-Key": canary}
    assert len(caplog.records) == 1
    assert canary not in caplog.text
    assert authenticated_url not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_sync_request_exhausted_timeout_keeps_family_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """Timeout callers can keep catching Timeout without retaining secret URLs."""
    canary = "synthetic-timeout-canary"
    original, authenticated_url = _authenticated_failure(requests.Timeout, canary)
    attempts = []
    pauses = []

    def fake_get(url, params=None, headers=None, timeout=None):
        attempts.append(timeout)
        raise original

    monkeypatch.setattr(helpers.requests, "get", fake_get)
    monkeypatch.setattr(helpers.time, "sleep", pauses.append)
    caplog.set_level(logging.WARNING, logger=helpers.logger.name)

    with pytest.raises(requests.Timeout) as raised:
        helpers._sync_request(
            "https://example.test/calendar",
            {},
            api_key=canary,
            retry_count=3,
            pause=0.25,
            timeout=9,
        )

    assert raised.value is not original
    assert attempts == [9, 9, 9]
    assert pauses == [0.25, 0.25]
    assert len(caplog.records) == 3
    _assert_sanitized_failure(raised.value, caplog, canary, authenticated_url)


def test_sync_request_json_decode_error_has_safe_valid_attributes(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """JSON failures need their multi-argument exception constructor preserved."""
    canary = "synthetic-json-canary"
    request = requests.Request(
        "GET", "https://example.test/calendar", params={"api_key": canary}
    ).prepare()
    response = requests.Response()
    response.url = request.url
    response.request = request
    original = requests.exceptions.JSONDecodeError(
        f"Invalid JSON for {request.url}",
        f'{{"credential": "{canary}"}}',
        1,
        request=request,
        response=response,
    )
    attempts = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            raise original

    def fake_get(url, params=None, headers=None, timeout=None):
        attempts.append(url)
        return FakeResponse()

    monkeypatch.setattr(helpers.requests, "get", fake_get)
    monkeypatch.setattr(helpers.time, "sleep", lambda pause: None)
    caplog.set_level(logging.WARNING, logger=helpers.logger.name)

    with pytest.raises(requests.exceptions.JSONDecodeError) as raised:
        helpers._sync_request(
            "https://example.test/calendar",
            {},
            api_key=canary,
            retry_count=2,
            pause=0,
        )

    error = raised.value
    assert error is not original
    assert isinstance(error, requests.RequestException)
    assert isinstance(error.msg, str)
    assert isinstance(error.doc, str)
    assert isinstance(error.pos, int)
    assert 0 <= error.pos <= len(error.doc)
    assert error.lineno >= 1
    assert error.colno >= 1
    assert canary not in error.msg
    assert canary not in error.doc
    assert request.url not in error.msg
    assert request.url not in error.doc
    assert len(attempts) == 2
    assert len(caplog.records) == 2
    _assert_sanitized_failure(error, caplog, canary, request.url)
