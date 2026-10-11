"""Offline contract and native ffn dispatch tests for the optional provider."""

from __future__ import annotations

import copy
import pickle
from datetime import date
from urllib.parse import quote, quote_plus

import pytest
import requests

pd = pytest.importorskip("pandas", reason="Optional ffn provider requires pandas")

from fxmacrodata import Client, FXMacroDataError  # noqa: E402
from fxmacrodata.ffn import FfnProvider  # noqa: E402


def page(rows, *, offset=0, total=None, next_offset=None, version=None):
    result = {
        "data": rows,
        "pagination": {
            "offset": offset,
            "returned_count": len(rows),
            "total_count": len(rows) if total is None else total,
            "has_more": next_offset is not None,
            "next_offset": next_offset,
        },
    }
    if version is not None:
        result["dataset_version"] = version
    return result


def transport(monkeypatch, responses):
    responses = iter(copy.deepcopy(responses))
    calls = []

    class Response:
        status_code = 200
        headers = {}

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return Response(next(responses))

    monkeypatch.setattr("fxmacrodata.client.requests.get", get)
    return calls


@pytest.mark.parametrize(
    ("ticker", "field", "row", "path", "key"),
    [
        (
            "macro/usd/policy_rate",
            None,
            {"val": 4.25},
            "announcements/usd/policy_rate",
            None,
        ),
        ("fx/eur/usd", "close", {"close": 1.12}, "forex/eur/usd", "inert-provider-key"),
        (
            "cot/eur",
            "noncommercial_net",
            {"noncommercial_net": -12},
            "cot/eur",
            "inert-provider-key",
        ),
        (
            "commodity/gold",
            None,
            {"val": 2000.0},
            "commodities/gold",
            "inert-provider-key",
        ),
    ],
)
def test_four_native_history_families(monkeypatch, ticker, field, row, path, key):
    calls = transport(monkeypatch, [page([{"date": "2026-01-02", **row}])])
    result = FfnProvider(Client(api_key=key))(ticker=ticker, field=field)
    assert isinstance(result, pd.Series)
    assert result.dtype == "float64"
    assert result.index.equals(pd.DatetimeIndex(["2026-01-02"]))
    assert result.iloc[0] == next(iter(row.values()))
    assert calls[0]["url"] == f"https://api.fxmacrodata.com/v1/{path}"
    assert calls[0]["headers"] == ({"X-API-Key": key} if key else {})
    assert calls[0]["params"] == {"limit": 100, "offset": 0}
    assert calls[0]["allow_redirects"] is False
    assert calls[0]["timeout"] == 30.0


def test_exhausts_pages_pins_version_and_applies_ffn_window(monkeypatch):
    calls = transport(
        monkeypatch,
        [
            page(
                [{"date": "2026-01-03", "val": 3}],
                total=3,
                next_offset=1,
                version="version-a",
            ),
            page(
                [{"date": "2026-01-01", "val": 1}, {"date": "2026-01-02", "val": 2}],
                offset=1,
                total=3,
                version="version-a",
            ),
        ],
    )
    result = FfnProvider(page_size=1)(
        ticker="macro/usd/policy_rate", start="2026-01-01", end=date(2026, 1, 3)
    )
    assert result.tolist() == [1.0, 2.0]
    assert result.index.is_unique and result.index.is_monotonic_increasing
    assert calls[1]["params"]["offset"] == 1
    assert calls[1]["params"]["dataset_version"] == "version-a"
    assert calls[0]["params"]["start_date"] == "2026-01-01"
    assert calls[0]["params"]["end_date"] == "2026-01-03"


@pytest.mark.parametrize(
    "ticker,field", [("cot/eur", "open_interest"), ("commodity/gold", "val")]
)
def test_unversioned_families_do_not_invent_version_parameters(
    monkeypatch, ticker, field
):
    calls = transport(
        monkeypatch,
        [
            page([{"date": "2026-01-02", field: 2}], total=2, next_offset=1),
            page([{"date": "2026-01-01", field: 1}], offset=1, total=2),
        ],
    )
    result = FfnProvider(Client(api_key="inert-provider-key"))(
        ticker=ticker, field=field
    )
    assert result.tolist() == [1.0, 2.0]
    assert all("dataset_version" not in call["params"] for call in calls)


