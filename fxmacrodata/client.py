import requests
from .exceptions import FXMacroDataError

class Client:
    BASE_URL = "https://fxmacrodata.com/api"

    def __init__(self, api_key: str = None):
        """
        Synchronous FXMacroData Client.
        api_key: Required for non-USD currencies. USD is public.
        """
        self.api_key = api_key

    def get(self, currency: str, indicator: str, start_date: str = None, end_date: str = None):
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

        try:
            response = requests.get(url, headers=headers, params=params)
        except Exception as e:
            raise FXMacroDataError(f"Request failed: {e}")

        if response.status_code != 200:
            raise FXMacroDataError(f"{response.status_code} - {response.text}")

        return response.json()
