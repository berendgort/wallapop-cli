"""Login: password attempt + NextAuth cookie mint."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

from curl_cffi import requests

from walla.account.cookies import SESSION_COOKIE, parse_cookie_export
from walla.account.session_store import load_session, save_session
from walla.core.dotenv import load_credentials
from walla.core.exceptions import WallaAuthError, WallaHTTPError
from walla.http.headers import WEB_BASE, default_headers, new_device_id
from walla.http.polite import wait_turn
from walla.models.account import SessionData

__all__ = (
    "login_cookies",
    "login_password",
    "mint_access_token",
    "refresh_session",
    "whoami",
)


def login_password(*, username: str | None = None, password: str | None = None) -> SessionData:
    """Try ``POST /api/v3/access/login``. Raises ``WallaAuthError`` on MFA/empty 400."""
    user, pw = load_credentials()
    user = username or user
    pw = password or pw
    if not user or not pw:
        raise WallaAuthError(
            "WALLAPOP_USER / WALLAPOP_PW not set. Put them in .env or pass credentials."
        )
    device = new_device_id()
    wait_turn()
    headers = default_headers(device_id=device)
    headers["Content-Type"] = "application/json"
    resp = requests.post(
        "https://api.wallapop.com/api/v3/access/login",
        json={"username": user, "password": pw},
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )
    if resp.status_code != 200 or not resp.content:
        raise WallaAuthError(
            f"Password login failed (HTTP {resp.status_code}). "
            "Likely MFA / Keycloak. Export cookies instead."
        )
    body = cast(Any, resp.json())  # type: ignore[no-untyped-call]
    data = body.get("data") if isinstance(body, dict) else body
    token_block = data.get("token", data) if isinstance(data, dict) else {}
    access = (
        token_block.get("access_token")
        or token_block.get("accessToken")
        or (data or {}).get("access_token")
    )
    refresh = token_block.get("refresh_token") or token_block.get("refreshToken")
    if not access:
        raise WallaAuthError("Password login returned no access token. Export cookies.")
    session = SessionData(
        access_token=str(access),
        refresh_token=str(refresh) if refresh else None,
        device_id=device,
        expires_at=time.time() + 300,
    )
    save_session(session)
    return session


def login_cookies(path: Path) -> SessionData:
    cookie, device = parse_cookie_export(path)
    device = device or new_device_id()
    session = SessionData(session_cookie=cookie, device_id=device)
    token, exp = mint_access_token(session)
    session.access_token = token
    session.expires_at = exp
    save_session(session)
    return session


def mint_access_token(session: SessionData) -> tuple[str, float]:
    """Mint a short-lived Bearer from the NextAuth session cookie."""
    if not session.session_cookie:
        if session.access_token:
            return session.access_token, session.expires_at or (time.time() + 240)
        raise WallaAuthError("No session cookie or access token")
    wait_turn()
    headers = default_headers(device_id=session.device_id)
    headers["Cookie"] = f"{SESSION_COOKIE}={session.session_cookie}"
    resp = requests.get(
        f"{WEB_BASE}/api/auth/session",
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )
    if resp.status_code != 200:
        raise WallaAuthError(f"Session mint failed (HTTP {resp.status_code})")
    data = cast(Any, resp.json()) if resp.content else {}  # type: ignore[no-untyped-call]
    token = data.get("token") if isinstance(data, dict) else None
    if not token:
        raise WallaAuthError("Stored session is no longer valid. Re-export cookies.")
    # Rotate cookie if Set-Cookie present
    for ck in resp.cookies.jar if hasattr(resp.cookies, "jar") else []:
        if getattr(ck, "name", None) == SESSION_COOKIE and ck.value:
            session.session_cookie = ck.value
    exp = time.time() + 240
    return str(token), exp


def refresh_session(session: SessionData | None = None) -> SessionData:
    sess = session or load_session()
    if sess is None:
        raise WallaAuthError("No session. Run walla login.")
    if sess.session_cookie:
        token, exp = mint_access_token(sess)
        sess.access_token = token
        sess.expires_at = exp
        save_session(sess)
        return sess
    if sess.refresh_token:
        wait_turn()
        headers = default_headers(device_id=sess.device_id)
        headers["Content-Type"] = "application/json"
        resp = requests.post(
            "https://api.wallapop.com/api/v3/access/refresh",
            json={"refresh_token": sess.refresh_token},
            headers=headers,
            impersonate="chrome",
            timeout=30,
        )
        if resp.status_code != 200:
            raise WallaAuthError(f"Refresh failed (HTTP {resp.status_code})")
        body = cast(Any, resp.json())  # type: ignore[no-untyped-call]
        data = body.get("data") if isinstance(body, dict) else body
        token_block = data.get("token", data) if isinstance(data, dict) else {}
        access = token_block.get("access_token") or token_block.get("accessToken")
        if not access:
            raise WallaAuthError("Refresh returned no access token")
        sess.access_token = str(access)
        new_refresh = token_block.get("refresh_token") or token_block.get("refreshToken")
        if new_refresh:
            sess.refresh_token = str(new_refresh)
        sess.expires_at = time.time() + 300
        save_session(sess)
        return sess
    raise WallaAuthError("Session has neither cookie nor refresh token")


def ensure_access_token() -> SessionData:
    sess = load_session()
    if sess is None:
        # try password from env
        try:
            return login_password()
        except WallaAuthError:
            raise WallaAuthError(
                "No session. Set WALLAPOP_USER/WALLAPOP_PW and run walla login, "
                "or walla login --cookies <file>."
            ) from None
    if sess.expires_at and sess.expires_at > time.time() + 30 and sess.access_token:
        return sess
    return refresh_session(sess)


def whoami(*, client_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return account label without secrets."""
    sess = ensure_access_token()
    if client_data:
        return client_data
    wait_turn()
    headers = default_headers(device_id=sess.device_id)
    headers["Authorization"] = f"Bearer {sess.access_token}"
    resp = requests.get(
        "https://api.wallapop.com/api/v3/users/me",
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )
    if resp.status_code == 404:
        # fallback minimal
        return {
            "user_id": sess.user_id,
            "micro_name": sess.micro_name,
            "authenticated": True,
        }
    if resp.status_code != 200:
        raise WallaHTTPError(
            f"whoami failed (HTTP {resp.status_code})",
            status_code=resp.status_code,
        )
    data = cast(Any, resp.json())  # type: ignore[no-untyped-call]
    user = data.get("data") if isinstance(data.get("data"), dict) else data
    micro = user.get("micro_name") or user.get("microName")
    uid = user.get("id") or user.get("user_id")
    sess.micro_name = str(micro) if micro else sess.micro_name
    sess.user_id = str(uid) if uid else sess.user_id
    save_session(sess)
    return {
        "user_id": sess.user_id,
        "micro_name": sess.micro_name,
        "authenticated": True,
    }
