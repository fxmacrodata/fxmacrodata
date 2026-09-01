"""OpenBB integration for the FXMacroData Python package.

This module registers FXMacroData as an OpenBB provider extension. The
user-facing commands live in :mod:`fxmacrodata.openbb.router`.

Install the main package with the OpenBB extra and run ``openbb-build`` so
OpenBB discovers the router and provider entry points::

    pip install "fxmacrodata[openbb]"
    openbb-build

Then use the OpenBB Python interface::

    from openbb import obb

    obb.user.credentials.fxmacrodata_api_key = "YOUR_KEY"
    df = obb.fxmacrodata.fx_historical(
        base="USD",
        quote="JPY",
        provider="fxmacrodata",
    ).to_df()

Fetcher classes can also be imported directly from
``fxmacrodata.openbb.models`` for lower-level tests and integrations::

    from fxmacrodata.openbb.models.macro_indicators import (
        FXMacroDataMacroIndicatorsFetcher,
    )
"""

from importlib.metadata import PackageNotFoundError, version
from typing import Any

try:
    __version__ = version("fxmacrodata")
except PackageNotFoundError:
    __version__ = "1.2.1"

_OpenBBProvider: Any = None
try:
    from openbb_core.provider.abstract.provider import Provider as _ImportedProvider
except ModuleNotFoundError as exc:
    if exc.name != "openbb_core":
        raise
else:
    _OpenBBProvider = _ImportedProvider

if _OpenBBProvider is None:
    fxmacrodata_provider = None
    __all__ = ["fxmacrodata_provider"]
else:
    from fxmacrodata.openbb.models.commodities import FXMacroDataCommodityFetcher
    from fxmacrodata.openbb.models.cot import FXMacroDataCotFetcher
    from fxmacrodata.openbb.models.data_catalogue import FXMacroDataDataCatalogueFetcher
    from fxmacrodata.openbb.models.forex import FXMacroDataFxHistoricalFetcher
    from fxmacrodata.openbb.models.macro_indicators import (
        FXMacroDataMacroIndicatorsFetcher,
    )
    from fxmacrodata.openbb.models.release_calendar import (
        FXMacroDataReleaseCalendarFetcher,
    )

    __all__ = [
        "fxmacrodata_provider",
        "FXMacroDataCotFetcher",
        "FXMacroDataCommodityFetcher",
        "FXMacroDataDataCatalogueFetcher",
        "FXMacroDataFxHistoricalFetcher",
        "FXMacroDataMacroIndicatorsFetcher",
        "FXMacroDataReleaseCalendarFetcher",
    ]

    fxmacrodata_provider = _OpenBBProvider(
        name="fxmacrodata",
        website="https://fxmacrodata.com",
        description=(
            "FXMacroData provides macroeconomic indicator time series, FX spot "
            "rates, CFTC Commitment of Traders positioning, commodity prices, "
            "and economic release calendars from official government and "
            "central-bank publications for FX market analysis."
        ),
        # OpenBB stores this as ``fxmacrodata_api_key`` in user credentials.
        credentials=["api_key"],
        fetcher_dict={
            # Usage: obb.fxmacrodata.data_catalogue(currency="USD")
            "FXMacroDataDataCatalogue": FXMacroDataDataCatalogueFetcher,
            # Usage: obb.fxmacrodata.macro_indicators(currency="USD", indicator="inflation")
            "FXMacroDataMacroIndicators": FXMacroDataMacroIndicatorsFetcher,
            # Usage: obb.fxmacrodata.fx_historical(base="USD", quote="JPY")
            "FXMacroDataFxHistorical": FXMacroDataFxHistoricalFetcher,
            # Usage: obb.fxmacrodata.cot(currency="USD")
            "FXMacroDataCot": FXMacroDataCotFetcher,
            # Usage: obb.fxmacrodata.commodity(indicator="gold")
            "FXMacroDataCommodity": FXMacroDataCommodityFetcher,
            # Usage: obb.fxmacrodata.release_calendar(currency="USD")
            "FXMacroDataReleaseCalendar": FXMacroDataReleaseCalendarFetcher,
        },
    )
