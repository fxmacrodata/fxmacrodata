from typing import Optional


class FXMacroDataError(Exception):
    """Custom exception for FXMacroData client errors.

    Every error the clients raise is this class or a subclass of it, so
    ``except FXMacroDataError`` keeps catching everything.
    """

    pass


class FXMacroDataAPIError(FXMacroDataError):
    """The API answered with a non-200 HTTP status."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class FXMacroDataResponseError(FXMacroDataError):
    """The API answered 200 but the body was an error or not a JSON object."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class FXMacroDataTransportError(FXMacroDataError):
    """The request could not be completed (connection, DNS, TLS, ...)."""

    pass


class FXMacroDataTimeoutError(FXMacroDataTransportError):
    """The request exceeded the client's timeout."""

    pass


class FXMacroDataRedirectError(FXMacroDataError):
    """A redirect was refused because following it could expose the API key."""

    pass
