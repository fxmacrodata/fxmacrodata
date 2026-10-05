# Changelog

## 1.2.2 - 2026-10-05

Security and robustness fixes for `Client` and `AsyncClient`. Upgrading is
recommended for everyone using an API key.

### Security

- The API key is no longer sent to a different origin on redirect. Both
  clients now follow redirects themselves: same-origin redirects are followed
  with the key, while a redirect to another host, port or scheme (including
  an HTTPS to HTTP downgrade) raises `FXMacroDataRedirectError` without making
  the request. Previously `requests` and `aiohttp` re-sent the `X-API-Key`
  header to whatever host a redirect named. Keyless (USD) requests still
  follow any HTTP(S) redirect, capped at 5 hops.
- The API key is refused on a plain `http://` base URL unless the host is
  `localhost`, `127.0.0.1` or `::1`.
- The API key never appears in exception messages or tracebacks. A key with
  embedded whitespace or control characters is rejected before any
  request, instead of surfacing the HTTP library's error, which quoted the
  header value. Transport errors and error bodies are redacted, and error
  bodies are truncated to 1,000 characters.
- OpenBB provider: the API key is now always sent in the `X-API-Key` header.
  The provider's default `auth_mode="query"` put the key in the request URL,
  so it appeared in `requests.HTTPError` messages and in the WARNING log line
  written on every failed attempt. `auth_mode` is still accepted but no longer
  changes how the key is sent. The provider also gets the same redirect guard,
  key validation and log redaction, and the Workspace backend maps these
  errors to HTTP 502.

### Added

- `timeout` argument on `Client` and `AsyncClient`, default 30 seconds.
  `Client` accepts a number, a `(connect, read)` tuple or `None`;
  `AsyncClient` accepts a number, an `aiohttp.ClientTimeout` or `None`.
  Previously `Client` had no timeout and `AsyncClient` used aiohttp's
  5-minute default.
- Typed exceptions, all subclasses of `FXMacroDataError`:
  `FXMacroDataAPIError` (non-200 status, with `.status_code`),
  `FXMacroDataResponseError` (HTTP 200 with an error message, non-JSON body
  or a body that is not a JSON object), `FXMacroDataTransportError`,
  `FXMacroDataTimeoutError` and `FXMacroDataRedirectError`.

### Fixed

- An HTTP 200 whose body is HTML, empty, a JSON array/string/null, or an
  `{"error": ...}` / `{"detail": ...}` message now raises
  `FXMacroDataResponseError` instead of a raw `JSONDecodeError` or returning
  the error as data.
- `AsyncClient` network failures and timeouts now raise `FXMacroDataError`
  subclasses instead of raw `aiohttp` / `asyncio` exceptions.
- Leading and trailing whitespace (such as a newline from a key file) is
  stripped from the API key.

### Compatibility

No public signatures were removed or reordered, and `except FXMacroDataError`
still catches every error. Non-200 errors keep the `"<status> - <body>"`
message format. Two behaviour changes to check:

- A request that takes longer than 30 seconds now raises
  `FXMacroDataTimeoutError`. Pass `timeout=None` to restore unlimited waits.
- Code that caught `aiohttp.ClientError` or `asyncio.TimeoutError` from
  `AsyncClient` should catch `FXMacroDataTransportError` instead.
