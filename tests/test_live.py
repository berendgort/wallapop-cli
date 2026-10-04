"""Live Wallapop probes (opt-in: pytest -m live)."""

from __future__ import annotations

import os

import pytest

from walla.http.client import HttpClient
from walla.http.polite import reset_polite
from walla.search.api import get_categories, get_item, search_listings

pytestmark = pytest.mark.live


def test_live_search_item_categories() -> None:
    reset_polite()
    cats = get_categories()
    assert cats
    result = search_listings(
        "bicicleta", latitude=41.3874, longitude=2.1686, max_results=5
    )
    assert result.count >= 1
    item = get_item(result.listings[0].id)
    assert item.id == result.listings[0].id


def test_live_login_password_or_skip() -> None:
    """Password login often returns empty 400 (MFA). Document outcome."""
    from walla.account.login import login_password
    from walla.core.dotenv import load_dotenv_files
    from walla.core.exceptions import WallaAuthError

    load_dotenv_files()
    if not os.environ.get("WALLAPOP_USER") or not os.environ.get("WALLAPOP_PW"):
        pytest.skip("no credentials")
    reset_polite()
    try:
        sess = login_password()
        assert sess.access_token
    except WallaAuthError as exc:
        # Expected for many accounts; cookie path is the fallback.
        assert "Password login failed" in str(exc) or "no access token" in str(exc)


def test_live_rate_probe_bounded() -> None:
    """Small fixed burst; stop at first 429."""
    from walla.core.exceptions import WallaRateLimitError

    reset_polite()
    client = HttpClient()
    statuses: list[int] = []
    for _ in range(8):
        try:
            client.get(
                "/api/v3/search",
                params={
                    "source": "search_box",
                    "keywords": "mesa",
                    "latitude": 41.39,
                    "longitude": 2.17,
                },
                use_cache=False,
            )
            statuses.append(200)
        except WallaRateLimitError:
            statuses.append(429)
            break
        except Exception:  # noqa: BLE001
            break
    assert statuses
    assert 429 not in statuses or statuses[-1] == 429
