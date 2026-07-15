"""Regression tests for the TensorTrade point-in-time example."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


EXAMPLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "tensortrade"
    / "fxmacrodata_macro_features.py"
)
SPEC = importlib.util.spec_from_file_location("tensortrade_macro_features", EXAMPLE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_features_only_appear_after_the_publication_timestamp() -> None:
    announcements = {
        "data": [
            {"val": 3.0, "announcement_datetime": 1704240000},  # 2024-01-03 UTC
            {"val": 3.2, "announcement_datetime": 1704326400},  # 2024-01-04 UTC
        ]
    }
    index = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")

    features = MODULE.point_in_time_features(index, announcements)

    assert features.loc["2024-01-01", "usd_inflation"] != features.loc[
        "2024-01-01", "usd_inflation"
    ]
    assert features.loc["2024-01-02", "usd_inflation"] != features.loc[
        "2024-01-02", "usd_inflation"
    ]
    assert features.loc["2024-01-03", "usd_inflation"] == 3.0
    assert features.loc["2024-01-04", "usd_inflation"] == 3.2
    assert features.loc["2024-01-04", "usd_inflation_release_change"] == pytest.approx(0.2)
    assert features.loc["2024-01-04", "usd_inflation_release_age_days"] == 0.0
