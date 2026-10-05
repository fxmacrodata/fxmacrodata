"""Shared HTTP helpers for the FXMacroData OpenBB provider."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Mapping, Optional

import requests

from fxmacrodata import _http
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


def _get_with_safe_redirects(
    url: str,
    params: Optional[Dict[str, Any]],
    headers: Dict[str, str],
    timeout: Any,
) -> requests.Response:
    """GET that only re-sends the API key on same-origin redirects."""
    has_key = bool(headers)
    _http.check_transport(url, has_key)
    for _ in range(_http.MAX_REDIRECTS + 1):
        resp = requests.get(
            url,
            params=params,
            headers=headers or None,
            timeout=timeout,
            allow_redirects=False,
        )
        location = resp.headers.get("Location")
        if resp.status_code in _http.REDIRECT_STATUSES and location:
            url = _http.resolve_redirect(url, location, has_key)
            params = None  # the Location already carries the query string
            continue
        return resp
    raise _http.too_many_redirects()


def _sync_request(
    url: str,
    params: Dict[str, Any],
    api_key: Optional[str] = None,
    auth_mode: str = "header",
    retry_count: int = _DEFAULT_RETRY_COUNT,
    pause: float = _DEFAULT_RETRY_PAUSE,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """Blocking GET request with simple retry logic.

    The API key is always sent in the ``X-API-Key`` header. ``auth_mode`` is
    accepted for backward compatibility only: the old ``"query"`` mode put the
    key in the URL, where it surfaced in exception messages and logs.
    """
    if retry_count < 1:
        raise ValueError(f"retry_count must be >= 1, got {retry_count}")

    clean_params: Dict[str, Any] = {k: v for k, v in params.items() if v is not None}
    api_key = _http.clean_api_key(api_key)
    headers: Dict[str, str] = {_http.API_KEY_HEADER: api_key} if api_key else {}

    last_exc: Optional[requests.RequestException] = None
    for attempt in range(retry_count):
        if attempt > 0:
            time.sleep(pause)
        try:
            resp = _get_with_safe_redirects(url, clean_params, headers, timeout)
            resp.raise_for_status()
            try:
                payload = resp.json()
            except ValueError:
                raise _http.invalid_json_error(
                    resp.status_code, resp.headers.get("Content-Type")
                ) from None
            return _http.check_payload(payload, resp.status_code, api_key)
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "FXMacroData request failed (attempt %d/%d): %s - %s",
                attempt + 1,
                retry_count,
                url,
                _http.redact(str(exc), api_key),
            )
    raise last_exc  # type: ignore[misc]


async def get_json(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    auth_mode: str = "header",
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
