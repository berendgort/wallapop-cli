# walla

```
██╗    ██╗  █████╗  ██╗      ██╗       █████╗            ██████╗ ██╗      ██╗
██║    ██║ ██╔══██╗ ██║      ██║      ██╔══██╗          ██╔════╝ ██║      ██║
██║ █╗ ██║ ███████║ ██║      ██║      ███████║  █████╗  ██║      ██║      ██║
██║███╗██║ ██╔══██║ ██║      ██║      ██╔══██║  ╚════╝  ██║      ██║      ██║
╚███╔███╔╝ ██║  ██║ ███████╗ ███████╗ ██║  ██║          ╚██████╗ ███████╗ ██║
 ╚══╝╚══╝  ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝           ╚═════╝ ╚══════╝ ╚═╝
  look · offer · talk
  Dr. Berend Gort  ·  www.berendgort.dev
```

![walla banner](docs/assets/walla-github-banner.jpg)

**walla** is an unofficial Wallapop.es **CLI + MCP + Python library** for Cursor
agents and humans: search listings, read inbox, send a message, make an offer.

Not affiliated with Wallapop. Respect ToS and rate limits.

### What this unlocks

You tell Cursor: *“Find me a used kite near Barcelona under €400, message
the seller, and offer if it’s a GRAB.”*

The agent runs `walla` — ranks listings **GRAB / LOOK / PASS**, links you the
item, asks before sending, then talks and offers on your behalf:

```bash
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona \
  --budget 400 --aggression fair --must "kite cabrinha"
walla search "tabla kite Cabrinha" --max 40 --json
# agent: GRAB · Cabrinha Moto 10m · €320 · 4 km
#        https://es.wallapop.com/item/...

walla search "…" --export md,csv,html,pdf --out ./shortlist --json
# or later: walla export --format md,csv,html,pdf --out ./shortlist --json

walla login                         # paste session cookie once
walla negotiate <id> --json         # draft only; you approve text + EUR
walla say <id> "…" --yes            # only after you approve
walla offer <id> --eur 280 --yes    # only after you approve; never pays
```

That is the product: a Cursor agent that can **look, draft, talk, and offer**
up to the point of payment. You finish pay/meet in the Wallapop app.

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

1. Install from **PyPI** (preferred):
   ```bash
   pipx install 'walla-cli[mcp]'
   ```
   From a clone only when hacking: `pipx install -e '.[mcp]'`.
2. `walla doctor --json` — read `auth.session` and `network.reachable`.
   **Never** print tokens or cookies.
3. If no session: ask the human to run `walla login` and paste
   `__Secure-next-auth.session-token` from es.wallapop.com (Cookie-Editor).
   Agents may pass it non-interactively: `walla login --cookie '<value>' --json`.
4. `walla instruct --json` — read `mandate` + `hitl`. If `mandate.budget` is
   null, ask once for budget / aggression / must words, then `walla setup …`.
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
| Mandate | `walla setup --budget 400 --aggression fair --must "kite"` |
| Look | `walla search "tabla kite" --max 40 --json` then `walla item <id> --json` |
| Draft | `walla negotiate <id> --json` (win-win Spanish draft; never sends) |
| Talk | `walla inbox --json` · `walla thread <id> --json` · `walla say <id> "…" --yes` |
| Offer | `walla offer <id> --eur 180 --yes` |

### HITL (ask once per decision)

| Step | Agent alone | Ask human |
|------|-------------|-----------|
| Search inside mandate | yes | if query vague or budget unset |
| Shortlist | show GRABs | if more than one GRAB, pick the id |
| Negotiate draft | yes | approve Spanish text |
| `say --yes` | never | yes to that exact text |
| `offer --yes` | never; refuse if EUR > budget | yes to that exact EUR |
| Pay / buy / reserve | **never** | human finishes in the Wallapop app |

Rules:

- Reads and negotiate drafts are safe. `say` / `offer` need `--yes`.
- `--yes` means send chat or price offer only. It never completes a purchase.
- If they only asked to look, do not send.
- Ambiguous match or multiple GRABs: ask once with candidates.
- In-person offers outside pickup radius: refuse.
- Envelope: `ok`, `api_version`, `data` or `error` / `error_type` / `retryable`.

`walla instruct --json` returns this recipe.

---

## Install

```bash
pipx install 'walla-cli[mcp]'   # PyPI: https://pypi.org/project/walla-cli/
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona --json
walla login          # paste __Secure-next-auth.session-token
walla doctor --json
```

## CLI

| Command | Role |
|---------|------|
| `walla setup` / `profile` | Home point, radius, budget |
| `walla search` / `item` / `categories` | Look |
| `walla watch add\|list\|check` | Local saved searches |
| `walla login` / `logout` / `whoami` | Session (paste cookie; optional `--password`) |
| `walla negotiate` | Win-win Spanish draft (never sends) |
| `walla inbox` / `thread` / `say` | Talk |
| `walla offer` | Offer (prints total, needs `--yes`) |
| `walla fav list\|add\|rm` | Favorites |
| `walla instruct` / `doctor` | Agent recipe + health |

## Develop

```bash
pip install -e '.[dev,mcp]'
pytest -q -m 'not live'
pytest -m live          # hits Wallapop; needs network
ruff check .
mypy walla
python scripts/check_code_quality.py
```

| Layer | Path | Role |
|-------|------|------|
| Models | `walla/models/` | Pydantic only |
| HTTP | `walla/http/` | curl_cffi + polite |
| Core | `walla/core/` | Envelope, errors, human_fix |
| Search | `walla/search/` | Look |
| Account | `walla/account/` | Session, inbox, offer |
| Hunter | `walla/hunter/` | Profile, watches, verdicts |
| CLI / MCP | `walla/cli/` · `walla/mcp/` | Entrypoints |

Read [`AGENTS.md`](AGENTS.md) before extending.

## Disclaimer

Unofficial. Not affiliated with Wallapop. Personal / research use.

## License

MIT
