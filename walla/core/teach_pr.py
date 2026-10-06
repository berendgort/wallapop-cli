"""Open a GitHub PR for a parked transcript (gh / git / hub / browser / manual)."""

from __future__ import annotations

import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Any

__all__ = (
    "MANUAL_PR",
    "METHODS",
    "REPO",
    "method_menu",
    "plan_pr",
    "ship_pr",
)

REPO = "berendgort/wallapop-cli"
MANUAL_PR = f"https://github.com/{REPO}/compare"
UPLOAD = f"https://github.com/{REPO}/upload/main/incoming/teach"

METHODS: dict[str, dict[str, str]] = {
    "a": {
        "bin": "gh",
        "label": "GitHub CLI (gh fork/push/pr create)",
    },
    "b": {
        "bin": "git",
        "label": "git branch, commit, push, then open the compare URL",
    },
    "c": {
        "bin": "browser",
        "label": "Open GitHub in the browser (upload + compare links)",
    },
    "d": {
        "bin": "hub",
        "label": "hub pull-request (legacy GitHub CLI)",
    },
    "e": {
        "bin": "manual",
        "label": "I will open the PR myself (print the link + file path)",
    },
}


def method_menu() -> list[dict[str, str]]:
    return [
        {"id": key.upper(), "key": key, **row} for key, row in METHODS.items()
    ]


def _which(name: str) -> str | None:
    if name in {"browser", "manual"}:
        return name
    return shutil.which(name)


def plan_pr(method: str) -> dict[str, Any]:
    key = method.strip().lower()
    if key not in METHODS:
        raise ValueError("method must be A B C D or E")
    spec = METHODS[key]
    binary = spec["bin"]
    found = _which(binary)
    return {
        "method": key,
        "label": spec["label"],
        "assume_on_path": binary,
        "found": bool(found),
        "manual_pr": MANUAL_PR,
        "upload": UPLOAD,
        "hint": (
            f"Assumes `{binary}` is installed. If not, open {MANUAL_PR} "
            "and create the PR by hand (or pick E)."
        ),
    }


def ship_pr(parked: Path, *, method: str, yes: bool) -> dict[str, Any]:
    """Copy into incoming/teach and open a PR. Needs --yes to mutate git/gh."""
    plan = plan_pr(method)
    plan["parked"] = str(parked)
    if not yes:
        plan["status"] = "draft"
        plan["next"] = (
            f"Reply with a letter, then: walla teach {parked} "
            f"--method {plan['method']} --yes --json"
        )
        return plan
    key = str(plan["method"])
    if key == "e" or not plan["found"]:
        plan["status"] = "manual"
        plan["open"] = MANUAL_PR
        return plan
    if key == "c":
        webbrowser.open(UPLOAD)
        webbrowser.open(MANUAL_PR)
        plan["status"] = "opened_browser"
        plan["open"] = MANUAL_PR
        return plan
    if key == "a":
        return _ship_gh(parked, plan)
    if key == "d":
        return _ship_hub(parked, plan)
    return _ship_git(parked, plan)


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _ship_gh(parked: Path, plan: dict[str, Any]) -> dict[str, Any]:
    code, out, err = _run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            REPO,
            "--title",
            f"teach: {parked.name}",
            "--body",
            f"Redacted agent transcript from `walla teach`.\n\nFile: `{parked}`",
        ]
    )
    blob = f"{out}\n{err}"
    url = next((ln for ln in blob.splitlines() if "github.com" in ln), "")
    plan["status"] = "ok" if code == 0 else "failed"
    plan["open"] = url or MANUAL_PR
    if code != 0:
        plan["error"] = (err or out or "gh pr create failed")[:300]
        plan["assist"] = (
            "gh is missing a fork/branch. Agent: help install/auth gh, or "
            f"open {MANUAL_PR} and attach {parked}."
        )
    return plan


def _ship_hub(parked: Path, plan: dict[str, Any]) -> dict[str, Any]:
    code, out, err = _run(["hub", "pull-request", "-m", f"teach: {parked.name}"])
    blob = f"{out}\n{err}"
    url = next((ln for ln in blob.splitlines() if "github.com" in ln), "")
    plan["status"] = "ok" if code == 0 else "failed"
    plan["open"] = url or MANUAL_PR
    if code != 0:
        plan["error"] = (err or out or "hub pull-request failed")[:300]
        plan["assist"] = f"hub failed. Open {MANUAL_PR} or switch to A (gh)."
    return plan


def _ship_git(parked: Path, plan: dict[str, Any]) -> dict[str, Any]:
    root = _git_root()
    if root is None:
        plan["status"] = "manual"
        plan["open"] = MANUAL_PR
        plan["assist"] = (
            "Not inside a wallapop-cli clone. Open the compare link or "
            "clone the repo, copy the parked file into incoming/teach/, "
            "commit, push, then open the PR URL."
        )
        return plan
    dest_dir = root / "incoming" / "teach"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / parked.name
    dest.write_text(parked.read_text(encoding="utf-8"), encoding="utf-8")
    branch = f"teach/{parked.stem}"[:60]
    for cmd in (
        ["git", "checkout", "-b", branch],
        ["git", "add", str(dest)],
        ["git", "commit", "-m", f"teach: park {parked.name}"],
        ["git", "push", "-u", "origin", "HEAD"],
    ):
        code, out, err = _run(cmd, cwd=root)
        if code != 0 and "already exists" not in (err + out):
            plan["status"] = "failed"
            plan["open"] = MANUAL_PR
            plan["error"] = (err or out or "git failed")[:300]
            plan["assist"] = f"Finish by hand: {MANUAL_PR}"
            return plan
    plan["status"] = "pushed"
    plan["open"] = f"https://github.com/{REPO}/compare/main...{branch}?expand=1"
    return plan


def _git_root() -> Path | None:
    code, out, _err = _run(["git", "rev-parse", "--show-toplevel"])
    if code != 0 or not out:
        return None
    return Path(out)
