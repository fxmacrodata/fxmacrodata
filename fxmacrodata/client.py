import requests
from typing import Optional
from .exceptions import FXMacroDataError


class Client:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def _request(self, url: str, params: dict, headers: dict) -> dict:
        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            raise FXMacroDataError(f"Request failed: {e}")
        if response.status_code != 200:
            raise FXMacroDataError(f"{response.status_code} - {response.text}")
        return response.json()

    def _auth_headers(self, currency: str, *, required: bool = True) -> dict:
        headers: dict[str, str] = {}
        if currency != "usd":
            if required and not self.api_key:
                raise FXMacroDataError(
                    f"API key required for {currency.upper()} endpoints."
                )
            if self.api_key:
                headers["X-API-Key"] = self.api_key
        return headers

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
    # FX spot rates (free)
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
        return self._request(url, params, {})

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
        if not self.api_key:
            raise FXMacroDataError("API key required for commodities endpoints.")
        url = f"{self.BASE_URL}/v1/commodities/{indicator.lower()}"
        headers: dict[str, str] = {"X-API-Key": self.api_key}
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._request(url, params, headers)
