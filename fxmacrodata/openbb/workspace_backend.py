"""OpenBB Workspace custom backend for FXMacroData.

Run locally:

    uvicorn fxmacrodata.openbb.workspace_backend:app --host 0.0.0.0 --port 7779
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from requests import HTTPError

from fxmacrodata.openbb.metadata import (
    APP_IMAGE_FILENAMES,
    app_image_svg,
    workspace_apps_json,
    workspace_widgets_json,
)
from fxmacrodata.openbb.utils.catalogue import flatten_catalogue_payload
from fxmacrodata.openbb.utils.datetimes import (
    OPENBB_DATETIME_SOURCE_FIELDS,
    as_utc,
    row_announcement_datetime,
    row_announcement_datetime_text,
)
from fxmacrodata.openbb.utils.helpers import get_json

APP_TITLE = "FXMacroData OpenBB Backend"
try:
    APP_VERSION = version("fxmacrodata")
except PackageNotFoundError:
    APP_VERSION = "1.2.1"
ENABLE_DOCS = os.environ.get("FXMACRODATA_OPENBB_ENABLE_DOCS", "").lower() in {
    "1",
    "true",
    "yes",
}

app = FastAPI(
    title=APP_TITLE,
    description="OpenBB Workspace widgets and apps backed by FXMacroData.",
    version=APP_VERSION,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pro.openbb.co",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _date_param(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _api_key_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return (
        request.headers.get("x-api-key")
        or request.headers.get("x-fxmd-api-key")
        or request.query_params.get("api_key")
    )


async def _proxy_json(
    request: Request,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        return await get_json(
            path,
            params=params or {},
            api_key=_api_key_from_request(request),
            auth_mode="header",
        )
    except HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        detail = "FXMacroData request failed"
        if exc.response is not None:
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text
        raise HTTPException(status_code=status_code, detail=detail) from exc


def _rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data", [])
    return data if isinstance(data, list) else []


def _release_datetime(row: Dict[str, Any]) -> Optional[datetime]:
    return row_announcement_datetime(row)


def _format_time_utc(value: datetime) -> str:
    dt = as_utc(value)
    if dt is None:
        dt = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return dt.strftime("%H:%M")


def _release_name(row: Dict[str, Any]) -> str:
    release = row.get("release") or row.get("indicator") or row.get("name")
    if not isinstance(release, str):
        return ""
    return release


def _catalogue_display_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    display_rows: List[Dict[str, Any]] = []
    for row in rows:
        display_rows.append(
            {
                "indicator": row.get("indicator"),
                "name": row.get("name"),
                "frequency": row.get("frequency"),
                "source": row.get("source"),
                "latest": row.get("latest_available_date"),
                "observations": row.get("row_count"),
                "coverage": row.get("coverage_quality"),
                "access": "Paid" if row.get("requires_api_key") else "Free",
            }
        )
    return display_rows


_ANNOUNCEMENT_SOURCE_FIELDS = OPENBB_DATETIME_SOURCE_FIELDS


def _announcement_display_rows(
    rows: List[Dict[str, Any]],
    *,
    date_label: str,
) -> List[Dict[str, Any]]:
    return [_announcement_display_row(row, date_label=date_label) for row in rows]


def _announcement_display_row(
    row: Dict[str, Any],
    *,
    date_label: str,
) -> Dict[str, Any]:
    display_row: Dict[str, Any] = {}
    announcement_datetime = row_announcement_datetime_text(row)
    if announcement_datetime:
        display_row["announcement_datetime"] = announcement_datetime
    if "announcement_id" in row:
        display_row["announcement_id"] = row.get("announcement_id")
    if row.get("date") is not None and date_label not in row:
        display_row[date_label] = row.get("date")
    elif row.get("date") is not None:
        display_row[date_label] = row.get("date")

    for key, value in row.items():
        if key in display_row:
            continue
        if key in _ANNOUNCEMENT_SOURCE_FIELDS:
            continue
        if key == "date":
            continue
        if key == "announcement_datetime":
            if announcement_datetime:
                continue
            value = str(value)
        display_row[key] = value
    return display_row


def _human_datetime_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalised_rows: List[Dict[str, Any]] = []
    for row in rows:
        display_row = dict(row)
        announcement_datetime = row_announcement_datetime_text(row)
        if announcement_datetime:
            display_row["announcement_datetime"] = announcement_datetime
            for field in OPENBB_DATETIME_SOURCE_FIELDS:
                display_row.pop(field, None)
        normalised_rows.append(display_row)
    return normalised_rows


def _release_category(release: str) -> str:
    slug = release.lower()
    if any(term in slug for term in ("inflation", "ppi", "pce", "price")):
        return "Prices"
    if any(
        term in slug
        for term in ("payroll", "employment", "unemployment", "jobless", "jobs")
    ):
        return "Labour"
    if any(term in slug for term in ("gdp", "retail", "sales", "confidence")):
        return "Activity"
    if any(term in slug for term in ("rate", "central_bank", "policy")):
        return "Policy"
    return "Other"


def _normalise_calendar_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalised: List[Dict[str, Any]] = []
    for row in rows:
        release = _release_name(row)
        confirmed = (
            row.get("release_date_confirmed")
            if "release_date_confirmed" in row
            else row.get("confirmed")
        )
        normalised.append(
            {
                "announcement_datetime": row_announcement_datetime_text(row)
                or row.get("release_datetime")
                or row.get("release_date"),
                "event": release,
                "name": row.get("name") or release.replace("_", " ").title(),
                "source": row.get("source"),
                "status": "Confirmed" if confirmed else "Tentative",
            }
        )
    return normalised


def _calendar_timeline_figure(
    rows: List[Dict[str, Any]],
    currency: str,
    indicator: Optional[str],
) -> Dict[str, Any]:
    date_category_counts: Dict[str, Counter[str]] = defaultdict(Counter)
    events_by_date_category: Dict[str, Dict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        dt = _release_datetime(row)
        if dt is None:
            continue
        row_date = dt.date().isoformat()
        time_utc = _format_time_utc(dt)
        release = _release_name(row) or "release"
        category = _release_category(release)
        date_category_counts[row_date][category] += 1
        events_by_date_category[row_date][category].append(
            f"{time_utc} UTC - {release}"
        )

    dates = sorted(date_category_counts)
    title = f"{currency.upper()} macro release radar"
    if indicator:
        title = f"{currency.upper()} {indicator} release radar"

    categories = ["Prices", "Labour", "Activity", "Policy", "Other"]
    category_colors = {
        "Prices": "#14b8a6",
        "Labour": "#38bdf8",
        "Activity": "#f59e0b",
        "Policy": "#a78bfa",
        "Other": "#94a3b8",
    }
    traces = []
    for category in categories:
        values = [date_category_counts[item][category] for item in dates]
        if not any(values):
            continue
        traces.append(
            {
                "type": "bar",
                "x": dates,
                "y": values,
                "marker": {"color": category_colors[category]},
                "hovertext": [
                    "<br>".join(events_by_date_category[item][category][:8])
                    for item in dates
                ],
                "hoverinfo": "text+y",
                "name": category,
            }
        )

    if not traces:
        traces = [
            {
                "type": "scatter",
                "x": [],
                "y": [],
                "mode": "markers",
                "name": "No releases",
            }
        ]

    return {
        "data": traces,
        "layout": {
            "title": {
                "text": title,
                "x": 0.02,
                "xanchor": "left",
                "font": {"size": 22, "color": "#f8fafc"},
            },
            "template": "plotly_dark",
            "barmode": "stack",
            "bargap": 0.18,
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#dbe4ef"},
            "legend": {
                "orientation": "h",
                "x": 0.02,
                "y": 1.08,
                "xanchor": "left",
                "font": {"size": 12},
            },
            "margin": {"l": 48, "r": 24, "t": 74, "b": 50},
            "xaxis": {
                "title": "",
                "tickformat": "%b %d",
                "gridcolor": "rgba(148,163,184,0.12)",
                "zeroline": False,
            },
            "yaxis": {
                "title": "release count",
                "dtick": 1,
                "gridcolor": "rgba(148,163,184,0.16)",
                "zeroline": False,
            },
        },
    }


def _widgets_json() -> Dict[str, Dict[str, Any]]:
    return workspace_widgets_json()


def _apps_json(request: Optional[Request] = None) -> List[Dict[str, Any]]:
    image_base_url = None
    if request is not None:
        image_base_url = f"{str(request.base_url).rstrip('/')}/assets/openbb-apps"
    return workspace_apps_json(image_base_url=image_base_url)


@app.get("/")
def root() -> Dict[str, str]:
    """Backend metadata."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "widgets": "/widgets.json",
        "apps": "/apps.json",
    }


