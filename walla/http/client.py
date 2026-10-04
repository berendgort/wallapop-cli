"""curl_cffi HTTP client with politeness and retries."""

from __future__ import annotations

import time
from typing import Any, Literal, cast

from curl_cffi import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from walla.core.exceptions import (
    WallaForbiddenError,
    WallaHTTPError,
    WallaRateLimitError,
)
from walla.http.headers import API_BASE, default_headers
from walla.http.polite import (
    cache_get,
    cache_key,
    cache_set,
    check_circuit,
    trip_circuit,
    wait_turn,
)

__all__ = (
    "HttpClient",
    "parse_retry_after",
)

Method = Literal["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE", "PATCH"]


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _retryable_http(exc: BaseException) -> bool:
    if isinstance(exc, WallaForbiddenError):
        return False
    if isinstance(exc, WallaRateLimitError):
        return True
    if isinstance(exc, WallaHTTPError):
        code = exc.status_code or 0
        return code >= 500
    return False


class HttpClient:
    """Thin Wallapop HTTP shell. No import-time network."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        device_id: str | None = None,
        base: str = API_BASE,
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.base = base.rstrip("/")
        self.access_token = access_token
        self.device_id = device_id
        self.cookies = cookies or {}
        self._session: Any = requests.Session()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        use_cache: bool = False,
        auth: bool = False,
    ) -> Any:
        check_circuit()
        params = params or {}
        key = cache_key(f"{method}:{path}", params)
        if use_cache and method.upper() == "GET":
            hit = cache_get(key)
            if hit is not None:
                return hit
        wait_turn()
        headers = default_headers(device_id=self.device_id)
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        url = path if path.startswith("http") else f"{self.base}{path}"
        resp = self._send(method, url, headers=headers, params=params, json_body=json_body)
        data = self._decode(resp)
        if use_cache and method.upper() == "GET":
            cache_set(key, data)
        return data

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    @retry(
        retry=retry_if_exception(_retryable_http),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any],
        json_body: dict[str, Any] | None,
    ) -> Any:
        resp = self._session.request(
            cast(Method, method.upper()),
            url,
            headers=headers,
            params=params or None,
            json=json_body,
            cookies=self.cookies or None,
            impersonate="chrome",
            timeout=30,
        )
        if resp.status_code == 429:
            ra = parse_retry_after(resp.headers.get("Retry-After"))
            if ra:
                time.sleep(ra)
            raise WallaRateLimitError(
                "Wallapop rate limited (429)",
                retry_after_s=ra,
            )
        if resp.status_code == 403:
            trip_circuit()
            raise WallaForbiddenError(
                "Wallapop Forbidden (403) -- circuit open",
                status_code=403,
            )
        if resp.status_code >= 500:
            raise WallaHTTPError(
                f"Wallapop server error {resp.status_code}",
                status_code=resp.status_code,
            )
        return resp

    def _decode(self, resp: Any) -> Any:
        if resp.status_code in (200, 201, 204):
            if not resp.content:
                return {}
            try:
                return cast(Any, resp.json())
            except Exception as exc:
                raise WallaHTTPError(
                    f"Invalid JSON ({resp.status_code})",
                    status_code=resp.status_code,
                ) from exc
        body = (resp.text or "")[:300]
        raise WallaHTTPError(
            f"HTTP {resp.status_code}: {body}",
            status_code=resp.status_code,
        )
