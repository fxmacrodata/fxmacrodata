import requests
from .exceptions import FXMacroDataError

class Client:
    BASE_URL = "https://fxmacrodata.p.rapidapi.com/api"
    RAPIDAPI_HOST = "fxmacrodata.p.rapidapi.com"

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
        if currency != "usd":
            if not self.api_key:
                raise FXMacroDataError(
                    f"API key required for {currency.upper()} endpoints."
                )
            headers["x-rapidapi-key"] = self.api_key
            headers["x-rapidapi-host"] = self.RAPIDAPI_HOST

        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            raise FXMacroDataError(f"{response.status_code} - {response.text}")

        return response.json()
