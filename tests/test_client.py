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


# ------------------------------------------------------------------
# get_indicator
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# get_fx_price
# ------------------------------------------------------------------

def test_free_fx_price_endpoint():
    """Free forex price endpoint should return data without API key."""
    client = Client()
    result = client.get_fx_price("usd", "gbp", start_date="2025-01-01")
    assert result["base"] == "USD"
    assert result["quote"] == "GBP"
    assert isinstance(result["data"], list)


def test_fx_price_with_indicators():
    """Forex endpoint should accept technical indicator parameter."""
    client = Client()
    result = client.get_fx_price(
        "eur", "usd", start_date="2026-01-01", indicators="sma_20,rsi_14"
    )
    assert result["base"] == "EUR"
    assert result["quote"] == "USD"
    assert "indicators" in result


# ------------------------------------------------------------------
# get_calendar
# ------------------------------------------------------------------

def test_calendar_usd_no_key(client_without_key):
    """Calendar should return release dates for USD without API key."""
    result = client_without_key.get_calendar("usd")
    assert result["currency"] == "USD"
    assert isinstance(result["data"], list)


def test_calendar_with_indicator_filter(client_without_key):
    """Calendar should accept an indicator filter."""
    result = client_without_key.get_calendar("usd", indicator="inflation")
    assert result["currency"] == "USD"
    assert isinstance(result["data"], list)


# ------------------------------------------------------------------
# get_data_catalogue
# ------------------------------------------------------------------

def test_data_catalogue_usd_no_key(client_without_key):
    """USD data catalogue should work without API key."""
    result = client_without_key.get_data_catalogue("usd")
    assert isinstance(result, dict)
    assert "inflation" in result


def test_data_catalogue_non_usd_no_key(client_without_key):
    """Non-USD data catalogue should raise FXMacroDataError without API key."""
    with pytest.raises(FXMacroDataError) as exc:
        client_without_key.get_data_catalogue("aud")
    assert "API key required" in str(exc.value)


def test_data_catalogue_non_usd_with_key(client_with_key):
    """Non-USD data catalogue should succeed with API key."""
    result = client_with_key.get_data_catalogue("aud")
    assert isinstance(result, dict)
    assert "policy_rate" in result


# ------------------------------------------------------------------
# get_cot
# ------------------------------------------------------------------

def test_cot_usd_no_key(client_without_key):
    """USD COT data should work without API key."""
    result = client_without_key.get_cot("usd")
    assert result["currency"] == "USD"
    assert isinstance(result["data"], list)


def test_cot_non_usd_no_key(client_without_key):
    """Non-USD COT should raise FXMacroDataError without API key."""
    with pytest.raises(FXMacroDataError) as exc:
        client_without_key.get_cot("eur")
    assert "API key required" in str(exc.value)


def test_cot_non_usd_with_key(client_with_key):
    """Non-USD COT should succeed with API key."""
    result = client_with_key.get_cot("eur", start_date="2025-01-01")
    assert result["currency"] == "EUR"
    assert isinstance(result["data"], list)


# ------------------------------------------------------------------
# get_commodities
# ------------------------------------------------------------------

def test_commodities_gold(client_with_key):
    """Commodities gold endpoint should return price data."""
    result = client_with_key.get_commodities("gold", start_date="2026-01-01")
    assert result["indicator"] == "gold"
    assert isinstance(result["data"], list)


def test_commodities_no_key(client_without_key):
    """Commodities should raise FXMacroDataError without API key."""
    with pytest.raises(FXMacroDataError) as exc:
        client_without_key.get_commodities("gold")
    assert "API key required" in str(exc.value)
