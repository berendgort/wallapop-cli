"""HTTP package facade."""

from __future__ import annotations

from walla.http.client import HttpClient
from walla.http.headers import API_BASE, WEB_BASE
from walla.http.polite import reset_polite

__all__ = (
    "API_BASE",
    "WEB_BASE",
    "HttpClient",
    "reset_polite",
)