@pytest.mark.parametrize("replacement", ["version-b", None, 12, ""])
def test_version_drift_or_malformed_version_fails(monkeypatch, replacement):
    transport(
        monkeypatch,
        [
            page(
                [{"date": "2026-01-02", "val": 2}],
                total=2,
                next_offset=1,
                version="version-a",
            ),
            page(
                [{"date": "2026-01-01", "val": 1}],
                offset=1,
                total=2,
                version=replacement,
            ),
        ],
    )
    with pytest.raises(FXMacroDataError, match="dataset_version"):
        FfnProvider()(ticker="macro/usd/gdp")


@pytest.mark.parametrize("first_total,second_total", [(3, 2), (2, 3)])
def test_total_count_drift_never_returns_partial_unversioned_history(
    monkeypatch, first_total, second_total
):
    calls = transport(
        monkeypatch,
        [
            page(
                [{"date": "2026-01-02", "val": 2}],
                total=first_total,
                next_offset=1,
            ),
            page(
                [{"date": "2026-01-01", "val": 1}],
                offset=1,
                total=second_total,
                next_offset=2 if second_total == 3 else None,
            ),
        ],
    )
    with pytest.raises(FXMacroDataError, match="total_count changed"):
        FfnProvider()(ticker="macro/usd/gdp")
    assert len(calls) == 2


@pytest.mark.parametrize("ticker", ["macro/usd/gdp", "fx/eur/usd"])
@pytest.mark.parametrize(
    "encoding",
    [lambda value: value, quote, quote_plus, lambda value: quote(value).lower()],
)
def test_dataset_version_cannot_move_credentials_into_query(
    monkeypatch, ticker, encoding
):
    key = "inert/provider+key?=one"
    echoed = encoding(key)
    calls = transport(
        monkeypatch,
        [
            page(
                [{"date": "2026-01-02", "val": 2}],
                total=2,
                next_offset=1,
                version="version-" + echoed,
            )
        ],
    )
    with pytest.raises(FXMacroDataError) as captured:
        FfnProvider(Client(api_key=key))(ticker=ticker)
    assert len(calls) == 1
    assert "dataset_version" not in calls[0]["params"]
    assert key not in calls[0]["url"] and echoed not in repr(calls[0]["params"])
    assert str(captured.value) == "History dataset_version contains credential data"
    assert key not in str(captured.value) and echoed not in str(captured.value)


@pytest.mark.parametrize(
    "change",
    [
        {"next_offset": 0},
        {"next_offset": True},
        {"next_offset": -1},
        {"next_offset": "1"},
        {"next_offset": None},
        {"next_offset": 2},
        {"offset": 1},
        {"returned_count": 0},
        {"returned_count": True},
        {"has_more": "true"},
        {"total_count": None},
        {"total_count": 0},
    ],
)
def test_bad_continuation_never_returns_partial_history(monkeypatch, change):
    payload = page([{"date": "2026-01-02", "val": 2}], total=2, next_offset=1)
    payload["pagination"].update(change)
    transport(monkeypatch, [payload])
    with pytest.raises(FXMacroDataError, match="pagination"):
        FfnProvider()(ticker="macro/usd/gdp")


@pytest.mark.parametrize(
    "payload",
    [
        page([], total=1, next_offset=1),
        page([{"date": "2026-01-01", "val": 1}], total=2),
    ],
)
def test_empty_continuation_or_early_stop_fails(monkeypatch, payload):
    transport(monkeypatch, [payload])
    with pytest.raises(FXMacroDataError, match="pagination"):
        FfnProvider()(ticker="macro/usd/gdp")


