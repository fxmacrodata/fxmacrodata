# FXMacroData Python SDK 🐍📊

![PyPI Version](https://img.shields.io/pypi/v/fxmacrodata?color=blue&logo=python&style=flat-square)
![Python Versions](https://img.shields.io/pypi/pyversions/fxmacrodata?style=flat-square)
![License](https://img.shields.io/github/license/fxmacrodata/fxmacrodata?style=flat-square)
![Build](https://img.shields.io/github/actions/workflow/status/fxmacrodata/fxmacrodata/ci-cd.yml?style=flat-square&logo=github)

The **FXMacroData Python SDK** provides a simple and efficient interface for fetching **macroeconomic indicators** and **forex price history** from  
[FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=readme&utm_campaign=python_sdk).  

It includes both synchronous and asynchronous clients, supports free USD endpoints, and offers a free Forex Price API for exchange rate data.

---

## 🌟 Features

- Fetch:
  - **Policy Rates**
  - **Inflation & CPI**
  - **GDP**
  - **Unemployment**
  - **Balance of Trade**
  - **Government Bond Yields**
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
```

---

### Asynchronous

```python
import asyncio
from fxmacrodata import AsyncClient

async def main():
    async with AsyncClient(api_key="YOUR_API_KEY") as client:
        # Fetch macroeconomic indicators
        data = await client.get_indicator("eur", "cpi")
        print(data)

        # Free Forex Price Endpoint
        fx = await client.get_fx_price("usd", "jpy")
        print(fx)

asyncio.run(main())
```

---

## 📘 API Overview

### `get_indicator(currency, indicator, start_date=None, end_date=None)`
Fetches macroeconomic indicator time series data.

- `currency`: `"usd"`, `"aud"`, `"eur"`, `"gbp"`, `"cad"`, `"nok"`, `"nzd"`, `"jpy"`, etc.
- `indicator`: `"policy_rate"`, `"cpi"`, `"inflation"`, `"gdp"`, `"unemployment"`, `"trade_balance"`, `"current_account"`, etc.
- **API key required for non-USD.**

### `get_fx_price(base, quote, start_date=None, end_date=None)`
Fetches historical FX prices between two currencies. **No API key needed for USD-based queries.**

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
