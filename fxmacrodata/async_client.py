import aiohttp
from typing import Optional
from .exceptions import FXMacroDataError

class AsyncClient:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: Optional[str] = None):
        """
        Asynchronous FXMacroData Client.
        api_key: Required for non-USD currencies. USD is public.
        """
        self.api_key: Optional[str] = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "AsyncClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def get(
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

        assert self.session is not None  # mypy now knows session is initialized

        async with self.session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise FXMacroDataError(f"{resp.status} - {text}")
            return await resp.json()
