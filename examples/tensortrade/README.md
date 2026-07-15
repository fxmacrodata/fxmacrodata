# TensorTrade macro-feature example

This example turns FXMacroData's realised USD inflation announcements into
point-in-time features for a TensorTrade `DataFeed`.

It deliberately uses the historical `announcements` endpoint, not the
forward-looking release calendar.  Each value becomes usable only at
`announcement_datetime`, so a training observation never receives a release
before it was published.

## Install

```bash
pip install fxmacrodata pandas tensortrade
```

USD inflation is public and needs no API key.

## Export features for price data

Provide a CSV with a `timestamp` column:

```bash
python examples/tensortrade/fxmacrodata_macro_features.py prices.csv \
  --output macro_features.csv
```

The output contains:

- `usd_inflation`: latest published inflation value.
- `usd_inflation_release_change`: change from the preceding published value.
- `usd_inflation_release_age_days`: time since that release.

Rows before the first published release remain null.  Drop or otherwise handle
them before training rather than backfilling from the future.

## Use with TensorTrade

```python
import pandas as pd

from examples.tensortrade.fxmacrodata_macro_features import (
    load_usd_inflation_features,
    tensortrade_feed,
)

prices = pd.read_csv("prices.csv", parse_dates=["timestamp"])
features = load_usd_inflation_features(pd.DatetimeIndex(prices["timestamp"]))
feed = tensortrade_feed(features.dropna())
```

Tests must use static announcement fixtures rather than making live API calls.
