import asyncio
import json
from typing import Optional, Union

import aiohttp  # type: ignore

from . import _http
from .exceptions import (
    FXMacroDataError,
    FXMacroDataTimeoutError,
    FXMacroDataTransportError,
)

AsyncTimeout = Optional[Union[float, aiohttp.ClientTimeout]]


class AsyncClient:
    BASE_URL = "https://api.fxmacrodata.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: AsyncTimeout = _http.DEFAULT_TIMEOUT,
    ):
        """Create an async client.

        ``timeout`` is the total seconds allowed per request, an
        ``aiohttp.ClientTimeout`` for finer control, or ``None`` to wait
        forever.
        """
        self.api_key: Optional[str] = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "AsyncClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    def _client_timeout(self) -> aiohttp.ClientTimeout:
        if isinstance(self.timeout, aiohttp.ClientTimeout):
            return self.timeout
        if self.timeout is None:
            return aiohttp.ClientTimeout(total=None)
        return aiohttp.ClientTimeout(total=float(self.timeout))

    async def _request(self, url: str, params: Optional[dict], headers: dict) -> dict:
        api_key = headers.get(_http.API_KEY_HEADER)
        has_key = bool(api_key)
        _http.check_transport(url, has_key)
        if not self.session:
            self.session = aiohttp.ClientSession()
        try:
            for _ in range(_http.MAX_REDIRECTS + 1):
                # Redirects are followed by hand: aiohttp re-sends custom
                # headers like ours to whatever host a redirect names.
                async with self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    allow_redirects=False,
                    timeout=self._client_timeout(),
                ) as resp:
                    location = resp.headers.get("Location")
                    if resp.status in _http.REDIRECT_STATUSES and location:
                        url = _http.resolve_redirect(url, location, has_key)
                        params = None  # the Location carries the query string
                        continue
                    status = resp.status
                    content_type = resp.headers.get("Content-Type")
                    if status != 200:
                        text = await resp.text()
                        raise _http.api_error(status, text, api_key)
                    body = await resp.read()
                    break
            else:
                raise _http.too_many_redirects()
        except FXMacroDataError:
            raise
        except asyncio.TimeoutError:
            raise FXMacroDataTimeoutError("Request timed out.") from None
        except Exception as e:
            # `from None`: the original exception can quote header values.
            raise FXMacroDataTransportError(
                "Request failed: " + _http.redact(f"{type(e).__name__}: {e}", api_key)
            ) from None

        try:
            data = json.loads(body)
        except ValueError:
            raise _http.invalid_json_error(status, content_type) from None
        return _http.check_payload(data, status, api_key)

    def _auth_headers(self, currency: str, *, required: bool = True) -> dict:
        # A configured key is sent for every currency, USD included: keyless
        # USD is the delayed, 90-day free tier, not the subscriber feed.
        api_key = _http.clean_api_key(self.api_key)
        if required and currency != "usd" and not api_key:
            raise FXMacroDataError(
                f"API key required for {currency.upper()} endpoints."
            )
        return {_http.API_KEY_HEADER: api_key} if api_key else {}

    def _required_key_headers(self, what: str) -> dict:
        api_key = _http.clean_api_key(self.api_key)
        if not api_key:
            raise FXMacroDataError(f"API key required for {what} endpoints.")
        return {_http.API_KEY_HEADER: api_key}

    # ------------------------------------------------------------------
    # Macroeconomic indicator time-series
    # ------------------------------------------------------------------
    async def get_indicator(
        self,
        currency: str,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        currency = currency.lower()
        url = f"{self.BASE_URL}/v1/announcements/{currency}/{indicator}"
        headers = self._auth_headers(currency)
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request(url, params, headers)

    # ------------------------------------------------------------------
    # FX spot rates
    # ------------------------------------------------------------------
    async def get_fx_price(
        self,
        base: str,
        quote: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        indicators: Optional[str] = None,
    ) -> dict:
        base = base.lower()
        quote = quote.lower()
        url = f"{self.BASE_URL}/v1/forex/{base}/{quote}"
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if indicators:
            params["indicators"] = indicators
        headers = self._required_key_headers("forex")
        return await self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Release calendar
    # ------------------------------------------------------------------
    async def get_calendar(
        self,
        currency: str,
        indicator: Optional[str] = None,
    ) -> dict:
        currency = currency.lower()
        url = f"{self.BASE_URL}/v1/calendar/{currency}"
        headers = self._auth_headers(currency, required=False)
        params: dict[str, str] = {}
        if indicator:
            params["indicator"] = indicator
        return await self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Data catalogue — available indicators for a currency
    # ------------------------------------------------------------------
    async def get_data_catalogue(
        self,
        currency: str,
        include_capabilities: bool = False,
        include_coverage: bool = False,
        indicator: Optional[str] = None,
    ) -> dict:
        currency = currency.lower()
        url = f"{self.BASE_URL}/v1/data_catalogue/{currency}"
        headers = self._auth_headers(currency)
        params: dict[str, str] = {}
        if include_capabilities:
            params["include_capabilities"] = "true"
        if include_coverage:
            params["include_coverage"] = "true"
        if indicator:
            params["indicator"] = indicator
        return await self._request(url, params, headers)

    # ------------------------------------------------------------------
    # CFTC Commitment of Traders (COT)
    # ------------------------------------------------------------------
    async def get_cot(
        self,
        currency: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        currency = currency.lower()
        url = f"{self.BASE_URL}/v1/cot/{currency}"
        headers = self._auth_headers(currency)
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Commodities (gold, silver, platinum)
    # ------------------------------------------------------------------
    async def get_commodities(
        self,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        headers = self._required_key_headers("commodities")
        url = f"{self.BASE_URL}/v1/commodities/{indicator.lower()}"
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request(url, params, headers)
