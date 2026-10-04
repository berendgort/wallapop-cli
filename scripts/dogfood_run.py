#!/usr/bin/env python3
"""Run one dogfood scenario. Usage: dogfood_run.py <scenario_id>"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WALLA = ROOT / ".venv" / "bin" / "walla"
OUT_ROOT = Path("/tmp/walla-dogfood")


def run(cmd: list[str], env: dict[str, str]) -> dict:
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    ms = int((time.perf_counter() - t0) * 1000)
    stdout = proc.stdout.strip()
    payload = None
    if "{" in stdout:
        try:
            payload = json.loads(stdout[stdout.find("{") :])
        except json.JSONDecodeError:
            payload = None
    return {
        "cmd": cmd,
        "exit": proc.returncode,
        "elapsed_ms": ms,
        "stdout_head": stdout[:800],
        "stderr_head": (proc.stderr or "")[:200],
        "payload": payload,
    }


def base_env(scenario: str) -> dict[str, str]:
    cfg = OUT_ROOT / scenario / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["WALLA_CONFIG_DIR"] = str(cfg)
    env["PATH"] = f"{ROOT / '.venv' / 'bin'}:{env.get('PATH', '')}"
    env.pop("VIRTUAL_ENV", None)
    return env


def scenario_fresh() -> dict:
    env = base_env("fresh")
    commands = [
        run([str(WALLA), "doctor", "--json"], env),
        run([str(WALLA), "search", "tabla", "--max", "3", "--json"], env),
        run([str(WALLA), "instruct", "--json"], env),
    ]
    search = commands[1]
    intake = bool(
        search.get("payload")
        and search["payload"].get("data", search["payload"]).get("ready") is False
    ) or "intake" in (search.get("stdout_head") or "")
    ok = commands[0]["exit"] == 0 and commands[2]["exit"] == 0 and not any(
        "Traceback" in (c.get("stderr_head") or "") for c in commands
    )
    return {
        "id": "fresh",
        "ok": ok,
        "commands": commands,
        "unclear": "" if intake or ok else "expected intake when no profile",
        "extra_steps": 0,
        "notes": {"intake_or_ready_false": intake},
    }


def scenario_mandate() -> dict:
    env = base_env("mandate")
    out = OUT_ROOT / "mandate" / "export"
    out.mkdir(parents=True, exist_ok=True)
    commands = [
        run(
            [
                str(WALLA),
                "setup",
                "--lat",
                "41.39",
                "--lon",
                "2.17",
                "--budget",
                "400",
                "--aggression",
                "fair",
                "--must",
                "kite",
                "--json",
            ],
            env,
        ),
        run(
            [
                str(WALLA),
                "search",
                "tabla kite",
                "--max",
                "5",
                "--json",
                "--export",
                "md,csv,html,pdf",
                "--out",
                str(out),
            ],
            env,
        ),
    ]
    search = commands[1].get("payload") or {}
    data = search.get("data", search)
    listings = data.get("listings") or []
    files_ok = all(
        (out / f"walla-shortlist.{ext}").is_file() for ext in ("md", "csv", "html", "pdf")
    )
    urls_ok = all(
        str(r.get("url", "")).startswith("https://es.wallapop.com/item/") for r in listings
    ) if listings else False
    fit_has_budget = False
    if files_ok:
        md = (out / "walla-shortlist.md").read_text(encoding="utf-8")
        fit_has_budget = "400" in md or "budget" in md.lower()
    ok = (
        commands[0]["exit"] == 0
        and commands[1]["exit"] == 0
        and "hitl" in data
        and files_ok
        and urls_ok
        and fit_has_budget
    )
    return {
        "id": "mandate",
        "ok": ok,
        "commands": commands,
        "unclear": "" if ok else "mandate/export checks failed",
        "extra_steps": 0,
        "notes": {
            "files_ok": files_ok,
            "urls_ok": urls_ok,
            "fit_has_budget": fit_has_budget,
            "grabs": (data.get("hitl") or {}).get("grabs"),
        },
    }


def scenario_draft() -> dict:
    env = base_env("draft")
    commands = [
        run(
            [
                str(WALLA),
                "setup",
                "--lat",
                "41.39",
                "--lon",
                "2.17",
                "--budget",
                "400",
                "--aggression",
                "fair",
                "--json",
            ],
            env,
        ),
        run([str(WALLA), "search", "tabla kite", "--max", "5", "--json"], env),
    ]
    data = (commands[1].get("payload") or {}).get("data") or commands[1].get("payload") or {}
    listings = data.get("listings") or []
    grabs = [L for L in listings if L.get("verdict") == "GRAB"]
    pick = (grabs or listings or [None])[0]
    if not pick:
        return {
            "id": "draft",
            "ok": False,
            "commands": commands,
            "unclear": "no listings to negotiate",
            "extra_steps": 0,
        }
    commands.append(
        run([str(WALLA), "negotiate", str(pick["id"]), "--json"], env)
    )
    neg = (commands[-1].get("payload") or {}).get("data") or commands[-1].get("payload") or {}
    opening = str(neg.get("opening") or "")
    hint = str(neg.get("hint") or "")
    offer = neg.get("offer_eur")
    ok = (
        commands[-1]["exit"] == 0
        and "¿Sigue disponible?" in opening
        and offer is not None
        and float(offer) <= 400
        and ("never" in hint.lower() or "pay" in hint.lower())
    )
    return {
        "id": "draft",
        "ok": ok,
        "commands": commands,
        "unclear": "" if ok else "negotiate draft missing fields",
        "extra_steps": 0,
        "notes": {"offer_eur": offer, "opening_head": opening[:80]},
    }


def scenario_gates() -> dict:
    env = base_env("gates")
    # no budget negotiate
    commands = [
        run(
            [str(WALLA), "setup", "--lat", "41.39", "--lon", "2.17", "--json"],
            env,
        ),
        run([str(WALLA), "search", "tabla", "--max", "1", "--json"], env),
    ]
    data = (commands[1].get("payload") or {}).get("data") or commands[1].get("payload") or {}
    listings = data.get("listings") or []
    item_id = listings[0]["id"] if listings else "missing"
    commands.append(run([str(WALLA), "negotiate", item_id, "--json"], env))
    no_budget = commands[-1]["exit"] != 0 or "set_budget" in (
        commands[-1].get("stdout_head") or ""
    ) + (commands[-1].get("stderr_head") or "")
    # with budget: offer without --yes
    env2 = base_env("gates-budget")
    commands.append(
        run(
            [
                str(WALLA),
                "setup",
                "--lat",
                "41.39",
                "--lon",
                "2.17",
                "--budget",
                "100",
                "--json",
            ],
            env2,
        )
    )
    commands.append(run([str(WALLA), "search", "tabla", "--max", "1", "--json"], env2))
    data2 = (commands[-1].get("payload") or {}).get("data") or commands[-1].get("payload") or {}
    listings2 = data2.get("listings") or []
    item2 = listings2[0]["id"] if listings2 else item_id
    commands.append(
        run([str(WALLA), "offer", item2, "--eur", "99999", "--json"], env2)
    )
    offer_payload = (commands[-1].get("payload") or {}).get("data") or commands[-1].get(
        "payload"
    ) or {}
    needs_confirm = bool(offer_payload.get("needs_confirm")) or commands[-1]["exit"] != 0
    # refuse over budget with --yes would send - don't use --yes for over budget check via negotiate
    ok = no_budget and needs_confirm
    return {
        "id": "gates",
        "ok": ok,
        "commands": commands,
        "unclear": "" if ok else "HITL gates not clear",
        "extra_steps": 0,
        "notes": {"no_budget": no_budget, "needs_confirm": needs_confirm},
    }


def scenario_auth() -> dict:
    env = base_env("auth")
    commands = [
        run([str(WALLA), "login", "--json"], env),
        run([str(WALLA), "whoami", "--json"], env),
    ]
    texts = " ".join(
        (c.get("stdout_head") or "") + (c.get("stderr_head") or "") for c in commands
    )
    names_next = "login" in texts.lower() or "--cookie" in texts.lower()
    no_tb = "Traceback" not in texts
    ok = commands[0]["exit"] != 0 and commands[1]["exit"] != 0 and names_next and no_tb
    return {
        "id": "auth",
        "ok": ok,
        "commands": commands,
        "unclear": "" if ok else "auth errors unclear",
        "extra_steps": 0,
    }


def scenario_help() -> dict:
    env = base_env("help")
    commands = [
        run([str(WALLA)], env),
        run([str(WALLA), "negotiate", "--help"], env),
        run([str(WALLA), "export", "--help"], env),
    ]
    text = " ".join(c.get("stdout_head") or "" for c in commands).lower()
    ok = (
        "kite" in text
        and ("pipx" in text or "walla-cli" in text)
        and "pdf" in text
        and "negotiate" in text
    )
    return {
        "id": "help",
        "ok": ok,
        "commands": commands,
        "unclear": "" if ok else "banner missing kite example, install, or pdf export",
        "extra_steps": 0,
    }


SCENARIOS = {
    "fresh": scenario_fresh,
    "mandate": scenario_mandate,
    "draft": scenario_draft,
    "gates": scenario_gates,
    "auth": scenario_auth,
    "help": scenario_help,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        print("usage: dogfood_run.py <" + "|".join(SCENARIOS) + ">", file=sys.stderr)
        return 2
    sid = sys.argv[1]
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    result = SCENARIOS[sid]()
    # strip bulky payloads for disk
    for c in result.get("commands") or []:
        if isinstance(c.get("payload"), dict):
            c["payload_ok"] = c["payload"].get("ok")
            c["payload_keys"] = list((c["payload"].get("data") or c["payload"]).keys())[:12]
            c.pop("payload", None)
    path = OUT_ROOT / f"{sid}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(path), "ok": result["ok"]}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
