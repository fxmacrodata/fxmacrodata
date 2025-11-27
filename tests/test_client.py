import os
import pytest
from dotenv import load_dotenv
from fxmacrodata.client import Client
from fxmacrodata.exceptions import FXMacroDataError

# Load API key from .env for tests
load_dotenv()
API_KEY = os.getenv("FXMACRODATA_API_KEY")


@pytest.fixture
def client_with_key():
    return Client(api_key=API_KEY)


@pytest.fixture
def client_without_key():
    return Client(api_key=None)


def test_usd_endpoint_no_key(client_without_key):
    """USD indicator endpoint should work without API key."""
    result = client_without_key.get_indicator("usd", "gdp")
    assert result["currency"] == "USD"
    assert result["indicator"] == "gdp"
    assert isinstance(result["data"], list)


def test_non_usd_endpoint_no_key(client_without_key):
    """Non-USD indicator endpoint should raise FXMacroDataError without API key."""
    with pytest.raises(FXMacroDataError) as exc:
        client_without_key.get_indicator("aud", "gdp")
    assert "API key required" in str(exc.value)


def test_non_usd_endpoint_with_key(client_with_key):
    """Non-USD indicator endpoint should succeed with API key."""
    result = client_with_key.get_indicator(
        "aud", "gdp", start_date="2023-01-01", end_date="2023-12-31"
    )
    assert result["currency"] == "AUD"
    assert result["indicator"] == "gdp"
    assert isinstance(result["data"], list)


def test_free_fx_price_endpoint():
    """Free forex price endpoint should return data without API key."""
    client = Client()   # no key needed for forex endpoints
    result = client.get_fx_price("usd", "gbp", start_date="2025-01-01")
    assert result["base"] == "USD"
    assert result["quote"] == "GBP"
    assert isinstance(result["data"], dict)
