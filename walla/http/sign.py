"""Wallapop consumer request signature (edit writes need it)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

__all__ = ("CONSUMER_KEY", "sign_request", "signed_headers")

# Public Wallapop consumer key (base64 of a recruiting toast). Needed for PUT edit.
CONSUMER_KEY = base64.b64decode(
    "Tm93IHRoYXQgeW91J3ZlIGZvdW5kIHRoaXMsIGFyZSB5b3UgcmVhZHkgdG8gam9pbiB1cz8g"
    "am9ic0B3YWxsYXBvcC5jb20="
)


def sign_request(*, method: str, url: str, timestamp_ms: str) -> str:
    """HMAC-SHA256 of ``METHOD|{url}|{timestamp_ms}|``."""
    msg = f"{method.upper()}|{url}|{timestamp_ms}|".encode()
    digest = hmac.new(CONSUMER_KEY, msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def signed_headers(*, method: str, url: str, base: dict[str, str]) -> dict[str, str]:
    """Copy base headers and add X-Signature + Timestamp."""
    ts = str(int(time.time() * 1000))
    out = dict(base)
    out["Timestamp"] = ts
    out["X-Signature"] = sign_request(method=method, url=url, timestamp_ms=ts)
    return out
