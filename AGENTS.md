# AGENTS.md — how to extend `walla`

You are working on **walla**: Wallapop.es CLI / library / MCP (look · offer · talk).

## Quality (read first)

- [`docs/code_quality.md`](docs/code_quality.md) — Korotkevich / Tourist bar
- [`docs/data_engineering_standards.md`](docs/data_engineering_standards.md) — Gray / Stonebraker bar
- [`docs/WIRE.md`](docs/WIRE.md) — captured wire
- [`docs/objective_function.md`](docs/objective_function.md)

Run before shipping:

```bash
python scripts/check_code_quality.py
ruff check .
mypy walla
pytest -q -m "not live"
```

## Calling walla from an agent

```bash
pipx install -e '.[mcp]'
walla instruct --json
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona --json
walla login --json          # WALLAPOP_USER / WALLAPOP_PW from .env
walla search "tabla" --json
```

Never print passwords or bearer tokens. On `error_type: auth`, follow `human_fix`.

## Architecture map

| Path | Owns | Must not |
|------|------|----------|
| `walla/models/` | Pydantic DTOs | I/O |
| `walla/http/` | curl_cffi, polite | CLI/MCP imports |
| `walla/core/` | Envelope, errors, paths, dotenv | Live Wallapop calls (except doctor via CLI) |
| `walla/search/` | Public look | Account mutations |
| `walla/account/` | Session, inbox, say, offer, fav | HTML scrape |
| `walla/hunter/` | Profile, watches, GRAB/LOOK/PASS | HTTP |
| `walla/cli/` | Typer + Rich + `--json` | Import MCP |
| `walla/mcp/` | FastMCP | Import CLI |

Ranks: models 10 → exceptions 15 → http 20 → core 30 → search/account/hunter 40 → cli/mcp 50.

## Live capture workflow

1. Reproduce in browser Network on `es.wallapop.com`.
2. Call with `curl_cffi` + `X-DeviceOS: 0`.
3. Redact secrets → `fixtures/` → parser test → update `docs/WIRE.md`.
4. Never HTML-scrape as the primary path. Never Playwright.

## Do / don't

- **Do** keep files <= 250 LOC.
- **Do** fail closed; typed `error_type`.
- **Do** require `--yes` for say/offer.
- **Don't** commit `.env`, session.json, cookies, or tokens.
- **Don't** invent wire shapes without a fixture.
