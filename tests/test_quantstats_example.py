"""Offline consumer tests; every price and credential fixture is synthetic."""

from __future__ import annotations

import json
import math

import pytest

pd = pytest.importorskip("pandas", reason="Optional QuantStats example needs pandas")
pytest.importorskip("quantstats", reason="Optional QuantStats example needs QuantStats")

from examples.quantstats import fxmacrodata_returns as example  # noqa: E402
from fxmacrodata import Client  # noqa: E402


def prices(values, dates=None):
    """Clearly synthetic reference prices; these are not market observations."""
    if dates is None:
        dates = pd.date_range("2026-01-01", periods=len(values))
    return pd.Series(values, index=dates, name="synthetic_fx")


def test_fractional_changes_keep_first_undefined_without_mutating_input():
    original = prices([100.0, 110.0, 99.0, 108.9])
    snapshot = original.copy(deep=True)
    actual = example.fractional_returns(original)
    assert pd.isna(actual.iloc[0])
    assert actual.iloc[1:].tolist() == pytest.approx([0.1, -0.1, 0.1])
    assert actual.index.equals(original.index)
    assert actual.name == original.name
    pd.testing.assert_series_equal(original, snapshot)


@pytest.mark.parametrize("values", [[], [1.0], [1.0, 2.0]])
def test_sample_needs_two_observed_intervals(values):
    with pytest.raises(ValueError, match="at least three"):
        example.summarize_reference_changes(prices(values))


@pytest.mark.parametrize(
    "bad",
    [None, float("nan"), pd.NA, float("inf"), -float("inf"), 0, -1, True, "1", 1j],
)
@pytest.mark.parametrize("position", [0, 1, 2])
def test_missing_and_invalid_prices_are_rejected_without_filling(bad, position):
    values = [1.0, 1.1, 1.2]
    values[position] = bad
    with pytest.raises(ValueError, match="positive finite real"):
        example.summarize_reference_changes(prices(values))


@pytest.mark.parametrize(
    "index",
    [
        ["2026-01-01", "2026-01-02", "2026-01-03"],
        pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-03"]),
        pd.to_datetime(["2026-01-02", "2026-01-01", "2026-01-03"]),
        pd.to_datetime(["2026-01-01", None, "2026-01-03"]),
        pd.date_range("2026-01-01", periods=3, tz="UTC"),
        pd.date_range("2026-01-01 12:00", periods=3),
    ],
)
def test_invalid_observation_dates_are_rejected(index):
    with pytest.raises(ValueError, match="calendar-date"):
        example.fractional_returns(prices([1.0, 1.1, 1.2], index))


def test_irregular_dates_are_retained_without_inventing_observations():
    source = prices(
        [100.0, 110.0, 99.0], pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-09"])
    )
    actual = example.fractional_returns(source)
    assert actual.index.equals(source.index)
    assert len(actual) == 3


def test_native_quantstats_consumes_explicit_fractional_returns():
    summary = example.summarize_reference_changes(prices([100.0, 110.0, 99.0, 108.9]))
    assert summary == pytest.approx(
        {
            "observed_intervals": 3,
            "compounded_reference_change": 0.089,
            "sample_volatility_per_observed_interval": math.sqrt(0.04 / 3),
        }
    )


def test_native_quantstats_does_not_reinterpret_gains_over_one_hundred_percent():
    summary = example.summarize_reference_changes(prices([1.0, 3.0, 12.0]))
    assert summary["compounded_reference_change"] == pytest.approx(11.0)
    assert summary["sample_volatility_per_observed_interval"] == pytest.approx(
        math.sqrt(0.5)
    )


def test_native_quantstats_accepts_gains_of_exactly_one_hundred_percent():
    summary = example.summarize_reference_changes(prices([1.0, 2.0, 4.0]))
    assert summary["compounded_reference_change"] == 3.0
    assert summary["sample_volatility_per_observed_interval"] == 0.0


def test_constant_reference_prices_have_zero_change_and_sample_volatility():
    summary = example.summarize_reference_changes(prices([1.0, 1.0, 1.0]))
    assert summary["compounded_reference_change"] == 0.0
    assert summary["sample_volatility_per_observed_interval"] == 0.0


def test_overflowing_fractional_change_is_rejected():
    with pytest.raises(ValueError, match="changes must be finite"):
        example.fractional_returns(prices([1e-300, 1e300, 1e300]))


def test_finite_prices_with_overflowing_native_summary_are_rejected():
    with pytest.raises(ValueError, match="statistics must be finite"):
        example.summarize_reference_changes(prices([1e-300, 1.0, 1e300]))


@pytest.mark.parametrize("function", ["comp", "volatility"])
def test_nonfinite_native_statistics_are_rejected(monkeypatch, function):
    monkeypatch.setattr(
        example.qs.stats, function, lambda *args, **kwargs: float("inf")
    )
    with pytest.raises(ValueError, match="statistics must be finite"):
        example.summarize_reference_changes(prices([1.0, 1.1, 1.2]))


