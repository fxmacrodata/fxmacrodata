"""Shared HTTP helpers for the FXMacroData OpenBB provider."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Mapping, Optional

import requests

from fxmacrodata.openbb.constants import DEFAULT_BASE_URL

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30
_DEFAULT_RETRY_COUNT = 3
_DEFAULT_RETRY_PAUSE = 0.1

_CREDENTIAL_KEYS = (
    "fxmacrodata_api_key",
    "api_key",
    "FXMACRODATA_API_KEY",
    "FXMD_API_KEY",
)
_ENV_KEYS = ("FXMACRODATA_API_KEY", "FXMD_API_KEY")


def get_base_url() -> str:
    """Return the API base URL, honouring the FXMACRODATA_BASE_URL env var."""
    return os.environ.get("FXMACRODATA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def resolve_api_key(credentials: Optional[Mapping[str, str]]) -> Optional[str]:
    """Resolve an FXMacroData API key from OpenBB credentials or env vars."""
    if credentials:
        for key in _CREDENTIAL_KEYS:
            value = credentials.get(key)
            if value:
                return value
    for key in _ENV_KEYS:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _sync_request(
    url: str,
    params: Dict[str, Any],
    api_key: Optional[str] = None,
    auth_mode: str = "query",
    retry_count: int = _DEFAULT_RETRY_COUNT,
    pause: float = _DEFAULT_RETRY_PAUSE,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """Blocking GET request with simple retry logic."""
    if retry_count < 1:
        raise ValueError(f"retry_count must be >= 1, got {retry_count}")

    clean_params: Dict[str, Any] = {k: v for k, v in params.items() if v is not None}
    headers: Dict[str, str] = {}
    if api_key:
        if auth_mode == "header":
            headers["X-API-Key"] = api_key
        else:
            clean_params["api_key"] = api_key

    last_exc: Optional[requests.RequestException] = None
    for attempt in range(retry_count):
        if attempt > 0:
            time.sleep(pause)
        try:
            resp = requests.get(
                url,
                params=clean_params,
                headers=headers or None,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "FXMacroData request failed (attempt %d/%d): %s - %s",
                attempt + 1,
                retry_count,
                url,
                exc,
            )
    raise last_exc  # type: ignore[misc]


async def get_json(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    auth_mode: str = "query",
    retry_count: int = _DEFAULT_RETRY_COUNT,
    pause: float = _DEFAULT_RETRY_PAUSE,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """Async GET to the FXMacroData API, returning the full JSON payload."""
    url = f"{get_base_url()}{path}"
    return await asyncio.to_thread(
        _sync_request,
        url,
        params or {},
        api_key,
        auth_mode,
        retry_count,
        pause,
        timeout,
    )


async def get_data(
    path: str,
    params: Dict[str, Any],
    api_key: Optional[str],
    retry_count: int = _DEFAULT_RETRY_COUNT,
    pause: float = _DEFAULT_RETRY_PAUSE,
    timeout: int = _DEFAULT_TIMEOUT,
) -> list:
    """Async GET to the FXMacroData API, returning the ``data`` array."""
    response = await get_json(
        path,
        params=params,
        api_key=api_key,
        retry_count=retry_count,
        pause=pause,
        timeout=timeout,
    )
    return response.get("data", [])
