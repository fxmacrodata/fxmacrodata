# OpenBB GitHub Submission Plan

This package is intended to stay in the public `fxmacrodata/fxmacrodata`
repository and be published to PyPI as `fxmacrodata`. Do not submit or publish
until the local validation report passes and release approval is explicit.

## Recommended Submission Path

OpenBB supports independently published provider extensions and says published
extensions can be featured by opening a pull request to `OpenBB-finance/OpenBB`.
For FXMacroData, the lowest-risk first submission is therefore:

1. Release `fxmacrodata` with the OpenBB entry points already present in this SDK.
2. Open a small OpenBB PR that adds FXMacroData to the provider extension
   catalogue and README listing.
3. Only build a full `openbb_platform/providers/fxmacrodata` monorepo provider
   package later if OpenBB maintainers explicitly prefer an in-tree package.

This avoids duplicating our SDK logic into a second package before OpenBB has
reviewed the integration.

## Install Commands

Existing OpenBB Desktop or OpenBB Python environments can install:

```bash
pip install fxmacrodata
openbb-build
```

Standalone environments should install the specific extra they need:

```bash
pip install "fxmacrodata[openbb]"
pip install "fxmacrodata[openbb-api]"
pip install "fxmacrodata[workspace]"
pip install "fxmacrodata[mcp]"
```

The plain `pip install fxmacrodata` command is the one to list upstream because
OpenBB-managed environments already provide OpenBB runtime packages.

## Upstream Provider Catalogue Draft

Add this object to `assets/extensions/provider.json` in the OpenBB repository:

```json
{
  "packageName": "fxmacrodata",
  "optional": false,
  "reprName": "FXMacroData",
  "description": "Official-source macroeconomic indicators, release calendars, FX spot rates, CFTC Commitment of Traders positioning, and commodity prices for FX research workflows.",
  "credentials": ["fxmacrodata_api_key"],
  "website": "https://fxmacrodata.com",
  "instructions": "Public USD macro catalogue, macro history, and release calendar data can be used without an API key. Add an FXMacroData API key as fxmacrodata_api_key for non-USD currencies, FX spot history, COT positioning, commodities, and subscriber datasets. Subscribe at https://fxmacrodata.com/subscribe."
}
```

## Upstream README Draft

Add this row to the OpenBB Platform provider table:

```markdown
| fxmacrodata | [FXMacroData](https://fxmacrodata.com) macro indicators, release calendars, FX spot, COT positioning, and commodities for FX research | pip install fxmacrodata | Free / Paid |
```

## Draft PR Body

```markdown
## Summary

Adds FXMacroData to OpenBB's provider extension catalogue.

FXMacroData provides official-source macroeconomic indicators, economic release
calendars, FX spot rates, CFTC Commitment of Traders positioning, and commodity
prices for FX research workflows.

## Package

- PyPI package: `fxmacrodata`
- OpenBB provider name: `fxmacrodata`
- OpenBB credential: `fxmacrodata_api_key`
- Public data without key: USD macro catalogue, USD macro history, USD release calendar
- Authenticated data: non-USD macro data, FX spot history, COT positioning, commodities

## Validation

- `python -m pytest tests -q`
- `python -m ruff check fxmacrodata tests`
- `python -m black --check fxmacrodata tests`
- `python -m mypy fxmacrodata`
- `python -m build`
- `python -m twine check dist/*`
- `openbb-build`
- Local OpenBB Platform API and OpenBB Workspace backend smoke tests
```

## Release Approval Gates

- Local test suite, lint, formatting, type check, compile, package build, and
  twine check pass.
- Fresh environment installs the built wheel and OpenBB discovers both
  `openbb_core_extension` and `openbb_provider_extension` entry points.
- Local OpenBB Platform API serves `/api/v1/fxmacrodata/*` routes.
- Custom OpenBB Workspace backend serves `/widgets.json`, `/apps.json`, branded
  app images, and USD-default widgets on the approved localhost port.
- Screenshots demonstrate the generated API route, custom Workspace backend,
  branded app cards, and human-readable `announcement_datetime` values.
- User approval is given for the SDK release.
- User approval is given separately for the OpenBB upstream PR.
