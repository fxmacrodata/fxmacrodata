# Use FX reference-price changes with QuantStats

This optional example uses the FXMacroData SDK to obtain a pandas price Series,
converts it to fractional changes, and passes those changes to QuantStats'
native statistics. QuantStats remains independent of the data provider.

FXMacroData also has an always-free public USD baseline: catalogue, macro
indicator history and release-calendar examples need no API key or account.
Those macro levels and schedules are not investment returns. The FX price
example below is a separate authenticated workflow. See the
[public API reference](https://fxmacrodata.com/documentation/reference?utm_source=github&utm_medium=referral&utm_campaign=quantstats&utm_content=docs)
for current access and data contracts.

## Install the example source

The example and its `FfnProvider` dependency are supplied in the SDK's
`feature/quantstats-example` source branch, stacked on `feature/ffn-provider`.
They are not features of the previously released SDK. Use Python 3.10 or newer
for QuantStats and a separate environment with the optional packages installed:

```bash
git clone --branch feature/quantstats-example https://github.com/fxmacrodata/fxmacrodata.git
cd fxmacrodata
python -m pip install . "pandas==2.3.3" "quantstats @ git+https://github.com/ranaroussi/quantstats.git@9ef4c6d0a4ffe7831f6ebba6a5824fd33a90c05a"
```

The native QuantStats APIs used here are `stats.comp` and
`stats.volatility(annualize=False, prepare_returns=False)`, checked against that
source commit. pandas and QuantStats remain optional; the SDK's mandatory
dependencies are unchanged. Calling `FfnProvider` directly does not require
installing ffn.

Configure `FXMD_API_KEY` in your environment using your normal secret manager
or shell settings, then run the example. The command has no API-key argument.

```bash
python examples/quantstats/fxmacrodata_returns.py --base eur --quote usd --start 2026-01-01 --end 2026-04-01
```

It prints the number of observed intervals, compounded reference-price change
and sample volatility per observed interval as JSON. Failure output is a fixed
message without remote error bodies or exception text. Dates use an inclusive
start and exclusive end. The provider follows validated pagination and uses
the documented FX `val` field; it adds no separate transport, credential cache
or global provider registration.

## Work with the pandas Series

```python
import os

from fxmacrodata import Client
from examples.quantstats.fxmacrodata_returns import (
    fractional_returns,
    load_fx_reference_prices,
    summarize_reference_changes,
)

prices = load_fx_reference_prices(
    "eur", "usd", start="2026-01-01", end="2026-04-01",
    client=Client(api_key=os.environ["FXMD_API_KEY"]),
)
changes = fractional_returns(prices)
summary = summarize_reference_changes(prices)
```

`fractional_returns` computes `pct_change(fill_method=None)`: a change from 100
to 110 is `0.10`, not `10`. Its first value remains undefined because there is
no previous observation. The summary discards only this first undefined value
and requires at least two observed changes. Null, nonpositive or nonfinite
price levels, invalid/duplicate/unordered dates, and nonfinite calculated
changes raise errors. No value is forward-filled, zero-filled or resampled.
The original input Series is not modified.

The summary uses native QuantStats calls that accept the supplied fractional
changes without inferring whether they are prices, including legitimate gains
greater than 100%. It does not use the report helpers' automatic preparation,
missing-value filling, annualization or benchmark downloads.

## Interpretation and capability boundary

These are changes in FX reference prices, not funded strategy returns or total
returns. They exclude carry, financing, transaction costs and leverage. The
sample volatility is the sample standard deviation (`ddof=1`) per observed
interval, not annualized volatility. The example does not infer a trading
calendar, insert absent dates or assume equal elapsed time between observations.
Choose a suitable calendar and explicit annualization model separately if your
analysis needs them.

Index dates are observation/reference labels, not publication timestamps or
proof that a value was available to a strategy on that date. This example does
not establish point-in-time eligibility or eliminate look-ahead bias. Use the
documented publication metadata and research-panel contracts for that work.

QuantStats consumes financial return Series; catalogue records, macro levels,
release events, predictions, news documents, session schedules, positioning
counts and separate seasonal analyses must not be converted into investment
returns indiscriminately. The existing
[provider capability guide](ffn_provider.md#capability-boundary) accounts for
all ten FXMacroData capability families, their SDK/direct public routes and
the limits of a single numeric Series. This example selects only FX reference
prices and adds no API operations or changes to QuantStats core.
