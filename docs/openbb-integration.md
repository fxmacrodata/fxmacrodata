# OpenBB Integration

FXMacroData exposes OpenBB integrations through the Python SDK package. Do not
publish or submit this package until the release checklist has passed and the
release has been approved.

OpenBB currently has multiple surfaces. The same FXMacroData provider/router
extension feeds the Python interface, REST API, CLI, generated Workspace
widgets, and MCP server. A separate custom Workspace backend is also included
for teams that want a small standalone FastAPI backend instead of a full OpenBB
Platform runtime.

## 1. Python Interface

Install into a Python 3.10+ environment:

```bash
pip install "fxmacrodata[openbb]"
openbb-build
```

Use the extension:

```python
from openbb import obb

obb.user.credentials.fxmacrodata_api_key = "YOUR_API_KEY"

df = obb.fxmacrodata.fx_historical(
    base="EUR",
    quote="USD",
    start_date="2024-01-01",
    provider="fxmacrodata",
).to_df()
```

Available commands:

- `obb.fxmacrodata.data_catalogue`
- `obb.fxmacrodata.macro_indicators`
- `obb.fxmacrodata.fx_historical`
- `obb.fxmacrodata.cot`
- `obb.fxmacrodata.commodity`
- `obb.fxmacrodata.release_calendar`

## 2. OpenBB REST API

Install:

```bash
pip install "fxmacrodata[openbb-api]"
openbb-build
```

Run the OpenBB Platform API:

```bash
fxmacrodata-openbb-api --host 127.0.0.1 --port 6900
```

Equivalent OpenBB command:

```bash
openbb-api --host 127.0.0.1 --port 6900
```

The FXMacroData routes are exposed below `/api/v1/fxmacrodata`.

## 3. Generated OpenBB Workspace Widgets

The OpenBB Platform API can generate Workspace widget definitions from the
installed OpenBB routes. FXMacroData routes include inline `widget_config`
metadata so the generated `/widgets.json` output uses human-readable names,
descriptions, defaults, categories, and table settings.

Run:

```bash
pip install "fxmacrodata[openbb-api]"
openbb-build
fxmacrodata-openbb-api --host 127.0.0.1 --port 6900
```

Then connect OpenBB Workspace to:

```text
http://127.0.0.1:6900
```

This path is best when the user already wants a full OpenBB Platform backend
with all installed extensions available.

## 4. Custom OpenBB Workspace Backend

Install:

```bash
pip install "fxmacrodata[workspace]"
fxmacrodata-openbb-backend
```

Default URL:

```text
http://127.0.0.1:7779
```

Endpoints:

- `/widgets.json`
- `/apps.json`
- `/catalogue`
- `/release_calendar`
- `/macro_indicator`
- `/forex`
- `/cot`
- `/commodity`

Use this path when the team wants only FXMacroData widgets and apps without a
full OpenBB Platform API runtime.

## 5. OpenBB MCP Server

Install:

```bash
pip install "fxmacrodata[mcp]"
openbb-build
```

Run:

```bash
fxmacrodata-openbb-mcp --default-categories fxmacrodata --host 127.0.0.1 --port 8001
```

Equivalent OpenBB command:

```bash
openbb-mcp --default-categories fxmacrodata --host 127.0.0.1 --port 8001
```

The MCP server exposes the installed OpenBB REST routes as MCP tools. The
FXMacroData router includes inline `mcp_config` metadata so these routes are
explicitly exposed as GET tools.

## 6. OpenBB CLI

Install:

```bash
pip install "fxmacrodata[openbb-cli]"
openbb-build
openbb
```

The CLI uses the same OpenBB extension registry. Once built, the `fxmacrodata`
router is available inside the OpenBB CLI environment.

## 7. Upstream OpenBB Repository Contribution

The external package above is the normal independent-extension path. If the goal
is to contribute FXMacroData into `OpenBB-finance/OpenBB`, prepare a separate PR
against OpenBB's `develop` branch with a provider package under:

```text
openbb_platform/providers/fxmacrodata/
```

The expected upstream structure is:

```text
openbb_platform/providers/fxmacrodata/
  README.md
  pyproject.toml
  tests/
  openbb_fxmacrodata/
    __init__.py
    models/
    utils/
```

That PR should reuse the fetcher logic from this SDK, but it must follow
OpenBB's monorepo packaging, lockfile, unit-test, and integration-test process.
Do not open or submit that upstream PR until approved.
