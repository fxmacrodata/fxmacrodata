# FXMacroData Python SDK 🐍📊

![PyPI Version](https://img.shields.io/pypi/v/fxmacrodata?color=blue&logo=python&style=flat-square)
![Python Versions](https://img.shields.io/pypi/pyversions/fxmacrodata?style=flat-square)
![License](https://img.shields.io/github/license/fxmacrodata/fxmacrodata?style=flat-square)
![Build](https://img.shields.io/github/actions/workflow/status/fxmacrodata/fxmacrodata/ci-cd.yml?style=flat-square&logo=github)

The **FXMacroData Python SDK** provides a simple and efficient interface for fetching **macroeconomic indicators**, **forex prices**, **release calendars**, **COT positioning**, and **commodity prices** from [FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=readme&utm_campaign=python_sdk).  

It includes both synchronous and asynchronous clients, supports free USD endpoints, and offers a free Forex Price API for exchange rate data.

---

## 🌟 Features

- Fetch:
  - **Macroeconomic indicators** — policy rates, inflation, GDP, unemployment, bond yields, and 100+ more
  - **FX spot rates** with optional technical indicators (SMA, RSI, MACD, Bollinger Bands)
  - **Release calendars** — upcoming economic data release dates
  - **Data catalogue** — discover available indicators per currency
  - **COT data** — CFTC Commitment of Traders positioning
  - **Commodity prices** — gold, silver, platinum
- Free access to **USD** macro data.
- Free **Forex Price API** (`get_fx_price`).
- API key required only for **non-USD** indicators.
- Full support for:
  - **Synchronous client**
  - **Asynchronous client**
- Lightweight: depends only on `requests` and `aiohttp`.

---

## 📦 Installation

Install from PyPI:

```bash
pip install fxmacrodata
```

Or install the latest version from GitHub:

```bash
pip install git+https://github.com/fxmacrodata/fxmacrodata.git
```

---

## 🔧 Usage

### Synchronous

```python
from fxmacrodata import Client

client = Client(api_key="YOUR_API_KEY")

# Fetch macroeconomic indicators
data = client.get_indicator(
    "aud", "policy_rate",
    start_date="2023-01-01",
    end_date="2023-11-01"
)
print(data)

# Free Forex Price Endpoint
fx = client.get_fx_price("usd", "gbp", start_date="2025-01-01")
print(fx)

# Forex with technical indicators
fx = client.get_fx_price("eur", "usd", indicators="sma_20,rsi_14,macd")
print(fx)

# Release calendar
calendar = client.get_calendar("usd")
print(calendar)

# Data catalogue — discover available indicators
catalogue = client.get_data_catalogue("usd")
print(catalogue)

# COT positioning data
cot = client.get_cot("eur", start_date="2025-01-01")
print(cot)

# Commodity prices
gold = client.get_commodities("gold", start_date="2026-01-01")
print(gold)
```

---

### Asynchronous

```python
import asyncio
from fxmacrodata import AsyncClient

async def main():
    async with AsyncClient(api_key="YOUR_API_KEY") as client:
        # Fetch macroeconomic indicators
        data = await client.get_indicator("eur", "inflation")
        print(data)

        # Free Forex Price Endpoint
        fx = await client.get_fx_price("usd", "jpy")
        print(fx)

        # Release calendar
        calendar = await client.get_calendar("usd")
        print(calendar)

        # Data catalogue
        catalogue = await client.get_data_catalogue("usd")
        print(catalogue)

        # COT positioning
        cot = await client.get_cot("jpy")
        print(cot)

        # Commodity prices
        gold = await client.get_commodities("gold")
        print(gold)

asyncio.run(main())
```

---

## 📘 API Overview

### `get_indicator(currency, indicator, start_date=None, end_date=None)`
Fetches macroeconomic indicator time series data.

- `currency`: `"usd"`, `"aud"`, `"eur"`, `"gbp"`, `"cad"`, `"nok"`, `"nzd"`, `"jpy"`, `"brl"`, `"cny"`, `"dkk"`, `"pln"`, `"sek"`, `"sgd"`, etc.
- `indicator`: `"policy_rate"`, `"inflation"`, `"gdp"`, `"unemployment"`, `"trade_balance"`, `"current_account_balance"`, `"gov_bond_10y"`, etc.
- **API key required for non-USD.**

### `get_fx_price(base, quote, start_date=None, end_date=None, indicators=None)`
Fetches daily FX spot rates (ECB reference rates) between two currencies.

- `indicators`: Optional comma-separated technical indicators — `"sma_20"`, `"sma_50"`, `"sma_200"`, `"rsi_14"`, `"macd"`, `"ema_12"`, `"ema_26"`, `"bollinger_bands"`, or `"all"`.
- **No API key needed.**

### `get_calendar(currency, indicator=None)`
Fetches upcoming economic data release dates for a currency.

- `indicator`: Optional filter to a specific indicator slug.
- Returns `announcement_datetime` (Unix timestamp) and `release` (indicator slug).

### `get_data_catalogue(currency, include_capabilities=False, include_coverage=False, indicator=None)`
Discovers available macroeconomic indicators for a given currency.

- Returns a dict keyed by indicator slug with `name`, `unit`, `frequency`, and `has_official_forecast`.
- **API key required for non-USD.**

### `get_cot(currency, start_date=None, end_date=None)`
Fetches CFTC Commitment of Traders (COT) positioning data.

- Supported currencies: `AUD`, `CAD`, `CHF`, `EUR`, `GBP`, `JPY`, `NZD`, `USD`.
- **API key required for non-USD.**

### `get_commodities(indicator, start_date=None, end_date=None)`
Fetches commodity price time series.

- `indicator`: `"gold"`, `"silver"`, or `"platinum"`.
- **API key required.**

---

## 💹 Supported Currencies & Indicators

| Category | Metric | USD | EUR | AUD | GBP |
|---------|--------|-----|-----|-----|-----|
| **Economy** | GDP Growth | ✓ | ✓ | ✓ | ✓ |
|  | Inflation Rate | ✓ | ✓ | ✓ | ✓ |
|  | Trade Balance | ✓ | ✓ | ✓ | ✓ |
|  | Current Account Balance | ✓ | ✓ | ✓ | ✓ |
| **Labor Market** | Unemployment Rate | ✓ | ✓ | ✓ | ✓ |
|  | Employment Level | ✓ | — | ✓ | ✓ |
|  | Full-Time Employment | ✓ | — | ✓ | — |
|  | Part-Time Employment | ✓ | — | ✓ | — |
|  | Participation Rate | ✓ | — | ✓ | ✓ |
|  | Non-Farm Payrolls | ✓ | — | — | — |
| **Monetary Policy** | Policy Rate | ✓ | ✓ | ✓ | ✓ |
|  | Interbank Rate | ✓ | ✓ | ✓ | ✓ |
| **Government Bond Yields** | 2-Year Govt Bond | ✓ | ✓ | ✓ | — |
|  | 3-Year Govt Bond | ✓ | ✓ | ✓ | — |
|  | 5-Year Govt Bond | ✓ | ✓ | ✓ | ✓ |
|  | 10-Year Govt Bond | ✓ | ✓ | ✓ | ✓ |
|  | Inflation-Linked Bond | ✓ | — | ✓ | ✓ |

---

## 📄 License

MIT License © FXMacroData

---

## 🌐 Links

- Website: https://fxmacrodata.com
- API Docs: https://fxmacrodata.com/docs
- GitHub: https://github.com/fxmacrodata/fxmacrodata
- PyPI: https://pypi.org/project/fxmacrodata/
- Readthedocs: https://fxmacrodata.readthedocs.io/en/latest/
- Zenodo: https://zenodo.org/records/18280968