def test_skipped_offset_cannot_lose_a_row(monkeypatch):
    transport(
        monkeypatch, [page([{"date": "2026-01-03", "val": 3}], total=3, next_offset=2)]
    )
    with pytest.raises(FXMacroDataError, match="pagination"):
        FfnProvider()(ticker="macro/usd/gdp")


def test_page_bound_fails_instead_of_truncating(monkeypatch):
    transport(
        monkeypatch, [page([{"date": "2026-01-02", "val": 2}], total=2, next_offset=1)]
    )
    with pytest.raises(FXMacroDataError, match="max_pages"):
        FfnProvider(max_pages=1)(ticker="macro/usd/gdp")


def test_empty_series_has_native_numeric_shape(monkeypatch):
    transport(monkeypatch, [page([])])
    result = FfnProvider()(ticker="macro/usd/gdp")
    assert result.empty and result.dtype == "float64"
    assert isinstance(result.index, pd.DatetimeIndex) and not result.index.hasnans


def test_null_values_stay_missing_without_fill(monkeypatch):
    transport(
        monkeypatch,
        [
            page(
                [
                    {"date": "2026-01-01", "val": None},
                    {"date": "2026-01-02"},
                    {"date": "2026-01-03", "val": 3},
                ]
            )
        ],
    )
    result = FfnProvider()(ticker="macro/usd/gdp")
    assert result.isna().tolist() == [True, True, False]


@pytest.mark.parametrize(
    "value", [True, "12.3", float("inf"), float("nan"), {"value": 2}, [2], 2 + 1j]
)
def test_non_real_or_nonfinite_data_fails(monkeypatch, value):
    transport(monkeypatch, [page([{"date": "2026-01-01", "val": value}])])
    with pytest.raises(FXMacroDataError, match="finite real"):
        FfnProvider()(ticker="macro/usd/gdp")


@pytest.mark.parametrize(
    "label", [None, "2026-02-30", "not-a-date", "20260101", "2026-01-01T12:00:00Z", 123]
)
def test_missing_or_invalid_date_never_uses_other_timestamp(monkeypatch, label):
    transport(
        monkeypatch,
        [
            page(
                [
                    {
                        "date": label,
                        "val": 2,
                        "announcement_datetime": 1767225600,
                        "collected_at_ns": 1767225600000000000,
                    }
                ]
            )
        ],
    )
    with pytest.raises(FXMacroDataError, match="date label"):
        FfnProvider()(ticker="macro/usd/gdp")


def test_duplicate_identical_rows_deduplicate_but_conflicts_fail(monkeypatch):
    transport(
        monkeypatch,
        [page([{"date": "2026-01-01", "val": 2}, {"date": "2026-01-01", "val": 2}])],
    )
    assert FfnProvider()(ticker="macro/usd/gdp").tolist() == [2.0]
    transport(
        monkeypatch,
        [page([{"date": "2026-01-01", "val": 2}, {"date": "2026-01-01", "val": 3}])],
    )
    with pytest.raises(FXMacroDataError, match="Conflicting"):
        FfnProvider()(ticker="macro/usd/gdp")


@pytest.mark.parametrize(
    "ticker",
    [
        "https://example.invalid",
        "macro/usd/../../private",
        "macro/USD/gdp",
        "macro/usd/gdp?api_key=x",
        "macro/usd/latest",
        "commodity/latest",
        "calendar/usd",
        "fx/eur/usd/extra",
        None,
    ],
)
def test_fixed_routes_reject_untrusted_paths_before_http(monkeypatch, ticker):
    calls = transport(monkeypatch, [])
    with pytest.raises(ValueError):
        FfnProvider()(ticker=ticker)
    assert not calls


@pytest.mark.parametrize(
    "ticker,field",
    [
        ("macro/usd/gdp", "collected_at_ns"),
        ("fx/eur/usd", "unexpected"),
        ("cot/eur", None),
        ("cot/eur", "producer_merchant_spread"),
        ("commodity/gold", "publication_time_status"),
    ],
)
def test_only_documented_numeric_fields(monkeypatch, ticker, field):
    calls = transport(monkeypatch, [])
    with pytest.raises(ValueError, match="numeric field"):
        FfnProvider(Client(api_key="inert-provider-key"))(ticker=ticker, field=field)
    assert not calls


