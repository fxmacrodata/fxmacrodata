"""Regression tests for request hardening in Client and AsyncClient.

Covers: the API key never following a redirect to another origin, request
timeouts, the key never appearing in error text or tracebacks, and 200
responses with error or malformed bodies raising typed errors.

Redirect and timeout tests run against real local HTTP servers on two ports
(two distinct origins), so they exercise the HTTP libraries' own behaviour.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from fxmacrodata import (
    AsyncClient,
    Client,
    FXMacroDataAPIError,
    FXMacroDataError,
    FXMacroDataRedirectError,
    FXMacroDataResponseError,
    FXMacroDataTimeoutError,
    FXMacroDataTransportError,
)

SECRET = "sk_live_SECRET123"


# ----------------------------------------------------------------------
# Local servers
# ----------------------------------------------------------------------


class _Server:
    """A tiny scripted HTTP server that records every request it receives."""

    def __init__(self) -> None:
        self.routes: dict = {}
        self.requests: list = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                path = self.path.split("?", 1)[0]
                server.requests.append(
                    {"path": self.path, "headers": dict(self.headers.items())}
                )
                status, headers, body, delay = server.routes.get(
                    path, (404, {}, b'{"detail": "Not Found"}', 0)
                )
                if delay:
                    time.sleep(delay)
                try:
                    self.send_response(status)
                    for name, value in headers.items():
                        self.send_header(name, value)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    pass  # client gave up (timeout tests)

            def log_message(self, *args) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.origin = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def route(self, path, status=200, headers=None, body=b"", delay=0.0):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
            headers = {"Content-Type": "application/json", **(headers or {})}
        self.routes[path] = (status, headers or {}, body, delay)

    def received_key(self) -> bool:
        return any(
            k.lower() == "x-api-key" for r in self.requests for k in r["headers"]
        )

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def api():
    server = _Server()
    yield server
    server.close()


@pytest.fixture
def attacker():
    server = _Server()
    yield server
    server.close()


def _client(cls, origin, **kwargs):
    client = cls(**kwargs)
    client.BASE_URL = origin
    return client


OK = {"currency": "AUD", "indicator": "gdp", "data": [{"date": "2024-01-01"}]}


def _assert_secret_absent(exc: BaseException) -> None:
    text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    assert SECRET not in str(exc)
    assert SECRET not in text


# ----------------------------------------------------------------------
# (1) Redirects never carry the key to another origin
# ----------------------------------------------------------------------


def test_cross_origin_redirect_with_key_is_refused(api, attacker):
    attacker.route("/v1/announcements/aud/gdp", body=OK)
    api.route(
        "/v1/announcements/aud/gdp",
        status=302,
        headers={"Location": f"{attacker.origin}/v1/announcements/aud/gdp"},
    )

    with pytest.raises(FXMacroDataRedirectError) as exc:
        _client(Client, api.origin, api_key=SECRET).get_indicator("aud", "gdp")

    assert attacker.requests == []
    assert isinstance(exc.value, FXMacroDataError)
    _assert_secret_absent(exc.value)


@pytest.mark.asyncio
async def test_async_cross_origin_redirect_with_key_is_refused(api, attacker):
    attacker.route("/v1/announcements/aud/gdp", body=OK)
    api.route(
        "/v1/announcements/aud/gdp",
        status=307,
        headers={"Location": f"{attacker.origin}/v1/announcements/aud/gdp"},
    )

    async with _client(AsyncClient, api.origin, api_key=SECRET) as client:
        with pytest.raises(FXMacroDataRedirectError):
            await client.get_indicator("aud", "gdp")

    assert attacker.requests == []


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_same_origin_redirect_is_followed_with_key(api, status):
    api.route("/old", status=status, headers={"Location": "/new?start_date=2024"})
    api.route("/new", body=OK)
    client = Client(api_key=SECRET)

    result = client._request(f"{api.origin}/old", {"x": "1"}, {"X-API-Key": SECRET})

    assert result == OK
    assert [r["path"] for r in api.requests] == ["/old?x=1", "/new?start_date=2024"]
    assert api.requests[1]["headers"]["X-API-Key"] == SECRET


@pytest.mark.asyncio
async def test_async_same_origin_redirect_is_followed_with_key(api):
    api.route("/v1/forex/eur/usd", status=308, headers={"Location": "/v2/forex"})
    api.route("/v2/forex", body=OK)

    async with _client(AsyncClient, api.origin, api_key=SECRET) as client:
        assert await client.get_fx_price("eur", "usd") == OK

    assert api.requests[1]["headers"]["X-API-Key"] == SECRET


def test_keyless_cross_origin_redirect_is_followed(api, attacker):
    attacker.route("/v1/calendar/usd", body={"currency": "USD", "data": []})
    api.route(
        "/v1/calendar/usd",
        status=301,
        headers={"Location": f"{attacker.origin}/v1/calendar/usd"},
    )

    result = _client(Client, api.origin).get_calendar("usd")

    assert result["currency"] == "USD"
    assert not attacker.received_key()


def test_redirect_loop_is_bounded(api):
    api.route("/v1/calendar/usd", status=302, headers={"Location": "/v1/calendar/usd"})

    with pytest.raises(FXMacroDataRedirectError, match="Too many redirects"):
        _client(Client, api.origin).get_calendar("usd")

    assert len(api.requests) == 6


class _FakeResponse:
    def __init__(self, status_code=200, headers=None, payload=None, text=""):
        self.status_code = status_code
        self.headers = requests.structures.CaseInsensitiveDict(headers or {})
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_https_to_http_downgrade_redirect_is_refused(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse(
            301, {"Location": "http://api.fxmacrodata.com/v1/announcements/aud/gdp"}
        )

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    with pytest.raises(FXMacroDataRedirectError, match="different origin"):
        Client(api_key=SECRET).get_indicator("aud", "gdp")

    assert calls == ["https://api.fxmacrodata.com/v1/announcements/aud/gdp"]


def test_requests_auto_redirects_are_disabled(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        return _FakeResponse(payload=OK)

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)
    Client(api_key=SECRET).get_indicator("aud", "gdp")

    assert seen["allow_redirects"] is False


def test_key_is_never_sent_over_plain_http_to_a_remote_host(monkeypatch):
    def fake_get(*args, **kwargs):
        raise AssertionError("request should not be made")

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)
    client = Client(api_key=SECRET)
    client.BASE_URL = "http://api.fxmacrodata.com"

    with pytest.raises(FXMacroDataError, match="plain HTTP"):
        client.get_indicator("aud", "gdp")


# ----------------------------------------------------------------------
# (2) Timeouts
# ----------------------------------------------------------------------


def test_default_timeout_is_sent(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        return _FakeResponse(payload=OK)

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)
    Client().get_indicator("usd", "gdp")

    assert seen["timeout"] == 30.0


def test_timeout_is_configurable(monkeypatch):
    seen = {}

    def fake_get(url, **kwargs):
        seen.update(kwargs)
        return _FakeResponse(payload=OK)

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)
    Client(timeout=(3.05, 60)).get_indicator("usd", "gdp")

    assert seen["timeout"] == (3.05, 60)


def test_slow_server_raises_timeout_error(api):
    api.route("/v1/calendar/usd", body=OK, delay=2.0)
    client = _client(Client, api.origin, api_key=SECRET, timeout=0.2)

    started = time.monotonic()
    with pytest.raises(FXMacroDataTimeoutError) as exc:
        client.get_calendar("usd")

    assert time.monotonic() - started < 1.5
    assert isinstance(exc.value, FXMacroDataTransportError)


@pytest.mark.asyncio
async def test_async_slow_server_raises_timeout_error(api):
    api.route("/v1/calendar/usd", body=OK, delay=2.0)

    async with _client(AsyncClient, api.origin, timeout=0.2) as client:
        started = time.monotonic()
        with pytest.raises(FXMacroDataTimeoutError):
            await client.get_calendar("usd")

    assert time.monotonic() - started < 1.5


def test_async_default_timeout():
    assert AsyncClient()._client_timeout().total == 30.0
    assert AsyncClient(timeout=None)._client_timeout().total is None


# ----------------------------------------------------------------------
# (3) The key never appears in error text
# ----------------------------------------------------------------------


@pytest.mark.parametrize("bad_key", [f"{SECRET} x", f"{SECRET}\tx", f"{SECRET}\x00"])
def test_malformed_key_fails_without_echoing_it(monkeypatch, bad_key):
    calls = []
    monkeypatch.setattr(
        "fxmacrodata.client.requests.get", lambda *a, **k: calls.append(a)
    )

    for call in (
        lambda c: c.get_indicator("aud", "gdp"),
        lambda c: c.get_fx_price("eur", "usd"),
        lambda c: c.get_commodities("gold"),
    ):
        with pytest.raises(FXMacroDataError, match="API key contains") as exc:
            call(Client(api_key=bad_key))
        _assert_secret_absent(exc.value)

    assert calls == []


@pytest.mark.asyncio
async def test_async_malformed_key_fails_without_echoing_it():
    client = AsyncClient(api_key=f"{SECRET}\r\nX-Injected: 1")
    with pytest.raises(FXMacroDataError, match="API key contains") as exc:
        await client.get_indicator("aud", "gdp")
    _assert_secret_absent(exc.value)
    assert client.session is None  # failed before any connection


def test_surrounding_whitespace_is_stripped(api):
    api.route("/v1/announcements/aud/gdp", body=OK)

    _client(Client, api.origin, api_key=f"  {SECRET}\n").get_indicator("aud", "gdp")

    assert api.requests[0]["headers"]["X-API-Key"] == SECRET


def test_real_requests_invalid_header_error_would_leak():
    """Documents why keys are validated first: requests quotes the value."""
    with pytest.raises(requests.exceptions.InvalidHeader) as exc:
        requests.Request(
            "GET", "https://example.invalid", headers={"X-API-Key": f" {SECRET}"}
        ).prepare()
    assert SECRET in str(exc.value)


def test_transport_error_text_is_redacted(monkeypatch):
    def fake_get(url, **kwargs):
        raise requests.ConnectionError(f"proxy rejected header {SECRET}")

    monkeypatch.setattr("fxmacrodata.client.requests.get", fake_get)

    with pytest.raises(FXMacroDataTransportError) as exc:
        Client(api_key=SECRET).get_indicator("aud", "gdp")

    assert "Request failed" in str(exc.value)
    _assert_secret_absent(exc.value)


def test_error_body_echoing_key_is_redacted(api):
    api.route(
        "/v1/announcements/aud/gdp",
        status=401,
        body={"detail": f"Invalid API key {SECRET}"},
    )

    with pytest.raises(FXMacroDataAPIError) as exc:
        _client(Client, api.origin, api_key=SECRET).get_indicator("aud", "gdp")

    assert exc.value.status_code == 401
    assert str(exc.value).startswith("401 - ")  # format unchanged from 1.2.1
    _assert_secret_absent(exc.value)


@pytest.mark.asyncio
async def test_async_error_body_echoing_key_is_redacted(api):
    api.route("/v1/cot/aud", status=403, body={"detail": f"bad key {SECRET}"})

    async with _client(AsyncClient, api.origin, api_key=SECRET) as client:
        with pytest.raises(FXMacroDataAPIError) as exc:
            await client.get_cot("aud")

    assert exc.value.status_code == 403
    _assert_secret_absent(exc.value)


def test_long_error_body_is_truncated(api):
    api.route("/v1/calendar/usd", status=502, body=b"x" * 50_000)

    with pytest.raises(FXMacroDataAPIError) as exc:
        _client(Client, api.origin).get_calendar("usd")

    assert len(str(exc.value)) < 1100


# ----------------------------------------------------------------------
# (4) HTTP 200 with an error or malformed body
# ----------------------------------------------------------------------


MALFORMED_200 = [
    (b"<html>captive portal</html>", {"Content-Type": "text/html"}, "not valid JSON"),
    (b"", {}, "not valid JSON"),
    (b"[1, 2]", {"Content-Type": "application/json"}, "got list"),
    (b"null", {"Content-Type": "application/json"}, "got NoneType"),
    (b'"ok"', {"Content-Type": "application/json"}, "got str"),
    (b'{"detail": "Upstream unavailable"}', {}, "Upstream unavailable"),
    (b'{"error": "quota exceeded"}', {}, "quota exceeded"),
]


@pytest.mark.parametrize("body,headers,message", MALFORMED_200)
def test_malformed_200_raises_response_error(api, body, headers, message):
    api.route("/v1/calendar/usd", body=body, headers=headers)

    with pytest.raises(FXMacroDataResponseError, match=message) as exc:
        _client(Client, api.origin).get_calendar("usd")

    assert exc.value.status_code == 200
    assert isinstance(exc.value, FXMacroDataError)


@pytest.mark.asyncio
@pytest.mark.parametrize("body,headers,message", MALFORMED_200)
async def test_async_malformed_200_raises_response_error(api, body, headers, message):
    api.route("/v1/calendar/usd", body=body, headers=headers)

    async with _client(AsyncClient, api.origin) as client:
        with pytest.raises(FXMacroDataResponseError, match=message):
            await client.get_calendar("usd")


def test_200_error_body_echoing_key_is_redacted(api):
    api.route("/v1/announcements/aud/gdp", body={"error": f"key {SECRET} revoked"})

    with pytest.raises(FXMacroDataResponseError) as exc:
        _client(Client, api.origin, api_key=SECRET).get_indicator("aud", "gdp")

    _assert_secret_absent(exc.value)


def test_catalogue_shape_without_data_key_is_accepted(api):
    """The catalogue is keyed by indicator slug and has no top-level `data`."""
    catalogue = {"gdp": {"name": "GDP"}, "detail": {"name": "Detail series"}}
    api.route("/v1/data_catalogue/usd", body=catalogue)

    assert _client(Client, api.origin).get_data_catalogue("usd") == catalogue


def test_payload_with_data_and_detail_is_accepted(api):
    payload = {"data": [], "detail": "No releases in range"}
    api.route("/v1/calendar/usd", body=payload)

    assert _client(Client, api.origin).get_calendar("usd") == payload


# ----------------------------------------------------------------------
# OpenBB provider request path (fxmacrodata.openbb.utils.helpers)
# ----------------------------------------------------------------------


def test_openbb_key_is_sent_as_header_never_in_url(api, caplog):
    from fxmacrodata.openbb.utils import helpers

    api.route("/v1/cot/aud", status=500, body={"detail": "boom"})

    with pytest.raises(requests.HTTPError) as exc:
        helpers._sync_request(
            f"{api.origin}/v1/cot/aud",
            {},
            api_key=SECRET,
            auth_mode="query",  # legacy value: must no longer put the key in the URL
            retry_count=2,
            pause=0,
        )

    assert all(SECRET not in r["path"] for r in api.requests)
    assert api.requests[0]["headers"]["X-API-Key"] == SECRET
    _assert_secret_absent(exc.value)
    assert SECRET not in caplog.text


def test_openbb_cross_origin_redirect_with_key_is_refused(api, attacker):
    from fxmacrodata.openbb.utils import helpers

    attacker.route("/v1/forex/eur/usd", body=OK)
    api.route(
        "/v1/forex/eur/usd",
        status=302,
        headers={"Location": f"{attacker.origin}/v1/forex/eur/usd"},
    )

    with pytest.raises(FXMacroDataRedirectError):
        helpers._sync_request(f"{api.origin}/v1/forex/eur/usd", {}, api_key=SECRET)

    assert attacker.requests == []


def test_openbb_malformed_key_is_not_logged_or_raised(api, caplog):
    from fxmacrodata.openbb.utils import helpers

    with pytest.raises(FXMacroDataError, match="API key contains") as exc:
        helpers._sync_request(f"{api.origin}/v1/cot/aud", {}, api_key=f" {SECRET} x")

    _assert_secret_absent(exc.value)
    assert SECRET not in caplog.text
    assert api.requests == []


def test_openbb_html_200_raises_response_error(api):
    from fxmacrodata.openbb.utils import helpers

    api.route("/v1/calendar/usd", body=b"<html>", headers={"Content-Type": "text/html"})

    with pytest.raises(FXMacroDataResponseError):
        helpers._sync_request(f"{api.origin}/v1/calendar/usd", {}, retry_count=1)
