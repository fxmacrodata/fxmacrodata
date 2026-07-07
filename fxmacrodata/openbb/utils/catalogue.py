"""Catalogue helpers shared by the OpenBB provider and Workspace backend."""

from __future__ import annotations

from typing import Any, Dict, List


def flatten_catalogue_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten the FXMacroData catalogue payload into table-friendly rows."""
    catalogue = payload.get("catalogue") or {}
    coverage_rows = {
        row.get("indicator"): row
        for row in payload.get("coverage", [])
        if isinstance(row, dict) and row.get("indicator")
    }
    rows: List[Dict[str, Any]] = []

    for indicator, meta in catalogue.items():
        if not isinstance(meta, dict):
            meta = {}
        coverage = meta.get("coverage") or coverage_rows.get(indicator, {})
        rows.append(
            {
                "indicator": indicator,
                "name": meta.get("name"),
                "unit": meta.get("unit"),
                "frequency": meta.get("frequency"),
                "source": meta.get("source"),
                "source_series_id": meta.get("source_series_id"),
                "source_series_name": meta.get("source_series_name"),
                "seasonal_adjustment": meta.get("seasonal_adjustment"),
                "price_basis": meta.get("price_basis"),
                "available": coverage.get("available"),
                "requires_api_key": coverage.get("requires_api_key"),
                "earliest_available_date": coverage.get("earliest_available_date"),
                "latest_available_date": coverage.get("latest_available_date"),
                "row_count": coverage.get("row_count"),
                "has_recent_data": coverage.get("has_recent_data"),
                "coverage_quality": coverage.get("coverage_quality"),
                "recent_observation_count": coverage.get("recent_observation_count"),
            }
        )
    return rows
