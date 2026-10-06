import requests
from typing import Optional, Tuple, Union

from . import _http
from .exceptions import (
    FXMacroDataError,
    FXMacroDataTimeoutError,
    FXMacroDataTransportError,
)

Timeout = Optional[Union[float, Tuple[float, float]]]


class Client:
    BASE_URL = "https://api.fxmacrodata.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Timeout = _http.DEFAULT_TIMEOUT,
    ):
        """Create a client.

        ``timeout`` is in seconds and accepts anything ``requests`` does: a
        number, a ``(connect, read)`` tuple, or ``None`` to wait forever.
        """
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, url: str, params: Optional[dict], headers: dict) -> dict:
        api_key = headers.get(_http.API_KEY_HEADER)
        has_key = bool(api_key)
        _http.check_transport(url, has_key)
        for _ in range(_http.MAX_REDIRECTS + 1):
            try:
                # Redirects are followed by hand: requests drops Authorization
                # on a cross-host redirect but keeps custom headers like ours.
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
            except requests.Timeout:
                raise FXMacroDataTimeoutError(
                    f"Request timed out after {self.timeout} seconds."
                ) from None
            except Exception as e:
                # `from None`: the original exception can quote header values.
                raise FXMacroDataTransportError(
                    "Request failed: "
                    + _http.redact(f"{type(e).__name__}: {e}", api_key)
                ) from None
            location = response.headers.get("Location")
            if response.status_code in _http.REDIRECT_STATUSES and location:
                url = _http.resolve_redirect(url, location, has_key)
                params = None  # the Location already carries the query string
                continue
            break
        else:
            raise _http.too_many_redirects()

        if response.status_code != 200:
            raise _http.api_error(response.status_code, response.text, api_key)
        try:
            data = response.json()
        except ValueError:
            raise _http.invalid_json_error(
                response.status_code, response.headers.get("Content-Type")
            ) from None
        return _http.check_payload(data, response.status_code, api_key)

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
    def get_indicator(
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
        return self._request(url, params, headers)

    # ------------------------------------------------------------------
    # FX spot rates
    # ------------------------------------------------------------------
    def get_fx_price(
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
        return self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Release calendar
    # ------------------------------------------------------------------
    def get_calendar(
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
        return self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Data catalogue — available indicators for a currency
    # ------------------------------------------------------------------
    def get_data_catalogue(
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
        return self._request(url, params, headers)

    # ------------------------------------------------------------------
    # CFTC Commitment of Traders (COT)
    # ------------------------------------------------------------------
    def get_cot(
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
        return self._request(url, params, headers)

    # ------------------------------------------------------------------
    # Commodities (gold, silver, platinum)
    # ------------------------------------------------------------------
    def get_commodities(
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
        return self._request(url, params, headers)
