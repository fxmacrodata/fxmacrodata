"""Summarize FX reference-price changes with the optional QuantStats package."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections.abc import Sequence
from numbers import Real
from typing import NoReturn

import pandas as pd  # type: ignore[import-untyped, import-not-found]
import quantstats as qs  # type: ignore[import-untyped, import-not-found]

from fxmacrodata import Client
from fxmacrodata.ffn import FfnProvider


def fractional_returns(prices: pd.Series) -> pd.Series:
    """Return fractional changes, retaining the first undefined observation.

    At least three positive, finite reference prices are required, giving two
    observed intervals for sample volatility. Dates must be unique, increasing,
    timezone-naive calendar labels. No observations are filled or resampled.
    """
    if not isinstance(prices, pd.Series) or len(prices) < 3:
        raise ValueError("Provide at least three reference-price observations")
    index = prices.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.hasnans
        or index.tz is not None
        or not index.is_unique
        or not index.is_monotonic_increasing
        or not index.equals(index.normalize())
    ):
        raise ValueError("Prices require ordered unique calendar-date labels")
    values = []
    for value in prices:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Prices must be positive finite real numbers")
        try:
            number = float(value)
        except (OverflowError, ValueError, TypeError):
            raise ValueError("Prices must be positive finite real numbers") from None
        if not math.isfinite(number) or number <= 0:
            raise ValueError("Prices must be positive finite real numbers")
        values.append(number)
    numeric = pd.Series(values, index=index.copy(), name=prices.name, dtype=float)
    returns = numeric.pct_change(fill_method=None)
    if not all(math.isfinite(float(value)) for value in returns.iloc[1:]):
        raise ValueError("Reference-price changes must be finite")
    return returns


def summarize_reference_changes(prices: pd.Series) -> dict[str, float | int]:
    """Use native QuantStats statistics without price inference or annualization."""
    observed = fractional_returns(prices).iloc[1:]
    compounded = float(qs.stats.comp(observed))
    volatility = float(
        qs.stats.volatility(observed, annualize=False, prepare_returns=False)
    )
    if not math.isfinite(compounded) or not math.isfinite(volatility):
        raise ValueError("Reference-price sample statistics must be finite")
    return {
        "observed_intervals": len(observed),
        "compounded_reference_change": compounded,
        "sample_volatility_per_observed_interval": volatility,
    }


def load_fx_reference_prices(
    base: str,
    quote: str,
    *,
    start: str,
    end: str,
    client: Client | None = None,
) -> pd.Series:
    """Load the public SDK's FX ``val`` view, inclusive start/exclusive end."""
    if any(
        not isinstance(currency, str) or re.fullmatch(r"[a-z]{3}", currency) is None
        for currency in (base, quote)
    ):
        raise ValueError("Use lowercase three-letter currency codes")
    provider = FfnProvider(client)
    return provider(ticker=f"fx/{base}/{quote}", field="val", start=start, end=end)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # Do not echo unrecognized arguments, which may contain a pasted key.
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid arguments; use --help for accepted options.\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--base", default="eur", help="Lowercase base currency")
    parser.add_argument("--quote", default="usd", help="Lowercase quote currency")
    parser.add_argument("--start", required=True, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Exclusive YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        client = Client(api_key=os.environ.get("FXMD_API_KEY"))
        prices = load_fx_reference_prices(
            args.base, args.quote, start=args.start, end=args.end, client=client
        )
        result = summarize_reference_changes(prices)
        output = json.dumps(result, allow_nan=False)
    except Exception:
        # Remote error bodies and exception text must not reach terminal output.
        print("Unable to summarize FX reference prices.", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
