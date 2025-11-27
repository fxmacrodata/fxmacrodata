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

    async def get_indicator(
        self,
        currency: str,
        indicator: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        currency = currency.lower()
        url = f"{self.BASE_URL}/{currency}/{indicator}"

        headers = {}
        if currency != "usd":
            if not self.api_key:
                raise FXMacroDataError(f"API key required for {currency.upper()} endpoints.")
            headers["X-API-Key"] = self.api_key

        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        if not self.session:
            self.session = aiohttp.ClientSession()

        async with self.session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise FXMacroDataError(f"{resp.status} - {text}")
            return await resp.json()

    # --------------------------------------------
    # NEW: Free Forex Endpoint (Async)
    # --------------------------------------------
    async def get_fx_price(
        self,
        base: str,
        quote: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        base = base.lower()
        quote = quote.lower()

        url = f"{self.BASE_URL}/forex/{base}/{quote}"

        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        if not self.session:
            self.session = aiohttp.ClientSession()

        async with self.session.get(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise FXMacroDataError(f"{resp.status} - {text}")
            return await resp.json()
