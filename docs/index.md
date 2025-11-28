# FXMacroData SDK Documentation

Welcome to the **FXMacroData SDK** documentation. This SDK allows you to fetch real-time macroeconomic and FX data from [FXMacroData](https://fxmacrodata.com/?utm_source=readthedocs&utm_medium=docs&utm_campaign=sdk_docs).

## Installation

```bash
pip install fxmacrodata
```

## Getting Started

The SDK provides two main functions:

### 1. `get_indicator()`

Fetch macroeconomic indicators like interest rates, inflation, or employment data.

```python
from fxmacrodata import get_indicator

# Example: Fetch the latest US CPI
cpi = get_indicator("US", "CPI")
print(cpi)
```

### 2. `get_fx_price()`

Fetch FX prices for any major currency pair in real time.

```python
from fxmacrodata import get_fx_price

# Example: Get USD/EUR price
price = get_fx_price("USD", "EUR")
print(price)
```

## More Information

For full documentation, tutorials, and examples, visit [FXMacroData](https://fxmacrodata.com/?utm_source=readthedocs&utm_medium=docs&utm_campaign=sdk_docs).