@pytest.mark.parametrize(
    "options",
    [
        {"api_key": "inert-provider-key"},
        {"offset": 20},
        {"revisions": "all"},
        {"frequency": "invented"},
        {"official_only": "true"},
        {"mrefresh": True},
    ],
)
def test_unsupported_options_fail_before_http(monkeypatch, options):
    calls = transport(monkeypatch, [])
    with pytest.raises(ValueError):
        FfnProvider()(ticker="macro/usd/gdp", **options)
    assert not calls


def test_public_options_and_computed_fx_fields(monkeypatch):
    calls = transport(monkeypatch, [page([]), page([]), page([])])
    provider = FfnProvider(Client(api_key="inert-provider-key"))
    provider(
        ticker="macro/usd/gdp",
        series_mode="raw",
        seasonality="sa",
        frequency="qoq",
        revisions="first",
        official_only=True,
    )
    provider(ticker="fx/eur/usd", field="rsi_14")
    provider(ticker="cot/eur", field="dealer_net", report="tff_futures")
    assert calls[0]["params"]["revisions"] == "first"
    assert calls[0]["params"]["official_only"] == "true"
    assert calls[1]["params"]["indicators"] == "all"
    assert calls[2]["params"]["report"] == "tff_futures"


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-02-30", None),
        ("20260101", None),
        (None, "2026-01-01T12:00:00Z"),
        ("2026-01-02", "2026-01-02"),
        ("2026-01-03", "2026-01-02"),
    ],
)
def test_date_window_validation_precedes_http(monkeypatch, start, end):
    calls = transport(monkeypatch, [])
    with pytest.raises(ValueError):
        FfnProvider()(ticker="macro/usd/gdp", start=start, end=end)
    assert not calls


@pytest.mark.parametrize(
    "kwargs",
    [
        {"page_size": True},
        {"page_size": 0},
        {"page_size": 101},
        {"max_pages": 0},
        {"max_pages": 1.5},
    ],
)
def test_bounds_are_finite_positive_integers(kwargs):
    with pytest.raises(ValueError):
        FfnProvider(**kwargs)


@pytest.mark.parametrize(
    "ticker,field",
    [
        ("macro/eur/gdp", None),
        ("fx/eur/usd", None),
        ("cot/eur", "open_interest"),
        ("commodity/gold", None),
    ],
)
def test_protected_routes_require_key_without_network(monkeypatch, ticker, field):
    calls = transport(monkeypatch, [])
    with pytest.raises(FXMacroDataError, match="API key required"):
        FfnProvider()(ticker=ticker, field=field)
    assert not calls


def test_configured_usd_key_is_header_only_and_never_serialized(monkeypatch):
    calls = transport(monkeypatch, [page([]), page([])])
    serialized = []

    def reject_pickle(*args, **kwargs):
        serialized.append(args)
        raise AssertionError("Provider should not serialize credentials")

    monkeypatch.setattr(pickle, "dumps", reject_pickle)
    for key in ("inert-provider-key-one", "inert-provider-key-two"):
        provider = FfnProvider(Client(api_key=key))
        provider(ticker="macro/usd/gdp")
        assert key not in repr(provider)
        assert calls[-1]["headers"] == {"X-API-Key": key}
        assert key not in calls[-1]["url"] and key not in repr(calls[-1]["params"])
    assert not serialized


def test_provider_rejects_serialization_before_client_credentials(monkeypatch):
    key = "inert-provider-key-one"
    provider = FfnProvider(Client(api_key=key))
    with pytest.raises(TypeError, match="uncached provider interface") as captured:
        pickle.dumps(provider)
    assert key not in str(captured.value)


def test_usd_cot_public_baseline_does_not_require_key(monkeypatch):
    calls = transport(
        monkeypatch, [page([{"date": "2026-01-01", "open_interest": 12}])]
    )
    assert FfnProvider()(ticker="cot/usd", field="open_interest").tolist() == [12.0]
    assert calls[0]["headers"] == {}


