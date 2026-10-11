# Use FXMacroData history with ffn

`FfnProvider` supplies numeric history to ffn's callable-provider interface. It
lives in the FXMacroData SDK, so using it requires no changes to ffn. USD macro
history has a no-key baseline; its current delay and history window still apply.
A configured API key adds the subscriber feed and protected datasets.

This adapter is supplied in the `feature/ffn-provider` source branch. It is not
part of the previously released SDK. Install that branch in a separate Python
environment, alongside pandas and the tested ffn source with the callable
provider contract described in [ffn's provider guide](https://pmorissette.github.io/ffn/docs/source/data-providers.html).
Validation used ffn repository source version 1.4.1 at the exact commit below.
Earlier cached dispatchers are not supported; the provider refuses pickling so
they cannot serialize its configured Client credentials.

```bash
git clone --branch feature/ffn-provider https://github.com/fxmacrodata/fxmacrodata.git
cd fxmacrodata
python -m pip install . pandas "ffn @ git+https://github.com/pmorissette/ffn.git@23eabb0be92daaf16a12184f9bf8615d354c70cc"
```

The SDK does not add pandas or ffn to its mandatory dependencies. Import the
provider explicitly in an environment where the optional dependencies exist.

```python
import ffn
from fxmacrodata.ffn import FfnProvider

history = ffn.get(
    "macro/usd/policy_rate:val,macro/usd/inflation:val",
    provider=FfnProvider(),
    clean_tickers=False,
    common_dates=False,
    forward_fill=False,
)
```

Macro levels and positioning counts are not investment returns. Use the
resulting DataFrame for alignment and analysis; apply ffn return/statistics
functions only to data for which those calculations are meaningful.

## Tickers and fields

Use lowercase tickers. The colon suffix selects one numeric row field; it is
ffn's existing field syntax. Set `clean_tickers=False` to preserve route names.

| Ticker | Default or example field | Access |
|---|---|---|
| `macro/usd/policy_rate` | `val`; also documented change/value fields | USD baseline without a key; authenticated expansion |
| `fx/eur/usd` | `val`; `open`, `high`, `low`, `close`, or documented technical indicator | API key |
| `cot/eur` | Explicit field required, such as `noncommercial_net` or `open_interest` | USD baseline without a key; other currencies require a key |
| `commodity/gold` | `val`; also documented source/conversion/change fields | API key |

For optional protected data, configure the SDK Client once and keep credentials
out of ffn request options:

```python
import os
from fxmacrodata import Client
from fxmacrodata.ffn import FfnProvider

provider = FfnProvider(Client(api_key=os.environ["FXMD_API_KEY"]))
positions = ffn.get(
    "cot/eur:noncommercial_net", provider=provider, report="legacy_futures",
    clean_tickers=False, common_dates=False, forward_fill=False,
)
```

Keys use the Client's header authentication and redirect safeguards. The
provider has no cache, serializes no request arguments, and omits remote error
bodies and exception text from its own errors. No global provider is registered.

## Dates, options and complete history

Indexes use each row's documented `date` label. These can represent observation,
reference or COT reporting dates; they are not publication timestamps and do not
establish when a value was available to a strategy. The adapter never substitutes
`announcement_datetime`, a capture clock or a report period for a missing date.
Use the public research-panel and publication metadata contracts for
point-in-time work.

`start` and `end` accept `YYYY-MM-DD` strings or `datetime.date` values. Start is
inclusive and end is exclusive. Dates are timezone-naive calendar labels; the
provider does not resample or create intraday times. Null values remain missing,
empty history is an empty numeric Series, and ffn's alignment/filling settings
remain the caller's choice.

The provider validates pagination and follows every page up to `max_pages`
(default 1,000, with `page_size=100`). Invalid, skipped or non-advancing
continuations, incomplete pagination, malformed data and conflicting values on
the same date raise an error. Identical duplicated values are combined; conflicting
revisions are not silently discarded. Macro and FX pagination pin the first
`dataset_version` when the API supplies it and reject observed version changes.
COT and commodity contracts currently have no dataset-version pin, so those
multi-page reads do not claim snapshot isolation.

Macro requests accept the documented `series_mode`, `seasonality`, `frequency`,
`annualization`, `period_aggregation`, `basis`, `value_mode`, `official_only`,
and `revisions` selectors. The single-Series revision choices are `latest`,
`first`, and `final`; use the API directly for a full revision ledger. COT
accepts `report`. Unsupported routes, fields, options and non-real numeric
values fail clearly. Selecting a technical FX field requests the API's computed
indicator set. The provider does not compute or rename the underlying measures.

## Capability boundary

This adapter covers the four numeric history methods in the existing SDK.
Other operations remain available through the SDK where it has a method, or
through the [public API reference](https://fxmacrodata.com/documentation/reference?utm_source=github&utm_medium=referral&utm_campaign=ffn&utm_content=docs).
The table accounts for the current public operations; absence from this adapter
does not change their API availability.

| Capability family | ffn adapter or direct route |
|---|---|
| Catalogue | `Client.get_data_catalogue` preserves listings, options and coverage metadata, which are not numeric time series. |
| Macro | `macro/<currency>/<indicator>`; `Client.get_indicator` preserves raw history. Latest multi-indicator snapshots use the documented REST route. |
| Calendar | `Client.get_calendar` preserves future release-event schedules; these are not historical observation Series. |
| Predictions | Documented prediction and coverage REST routes preserve publisher, target-period and vintage identities. One date/value Series cannot retain all those dimensions. This SDK baseline has no prediction method. |
| News and headlines | The published route is `/v1/press-releases/{currency}`. Documents and provenance are not numeric Series; this SDK baseline has no press-release method. |
| FX | `fx/<base>/<quote>` uses SDK daily FX history. Timestamped, intraday and session-reference REST histories and source/universe discovery are additional public API contracts without methods in this SDK baseline. Their numeric histories could support separate explicit views; this adapter does not claim coverage of them. |
| Sessions | `/v1/market_sessions` preserves timezone-dependent schedules and open/closed status. It is not a numeric history Series and has no method in this SDK baseline. |
| COT positioning | `cot/<currency>:<field>`; `Client.get_cot` preserves the raw report and release metadata. |
| Commodity history and latest values | `commodity/<indicator>`; `Client.get_commodities` preserves raw history. The latest-commodities REST response is a multi-series snapshot. |
| Seasonality | The macro `seasonality` selector is exposed when supported by the requested indicator. The current published REST reference documents no separate seasonality-analysis route; this SDK/adapter supplies no separate seasonal-analysis workflow. |

Other publicly documented operations include rate differentials, curves,
financial prices, factors and risk sentiment; this SDK baseline has no methods
for those contracts. Their snapshots and panels carry additional dimensions,
and numeric histories may support future explicit views. Research-panel POST
preserves decision-time matrices. Announcement changes and SSE preserve event
envelopes/cursors, while health/ping return service status. Those contracts are
not represented by this adapter's finite single-Series result.

The exact REST operations are `/v1/announcements/{currency}/{indicator}`,
`/v1/announcements/{currency}/latest`, `/v1/forex/{base}/{quote}`,
`/v1/fx/reference-rates/{base}/{quote}`,
`/v1/fx/intraday-reference-rates/{base}/{quote}`,
`/v1/fx/session-rates/{base}/{quote}`, `/v1/fx/sources`,
`/v1/fx/source-universe`, `/v1/cot/{currency}`,
`/v1/commodities/{indicator}`, `/v1/commodities/latest`,
`/v1/data_catalogue/{currency}`, `/v1/predictions/coverage`,
`/v1/predictions/coverage/{currency}`, `/v1/calendar/{currency}`,
`/v1/market_sessions`, `/v1/predictions/{currency}`,
`/v1/predictions/{currency}/{indicator}`,
`/v1/rate_differentials/{base}/{quote}`, `/v1/curves/{currency}`,
`/v1/financial_prices/{currency}`, `/v1/factors/{currency}/{factor}`,
`/v1/risk_sentiment`, `/v1/risk_sentiment/changes`,
`/v1/press-releases/{currency}`, `/v1/research/panel`,
`/v1/announcements/changes`, `/v1/stream/events`, `/v1/health`, and `/v1/ping`.
