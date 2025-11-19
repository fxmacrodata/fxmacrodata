import aiohttp
from .exceptions import FXMacroDataError

class AsyncClient:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: str = None):
        """
        Asynchronous FXMacroData Client.
        api_key: Required for non-USD currencies. USD is public.
        """
        self.api_key = api_key
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, currency: str, indicator: str, start_date: str = None, end_date: str = None):
        currency = currency.lower()
        url = f"{self.BASE_URL}/{currency}/{indicator}"

        headers = {}
        # Non-USD endpoints require API key
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
