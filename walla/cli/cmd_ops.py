"""Ops commands: doctor, instruct, setup, profile."""

from __future__ import annotations

from typing import Any

import typer

from walla import __version__
from walla.account.session_store import load_session
from walla.cli.catch import run_cmd
from walla.core.instruct import instruct_recipe
from walla.core.teach import teach_payload
from walla.hunter.profile_store import load_profile, parse_intake, save_profile

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("instruct")
    def instruct(json: bool = typer.Option(False, "--json")) -> None:
        """Agent recipe."""
        run_cmd(instruct_recipe, as_json=json)

    @app.command("doctor")
    def doctor(json: bool = typer.Option(False, "--json")) -> None:
        """Network + session (never prints secrets)."""

        def _run() -> dict[str, Any]:
            sess = load_session()
            profile = load_profile()
            reachable = False
            try:
                from walla.http.client import HttpClient

                HttpClient().get("/api/v3/categories", use_cache=False)
                reachable = True
            except Exception:  # noqa: BLE001
                reachable = False
            has_session = bool(sess and (sess.access_token or sess.session_cookie))
            out: dict[str, Any] = {
                "version": __version__,
                "network": {"reachable": reachable},
                "auth": {
                    "session": has_session,
                    "how": "walla login  (paste browser session cookie)",
                },
                "profile": {"ready": profile.ready, "label": profile.label},
            }
            notice = teach_payload()
            if notice.get("first_notice"):
                out["teach"] = notice
            return out

        run_cmd(_run, as_json=json)

    @app.command("setup")
    def setup(
        lat: float | None = typer.Option(None),
        lon: float | None = typer.Option(None),
        km: float = typer.Option(30.0),
        pickup_km: float = typer.Option(30.0, "--pickup-km"),
        label: str | None = typer.Option(None),
        budget: float | None = typer.Option(None),
        aggression: str | None = typer.Option(
            None, "--aggression", help="soft | fair | firm"
        ),
        must: str | None = typer.Option(
            None, "--must", help="Words title/description must contain"
        ),
        intake: str | None = typer.Option(None, "--intake"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Save home point, radius, budget, and buyer mandate."""

        def _run() -> dict[str, Any]:
            if intake:
                profile = parse_intake(intake)
            else:
                profile = load_profile()
                if lat is not None:
                    profile.lat = lat
                if lon is not None:
                    profile.lon = lon
                profile.km = km
                profile.pickup_km = pickup_km
                if label is not None:
                    profile.label = label
                if budget is not None:
                    profile.budget = budget
                if aggression is not None:
                    a = aggression.strip().lower()
                    if a not in ("soft", "fair", "firm"):
                        raise ValueError("aggressiveness must be soft, fair, or firm")
                    profile.aggressiveness = a  # type: ignore[assignment]
                if must is not None:
                    profile.must_match = [w for w in must.replace(",", " ").split() if w]
            if not profile.ready:
                return {
                    "ready": False,
                    "intake": {"prompt_to_user": profile.intake_prompt()},
                }
            save_profile(profile)
            return {
                "ready": True,
                "profile": profile.model_dump(mode="json"),
                "mandate": {
                    "budget": profile.spend_cap,
                    "aggressiveness": profile.aggressiveness,
                    "must_match": profile.must_match,
                },
            }

        run_cmd(_run, as_json=json)

    @app.command("profile")
    def profile_cmd(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            p = load_profile()
            return {
                "ready": p.ready,
                "profile": p.model_dump(mode="json"),
                "mandate": {
                    "budget": p.spend_cap,
                    "aggressiveness": p.aggressiveness,
                    "must_match": p.must_match,
                },
                "intake": None if p.ready else {"prompt_to_user": p.intake_prompt()},
            }

        run_cmd(_run, as_json=json)
