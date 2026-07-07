"""OpenBB Workspace custom backend for FXMacroData.

Run locally:

    uvicorn fxmacrodata.openbb.workspace_backend:app --host 0.0.0.0 --port 7779
"""

from __future__ import annotations

from datetime import date
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from requests import HTTPError

from fxmacrodata.openbb.metadata import workspace_apps_json, workspace_widgets_json
from fxmacrodata.openbb.utils.catalogue import flatten_catalogue_payload
from fxmacrodata.openbb.utils.helpers import get_json

APP_TITLE = "FXMacroData OpenBB Backend"
APP_VERSION = "0.1.0"
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


def _widgets_json() -> Dict[str, Dict[str, Any]]:
    return workspace_widgets_json()


def _apps_json() -> List[Dict[str, Any]]:
    return workspace_apps_json()


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
def apps_json() -> JSONResponse:
    """Return OpenBB Workspace app definitions."""
    return JSONResponse(content=_apps_json())


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
    return flatten_catalogue_payload(payload)


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
    return _rows(payload)


@app.get("/macro_indicator")
async def macro_indicator(
    request: Request,
    currency: str,
    indicator: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Return macro indicator history rows."""
    payload = await _proxy_json(
        request,
        f"/v1/announcements/{currency.lower()}/{indicator.lower()}",
        {"start_date": _date_param(start_date), "end_date": _date_param(end_date)},
    )
    return _rows(payload)


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
    return _rows(payload)


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
    return _rows(payload)


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
    return _rows(payload)


def main() -> None:
    """Run the Workspace backend with uvicorn."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7779)


if __name__ == "__main__":
    main()
