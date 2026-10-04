#!/usr/bin/env python3
"""Korotkevich bar checks for walla (LOC, em-dash, cycles, layers)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WALLA = ROOT / "walla"
MAX_LOC = 250

LAYER: dict[str, int] = {
    "walla.models": 10,
    "walla.core.exceptions": 15,
    "walla.http": 20,
    "walla.core": 30,
    "walla.search": 40,
    "walla.account": 40,
    "walla.hunter": 40,
    "walla.cli": 50,
    "walla.mcp": 50,
}

PRINT_ALLOW = {
    "walla/cli/banner.py",
    "walla/cli/console.py",
    "walla/cli/catch.py",
    "walla/mcp/_entry.py",
}


def _pkg_rank(mod: str) -> int | None:
    for prefix, rank in sorted(LAYER.items(), key=lambda x: -len(x[0])):
        if mod == prefix or mod.startswith(prefix + "."):
            return rank
    return None


def check_loc() -> list[str]:
    bad: list[str] = []
    for path in WALLA.rglob("*.py"):
        n = len(path.read_text(encoding="utf-8").splitlines())
        if n > MAX_LOC:
            bad.append(f"{path.relative_to(ROOT)}: {n} LOC > {MAX_LOC}")
    return bad


def check_emdash() -> list[str]:
    bad: list[str] = []
    for path in WALLA.rglob("*.py"):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "\u2014" in line or "\u2013" in line:
                bad.append(f"{path.relative_to(ROOT)}:{i}: em/en-dash")
    return bad


def check_print() -> list[str]:
    bad: list[str] = []
    for path in WALLA.rglob("*.py"):
        rel = str(path.relative_to(ROOT))
        if rel in PRINT_ALLOW:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            bad.append(f"{rel}: syntax {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "print":
                    bad.append(f"{rel}:{node.lineno}: bare print()")
    return bad


def check_layers() -> list[str]:
    bad: list[str] = []
    for path in WALLA.rglob("*.py"):
        parts = path.relative_to(WALLA).with_suffix("").parts
        if path.name == "__init__.py":
            mod = ".".join(("walla", *parts[:-1])) if len(parts) > 1 else "walla"
        else:
            mod = ".".join(("walla", *parts))
        src_rank = _pkg_rank(mod)
        if src_rank is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if not name.startswith("walla."):
                    continue
                dst = _pkg_rank(name)
                if dst is None:
                    continue
                if dst > src_rank:
                    bad.append(
                        f"{path.relative_to(ROOT)}: {mod} (rank {src_rank}) "
                        f"imports higher {name} (rank {dst})"
                    )
    return bad


def main() -> int:
    errors = check_loc() + check_emdash() + check_print() + check_layers()
    if errors:
        print("FAILED code quality:")
        for e in errors:
            print(f"  {e}")
        return 1
    print("OK: LOC<=250, no em-dash, no bare print, layer DAG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
