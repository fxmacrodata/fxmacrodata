"""OpenBB Workspace and MCP metadata for FXMacroData commands."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote

CATEGORY = "FXMacroData"
SOURCE = ["FXMacroData"]
DEFAULT_HISTORY_START_DATE = "2025-01-01"
DEFAULT_FX_BASE = "USD"
DEFAULT_FX_QUOTE = "JPY"
DEFAULT_COT_CURRENCY = "USD"


def _svg_data_uri(svg: str) -> str:
    """Encode an SVG preview so OpenBB Workspace can load it from apps.json."""
    compact_svg = " ".join(svg.split())
    return f"data:image/svg+xml,{quote(compact_svg)}"


def _brand_defs() -> str:
    return """
    <defs>
      <linearGradient id="fxmd-bg" x1="0" y1="0" x2="960" y2="540" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#04101d"/>
        <stop offset="0.48" stop-color="#071723"/>
        <stop offset="1" stop-color="#0b1020"/>
      </linearGradient>
      <linearGradient id="fxmd-brand" x1="0" y1="0" x2="280" y2="0" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#2f9bff"/>
        <stop offset="0.52" stop-color="#18d5ff"/>
        <stop offset="1" stop-color="#1ff2b0"/>
      </linearGradient>
      <linearGradient id="fxmd-amber" x1="0" y1="0" x2="200" y2="0" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#ffd166"/>
        <stop offset="1" stop-color="#f59e0b"/>
      </linearGradient>
      <linearGradient id="fxmd-violet" x1="0" y1="0" x2="220" y2="0" gradientUnits="userSpaceOnUse">
        <stop offset="0" stop-color="#8b5cf6"/>
        <stop offset="1" stop-color="#22d3ee"/>
      </linearGradient>
      <pattern id="fxmd-grid" width="42" height="42" patternUnits="userSpaceOnUse">
        <path d="M42 0H0V42" fill="none" stroke="#163044" stroke-width="1" opacity="0.38"/>
      </pattern>
      <pattern id="fxmd-dots" width="28" height="28" patternUnits="userSpaceOnUse">
        <circle cx="3" cy="3" r="1.7" fill="#22d3ee" opacity="0.38"/>
      </pattern>
      <filter id="fxmd-glow" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="8" result="blur"/>
        <feColorMatrix in="blur" type="matrix" values="0 0 0 0 0.03 0 0 0 0 0.88 0 0 0 0 0.88 0 0 0 0.72 0" result="glow"/>
        <feMerge>
          <feMergeNode in="glow"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
      <clipPath id="fxmd-card-clip">
        <rect x="30" y="28" width="900" height="484" rx="34"/>
      </clipPath>
    </defs>
    """


def _fxmd_logo_group(x: int = 58, y: int = 42, scale: float = 0.58) -> str:
    return f"""
    <g transform="translate({x} {y}) scale({scale})" filter="url(#fxmd-glow)">
      <g opacity="0.84">
        <circle cx="16" cy="16" r="3" fill="#22d3ee"/>
        <circle cx="42" cy="16" r="3" fill="#22d3ee"/>
        <circle cx="68" cy="16" r="3" fill="#22d3ee"/>
        <circle cx="94" cy="16" r="3" fill="#14b8a6"/>
        <circle cx="16" cy="42" r="3" fill="#38bdf8"/>
        <circle cx="42" cy="42" r="3" fill="#22d3ee"/>
        <circle cx="68" cy="42" r="3" fill="#14b8a6"/>
        <circle cx="94" cy="42" r="3" fill="#14b8a6"/>
      </g>
      <rect x="114" y="84" width="24" height="60" rx="4" fill="url(#fxmd-brand)" opacity="0.72"/>
      <rect x="152" y="60" width="24" height="84" rx="4" fill="url(#fxmd-brand)" opacity="0.82"/>
      <rect x="190" y="34" width="24" height="110" rx="4" fill="url(#fxmd-brand)" opacity="0.95"/>
      <path d="M18 134L96 56L142 102L248 4" fill="none" stroke="url(#fxmd-brand)" stroke-width="19" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M222 0L254 4L250 38" fill="none" stroke="#1ff2b0" stroke-width="19" stroke-linecap="round" stroke-linejoin="round"/>
      <text x="0" y="212" font-family="Arial, sans-serif" font-size="44" font-weight="800" fill="url(#fxmd-brand)" letter-spacing="0">FXMacroData</text>
    </g>
    """


def _watermark_logo(x: int = 650, y: int = 48, scale: float = 1.05) -> str:
    return f"""
    <g transform="translate({x} {y}) scale({scale})" opacity="0.12">
      <rect x="118" y="86" width="24" height="62" rx="4" fill="#22d3ee"/>
      <rect x="154" y="62" width="24" height="86" rx="4" fill="#22d3ee"/>
      <rect x="190" y="34" width="24" height="114" rx="4" fill="#22d3ee"/>
      <path d="M18 138L96 58L142 104L250 6" fill="none" stroke="#22d3ee" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M224 2L256 6L252 40" fill="none" stroke="#22d3ee" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
    </g>
    """


def _app_frame(title: str, subtitle: str, body: str, accent: str = "#22d3ee") -> str:
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
      {_brand_defs()}
      <rect width="960" height="540" fill="url(#fxmd-bg)"/>
      <rect width="960" height="540" fill="url(#fxmd-grid)" opacity="0.72"/>
      <rect x="30" y="28" width="900" height="484" rx="34" fill="#07131f" stroke="{accent}" stroke-width="2.5" opacity="0.98"/>
      <g clip-path="url(#fxmd-card-clip)">
        <rect x="30" y="28" width="900" height="484" fill="url(#fxmd-dots)" opacity="0.22"/>
        {_watermark_logo()}
        <path d="M36 438C178 354 294 394 410 320C514 254 632 266 924 126" fill="none" stroke="{accent}" stroke-width="2" opacity="0.22"/>
        <path d="M36 460C212 396 334 444 506 338C650 250 754 276 924 204" fill="none" stroke="#8b5cf6" stroke-width="2" opacity="0.16"/>
      </g>
      {_fxmd_logo_group()}
      <text x="330" y="86" fill="#f8fafc" font-family="Arial, sans-serif" font-size="32" font-weight="800">{title}</text>
      <text x="332" y="122" fill="#98aec4" font-family="Arial, sans-serif" font-size="18" font-weight="700">{subtitle}</text>
      {body}
    </svg>
    """