def test_summary_uses_no_inference_or_annualization(monkeypatch):
    calls = []

    def comp(returns):
        calls.append(("comp", returns.copy(), {}))
        return 0.089

    def volatility(returns, **options):
        calls.append(("volatility", returns.copy(), options))
        return 0.1

    monkeypatch.setattr(example.qs.stats, "comp", comp)
    monkeypatch.setattr(example.qs.stats, "volatility", volatility)
    example.summarize_reference_changes(prices([100.0, 110.0, 99.0, 108.9]))
    assert [call[0] for call in calls] == ["comp", "volatility"]
    for _, returns, _ in calls:
        assert returns.tolist() == pytest.approx([0.1, -0.1, 0.1])
        assert returns.notna().all()
    assert calls[1][2] == {"annualize": False, "prepare_returns": False}


def response_page(rows, *, offset=0, total=None, next_offset=None):
    return {
        "data": rows,
        "dataset_version": "synthetic-v1",
        "pagination": {
            "offset": offset,
            "returned_count": len(rows),
            "total_count": len(rows) if total is None else total,
            "has_more": next_offset is not None,
            "next_offset": next_offset,
        },
    }


def transport(monkeypatch, pages):
    pages = iter(pages)
    calls = []

    class Response:
        status_code = 200
        headers = {}

        def json(self):
            return next(pages)

    def get(url, **options):
        calls.append((url, options))
        return Response()

    monkeypatch.setattr("fxmacrodata.client.requests.get", get)
    return calls


def test_existing_provider_fetches_all_pages_and_applies_exclusive_end(monkeypatch):
    first = [
        {"date": "2026-01-01", "val": 100.0},
        {"date": "2026-01-02", "val": 110.0},
    ]
    last = [
        {"date": "2026-01-03", "val": 99.0},
        {"date": "2026-01-04", "val": 108.9},
    ]
    calls = transport(
        monkeypatch,
        [
            response_page(first, total=4, next_offset=2),
            response_page(last, offset=2, total=4),
        ],
    )
    fixture_key = "synthetic-test-value"
    actual = example.load_fx_reference_prices(
        "eur",
        "usd",
        start="2026-01-01",
        end="2026-01-04",
        client=Client(api_key=fixture_key),
    )
    assert actual.tolist() == [100.0, 110.0, 99.0]
    assert len(calls) == 2
    assert [call[1]["params"]["offset"] for call in calls] == [0, 2]
    assert calls[1][1]["params"]["dataset_version"] == "synthetic-v1"
    for url, options in calls:
        assert url == "https://api.fxmacrodata.com/v1/forex/eur/usd"
        assert options["headers"] == {"X-API-Key": fixture_key}
        assert fixture_key not in url
        assert options["allow_redirects"] is False


@pytest.mark.parametrize(
    "base,quote", [("EUR", "usd"), ("eur/gbp", "usd"), ("eur", "us")]
)
def test_loader_restricts_currency_identifiers(base, quote):
    with pytest.raises(ValueError, match="currency codes"):
        example.load_fx_reference_prices(
            base, quote, start="2026-01-01", end="2026-01-04"
        )


def test_cli_uses_environment_header_and_prints_only_summary(monkeypatch, capsys):
    fixture_key = "synthetic-test-value"
    monkeypatch.setenv("FXMD_API_KEY", fixture_key)
    calls = transport(
        monkeypatch,
        [
            response_page(
                [
                    {"date": "2026-01-01", "val": 100.0},
                    {"date": "2026-01-02", "val": 110.0},
                    {"date": "2026-01-03", "val": 99.0},
                ]
            )
        ],
    )
    assert example.main(["--start", "2026-01-01", "--end", "2026-01-04"]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["observed_intervals"] == 2
    assert output["compounded_reference_change"] == pytest.approx(-0.01)
    assert captured.err == ""
    assert fixture_key not in captured.out
    assert calls[0][1]["headers"] == {"X-API-Key": fixture_key}


def test_cli_does_not_expose_error_bodies_or_credentials(monkeypatch, capsys):
    fixture_key = "synthetic-test-value"
    monkeypatch.setenv("FXMD_API_KEY", fixture_key)

    def fail(*args, **kwargs):
        raise RuntimeError(f"synthetic remote error body {fixture_key}")

    monkeypatch.setattr(example, "load_fx_reference_prices", fail)
    assert example.main(["--start", "2026-01-01", "--end", "2026-01-04"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Unable to summarize FX reference prices.\n"
    assert fixture_key not in captured.err


def test_cli_does_not_echo_unrecognized_secret_arguments(capsys):
    with pytest.raises(SystemExit) as error:
        example.main(
            [
                "--start",
                "2026-01-01",
                "--end",
                "2026-01-04",
                "--api-key",
                "synthetic-test-value",
            ]
        )
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert "synthetic-test-value" not in captured.err
    assert "Invalid arguments" in captured.err


def test_cli_without_optional_fx_credential_fails_before_transport(monkeypatch, capsys):
    monkeypatch.delenv("FXMD_API_KEY", raising=False)

    def unexpected_request(*args, **kwargs):
        pytest.fail("No transport call should occur without the required FX credential")

    monkeypatch.setattr("fxmacrodata.client.requests.get", unexpected_request)
    assert example.main(["--start", "2026-01-01", "--end", "2026-01-04"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Unable to summarize FX reference prices.\n"
