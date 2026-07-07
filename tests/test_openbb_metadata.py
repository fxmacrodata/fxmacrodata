"""Tests for OpenBB Workspace and MCP metadata."""

from __future__ import annotations

from fxmacrodata.openbb.metadata import (
    MCP_CONFIGS,
    WIDGET_CONFIGS,
    openapi_extra,
    workspace_apps_json,
    workspace_widgets_json,
)


def test_openapi_extra_contains_workspace_and_mcp_config():
    """Router metadata should support generated Workspace and MCP integrations."""
    extra = openapi_extra("fx_historical")

    assert extra["widget_config"]["name"] == "FXMacroData FX Spot History"
    assert extra["widget_config"]["data"]["dataKey"] == "results"
    assert extra["mcp_config"] == {
        "expose": True,
        "mcp_type": "tool",
        "methods": ["GET"],
    }


def test_openapi_extra_returns_isolated_copies():
    """Callers should not mutate shared metadata by editing returned objects."""
    extra = openapi_extra("data_catalogue")
    extra["widget_config"]["name"] = "Changed"

    assert WIDGET_CONFIGS["data_catalogue"]["name"] == "FXMacroData Data Catalogue"


def test_all_workspace_widgets_have_mcp_configs():
    """Every generated widget command should also be exposed to OpenBB MCP."""
    assert set(WIDGET_CONFIGS) == set(MCP_CONFIGS)


def test_custom_backend_widgets_match_workspace_contract():
    """Static Workspace backend metadata should stay compatible with OpenBB."""
    widgets = workspace_widgets_json()
    apps = workspace_apps_json()

    assert {
        "fxmacrodata_catalogue",
        "fxmacrodata_release_calendar",
        "fxmacrodata_macro_indicator",
        "fxmacrodata_forex",
        "fxmacrodata_cot",
        "fxmacrodata_commodity",
    } == set(widgets)
    assert widgets["fxmacrodata_catalogue"]["endpoint"] == "catalogue"
    assert widgets["fxmacrodata_forex"]["params"]
    assert {app["name"] for app in apps} == {
        "FXMacroData Macro Event Radar",
        "FXMacroData FX Research Board",
    }
