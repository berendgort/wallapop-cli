"""Live Wallapop probes (opt-in: pytest -m live)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from walla.account.chat import open_conversation
from walla.account.inbox import list_conversations_raw
from walla.account.login import ensure_access_token, whoami
from walla.account.sell import _step, delete_listing, publish_listing, upload_pictures
from walla.account.session_store import load_session
from walla.http.client import HttpClient
from walla.http.polite import reset_polite
from walla.hunter.profile_store import load_profile
from walla.search.api import get_categories, get_item, search_listings

# 1x1 JPEG. Upload sessions are not public listings.
_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c"
    "1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100"
    "ffc4001f0000010501010101010100000000000000000102030405060708090a0bff"
    "c400b5100002010303020403050504040000017d0102030004110512213141061351"
    "6107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728"
    "292a3435363738393a434445464748494a535455565758595a636465666768696a73"
    "7475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2"
    "b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9"
    "eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbffd9"
)

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


def test_live_login_cookie_or_skip() -> None:
    """Cookie mint via stored session, or skip if none."""
    from walla.account.login import ensure_access_token
    from walla.account.session_store import load_session
    from walla.core.exceptions import WallaAuthError

    if load_session() is None:
        pytest.skip("no session; run walla login first")
    reset_polite()
    try:
        sess = ensure_access_token()
        assert sess.access_token
    except WallaAuthError as exc:
        assert "login" in str(exc).lower() or "session" in str(exc).lower()


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


def _step_id(raw: object) -> str | None:
    if not isinstance(raw, dict):
        return None
    step = raw.get("step")
    if isinstance(step, dict) and step.get("id"):
        return str(step["id"])
    if raw.get("id"):
        return str(raw["id"])
    return None


def test_live_auth_reads_chat_and_sell_steps(tmp_path: Path) -> None:
    """Reads, one chat-open, and sell steps through photo. No publish."""
    if load_session() is None:
        pytest.skip("no session; run walla login first")
    reset_polite()
    me = whoami()
    assert me.get("authenticated") is True
    inbox = list_conversations_raw()
    assert isinstance(inbox, dict)
    result = search_listings(
        "bicicleta", latitude=41.3874, longitude=2.1686, max_results=1
    )
    opened = open_conversation(result.listings[0].id)
    assert opened["conversation_id"]
    sess = ensure_access_token()
    http = HttpClient(access_token=sess.access_token, device_id=sess.device_id)
    upload_id = str(uuid.uuid4())
    started = _step(http, upload_id, current=None, draft={})
    assert _step_id(started) == "title"
    titled = _step(http, upload_id, current="title", draft={"title": "TEST draft"})
    assert _step_id(titled) == "photo"
    photo = tmp_path / "draft.jpg"
    photo.write_bytes(_JPEG)
    assert upload_pictures(upload_id, [photo]) == 1
    after_photo = _step(http, upload_id, current="photo", draft={"title": "TEST draft"})
    assert _step_id(after_photo) == "category"


def test_live_write_sell_roundtrip(tmp_path: Path) -> None:
    """Create and delete one listing. Skipped unless WALLA_LIVE_WRITE=1."""
    if os.environ.get("WALLA_LIVE_WRITE") != "1":
        pytest.skip("set WALLA_LIVE_WRITE=1 to create and delete a listing")
    if load_session() is None:
        pytest.skip("no session; run walla login first")
    profile = load_profile()
    if profile.lat is None or profile.lon is None:
        pytest.skip("profile has no lat/lon; run walla setup")
    reset_polite()
    photo = tmp_path / "live.jpg"
    photo.write_bytes(_JPEG)
    created = publish_listing(
        [photo],
        title="TEST walla CLI - borrar",
        description="Listado de prueba del CLI. Borrar.",
        price_eur=9,
        category_leaf_id="10105",
        root_category_id="12579",
        lat=profile.lat,
        lon=profile.lon,
    )
    try:
        assert created["id"]
    finally:
        delete_listing(created["id"])