def test_error_redaction_and_response_preview_use_existing_transport(monkeypatch):
    key = "inert-provider-key-one"

    class Response:
        status_code = 409
        headers = {}
        text = "version conflict " + key + "x" * 3000

    monkeypatch.setattr(
        "fxmacrodata.client.requests.get", lambda *args, **kwargs: Response()
    )
    with pytest.raises(FXMacroDataError) as captured:
        FfnProvider(Client(api_key=key))(ticker="fx/eur/usd")
    assert key not in str(captured.value)
    assert "409" in str(captured.value) and len(str(captured.value)) < 1100
    assert captured.value.__suppress_context__ or captured.value.__cause__ is None


def test_transport_exception_cannot_echo_header(monkeypatch):
    key = "inert-provider-key-one"

    def fail(*args, **kwargs):
        raise requests.ConnectionError("cannot send " + key)

    monkeypatch.setattr("fxmacrodata.client.requests.get", fail)
    with pytest.raises(FXMacroDataError) as captured:
        FfnProvider(Client(api_key=key))(ticker="fx/eur/usd")
    assert key not in str(captured.value)
    assert captured.value.__suppress_context__


@pytest.mark.parametrize("encoding", [lambda value: value, quote, quote_plus])
def test_encoded_remote_error_is_not_propagated(monkeypatch, encoding):
    key = "inert/provider+key-one"
    echoed = encoding(key)

    def fail(*args, **kwargs):
        raise FXMacroDataError("remote echoed credential " + echoed)

    monkeypatch.setattr(Client, "_request", fail)
    with pytest.raises(FXMacroDataError) as captured:
        FfnProvider(Client(api_key=key))(ticker="fx/eur/usd")
    assert str(captured.value) == "History request failed"
    assert key not in str(captured.value) and echoed not in str(captured.value)
    assert captured.value.__suppress_context__


def test_authenticated_cross_origin_redirect_is_not_followed(monkeypatch):
    calls = []

    class Response:
        status_code = 302
        headers = {"Location": "https://example.invalid/steal"}

    def get(url, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr("fxmacrodata.client.requests.get", get)
    with pytest.raises(FXMacroDataError, match="History request failed"):
        FfnProvider(Client(api_key="inert-provider-key"))(ticker="fx/eur/usd")
    assert calls == ["https://api.fxmacrodata.com/v1/forex/eur/usd"]


@pytest.mark.parametrize(
    "payload",
    [
        {"error": "unavailable"},
        {"detail": "unavailable", "data": []},
        {"data": {}},
        {"data": [1]},
        {"data": []},
    ],
)
def test_error_or_malformed_payload_never_becomes_empty_history(monkeypatch, payload):
    transport(monkeypatch, [payload])
    with pytest.raises(FXMacroDataError):
        FfnProvider()(ticker="macro/usd/gdp")


def test_real_ffn_get_consumes_provider_without_cleaning_route_identity(monkeypatch):
    ffn = pytest.importorskip(
        "ffn", reason="Native dispatch test requires optional ffn"
    )

    transport(
        monkeypatch,
        [
            page([{"date": "2026-01-02", "val": 2}, {"date": "2026-01-01", "val": 1}]),
            page(
                [{"date": "2026-01-01", "val": 10}, {"date": "2026-01-02", "val": None}]
            ),
        ],
    )
    result = ffn.get(
        "macro/usd/gdp:val,macro/usd/policy_rate:val",
        provider=FfnProvider(),
        clean_tickers=False,
        common_dates=False,
        forward_fill=False,
        start="2026-01-01",
        end="2026-01-03",
    )
    assert list(result.columns) == ["macro/usd/gdp:val", "macro/usd/policy_rate:val"]
    assert result.iloc[:, 0].tolist() == [1.0, 2.0]
    assert result.iloc[0, 1] == 10.0 and pd.isna(result.iloc[1, 1])
    assert result.index.is_unique and result.index.is_monotonic_increasing
