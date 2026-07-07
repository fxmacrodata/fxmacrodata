"""OpenBB router extension exposing FXMacroData commands."""

from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router

from fxmacrodata.openbb.metadata import openapi_extra

router = Router(
    prefix="",
    description=(
        "FXMacroData macroeconomic, release-calendar, FX, COT, and commodity "
        "data for FX research workflows."
    ),
)


async def _query_provider_interface(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Execute a command through OpenBB's provider interface."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="FXMacroDataDataCatalogue",
    openapi_extra=openapi_extra("data_catalogue"),
)
async def data_catalogue(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Discover available FXMacroData indicators and coverage metadata."""
    return await _query_provider_interface(**locals())


@router.command(
    model="FXMacroDataMacroIndicators",
    openapi_extra=openapi_extra("macro_indicators"),
)
async def macro_indicators(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get macroeconomic indicator history from FXMacroData."""
    return await _query_provider_interface(**locals())


@router.command(
    model="FXMacroDataFxHistorical",
    openapi_extra=openapi_extra("fx_historical"),
)
async def fx_historical(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get FX spot-rate history from FXMacroData."""
    return await _query_provider_interface(**locals())


@router.command(model="FXMacroDataCot", openapi_extra=openapi_extra("cot"))
async def cot(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get CFTC Commitment of Traders positioning from FXMacroData."""
    return await _query_provider_interface(**locals())


@router.command(model="FXMacroDataCommodity", openapi_extra=openapi_extra("commodity"))
async def commodity(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get commodity price history from FXMacroData."""
    return await _query_provider_interface(**locals())


@router.command(
    model="FXMacroDataReleaseCalendar",
    openapi_extra=openapi_extra("release_calendar"),
)
async def release_calendar(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get official economic release schedules from FXMacroData."""
    return await _query_provider_interface(**locals())
