"""Optional numeric-history provider for ffn's callable provider interface."""

from __future__ import annotations

import math
import re
from datetime import date
from numbers import Real
from typing import Any, NoReturn, SupportsIndex
from urllib.parse import unquote

import pandas as pd  # type: ignore[import-untyped, import-not-found]

from .client import Client
from .exceptions import FXMacroDataError

_SLUG = re.compile(r"[a-z][a-z0-9_]*\Z")
_CURRENCY = re.compile(r"[a-z]{3}\Z")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_MACRO_FIELDS = frozenset(
    {
        "val",
        "previous_value",
        "change",
        "change_from_previous",
        "pct_change_from_previous",
        "original_val",
        "val_mom",
        "pct_change",
        "pct_change_yoy",
        "pct_change_qoq",
        "pct_change_mom",
        "pct_change_12m",
    }
)
_FX_FIELDS = frozenset(
    {
        "val",
        "open",
        "high",
        "low",
        "close",
        "sma_20",
        "sma_50",
        "sma_200",
        "ema_12",
        "ema_20",
        "ema_26",
        "ema_50",
        "ema_200",
        "rsi_14",
        "atr_14",
        "adx_14",
        "stoch_k_14",
        "stoch_d_3",
        "williams_r_14",
        "cci_20",
        "donchian_upper_20",
        "donchian_middle_20",
        "donchian_lower_20",
        "macd",
        "macd_signal",
        "macd_histogram",
        "bb_upper",
        "bb_middle",
        "bb_lower",
    }
)
_COT_COUNTS = frozenset(
    {
        "open_interest",
        "noncommercial_long",
        "noncommercial_short",
        "noncommercial_net",
        "noncommercial_spread",
        "commercial_long",
        "commercial_short",
        "commercial_net",
        "total_reportable_long",
        "total_reportable_short",
        "nonreportable_long",
        "nonreportable_short",
        "nonreportable_net",
    }
    | {
        f"{group}_{position}"
        for group in (
            "dealer",
            "asset_manager",
            "leveraged_funds",
            "other_reportable",
            "producer_merchant",
            "swap_dealer",
            "managed_money",
        )
        for position in ("long", "short", "net")
    }
    | {
        "dealer_spread",
        "asset_manager_spread",
        "leveraged_funds_spread",
        "other_reportable_spread",
        "swap_dealer_spread",
        "managed_money_spread",
    }
)
_COT_FIELDS = _COT_COUNTS | {f"{name}_zscore" for name in _COT_COUNTS}
_COMMODITY_FIELDS = frozenset(
    {
        "val",
        "source_value",
        "conversion_rate",
        "cross_check_val",
        "cross_check_divergence_pct",
        "pct_change",
        "pct_change_12m",
    }
)
_MACRO_OPTIONS = {
    "series_mode": {"raw", "canonical"},
    "seasonality": {"sa", "nsa"},
    "frequency": {"level", "yoy", "qoq", "mom"},
    "annualization": {"not_annualized", "saar"},
    "period_aggregation": {"monthly", "quarterly_average"},
    "revisions": {"latest", "first", "final"},
    "basis": {"real", "nominal"},
    "value_mode": {"normalized", "source"},
}
_COT_REPORTS = {
    "legacy_futures",
    "legacy_combined",
    "tff_futures",
    "tff_combined",
    "disaggregated_futures",
}


def _day(value: Any, label: str) -> pd.Timestamp | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        value = value.isoformat()
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"{label} must be a YYYY-MM-DD date")
    try:
        return pd.Timestamp(date.fromisoformat(value))
    except (ValueError, OverflowError):
        raise ValueError(f"{label} must be a valid calendar date") from None


def _integer(value: Any, minimum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label} must be an integer >= {minimum}")
    return value


