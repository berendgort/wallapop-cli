"""Process-wide Wallapop politeness: spacing, short TTL cache, ban circuit."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any

from walla.core.exceptions import WallaForbiddenError

__all__ = (
    "CACHE_MAX",
    "CACHE_TTL",
    "CIRCUIT_TTL",
    "MIN_INTERVAL",
    "cache_get",
    "cache_key",
    "cache_set",
    "check_circuit",
    "reset_polite",
    "trip_circuit",
    "wait_turn",
)

MIN_INTERVAL = float(os.environ.get("WALLA_MIN_INTERVAL", "1.0"))
CACHE_TTL = float(os.environ.get("WALLA_CACHE_TTL", "60"))
CIRCUIT_TTL = float(os.environ.get("WALLA_CIRCUIT_TTL", "3600"))
CACHE_MAX = int(os.environ.get("WALLA_CACHE_MAX", "256"))

_lock = threading.Lock()
_last_request_at = 0.0
_circuit_open_until = 0.0
_cache: dict[str, tuple[float, Any]] = {}


def reset_polite() -> None:
    """Clear spacing / cache / circuit (tests)."""
    global _last_request_at, _circuit_open_until, _cache
    with _lock:
        _last_request_at = 0.0
        _circuit_open_until = 0.0
        _cache = {}


def cache_key(base: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"base": base, "params": params}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def cache_get(key: str) -> Any | None:
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires <= now:
            del _cache[key]
            return None
        return value


def cache_set(key: str, value: Any, *, ttl: float | None = None) -> None:
    life = CACHE_TTL if ttl is None else ttl
    with _lock:
        if len(_cache) >= CACHE_MAX:
            now = time.monotonic()
            expired = [k for k, (exp, _) in _cache.items() if exp <= now]
            for k in expired:
                del _cache[k]
            while len(_cache) >= CACHE_MAX:
                _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic() + life, value)


def check_circuit() -> None:
    with _lock:
        open_until = _circuit_open_until
    if open_until and time.monotonic() < open_until:
        raise WallaForbiddenError(
            "Wallapop Forbidden circuit open -- stop requests. "
            "Wait for WALLA_CIRCUIT_TTL or reset_polite().",
            status_code=403,
        )


def trip_circuit(*, ttl: float | None = None) -> None:
    life = CIRCUIT_TTL if ttl is None else ttl
    global _circuit_open_until
    with _lock:
        _circuit_open_until = time.monotonic() + max(life, 0.0)


def wait_turn(*, min_interval: float | None = None) -> None:
    """Serialize dials with a minimum gap (sleep outside the lock)."""
    gap = MIN_INTERVAL if min_interval is None else min_interval
    global _last_request_at
    while True:
        with _lock:
            now = time.monotonic()
            delay = (_last_request_at + gap) - now
            if delay <= 0:
                _last_request_at = now
                return
        time.sleep(delay)
