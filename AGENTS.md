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
pipx install 'walla-cli[mcp]'   # PyPI preferred
walla instruct --json
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona --json
walla login --cookie '<session-token>' --json
walla search "tabla" --json
```

Never print session cookies or bearer tokens. On `error_type: auth`, ask the human
to run `walla login` and paste `__Secure-next-auth.session-token`.

## Architecture map

| Path | Owns | Must not |
|------|------|----------|
| `walla/models/` | Pydantic DTOs | I/O |
| `walla/http/` | curl_cffi, polite | CLI/MCP imports |
| `walla/core/` | Envelope, errors, paths, human_fix | Live Wallapop calls (except doctor via CLI) |
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
- **Do** require `--yes` for bare say/offer/sell/unsell. `pursue` and `desk` send negotiation chat without a per-message prompt. Never pay.
- **Don't** commit session.json, cookies, or tokens.
- **Don't** invent wire shapes without a fixture.
- **Don't** post buyer offers as `{item_id, amount, currency}` (HTTP 400).
  Use `walla.account.offer_wire.build_offer_body` / `fixtures/offer_buyer_request.json`.
- **Don't** create listings without `Accept: application/vnd.upload-v2+json`
  (HTTP 405). Use `walla sell` / `fixtures/sell_item_request.json`.
- **Don't** require `.env` credentials; login is cookie paste.
