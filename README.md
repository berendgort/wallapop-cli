# walla

```
██╗    ██╗  █████╗  ██╗      ██╗       █████╗            ██████╗ ██╗      ██╗
██║    ██║ ██╔══██╗ ██║      ██║      ██╔══██╗          ██╔════╝ ██║      ██║
██║ █╗ ██║ ███████║ ██║      ██║      ███████║  █████╗  ██║      ██║      ██║
██║███╗██║ ██╔══██║ ██║      ██║      ██╔══██║  ╚════╝  ██║      ██║      ██║
╚███╔███╔╝ ██║  ██║ ███████╗ ███████╗ ██║  ██║          ╚██████╗ ███████╗ ██║
 ╚══╝╚══╝  ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝           ╚═════╝ ╚══════╝ ╚═╝
  look · offer · talk · sell
  Dr. Berend Gort  ·  www.berendgort.dev
```

![walla banner](docs/assets/walla-github-banner.jpg)

**walla** is an unofficial Wallapop.es **CLI + MCP + Python library** for Cursor
agents and humans: search listings, negotiate, publish a listing, and follow the inbox.

Not affiliated with Wallapop. Respect ToS and rate limits.

### What this unlocks

You tell Cursor: *“Find me a used kite near Barcelona under €400, message
the seller, and offer if it’s a GRAB.”*

The agent runs `walla` — ranks listings **GRAB / LOOK / PASS**, messages the
shortlist, and follows replies until a price is agreed. You close the deal
in the Wallapop app.

```bash
walla setup --lat 41.39 --lon 2.17 --km 30 --label Barcelona \
  --budget 400 --aggression fair --must "kite cabrinha"
walla login                         # paste session cookie once
walla pursue "tabla kite Cabrinha" --json
walla desk --json                   # one inbox read; replies; stack.best
```

Sell is the same idea: answer the photo questions, publish once, then desk
talks to buyers.

```bash
walla sell ./shot.jpg --json
walla sell ./shot.jpg --title "…" --desc "…" --eur 40 \
  --category 10105 --root 12579 --floor 35 --yes --json
```

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
| Look | `walla search "tabla kite" --max 40 --json` |
| Buy | `walla pursue "<query>" --json` then `walla desk --json` |
| Sell | `walla sell <photos> --json`, then the same command with `--yes` |
| Close | Human pays or accepts in the Wallapop app |

### HITL

| Step | Agent alone | Ask human |
|------|-------------|-----------|
| Search inside mandate | yes | if query vague or budget unset |
| `pursue` / `desk` | yes, including the chat messages | never for each text |
| Publish or delete a listing | no | `--yes` once the questions are answered |
| Pay / accept / meet | **never** | human finishes in the Wallapop app |

Rules:

- `pursue` and `desk` send negotiation chat. Do not ask the human to send.
- Bare `say` / `offer` / `sell` / `unsell` still need `--yes`.
- `--yes` never completes a purchase or accepts a sale.
- If they only asked to look, do not send.
- Ambiguous match or multiple GRABs: ask once with candidates.
- Always present Wallapop shortlists ranked best-first with a markdown link on every item URL.
- Default search is all of Spain. Shipping counts anywhere. Use `walla search --local` only when the human asked for nearby or pickup.
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
| `walla pursue` / `desk` | Message a shortlist and follow the inbox |
| `walla negotiate` | Win-win Spanish draft (never sends) |
| `walla inbox` / `thread` / `say` | Talk (`say` needs `--yes`) |
| `walla offer` | Formal offer (needs `--yes`) |
| `walla sell` / `unsell` | Publish or delete a listing (`--yes`) |
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
