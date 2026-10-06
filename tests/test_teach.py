"""Local transcript parking (no Wallapop wire)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from walla.core.teach import (
    FIRST_NOTICE,
    park_transcript,
    redact_secrets,
    should_ask_feedback,
    teach_payload,
)
from walla.core.teach_pr import MANUAL_PR, plan_pr, ship_pr


def test_redact_jwt_and_cookie() -> None:
    blob, n = redact_secrets(
        "cookie __Secure-next-auth.session-token=abc.def\n"
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb"
    )
    assert n == 2
    assert "[redacted]" in blob
    assert "session-token=abc" not in blob


def test_park_and_first_notice(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    first = teach_payload()
    assert first["first_notice"] == FIRST_NOTICE
    second = teach_payload()
    assert second["first_notice"] is None
    parked = park_transcript(
        "hello Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb",
        name="hunt",
    )
    path = Path(str(parked["path"]))
    assert path.is_file()
    assert path.parent == tmp_path / "teach"
    assert parked["redacted"] >= 1
    assert "eyJhbGci" not in path.read_text(encoding="utf-8")


def test_should_ask_every_twenty() -> None:
    assert should_ask_feedback(19) is False
    assert should_ask_feedback(20) is True
    assert should_ask_feedback(21, last_asked_band=20) is False
    assert should_ask_feedback(40, last_asked_band=20) is True
    assert should_ask_feedback(40, last_asked_band=40) is False
    assert should_ask_feedback(60, last_asked_band=40) is True


def test_pr_menu_and_draft(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    payload = teach_payload()
    ids = [m["id"] for m in payload["methods"]]
    assert ids == ["A", "B", "C", "D", "E"]
    assert payload["manual_pr"] == MANUAL_PR
    draft = plan_pr("a")
    assert draft["method"] == "a"
    assert "github.com" in draft["manual_pr"]
    parked = park_transcript("hello kite hunt", name="x")
    pr = ship_pr(Path(str(parked["path"])), method="e", yes=False)
    assert pr["status"] == "draft"
    assert pr["manual_pr"] == MANUAL_PR
    manual = ship_pr(Path(str(parked["path"])), method="E", yes=True)
    assert manual["status"] == "manual"
    assert manual["open"] == MANUAL_PR
    with pytest.raises(ValueError, match="method"):
        plan_pr("z")