class FfnProvider:
    """Return one numeric Series for a documented history route.

    Tickers are ``macro/<currency>/<indicator>``, ``fx/<base>/<quote>``,
    ``cot/<currency>`` and ``commodity/<indicator>``. The optional ffn field
    suffix selects a documented numeric row field. The default is ``val``
    except COT, which requires an explicit field. Index dates are observation
    labels, not publication times or evidence of point-in-time availability.
    """

    def __init__(
        self,
        client: Client | None = None,
        *,
        page_size: int = 100,
        max_pages: int = 1000,
    ) -> None:
        self.client = client if client is not None else Client()
        if not isinstance(self.client, Client):
            raise TypeError("client must be an FXMacroData Client")
        self.page_size = _integer(page_size, 1, "page_size")
        if self.page_size > 100:
            raise ValueError("page_size must be <= 100")
        self.max_pages = _integer(max_pages, 1, "max_pages")

    def __repr__(self) -> str:
        return f"FfnProvider(page_size={self.page_size}, max_pages={self.max_pages})"

    def __reduce_ex__(self, protocol: SupportsIndex) -> NoReturn:
        raise TypeError(
            "FfnProvider cannot be serialized; use ffn's uncached provider interface"
        )

    def __call__(
        self,
        *,
        ticker: str,
        field: str | None = None,
        start: str | date | None = None,
        end: str | date | None = None,
        **options: Any,
    ) -> pd.Series:
        family, path, selected, params, headers = self._route(ticker, field, options)
        first = _day(start, "start")
        last = _day(end, "end")
        if first is not None and last is not None and first >= last:
            raise ValueError("start must precede end")
        if first is not None:
            params["start_date"] = first.strftime("%Y-%m-%d")
        if last is not None:
            # The API date window can include this day; enforce ffn's exclusive end below.
            params["end_date"] = last.strftime("%Y-%m-%d")
        values: dict[pd.Timestamp, float] = {}
        version: str | None = None
        expected_total: int | None = None
        for page_number in range(self.max_pages):
            offset = params["offset"]
            try:
                payload = self.client._request(
                    f"{self.client.BASE_URL}/v1/{path}", dict(params), dict(headers)
                )
            except Exception as error:
                # Remote bodies and library errors can encode header values.
                # Keep the existing transport's safety and omit that text entirely.
                status = getattr(error, "status_code", None)
                suffix = (
                    f" (HTTP {status})"
                    if isinstance(status, int) and not isinstance(status, bool)
                    else ""
                )
                raise FXMacroDataError(f"History request failed{suffix}") from None
            if (
                not isinstance(payload, dict)
                or payload.get("error")
                or payload.get("detail")
            ):
                raise FXMacroDataError("History endpoint returned an error envelope")
            rows = payload.get("data")
            if not isinstance(rows, list):
                raise FXMacroDataError("History response must contain a data array")
            current_version = payload.get("dataset_version")
            if current_version is not None:
                if not isinstance(current_version, str) or not current_version:
                    raise FXMacroDataError("Invalid history dataset_version")
                key = headers.get("X-API-Key")
                if key and (key in current_version or key in unquote(current_version)):
                    raise FXMacroDataError(
                        "History dataset_version contains credential data"
                    )
                if page_number == 0:
                    version = current_version
                elif version != current_version:
                    raise FXMacroDataError(
                        "History dataset_version changed during pagination"
                    )
            elif version is not None:
                raise FXMacroDataError(
                    "History dataset_version disappeared during pagination"
                )
            for row in rows:
                if not isinstance(row, dict):
                    raise FXMacroDataError("History rows must be objects")
                try:
                    timestamp = _day(row.get("date"), "row date")
                except ValueError:
                    raise FXMacroDataError(
                        "History row has an invalid date label"
                    ) from None
                if timestamp is None:
                    raise FXMacroDataError("History row is missing its date label")
                raw = row.get(selected)
                if raw is None:
                    value = float("nan")
                elif (
                    isinstance(raw, bool)
                    or not isinstance(raw, Real)
                    or not math.isfinite(raw)
                ):
                    raise FXMacroDataError(
                        "History field must contain finite real numbers or null"
                    )
                else:
                    value = float(raw)
                if timestamp in values:
                    previous = values[timestamp]
                    if not (
                        previous == value
                        or (math.isnan(previous) and math.isnan(value))
                    ):
                        raise FXMacroDataError(
                            "Conflicting history values share a date label"
                        )
                values[timestamp] = value
            continuation = self._continuation(
                payload.get("pagination"), offset, len(rows)
            )
            current_total = payload["pagination"]["total_count"]
            if expected_total is None:
                expected_total = current_total
            elif expected_total != current_total:
                raise FXMacroDataError("History total_count changed during pagination")
            if continuation is None:
                break
            params["offset"] = continuation
            if version is not None and family in {"macro", "fx"}:
                params["dataset_version"] = version
        else:
            raise FXMacroDataError(
                "History exceeded max_pages; narrow the requested window"
            )
        series = pd.Series(
            list(values.values()),
            index=pd.DatetimeIndex(list(values)),
            dtype="float64",
            name=f"{ticker}:{selected}",
        ).sort_index()
        if first is not None:
            series = series.loc[series.index >= first]
        if last is not None:
            series = series.loc[series.index < last]
        return series

    def _route(
        self, ticker: str, field: str | None, options: dict[str, Any]
    ) -> tuple[str, str, str, dict[str, Any], dict[str, str]]:
        if not isinstance(ticker, str):
            raise ValueError("ticker must be a documented history route")
        parts = ticker.split("/")
        family = parts[0]
        selected: str | None
        if family == "macro" and len(parts) == 3:
            currency, indicator = parts[1:]
            if (
                not _CURRENCY.fullmatch(currency)
                or not _SLUG.fullmatch(indicator)
                or indicator == "latest"
            ):
                raise ValueError("Invalid macro ticker")
            path, allowed, selected = (
                f"announcements/{currency}/{indicator}",
                _MACRO_FIELDS,
                field or "val",
            )
            headers = self.client._auth_headers(currency)
            permitted = set(_MACRO_OPTIONS) | {"official_only"}
        elif family == "fx" and len(parts) == 3:
            base, quote = parts[1:]
            if not _CURRENCY.fullmatch(base) or not _CURRENCY.fullmatch(quote):
                raise ValueError("Invalid FX ticker")
            path, allowed, selected = (
                f"forex/{base}/{quote}",
                _FX_FIELDS,
                field or "val",
            )
            headers = self.client._required_key_headers("forex")
            permitted = set()
        elif family == "cot" and len(parts) == 2 and _CURRENCY.fullmatch(parts[1]):
            path, allowed, selected = f"cot/{parts[1]}", _COT_FIELDS, field
            headers = self.client._auth_headers(parts[1])
            permitted = {"report"}
        elif (
            family == "commodity"
            and len(parts) == 2
            and _SLUG.fullmatch(parts[1])
            and parts[1] != "latest"
        ):
            path, allowed, selected = (
                f"commodities/{parts[1]}",
                _COMMODITY_FIELDS,
                field or "val",
            )
            headers = self.client._required_key_headers("commodities")
            permitted = set()
        else:
            raise ValueError("Unsupported ticker; use macro/, fx/, cot/ or commodity/")
        if not isinstance(selected, str) or selected not in allowed:
            raise ValueError(
                "Select a documented numeric field; COT requires an explicit field"
            )
        if set(options) - permitted:
            raise ValueError("Unsupported provider option for this history family")
        params: dict[str, Any] = {"limit": self.page_size, "offset": 0}
        for name, value in options.items():
            if name == "official_only":
                if not isinstance(value, bool):
                    raise ValueError("official_only must be boolean")
                params[name] = str(value).lower()
            else:
                accepted = _COT_REPORTS if name == "report" else _MACRO_OPTIONS[name]
                if not isinstance(value, str) or value not in accepted:
                    raise ValueError("Unsupported history option value")
                params[name] = value
        if family == "fx" and selected not in {"val", "open", "high", "low", "close"}:
            params["indicators"] = "all"
        return family, path, selected, params, headers

    @staticmethod
    def _continuation(pagination: Any, offset: int, count: int) -> int | None:
        if not isinstance(pagination, dict):
            raise FXMacroDataError("History response is missing pagination metadata")
        try:
            returned = _integer(pagination.get("returned_count"), 0, "returned_count")
            actual_offset = _integer(pagination.get("offset"), 0, "offset")
            total = _integer(pagination.get("total_count"), 0, "total_count")
        except ValueError:
            raise FXMacroDataError("Invalid history pagination counts") from None
        more = pagination.get("has_more")
        if (
            not isinstance(more, bool)
            or actual_offset != offset
            or returned != count
            or offset + count > total
        ):
            raise FXMacroDataError("Inconsistent history pagination metadata")
        next_offset = pagination.get("next_offset")
        if not more:
            if next_offset is not None or offset + count != total:
                raise FXMacroDataError(
                    "History pagination stopped before the full result"
                )
            return None
        if (
            count == 0
            or isinstance(next_offset, bool)
            or not isinstance(next_offset, int)
            or next_offset != offset + count
            or not offset < next_offset < total
        ):
            raise FXMacroDataError("History pagination did not advance")
        return next_offset
