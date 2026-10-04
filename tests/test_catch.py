"""Catch / envelope / catch error paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from walla.cli.catch import emit, run_cmd
from walla.cli.main import app
from walla.core.envelope import dump_model, error_payload
from walla.core.errors import classify_error
from walla.core.exceptions import WallaAmbiguousError, WallaHTTPError
from walla.models.listing import Listing, Money

runner = CliRunner()


def test_emit_success_human() -> None:
    emit({"ok": True, "data": {"a": 1}}, as_json=False)


def test_run_cmd_error_json() -> None:
    def boom() -> None:
        raise ValueError("nope")

    with pytest.raises(typer.Exit):
        run_cmd(boom, as_json=True)


def test_dump_model() -> None:
    m = Listing(
        id="1",
        title="t",
        price=Money(amount=1, currency="EUR"),
        web_slug="t",
        url="https://es.wallapop.com/item/t",
    )
    assert dump_model(m)["id"] == "1"


def test_ambiguous_payload() -> None:
    p = error_payload(WallaAmbiguousError("many", candidates=[{"id": "1"}]))
    assert p["candidates"][0]["id"] == "1"


def test_http_error_classify() -> None:
    c = classify_error(WallaHTTPError("x", status_code=502))
    assert c.retryable is True


def test_profile_json_cmd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["profile", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
