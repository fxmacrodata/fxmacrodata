"""Datetime formatting helpers for OpenBB-facing data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

ANNOUNCEMENT_DATETIME_FIELDS = (
    "announcement_datetime_utc",
    "announcement_datetime",
    "announcement_datetime_local",
    "official_actual_release_datetime",
    "official_actual_release_datetime_local",
    "release_datetime",
    "release_date",
)

OPENBB_DATETIME_SOURCE_FIELDS = {
    "announcement_datetime_utc",
    "announcement_datetime_local",
    "announcement_datetime_requested_timezone",
    "official_actual_release_datetime",
    "official_actual_release_datetime_local",
    "release_datetime",
    "release_date",
    "release_time_utc",
    "collected_at_ns",
    "collected_at_iso",
    "ingestion_latency_ms",
    "ingestion_latency_reference",
    "revisions",
}


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse API datetime values, including epoch seconds/milliseconds/nanoseconds."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return _parse_epoch(value)
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    if not cleaned:
        return None
    if _is_numeric_string(cleaned):
        return _parse_epoch(float(cleaned))

    iso_value = cleaned.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(iso_value)
    except ValueError:
        try:
            return datetime.fromisoformat(iso_value.split("+", 1)[0])
        except ValueError:
            return None


def as_utc(value: Any) -> Optional[datetime]:
    """Return a parsed datetime as timezone-aware UTC."""
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_utc_datetime(value: Any) -> Optional[str]:
    """Format a datetime value for human-readable OpenBB tables."""
    parsed = as_utc(value)
    if parsed is None:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def row_announcement_datetime(row: Dict[str, Any]) -> Optional[datetime]:
    """Find the first announcement datetime value available on a row."""
    for field in ANNOUNCEMENT_DATETIME_FIELDS:
        parsed = as_utc(row.get(field))
        if parsed is not None:
            return parsed
    return None


def row_announcement_datetime_text(row: Dict[str, Any]) -> Optional[str]:
    """Find and format the first announcement datetime value available on a row."""
    parsed = row_announcement_datetime(row)
    if parsed is None:
        return None
    return format_utc_datetime(parsed)


def with_human_announcement_datetime(
    row: Dict[str, Any],
    *,
    drop_source_fields: bool = False,
) -> Dict[str, Any]:
    """Return a copy with announcement_datetime formatted for OpenBB display."""
    normalised: Dict[str, Any] = {}
    announcement_datetime = row_announcement_datetime_text(row)
    if announcement_datetime:
        normalised["announcement_datetime"] = announcement_datetime
    for key, value in row.items():
        if key == "announcement_datetime" and announcement_datetime:
            continue
        normalised[key] = value
    if drop_source_fields:
        for field in OPENBB_DATETIME_SOURCE_FIELDS:
            normalised.pop(field, None)
    return normalised


def _parse_epoch(value: float) -> Optional[datetime]:
    seconds = float(value)
    magnitude = abs(seconds)
    if magnitude > 1e17:
        seconds /= 1_000_000_000
    elif magnitude > 1e11:
        seconds /= 1_000
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _is_numeric_string(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
