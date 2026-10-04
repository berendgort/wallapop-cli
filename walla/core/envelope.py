"""Shared JSON envelope for CLI and MCP (agent contract)."""

from __future__ import annotations

from typing import Any

from walla.core.errors import classify_error
from walla.core.exceptions import WallaAmbiguousError, WallaAuthError

__all__ = (
    "API_VERSION",
    "dump_model",
    "error_payload",
    "success_payload",
)

API_VERSION = 1


def success_payload(data: Any) -> dict[str, Any]:
    return {"ok": True, "api_version": API_VERSION, "data": data}


def error_payload(exc: BaseException) -> dict[str, Any]:
    classified = classify_error(exc)
    payload: dict[str, Any] = {
        "ok": False,
        "api_version": API_VERSION,
        "error": str(exc),
        **classified.as_fields(),
    }
    if isinstance(exc, WallaAmbiguousError):
        payload["candidates"] = [
            c.model_dump(mode="json") if hasattr(c, "model_dump") else c
            for c in exc.candidates
        ]
    if isinstance(exc, WallaAuthError):
        from walla.core.human_fix import cookie_export_fix

        payload["human_fix"] = cookie_export_fix()
    return payload


def dump_model(model: Any) -> Any:
    """Pydantic model to JSON-ready dict."""
    return model.model_dump(mode="json")