@app.get("/health")
def health() -> Dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


@app.get("/widgets.json")
def widgets_json() -> JSONResponse:
    """Return OpenBB Workspace widget definitions."""
    return JSONResponse(content=_widgets_json())


@app.get("/apps.json")
def apps_json(request: Request) -> JSONResponse:
    """Return OpenBB Workspace app definitions."""
    return JSONResponse(content=_apps_json(request))


@app.get("/assets/openbb-apps/{filename}", include_in_schema=False)
def app_image_asset(filename: str) -> Response:
    """Serve self-contained SVG preview images for OpenBB Workspace app cards."""
    if filename not in APP_IMAGE_FILENAMES.values():
        raise HTTPException(status_code=404, detail="App image not found")
    return Response(
        content=app_image_svg(filename),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/catalogue")
async def catalogue(
    request: Request,
    currency: str = "USD",
    indicator: Optional[str] = None,
    include_coverage: bool = True,
    include_capabilities: bool = False,
) -> List[Dict[str, Any]]:
    """Return flattened indicator catalogue rows."""
    payload = await _proxy_json(
        request,
        f"/v1/data_catalogue/{currency.lower()}",
        {
            "include_coverage": include_coverage,
            "include_capabilities": include_capabilities,
            "indicator": indicator.lower() if indicator else None,
        },
    )
    return _catalogue_display_rows(flatten_catalogue_payload(payload))


@app.get("/release_calendar")
async def release_calendar(
    request: Request,
    currency: str = "USD",
    indicator: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return release-calendar rows."""
    payload = await _proxy_json(
        request,
        f"/v1/calendar/{currency.lower()}",
        {"indicator": indicator.lower() if indicator else None},
    )
    return _normalise_calendar_rows(_rows(payload))


@app.get("/release_calendar_timeline")
async def release_calendar_timeline(
    request: Request,
    currency: str = "USD",
    indicator: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a Plotly timeline of upcoming release-calendar rows."""
    payload = await _proxy_json(
        request,
        f"/v1/calendar/{currency.lower()}",
        {"indicator": indicator.lower() if indicator else None},
    )
    return _calendar_timeline_figure(_rows(payload), currency, indicator)


@app.get("/macro_indicator")
async def macro_indicator(
    request: Request,
    currency: str,
    indicator: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return macro indicator history rows."""
    path = f"/v1/announcements/{currency.lower()}/{indicator.lower()}"
    params = {"start_date": _date_param(start_date), "end_date": _date_param(end_date)}
    try:
        payload = await _proxy_json(request, path, params)
    except HTTPException as exc:
        detail: Dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {}
        if isinstance(detail.get("detail"), dict):
            detail = detail["detail"]
        can_retry = (
            detail.get("error_code") == "NO_DATA_IN_REQUESTED_WINDOW"
            and start_date is not None
            and end_date is not None
            and start_date == end_date
            and detail.get("recommended_start_date")
            and detail.get("latest_available_date")
        )
        if not can_retry:
            raise
        payload = await _proxy_json(
            request,
            path,
            {
                "start_date": detail["recommended_start_date"],
                "end_date": detail["latest_available_date"],
            },
        )
    return _announcement_display_rows(_rows(payload), date_label="observation_date")


@app.get("/forex")
async def forex(
    request: Request,
    base: str,
    quote: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return FX spot-rate history rows."""
    payload = await _proxy_json(
        request,
        f"/v1/forex/{base.lower()}/{quote.lower()}",
        {"start_date": _date_param(start_date), "end_date": _date_param(end_date)},
    )
    return _human_datetime_rows(_rows(payload))


@app.get("/cot")
async def cot(
    request: Request,
    currency: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return COT positioning rows."""
    payload = await _proxy_json(
        request,
        f"/v1/cot/{currency.lower()}",
        {"start_date": _date_param(start_date), "end_date": _date_param(end_date)},
    )
    return _announcement_display_rows(_rows(payload), date_label="report_date")


@app.get("/commodity")
async def commodity(
    request: Request,
    indicator: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return commodity price history rows."""
    payload = await _proxy_json(
        request,
        f"/v1/commodities/{indicator.lower()}",
        {"start_date": _date_param(start_date), "end_date": _date_param(end_date)},
    )
    return _human_datetime_rows(_rows(payload))


def main() -> None:
    """Run the Workspace backend with uvicorn."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7779)


if __name__ == "__main__":
    main()
