"""Shared error classification for CLI and MCP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from walla.core.exceptions import (
    WallaAmbiguousError,
    WallaAuthError,
    WallaError,
    WallaForbiddenError,
    WallaHTTPError,
    WallaNotFoundError,
    WallaParseError,
    WallaRateLimitError,
    WallaUnsupportedError,
)

__all__ = (
    "ErrorClassification",
    "classify_error",
)


@dataclass(frozen=True)
class ErrorClassification:
    error_type: str
    retryable: bool
    http_status: int | None = None
    retry_after_s: float | None = None

    def as_fields(self) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "error_type": self.error_type,
            "retryable": self.retryable,
        }
        if self.http_status is not None:
            fields["http_status"] = self.http_status
        if self.retry_after_s is not None:
            fields["retry_after_s"] = self.retry_after_s
        return fields


def classify_error(exc: BaseException) -> ErrorClassification:
    """Map an exception to a stable ``error_type`` + ``retryable`` pair."""
    cause = getattr(exc, "last_attempt", None)
    if cause is not None:
        try:
            inner = cause.exception()
            if inner is not None:
                return classify_error(inner)
        except Exception:  # noqa: BLE001
            pass
    if isinstance(exc, WallaAmbiguousError):
        return ErrorClassification("ambiguous", retryable=False)
    if isinstance(exc, WallaAuthError):
        return ErrorClassification("auth", retryable=False)
    if isinstance(exc, WallaUnsupportedError):
        return ErrorClassification("unsupported", retryable=False)
    if isinstance(exc, WallaNotFoundError):
        return ErrorClassification("not_found", retryable=False)
    if isinstance(exc, WallaParseError):
        return ErrorClassification("parse_error", retryable=False)
    if isinstance(exc, WallaRateLimitError):
        return ErrorClassification(
            "rate_limited",
            retryable=True,
            http_status=exc.status_code,
            retry_after_s=exc.retry_after_s,
        )
    if isinstance(exc, WallaForbiddenError):
        return ErrorClassification(
            "forbidden", retryable=False, http_status=exc.status_code
        )
    if isinstance(exc, WallaHTTPError):
        status = getattr(exc, "status_code", None)
        retryable = status is not None and (status == 429 or status >= 500)
        return ErrorClassification(
            "http_error", retryable=retryable, http_status=status
        )
    if isinstance(exc, TimeoutError):
        return ErrorClassification("timeout", retryable=True)
    if isinstance(exc, ConnectionError | OSError):
        return ErrorClassification("connection_error", retryable=True)
    if isinstance(exc, ValueError):
        return ErrorClassification("validation_error", retryable=False)
    if isinstance(exc, WallaError):
        return ErrorClassification("walla_error", retryable=False)
    return ErrorClassification("unexpected_error", retryable=False)
