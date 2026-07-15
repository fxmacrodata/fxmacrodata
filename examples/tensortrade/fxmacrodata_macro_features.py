"""Build point-in-time FXMacroData macro features for a TensorTrade DataFeed.

This example uses the always-free USD inflation announcements endpoint.  It
intentionally uses realised announcements rather than the forward-looking
release calendar: a feature becomes available only at its publication time.

Install the optional example dependencies with:

    pip install fxmacrodata pandas tensortrade
"""

from __future__ import annotations

import argparse
from typing import Any, Mapping, Sequence

import pandas as pd

from fxmacrodata import Client


def announcement_frame(payload: Mapping[str, Any]) -> pd.DataFrame:
    """Return realised observations indexed by their UTC publication time.

    Rows without both a numeric value and ``announcement_datetime`` are
    excluded: assigning them to the observation date could introduce
    look-ahead bias.
    """

    rows: list[dict[str, float | pd.Timestamp]] = []
    for row in payload.get("data", []):
        value = row.get("val")
        published_at = row.get("announcement_datetime")
        if value is None or published_at is None:
            continue
        rows.append(
            {
                "published_at": pd.to_datetime(published_at, unit="s", utc=True),
                "value": float(value),
            }
        )

    if not rows:
        return pd.DataFrame(
            {
                "value": pd.Series(dtype="float64"),
                "release_change": pd.Series(dtype="float64"),
            },
            index=pd.DatetimeIndex([], tz="UTC", name="published_at"),
        )

    frame = (
        pd.DataFrame(rows)
        .drop_duplicates(subset="published_at", keep="last")
        .sort_values("published_at")
        .set_index("published_at")
    )
    frame["release_change"] = frame["value"].diff()
    return frame


def point_in_time_features(
    price_index: pd.DatetimeIndex,
    announcements: Mapping[str, Any],
    *,
    prefix: str = "usd_inflation",
) -> pd.DataFrame:
    """Align realised announcement values to a price index without look-ahead.

    ``price_index`` is converted to UTC.  Values are forward-filled only from
    a release timestamp to later observations; dates before the first release
    remain missing and should be removed during model preparation.
    """

    if not isinstance(price_index, pd.DatetimeIndex):
        raise TypeError("price_index must be a pandas DatetimeIndex")
    if price_index.tz is None:
        price_index = price_index.tz_localize("UTC")
    else:
        price_index = price_index.tz_convert("UTC")
    if not price_index.is_monotonic_increasing:
        price_index = price_index.sort_values()

    releases = announcement_frame(announcements)
    feature_index = pd.DatetimeIndex(price_index, name="timestamp")
    values = releases["value"].reindex(feature_index, method="ffill")
    changes = releases["release_change"].reindex(feature_index, method="ffill")
    release_times = pd.Series(releases.index, index=releases.index).reindex(
        feature_index, method="ffill"
    )
    age_days = (pd.Series(feature_index, index=feature_index) - release_times).dt.total_seconds() / 86400

    return pd.DataFrame(
        {
            prefix: values,
            f"{prefix}_release_change": changes,
            f"{prefix}_release_age_days": age_days,
        },
        index=feature_index,
    )


def tensortrade_feed(features: pd.DataFrame) -> Any:
    """Create a TensorTrade ``DataFeed`` from numeric feature columns.

    TensorTrade is intentionally imported here, so feature construction can be
    tested or exported to CSV without installing the optional framework.
    """

    from tensortrade.feed.core import DataFeed, Stream

    streams = [
        Stream.source(features[column].astype(float).tolist(), dtype="float").rename(column)
        for column in features.columns
    ]
    return DataFeed(streams)


def load_usd_inflation_features(price_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Fetch the public USD inflation history and create point-in-time features."""

    payload = Client().get_indicator("usd", "inflation")
    return point_in_time_features(price_index, payload)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prices_csv", help="CSV containing a timestamp column")
    parser.add_argument("--timestamp-column", default="timestamp")
    parser.add_argument("--output", default="fxmacrodata_tensortrade_features.csv")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    prices = pd.read_csv(args.prices_csv, parse_dates=[args.timestamp_column])
    index = pd.DatetimeIndex(prices[args.timestamp_column])
    features = load_usd_inflation_features(index)
    features.to_csv(args.output, index_label=args.timestamp_column)
    print(f"Wrote {len(features)} point-in-time feature rows to {args.output}")


if __name__ == "__main__":
    main()
