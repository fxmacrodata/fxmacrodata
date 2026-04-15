import aiohttp  # type: ignore
from typing import Optional
from .exceptions import FXMacroDataError


class AsyncClient:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key: Optional[str] = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "AsyncClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def _request(self, url: str, params: dict, headers: dict) -> dict:
        if not self.session:
            self.session = aiohttp.ClientSession()
        async with self.session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise FXMacroDataError(f"{resp.status} - {text}")
            return await resp.json()

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
    # FX spot rates (free)
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
        return await self._request(url, params, {})

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
        if not self.api_key:
            raise FXMacroDataError("API key required for commodities endpoints.")
        url = f"{self.BASE_URL}/v1/commodities/{indicator.lower()}"
        headers: dict[str, str] = {"X-API-Key": self.api_key}
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._request(url, params, headers)