APP_IMAGE_URIS = {
    "event_radar": _svg_data_uri(
        _app_frame(
            "Macro Event Radar",
            "USD release risk, exact timestamps, coverage",
            """
            <g transform="translate(92 188)">
              <rect x="0" y="0" width="776" height="248" rx="26" fill="#0b1a29" stroke="#1f4f6a" opacity="0.94"/>
              <path d="M48 196H728M48 132H728M48 68H728" stroke="#24475a" stroke-width="2"/>
              <path d="M74 190C144 116 202 152 262 88C342 2 412 82 492 42C572 2 648 74 720 24" fill="none" stroke="#22d3ee" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" filter="url(#fxmd-glow)"/>
              <g font-family="Arial, sans-serif" font-weight="800" font-size="18">
                <rect x="68" y="46" width="122" height="42" rx="21" fill="#102f2c" stroke="#14b8a6"/>
                <circle cx="94" cy="67" r="8" fill="#1ff2b0"/>
                <text x="112" y="74" fill="#dffcf6">CPI 12:30</text>
                <rect x="276" y="112" width="126" height="42" rx="21" fill="#312614" stroke="#f59e0b"/>
                <circle cx="302" cy="133" r="8" fill="#ffd166"/>
                <text x="320" y="140" fill="#fff4d8">PPI 12:30</text>
                <rect x="532" y="58" width="142" height="42" rx="21" fill="#152746" stroke="#38bdf8"/>
                <circle cx="558" cy="79" r="8" fill="#38bdf8"/>
                <text x="576" y="86" fill="#e0f7ff">Claims 12:30</text>
              </g>
              <text x="48" y="234" fill="#7dd3fc" font-family="Arial, sans-serif" font-size="22" font-weight="800">confirmed calendar rows</text>
              <text x="532" y="234" fill="#b9c8d9" font-family="Arial, sans-serif" font-size="22" font-weight="800">195 upcoming</text>
            </g>
            """,
            "#22d3ee",
        )
    ),
    "macro_monitor": _svg_data_uri(
        _app_frame(
            "USD Macro Monitor",
            "Public CPI, releases, freshness",
            """
            <g transform="translate(90 180)">
              <rect x="0" y="0" width="224" height="118" rx="24" fill="#082821" stroke="#1ff2b0" opacity="0.95"/>
              <text x="26" y="42" fill="#8fffee" font-family="Arial, sans-serif" font-size="20" font-weight="800">Inflation</text>
              <text x="26" y="88" fill="#ffffff" font-family="Arial, sans-serif" font-size="48" font-weight="900">4.20%</text>
              <rect x="252" y="0" width="224" height="118" rx="24" fill="#0b2438" stroke="#38bdf8" opacity="0.95"/>
              <text x="278" y="42" fill="#bfefff" font-family="Arial, sans-serif" font-size="20" font-weight="800">Coverage</text>
              <text x="278" y="88" fill="#ffffff" font-family="Arial, sans-serif" font-size="44" font-weight="900">46</text>
              <rect x="504" y="0" width="276" height="118" rx="24" fill="#261d0c" stroke="#f59e0b" opacity="0.95"/>
              <text x="530" y="42" fill="#ffe8b3" font-family="Arial, sans-serif" font-size="20" font-weight="800">Next release</text>
              <text x="530" y="88" fill="#ffffff" font-family="Arial, sans-serif" font-size="44" font-weight="900">Jul 14</text>
              <rect x="0" y="154" width="780" height="132" rx="26" fill="#091827" stroke="#21465a"/>
              <path d="M36 102L112 78L188 88L264 52L340 62L416 24L492 38L568 18L644 50L744 30" transform="translate(0 154)" fill="none" stroke="url(#fxmd-brand)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" filter="url(#fxmd-glow)"/>
              <path d="M36 258H744" stroke="#27485a" stroke-width="2"/>
              <text x="36" y="272" fill="#9fb4c8" font-family="Arial, sans-serif" font-size="19" font-weight="800">official-source macro history</text>
            </g>
            """,
            "#1ff2b0",
        )
    ),
    "fx_research": _svg_data_uri(
        _app_frame(
            "Pro FX Board",
            "USD pairs, COT, commodities, macro",
            """
            <g transform="translate(86 176)">
              <rect x="0" y="0" width="516" height="276" rx="28" fill="#071624" stroke="#246079"/>
              <path d="M36 218H478M36 162H478M36 106H478M36 50H478" stroke="#214257" stroke-width="2"/>
              <g transform="translate(52 34)">
                <rect x="0" y="42" width="20" height="92" rx="5" fill="#1ff2b0"/>
                <line x1="10" y1="12" x2="10" y2="164" stroke="#1ff2b0" stroke-width="5" stroke-linecap="round"/>
                <rect x="74" y="88" width="20" height="86" rx="5" fill="#ff4d5e"/>
                <line x1="84" y1="58" x2="84" y2="206" stroke="#ff4d5e" stroke-width="5" stroke-linecap="round"/>
                <rect x="148" y="28" width="20" height="112" rx="5" fill="#1ff2b0"/>
                <line x1="158" y1="0" x2="158" y2="178" stroke="#1ff2b0" stroke-width="5" stroke-linecap="round"/>
                <rect x="222" y="62" width="20" height="106" rx="5" fill="#ff4d5e"/>
                <line x1="232" y1="26" x2="232" y2="204" stroke="#ff4d5e" stroke-width="5" stroke-linecap="round"/>
                <rect x="296" y="22" width="20" height="92" rx="5" fill="#1ff2b0"/>
                <line x1="306" y1="0" x2="306" y2="156" stroke="#1ff2b0" stroke-width="5" stroke-linecap="round"/>
                <path d="M10 178L84 154L158 116L232 132L306 82L394 34" fill="none" stroke="#38bdf8" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" filter="url(#fxmd-glow)"/>
              </g>
              <text x="42" y="248" fill="#dff8ff" font-family="Arial, sans-serif" font-size="24" font-weight="900">USD/JPY spot</text>
              <rect x="546" y="0" width="246" height="124" rx="26" fill="#15172c" stroke="#8b5cf6"/>
              <text x="574" y="42" fill="#ddd6fe" font-family="Arial, sans-serif" font-size="22" font-weight="900">COT USD</text>
              <rect x="574" y="72" width="160" height="18" rx="9" fill="#2c2f45"/>
              <rect x="574" y="72" width="116" height="18" rx="9" fill="url(#fxmd-violet)"/>
              <rect x="546" y="152" width="246" height="124" rx="26" fill="#231a09" stroke="#f59e0b"/>
              <text x="574" y="194" fill="#fde68a" font-family="Arial, sans-serif" font-size="22" font-weight="900">Gold context</text>
              <path d="M574 244L622 222L674 234L732 198L770 206" fill="none" stroke="url(#fxmd-amber)" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
            </g>
            """,
            "#8b5cf6",
        )
    ),
}


