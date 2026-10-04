# walla

```
 ██╗    ██╗ █████╗ ██╗     ██╗      █████╗
 ██║    ██║██╔══██╗██║     ██║     ██╔══██╗
 ██║ █╗ ██║███████║██║     ██║     ███████║
 ██║███╗██║██╔══██║██║     ██║     ██╔══██║
 ╚███╔███╔╝██║  ██║███████╗███████╗██║  ██║
  ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
  WALLA-CLI  ·  look · offer · talk
  Dr. Berend Gort  ·  www.berendgort.dev
```

![walla banner](docs/assets/walla-github-banner.jpg)

**walla** is an unofficial Wallapop.es **CLI + MCP + Python library** for Cursor
agents and humans: search listings, read inbox, send a message, make an offer.

Private repo. Not affiliated with Wallapop. Respect ToS and rate limits.

**Quality bar (enforced in CI):**

- [`docs/code_quality.md`](docs/code_quality.md) — Korotkevich / Tourist bar
- [`docs/data_engineering_standards.md`](docs/data_engineering_standards.md) — Gray / Stonebraker bar
- [`docs/WIRE.md`](docs/WIRE.md) — captured consumer API
- [`docs/rate_limit_analysis.md`](docs/rate_limit_analysis.md) — polite spacing

---

## For AI agents (mandatory protocol)

If the user pasted this GitHub link (or this README), **follow this section exactly**.

### Goal

Look, offer, and talk on wallapop.es using the `walla` package. Speak briefly.
Link listings as `https://es.wallapop.com/item/<web_slug>`. Verdicts:
**GRAB / LOOK / PASS**.

### Bootstrap

1. Install from this private clone:
   ```bash
   pipx install -e '.[mcp]'
   # or: pip install -e '.[mcp]'
   ```
2. `walla doctor --json` — read `auth.configured` and `network.reachable`.
   **Never** print `WALLAPOP_PW` or tokens. Never ask the human to paste the password.
3. Credentials live in `.env` as `WALLAPOP_USER` / `WALLAPOP_PW`.
4. If no session: `walla login --json`. On MFA / empty 400, follow `human_fix`
   (cookie export) then `walla login --cookies <file> --json`.
5. Do the ask with `walla … --json` and narrate in prose.

Optional MCP:

```json
{
  "mcpServers": {
    "walla": { "command": "walla-mcp" }
  }
}
```

### Operating loop

| Ask | Command |
|-----|---------|
| Look | `walla search "tabla kite" --max 40 --json` then `walla item <id> --json` |
| Talk | `walla inbox --json` · `walla thread <id> --json` · `walla say <id> "…" --yes` |
| Offer | `walla offer <id> --eur 180 --yes` |

Rules:

- Reads are safe. `say` / `offer` need `--yes` / `confirm=true`. Name listing + euros.
- If they only asked to look, do not send.
- Ambiguous match: ask once with candidates.
- In-person offers outside pickup radius: refuse.
- Envelope: `ok`, `api_version`, `data` or `error` / `error_type` / `retryable`.

`walla instruct --json` returns this recipe.

---

## Install

```bash
git clone git@github.com:berendgort/wallapop-cli.git
cd wallapop-cli
pipx install -e '.[mcp]'
# put WALLAPOP_USER / WALLAPOP_PW in .env (gitignored)
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona --json
walla doctor --json
```

## CLI

| Command | Role |
|---------|------|
| `walla setup` / `profile` | Home point, radius, budget |
| `walla search` / `item` / `categories` | Look |
| `walla watch add\|list\|check` | Local saved searches |
| `walla login` / `logout` / `whoami` | Session (password or `--cookies`) |
| `walla inbox` / `thread` / `say` | Talk |
| `walla offer` | Offer (prints total, needs `--yes`) |
| `walla fav list\|add\|rm` | Favorites |
| `walla instruct` / `doctor` | Agent recipe + health |

## Develop

```bash
pip install -e '.[dev,mcp]'
pytest -q -m 'not live'
pytest -m live          # hits Wallapop; needs network + .env
ruff check .
mypy walla
python scripts/check_code_quality.py
```

| Layer | Path | Role |
|-------|------|------|
| Models | `walla/models/` | Pydantic only |
| HTTP | `walla/http/` | curl_cffi + polite |
| Core | `walla/core/` | Envelope, errors, dotenv |
| Search | `walla/search/` | Look |
| Account | `walla/account/` | Session, inbox, offer |
| Hunter | `walla/hunter/` | Profile, watches, verdicts |
| CLI / MCP | `walla/cli/` · `walla/mcp/` | Entrypoints |

Read [`AGENTS.md`](AGENTS.md) before extending.

## Disclaimer

Unofficial. Not affiliated with Wallapop. Personal / research use.

## License

MIT
