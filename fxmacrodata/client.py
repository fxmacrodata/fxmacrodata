import requests
from typing import Optional
from .exceptions import FXMacroDataError

class Client:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def get_indicator(
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

        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            raise FXMacroDataError(f"Request failed: {e}")

        if response.status_code != 200:
            raise FXMacroDataError(f"{response.status_code} - {response.text}")

        return response.json()

    # --------------------------------------------
    # NEW: Free Forex Endpoint
    # --------------------------------------------
    def get_fx_price(
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

        try:
            response = requests.get(url, params=params)
        except Exception as e:
            raise FXMacroDataError(f"Request failed: {e}")

        if response.status_code != 200:
            raise FXMacroDataError(f"{response.status_code} - {response.text}")

        return response.json()
