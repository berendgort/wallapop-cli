"""Shared walla error types (foundation -- importable by http + core)."""

from __future__ import annotations

from typing import Any

__all__ = (
    "WallaAmbiguousError",
    "WallaAuthError",
    "WallaError",
    "WallaForbiddenError",
    "WallaHTTPError",
    "WallaNotFoundError",
    "WallaParseError",
    "WallaRateLimitError",
    "WallaUnsupportedError",
)


class WallaError(Exception):
    """Base."""


class WallaHTTPError(WallaError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WallaRateLimitError(WallaHTTPError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.retry_after_s = retry_after_s


class WallaAuthError(WallaError):
    """Missing or rejected credentials / session."""


class WallaForbiddenError(WallaHTTPError):
    """Hard stop (403 circuit)."""


class WallaParseError(WallaError):
    pass


class WallaNotFoundError(WallaError):
    pass


class WallaUnsupportedError(WallaError):
    """Wire shape not captured yet."""


class WallaAmbiguousError(WallaError):
    """Multiple listings matched; caller must pick an id."""

    def __init__(self, message: str, *, candidates: list[Any]) -> None:
        super().__init__(message)
        self.candidates = candidates