APP_IMAGE_FILENAMES = {
    "event_radar": "event-radar.svg",
    "macro_monitor": "usd-macro-monitor.svg",
    "fx_research": "pro-fx-board.svg",
}
APP_IMAGE_KEYS_BY_FILENAME = {value: key for key, value in APP_IMAGE_FILENAMES.items()}


def app_image_svg(filename: str) -> str:
    """Return raw SVG markup for a Workspace app preview image filename."""
    image_key = APP_IMAGE_KEYS_BY_FILENAME[filename]
    return unquote(APP_IMAGE_URIS[image_key].split(",", 1)[1])


def _app_image_uri(image_key: str, image_base_url: Optional[str] = None) -> str:
    if image_base_url:
        return f"{image_base_url.rstrip('/')}/{APP_IMAGE_FILENAMES[image_key]}"
    return APP_IMAGE_URIS[image_key]


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
                DEFAULT_HISTORY_START_DATE,
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
            _param("base", "Base", "Base currency.", DEFAULT_FX_BASE),
            _param("quote", "Quote", "Quote currency.", DEFAULT_FX_QUOTE),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                DEFAULT_HISTORY_START_DATE,
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
            _param(
                "currency",
                "Currency",
                "FX futures contract currency.",
                DEFAULT_COT_CURRENCY,
            ),
            _param(
                "start_date",
                "Start Date",
                "Optional inclusive start date.",
                DEFAULT_HISTORY_START_DATE,
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
                DEFAULT_HISTORY_START_DATE,
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

    widgets["fxmacrodata_release_timeline"] = {
        "category": CATEGORY,
        "type": "chart",
        "source": "FXMacroData",
        "gridData": {"w": 40, "h": 12},
        "name": "FXMacroData Release Radar",
        "description": (
            "Stacked visual radar of upcoming official macro releases by date "
            "and event category."
        ),
        "endpoint": "release_calendar_timeline",
        "params": [
            _param("currency", "Currency", "Calendar currency.", "USD"),
            _param(
                "indicator",
                "Indicator",
                "Optional release indicator filter.",
                "",
            ),
        ],
    }

    return widgets


def workspace_apps_json(image_base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return OpenBB Workspace app definitions for FXMacroData widgets."""
    return [
        {
            "name": "FXMacroData Macro Event Radar",
            "img": _app_image_uri("event_radar", image_base_url),
            "img_dark": _app_image_uri("event_radar", image_base_url),
            "img_light": _app_image_uri("event_radar", image_base_url),
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
                            "i": "fxmacrodata_release_timeline",
                            "x": 0,
                            "y": 0,
                            "w": 40,
                            "h": 12,
                            "state": {
                                "params": {"currency": "USD", "indicator": ""},
                            },
                        },
                        {
                            "i": "fxmacrodata_release_calendar",
                            "x": 0,
                            "y": 12,
                            "w": 24,
                            "h": 12,
                            "state": {
                                "params": {"currency": "USD", "indicator": ""},
                                "columnState": {
                                    "default_": {
                                        "columnPinning": {
                                            "leftColIds": [
                                                "announcement_datetime",
                                                "event",
                                            ],
                                            "rightColIds": [],
                                        }
                                    }
                                },
                            },
                        },
                        {
                            "i": "fxmacrodata_catalogue",
                            "x": 24,
                            "y": 12,
                            "w": 16,
                            "h": 12,
                            "state": {
                                "params": {
                                    "currency": "USD",
                                    "include_coverage": True,
                                    "include_capabilities": False,
                                    "indicator": "",
                                }
                            },
                        },
                    ],
                }
            },
            "groups": [],
        },
        {
            "name": "FXMacroData USD Macro Monitor",
            "img": _app_image_uri("macro_monitor", image_base_url),
            "img_dark": _app_image_uri("macro_monitor", image_base_url),
            "img_light": _app_image_uri("macro_monitor", image_base_url),
            "description": (
                "Track public USD macro history, upcoming release risk, and "
                "catalogue freshness without an FXMacroData API key."
            ),
            "allowCustomization": True,
            "tabs": {
                "macro": {
                    "id": "macro",
                    "name": "Macro",
                    "layout": [
                        {
                            "i": "fxmacrodata_macro_indicator",
                            "x": 0,
                            "y": 0,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "currency": "USD",
                                    "indicator": "inflation",
                                    "start_date": DEFAULT_HISTORY_START_DATE,
                                },
                                "chartView": {
                                    "enabled": False,
                                    "chartType": "line",
                                },
                            },
                        },
                        {
                            "i": "fxmacrodata_release_timeline",
                            "x": 20,
                            "y": 0,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {"currency": "USD", "indicator": ""},
                            },
                        },
                        {
                            "i": "fxmacrodata_release_calendar",
                            "x": 0,
                            "y": 10,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {"currency": "USD", "indicator": ""},
                            },
                        },
                        {
                            "i": "fxmacrodata_catalogue",
                            "x": 20,
                            "y": 10,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "currency": "USD",
                                    "include_coverage": True,
                                    "include_capabilities": False,
                                    "indicator": "",
                                }
                            },
                        },
                    ],
                }
            },
            "groups": [],
        },
        {
            "name": "FXMacroData Pro FX Board",
            "img": _app_image_uri("fx_research", image_base_url),
            "img_dark": _app_image_uri("fx_research", image_base_url),
            "img_light": _app_image_uri("fx_research", image_base_url),
            "description": (
                "Combine FX spot history, COT positioning, commodity context, "
                "and macro rows. Requires an FXMacroData API key."
            ),
            "authentication": (
                "Requires an FXMacroData Professional API key. Add it as an "
                "X-API-Key header on this Workspace backend connection."
            ),
            "allowCustomization": True,
            "tabs": {
                "research": {
                    "id": "research",
                    "name": "Research",
                    "layout": [
                        {
                            "i": "fxmacrodata_forex",
                            "x": 0,
                            "y": 0,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "base": DEFAULT_FX_BASE,
                                    "quote": DEFAULT_FX_QUOTE,
                                    "start_date": DEFAULT_HISTORY_START_DATE,
                                },
                                "chartView": {
                                    "enabled": False,
                                    "chartType": "line",
                                },
                            },
                        },
                        {
                            "i": "fxmacrodata_macro_indicator",
                            "x": 20,
                            "y": 0,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "currency": "USD",
                                    "indicator": "inflation",
                                    "start_date": DEFAULT_HISTORY_START_DATE,
                                },
                                "chartView": {
                                    "enabled": False,
                                    "chartType": "line",
                                },
                            },
                        },
                        {
                            "i": "fxmacrodata_cot",
                            "x": 0,
                            "y": 10,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "currency": DEFAULT_COT_CURRENCY,
                                    "start_date": DEFAULT_HISTORY_START_DATE,
                                }
                            },
                        },
                        {
                            "i": "fxmacrodata_commodity",
                            "x": 20,
                            "y": 10,
                            "w": 20,
                            "h": 10,
                            "state": {
                                "params": {
                                    "indicator": "gold",
                                    "start_date": DEFAULT_HISTORY_START_DATE,
                                }
                            },
                        },
                    ],
                }
            },
            "groups": [],
        },
    ]
