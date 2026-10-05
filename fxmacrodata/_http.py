"""Request hardening shared by Client and AsyncClient.

The clients follow redirects by hand so the API key is only ever re-sent to
the origin it was first sent to, never echo the key in error text, and turn
every malformed response into a typed FXMacroDataError.
"""

import re
from typing import Any, Optional, Tuple
from urllib.parse import urljoin, urlsplit

from .exceptions import (
    FXMacroDataAPIError,
    FXMacroDataError,
    FXMacroDataRedirectError,
    FXMacroDataResponseError,
)

API_KEY_HEADER = "X-API-Key"

# Seconds. Generous enough for multi-year history requests, short enough that
# a stalled connection cannot hang a job forever.
DEFAULT_TIMEOUT = 30.0

MAX_REDIRECTS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

_BODY_PREVIEW_CHARS = 1000
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_VALID_KEY = re.compile(r"[\x21-\x7e]+")
_REDACTED = "***"


def clean_api_key(api_key: Optional[str]) -> str:
    """Return the key without surrounding whitespace, or "" when unset.

    A key copied from a file or shell often carries a trailing newline; strip
    it. Anything still outside printable ASCII would make the HTTP library
    raise an error that quotes the header value, so reject it here with a
    message that does not contain the key.
    """
    if api_key is None:
        return ""
    if not isinstance(api_key, str):
        raise FXMacroDataError("API key must be a string.")
    key = api_key.strip()
    if key and not _VALID_KEY.fullmatch(key):
        raise FXMacroDataError(
            "API key contains spaces or non-printable characters. "
            "Check it was copied correctly."
        )
    return key


def redact(text: str, api_key: Optional[str]) -> str:
    """Remove the API key from text that may end up in an exception."""
    if api_key:
        text = text.replace(api_key, _REDACTED)
        stripped = api_key.strip()
        if stripped:
            text = text.replace(stripped, _REDACTED)
    return text


def _origin(url: str) -> Tuple[str, str, Optional[int]]:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    try:
        port = parts.port
    except ValueError:
        port = None
    if port is None:
        port = {"https": 443, "http": 80}.get(scheme)
    return scheme, (parts.hostname or "").lower(), port


def _display_origin(url: str) -> str:
    scheme, host, _ = _origin(url)
    return f"{scheme}://{host}" if scheme else host


def check_transport(url: str, has_key: bool) -> None:
    """Refuse to put the API key on a plain-HTTP request to a remote host."""
    scheme, host, _ = _origin(url)
    if scheme not in ("http", "https"):
        raise FXMacroDataError(f"Unsupported URL scheme: {scheme or '(none)'}")
    if has_key and scheme != "https" and host not in _LOOPBACK_HOSTS:
        raise FXMacroDataError(
            f"Refusing to send the API key over plain HTTP to {host}. "
            "Use an https:// base URL."
        )


def resolve_redirect(current_url: str, location: str, has_key: bool) -> str:
    """Return the redirect target, or raise if following it could leak the key.

    With a key attached, only same-origin redirects (same scheme, host and
    port) are followed, so neither a different host nor an https -> http
    downgrade ever receives the key. Keyless requests follow any http(s)
    redirect.
    """
    target = urljoin(current_url, location)
    if has_key and _origin(target) != _origin(current_url):
        raise FXMacroDataRedirectError(
            f"Refused redirect from {_display_origin(current_url)} to "
            f"{_display_origin(target)}: following it would send the API key "
            "to a different origin."
        )
    check_transport(target, has_key)
    return target


def too_many_redirects() -> FXMacroDataRedirectError:
    return FXMacroDataRedirectError(f"Too many redirects (more than {MAX_REDIRECTS}).")


def api_error(status: int, body: str, api_key: Optional[str]) -> FXMacroDataAPIError:
    """Build the error for a non-200 response ("<status> - <body>")."""
    body = redact(body or "", api_key)
    if len(body) > _BODY_PREVIEW_CHARS:
        body = body[:_BODY_PREVIEW_CHARS] + "..."
    return FXMacroDataAPIError(f"{status} - {body}", status_code=status)


def invalid_json_error(
    status: int, content_type: Optional[str]
) -> FXMacroDataResponseError:
    return FXMacroDataResponseError(
        f"API returned HTTP {status} with a body that is not valid JSON "
        f"(content type: {content_type or 'unknown'}).",
        status_code=status,
    )


def check_payload(data: Any, status: int, api_key: Optional[str]) -> dict:
    """Return the decoded body if it is a successful JSON object, else raise."""
    if not isinstance(data, dict):
        raise FXMacroDataResponseError(
            "Unexpected response from the API: expected a JSON object, "
            f"got {type(data).__name__}.",
            status_code=status,
        )
    if "data" not in data:
        # Error bodies carry a string message; real payloads never put a bare
        # string under these keys (catalogue entries are objects).
        for field in ("error", "detail"):
            message = data.get(field)
            if isinstance(message, str):
                raise FXMacroDataResponseError(
                    f"API returned an error with HTTP {status}: "
                    f"{redact(message, api_key)}",
                    status_code=status,
                )
    return data
