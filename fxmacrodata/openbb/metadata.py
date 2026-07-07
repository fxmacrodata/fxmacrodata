"""OpenBB Workspace and MCP metadata for FXMacroData commands."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

CATEGORY = "FXMacroData"
SOURCE = ["FXMacroData"]


def _param(
    name: str,
    label: str,
    description: str,
    value: Any = None,
    param_type: str = "text",
) -> Dict[str, Any]:
    return {
        "paramName": name,
        "label": label,
        "description": description,
        "type": param_type,
        "value": value,
        "show": True,
    }


def _table_config(width: int = 20, height: int = 12) -> Dict[str, Any]:
    return {
        "category": CATEGORY,
        "searchCategory": CATEGORY,
        "type": "table",
        "source": SOURCE,
        "gridData": {"w": width, "h": height},
        "data": {
            "dataKey": "results",
            "table": {
                "showAll": True,
                "enableAdvanced": True,
            },
        },
    }


WIDGET_CONFIGS: Dict[str, Dict[str, Any]] = {
    "data_catalogue": {
        **_table_config(),
        "name": "FXMacroData Data Catalogue",
        "description": (
            "Discover available macro indicators, source metadata, and coverage "
            "freshness for a currency."
        ),
        "params": [
            _param(
                "currency",
                "Currency",
                "Three-letter currency code, e.g. USD, EUR, AUD, or JPY.",
                "USD",
            ),
            _param(
                "include_coverage",
                "Coverage",
                "Include row counts, date ranges, and freshness metadata.",
                True,
                "boolean",
            ),
            _param(
                "include_capabilities",
                "Capabilities",
                "Include machine-readable endpoint capabilities where available.",
                False,
                "boolean",
            ),
            _param(
                "indicator",
                "Indicator",
                "Optional indicator slug to filter the catalogue.",
                "",
            ),
            _param(
                "provider",
                "Provider",
                "OpenBB provider name.",
                "fxmacrodata",
            ),
        ],
    },
    "macro_indicators": {
        **_table_config(),
        "name": "FXMacroData Macro Indicator History",
        "description": (
            "Official-source macroeconomic indicator history with announcement "
            "timestamps where available."
        ),
        "params": [
            _param("currency", "Currency", "Three-letter currency code.", "USD"),
            _param(
                "indicator",
                "Indicator",
                "Indicator slug from the FXMacroData data catalogue.",
                "inflation",
            ),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                "",
                "date",
            ),
            _param(
                "end_date",
                "End Date",
                "Optional inclusive end date.",
                "",
                "date",
            ),
            _param("provider", "Provider", "OpenBB provider name.", "fxmacrodata"),
        ],
    },
    "fx_historical": {
        **_table_config(),
        "name": "FXMacroData FX Spot History",
        "description": "FX spot-rate history for supported currency pairs.",
        "params": [
            _param("base", "Base", "Base currency.", "EUR"),
            _param("quote", "Quote", "Quote currency.", "USD"),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                "",
                "date",
            ),
            _param(
                "end_date",
                "End Date",
                "Optional inclusive end date.",
                "",
                "date",
            ),
            _param("provider", "Provider", "OpenBB provider name.", "fxmacrodata"),
        ],
    },
    "cot": {
        **_table_config(),
        "name": "FXMacroData COT Positioning",
        "description": "CFTC Commitment of Traders FX futures positioning.",
        "params": [
            _param("currency", "Currency", "FX futures contract currency.", "EUR"),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                "",
                "date",
            ),
            _param(
                "end_date",
                "End Date",
                "Optional inclusive end date.",
                "",
                "date",
            ),
            _param("provider", "Provider", "OpenBB provider name.", "fxmacrodata"),
        ],
    },
    "commodity": {
        **_table_config(),
        "name": "FXMacroData Commodity Prices",
        "description": "Commodity and energy price history.",
        "params": [
            _param(
                "indicator",
                "Commodity",
                "Commodity slug such as gold, silver, platinum, or oil_wti.",
                "gold",
            ),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                "",
                "date",
            ),
            _param(
                "end_date",
                "End Date",
                "Optional inclusive end date.",
                "",
                "date",
            ),
            _param("provider", "Provider", "OpenBB provider name.", "fxmacrodata"),
        ],
    },
    "release_calendar": {
        **_table_config(),
        "name": "FXMacroData Release Calendar",
        "description": (
            "Official macroeconomic release schedules with timestamps, source "
            "metadata, and confirmation flags where available."
        ),
        "params": [
            _param("currency", "Currency", "Calendar currency.", "USD"),
            _param(
                "indicator",
                "Indicator",
                "Optional release indicator filter.",
                "",
            ),
            _param("provider", "Provider", "OpenBB provider name.", "fxmacrodata"),
        ],
    },
}


def _mcp_config(command_name: str) -> Dict[str, Any]:
    return {
        "expose": True,
        "mcp_type": "tool",
        "methods": ["GET"],
    }


MCP_CONFIGS: Dict[str, Dict[str, Any]] = {
    command_name: _mcp_config(command_name) for command_name in WIDGET_CONFIGS
}


def openapi_extra(command_name: str) -> Dict[str, Any]:
    """Return OpenAPI metadata consumed by OpenBB Workspace and MCP tooling."""
    return {
        "widget_config": deepcopy(WIDGET_CONFIGS[command_name]),
        "mcp_config": deepcopy(MCP_CONFIGS[command_name]),
    }


def workspace_widgets_json() -> Dict[str, Dict[str, Any]]:
    """Return static Workspace widget definitions for the custom backend."""
    widgets: Dict[str, Dict[str, Any]] = {}
    endpoint_map = {
        "data_catalogue": "catalogue",
        "macro_indicators": "macro_indicator",
        "fx_historical": "forex",
        "cot": "cot",
        "commodity": "commodity",
        "release_calendar": "release_calendar",
    }
    widget_id_map = {
        "data_catalogue": "fxmacrodata_catalogue",
        "macro_indicators": "fxmacrodata_macro_indicator",
        "fx_historical": "fxmacrodata_forex",
        "cot": "fxmacrodata_cot",
        "commodity": "fxmacrodata_commodity",
        "release_calendar": "fxmacrodata_release_calendar",
    }

    for command_name, config in WIDGET_CONFIGS.items():
        widget = deepcopy(config)
        widget["endpoint"] = endpoint_map[command_name]
        widget["source"] = "FXMacroData"
        widget.pop("searchCategory", None)
        widget["data"] = {
            "table": {
                "showAll": True,
                "enableAdvanced": True,
            }
        }
        widget["params"] = [
            param
            for param in widget.get("params", [])
            if param.get("paramName") != "provider"
        ]
        widgets[widget_id_map[command_name]] = widget

    return widgets


def workspace_apps_json() -> List[Dict[str, Any]]:
    """Return OpenBB Workspace app definitions for FXMacroData widgets."""
    return [
        {
            "name": "FXMacroData Macro Event Radar",
            "img": "",
            "img_dark": "",
            "img_light": "",
            "description": (
                "Track upcoming official macro releases and inspect available "
                "currency-level macro data coverage."
            ),
            "allowCustomization": True,
            "tabs": {
                "events": {
                    "id": "events",
                    "name": "Events",
                    "layout": [
                        {
                            "i": "fxmacrodata_release_calendar",
                            "x": 0,
                            "y": 0,
                            "w": 24,
                            "h": 12,
                        },
                        {
                            "i": "fxmacrodata_catalogue",
                            "x": 24,
                            "y": 0,
                            "w": 16,
                            "h": 12,
                        },
                    ],
                }
            },
            "groups": [],
        },
        {
            "name": "FXMacroData FX Research Board",
            "img": "",
            "img_dark": "",
            "img_light": "",
            "description": (
                "Combine FX spot history, macro indicator rows, COT positioning, "
                "and commodity context in one Workspace app."
            ),
            "allowCustomization": True,
            "tabs": {
                "research": {
                    "id": "research",
                    "name": "Research",
                    "layout": [
                        {"i": "fxmacrodata_forex", "x": 0, "y": 0, "w": 20, "h": 10},
                        {
                            "i": "fxmacrodata_macro_indicator",
                            "x": 20,
                            "y": 0,
                            "w": 20,
                            "h": 10,
                        },
                        {"i": "fxmacrodata_cot", "x": 0, "y": 10, "w": 20, "h": 10},
                        {
                            "i": "fxmacrodata_commodity",
                            "x": 20,
                            "y": 10,
                            "w": 20,
                            "h": 10,
                        },
                    ],
                }
            },
            "groups": [],
        },
    ]
