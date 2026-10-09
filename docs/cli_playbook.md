# Playbook: build a public CLI the way fli, guru, walla, and pakket were built

Follow this document in order. The result is a Python library, a Typer CLI, and a FastMCP server for one job. The same steps apply to Mercadona, LinkedIn outreach, Bizneo, WhatsApp, or anything else.

Evidence these steps come from:

- [fli](https://github.com/punitarani/fli): Google Flights library, `fli` CLI, `fli-mcp`. Offline fixtures by default. Live tests are a small canary (`pytest -m live`). Commit `546ab9e` put `error_type` and `retryable` on CLI JSON and MCP.
- [guru](https://github.com/berendgort/guru): commit `45e1b98` scaffolded Windguru by mirroring fli. Later commits added `instruct`, rider intake, sandbox unlock, polite spacing, and the Korotkevich pass. PyPI package `windguru`, command `guru`.
- [wallapop-cli](https://github.com/berendgort/wallapop-cli): same stack. Wire catalog in `fixtures/wire_contracts.json`. Mutations need `--yes`. Draft must not upload unless `--suggest`. Public item URL is the `web_slug`, not the hash. Polite spacing + 429/`Retry-After` + Forbidden circuit.
- [pakketadvies-cli](https://github.com/berendgort/pakketadvies-cli): same envelope, local JSONL instead of HTTP. Humans paste the GitHub link. The agent owns the runtime. Commit `ff8d8d8` fixed cite matching after agents field-tested the CLI.
- [mercadona-cli](https://github.com/berendgort/mercadona-cli), [linkedin-cli](https://github.com/berendgort/linkedin-cli), [bizneo-cli](https://github.com/berendgort/bizneo-cli): same envelope. Stop before pay / send / click. Empty wire catalog means the live mutation stays `unsupported`. Private only when the human says so (Bizneo).

Do not invent a second architecture. Copy this one and change the domain.

Every CLI repo ships a copy of this playbook at `docs/cli_playbook.md`. Keep that file in sync with this one when the bar changes. Household catalog: `AGENT_CLI_STORE.md`.

---

## 0. Create a GitHub repo with `gh`

Do this before the first commit. The account is **berendgort**. Default is **public**. Do not ask the human to click through github.com/new.

```bash
# from an empty project directory, after git init and the first commit
gh repo create berendgort/<name>-cli --public --source=. --remote=origin --description "<one line>"
git push -u origin HEAD
```

Rules:

- Name: `<command>-cli` when the PyPI name may collide (`walla-cli` serves command `walla`). Use the product name when it is free (`windguru` serves command `guru`).
- `gh auth status` must show the `berendgort` account. If it shows another account, stop and say so. Do not create the repo elsewhere.
- Confirm visibility before the push: `gh repo view berendgort/<name>-cli --json visibility,url`. Public is the default. Private only when the human said so in this chat (Bizneo).
- Add `https://github.com/berendgort/<name>-cli` to the README agent section the same day.
- Do not force-push `main`. Do not push secrets (`.env`, `session.json`, cookies).

---

## 1. Name the objective before any endpoint

Write `docs/objective_function.md` first. Ask, in order:

1. What job does this CLI finish for a person?
2. If it works, what is true in their day that was not true before?
3. If JSON, tests, and MCP tool count are perfect and that day is not better, did we succeed? No. Those are proxies.
4. What optimization looks like a better CLI while missing the job?
5. What must never happen even if it raised usage?

Mercadona example. The job is: the household cart holds the right products for a delivery slot they can receive. The human taps pay in the Mercadona app or site. A green schema with the wrong milk is a failure. Never pay from the CLI. Never invent a product id. Never HTML-scrape the shop as the primary path.

Hard constraints go in that file and in `instruct`. They are not comments. Always include: stay polite on rate limits.

---

## 2. Korotkevich / Tourist bar (code)

Every line meets a competitive-programming bar: mathematical clarity, modular purity, machine readability. Sprawling monoliths, circular imports, hidden I/O on import, and ambiguous contracts are forbidden.

Copy `scripts/check_code_quality.py` from walla or guru and retarget the package name. The script is the law. A review comment is not.

### Layers (strict downward DAG)

Lower ranks never import higher ranks. Cycles are fatal.

```text
[10] models                 Frozen Pydantic DTOs. No disk, no clock, no HTTP.
[15] core.exceptions        Exception types only.
[20] http or data           curl_cffi client, polite spacing, headers; or the one JSONL loader.
[30] core                   Envelope, error_type, paths, human_fix. No live calls.
[40] domain                 Pure policy: search rank, cart math, cite, budget, day window.
[50] cli and mcp            Typer and FastMCP. They do not import each other.
```

Same-rank packages (walla `search`, `account`, `hunter`) may not form a cycle. If two domains need each other, extract the shared pure function down into `core` or `models`.

Invariants:

- Zero circular dependencies at module or package level.
- Downward imports only. `models` never imports `core`. `http` never imports `cli`. `search` never imports `mcp`.
- Zero import side effects. No network, no profile read, no client constructed at import.
- Package `__init__.py` files are thin re-exports.
- Type-only upward references use `if TYPE_CHECKING`.

### File size

No file in the package exceeds **250 lines**. Split before you hit the cap. One responsibility per module.

### Functional core, imperative shell

- Parsers, rankers, cookie parsers, and verdict math take data in and return data out.
- HTTP, disk writes, and Typer I/O live in the shell.
- Invalid input fails closed with `ValueError` or a typed error. No silent default that hides a bad id.
- Domain transfers are frozen Pydantic models.

### Credentials

- Never log a bearer token, session cookie, or password.
- Session file mode is `0600`. Path: `~/.config/<name>/session.json` (or `$FOO_HOME`). Atomic write: `tempfile.mkstemp` in the same dir, write, `os.replace`.
- `doctor --json` reports `auth.session` as a boolean, never the secret.
- Login is cookie paste or an explicit token flag. Do not require a `.env` full of passwords. Do not open household `.env` files for CLI auth.
- Fixtures are redacted. No tokens in `fixtures/`.

### Machine readability

- `mypy --strict` passes with 0 errors on the package and on `scripts/check_code_quality.py`.
- Every library module defines `__all__`.
- No em-dash (`\u2014`) or en-dash (`\u2013`) in code or agent-facing strings.
- No bare `print()` except an allowlist: CLI banner, console, catch, MCP entry.

### Gate (run before any "it works" claim)

```bash
python scripts/check_code_quality.py
ruff check .
mypy <package> scripts/check_code_quality.py
pytest -q -m "not live"
```

All four must pass. Do not weaken the script to go green.

---

## 3. Gray / Stonebraker bar (data)

Every stored fact has one writer, one clock, and an idempotent sink. Dual-writes and invented live-API shapes are forbidden.

Jim Gray: put all the eggs in one basket and watch that basket. Exactly-once delivery across two systems does not exist. At-least-once plus an idempotent sink does.

### One mode per fact

| Mode | What | Mutability | Clock |
|---|---|---|---|
| Working | `profile.json`, `session.json`, watches, invite log | mutable | user lifetime |
| Archive | redacted fixtures under `fixtures/` | append on capture | repo life |
| Live | the real API response | read | one request |

No database in v1. No Postgres, Redis, or a second warehouse copy of the same rows. The live API is not a second source of truth for parsers. **Fixtures are.**

Local-archive CLIs (pakket) replace Live with a JSONL basket. One ingest script is the only writer. The CLI only reads. Advice date or snapshot `as_of` is the domain clock. Unknown keys fail at ingest.

### Hard constraints

- One writer. Writing the profile to disk and also to a side cache of the same fields is a defect.
- Declare the grain in `docs/data_engineering_standards.md` before the second feature. Profile: one home, one radius, one budget. Session: tokens only, never the password. Fixture: one captured response, secrets redacted, `schema_version` noted next to the parser.
- Schema-on-write. Pydantic is the contract. Consumers ignore unknown wire keys. Required fields fail closed. A breaking envelope change bumps `api_version` and updates `docs/WIRE.md`.
- Idempotent sinks. Session save overwrites one path. A watch check diffs ids against the stored set. Re-running the same result yields an empty new list. Invite log: one row per person; a repeat updates status and keeps the original day.
- Do not invent a request or response body. If there is no fixture, the call fails with `error_type: unsupported`. Empty wire catalog calls means the live mutation stays unsupported (LinkedIn invite POST, Bizneo clock).
- Trace with non-secret ids (product id, listing id, slug). Never trace the cookie.

Copy `docs/code_quality.md` and `docs/data_engineering_standards.md` into the new repo and replace the package name. The playbook states the bar. Those two files are what `AGENTS.md` points at inside the new repo.

---

## 4. Capture the wire before the feature

1. Reproduce the call in the browser Network panel on the real site.
2. Repeat it with `curl_cffi` (browser impersonation, the headers the site actually requires). Plain curl often 403s (Mercadona search).
3. Redact secrets. Save the response under `fixtures/`.
4. Write a parser test that loads that fixture and checks required fields.
5. Update `docs/WIRE.md` with method, path, required headers, and the body keys.
6. Add the call to a wire catalog (`fixtures/wire_contracts.json`). `scripts/check_code_quality.py` fails if a new `/api/` literal is missing from the catalog.

Never HTML-scrape as the primary path. Never Playwright as the product. Never CDP as the product.

Lessons that are now rules:

- Offer and sell bodies come from fixtures. The "obvious" JSON (`{item_id, amount, currency}`) was HTTP 400. Listing create without `Accept: application/vnd.upload-v2+json` was HTTP 405.
- A draft command stays local. It must not upload photos or open a remote session unless the user passed an explicit flag (`walla sell --suggest`).
- Public URLs use the site's slug, not an opaque internal hash.
- Category and product pickers accept a human name and return candidates when ambiguous. Numeric ids are optional. Duplicate keys raise `ambiguous` before a name fallback (LinkedIn resolve).
- No fixture means `unsupported`, not a generated stand-in. Inventing Bizneo clock blocks presented them as worked time. That is a defect. Delete the generator; refuse with a human_fix recipe.

---

## 5. Rate limits (required)

Every CLI that dials a network must respect rate limits. A local-only CLI (pakket) still classifies `rate_limited` in the envelope so agents share one contract. Policy caps (LinkedIn daily/weekly) are rate limits too.

### What the HTTP client must do

1. **Minimum interval** between outbound dials (one process-wide clock). Default from an env knob, documented in `docs/WIRE.md` (walla: `WALLA_MIN_INTERVAL=1.0`; merca: 0.3 s; guru: `GURU_MIN_INTERVAL`).
2. **Honor `Retry-After`** on HTTP 429. Sleep that many seconds when present, then raise or retry with a bounded attempt count. Never spin.
3. **Map 429** to `error_type: rate_limited` with `retryable: true` and `retry_after_s` when the header exists.
4. **Circuit on hard bans** (403 Forbidden / anti-scrape body). Trip for `CIRCUIT_TTL`, refuse further dials, classify as `rate_limited` with `retryable: false` when it is an IP ban (guru). Document the knob.
5. **Short TTL GET cache** when the same read repeats inside one process (optional but preferred; walla and guru do this).
6. **Do not blast.** Reads may be exercised during development. Writes once against a safe target. Never loop offers, invites, or chat sends to probe.

Domain policy caps (LinkedIn): hard daily 15, soft target 8-12, weekly 80, rest days, accept-rate gate. Those live in pure policy with offline tests. They are not a substitute for HTTP spacing once a send path exists.

### What to test (offline, default gate)

Ship `tests/test_polite.py` (or equivalent). Cover at least:

| Test | Assert |
|---|---|
| Spacing | Two `wait_turn` calls with `min_interval=0.15` take at least ~0.14 s |
| 429 classify | Fake transport returns 429 → `error_type: rate_limited`, `retryable: true` |
| `Retry-After` | Header `"2"` surfaces as `retry_after_s == 2` (or client sleeps then succeeds on next fake) |
| Circuit | After a Forbidden trip, a second dial does not hit the transport |
| Cache (if present) | Identical GET hits the transport once |
| Env knobs | Documented names appear in `docs/WIRE.md` or `docs/rate_limit_analysis.md` |
| Policy caps (if any) | Budget at the hard cap returns `remaining == 0`; accept-rate throttle tested with pinned dates |

Classify tests stay offline. Fake the transport. Do not hit the live site in the default gate.

### What to test (live, opt-in)

Mark `pytest -m live`. A bounded probe only:

- Small fixed burst (for example 8 spaced reads).
- Stop at the first 429. Do not continue the burst.
- Assert either no 429, or the last status is 429 and the envelope is `rate_limited`.
- Write observed numbers into `docs/rate_limit_analysis.md` (walla pattern). Do not invent a limit you did not measure.

`scripts/probe_rate.py` is allowed as a manual tool. It must stop at the first 429 and must not hammer.

### Envelope and docs

- `error_type` includes `rate_limited`. Agents slow down or stop; they do not retry in a tight loop.
- `docs/WIRE.md` lists the spacing env vars and the 429 behavior.
- `docs/objective_function.md` lists "stay polite on rate limits" in the never-list / constraints.
- `check_code_quality.py` may ban tokens that mean browser automation (`playwright`, CDP ports) so agents do not "fix" rate limits by switching to a browser hammer.

---

## 6. Scaffold

```text
<pkg>/
  models/          frozen DTOs
  http/            client, polite spacing, headers
  core/            envelope, errors, paths, human_fix, instruct
  <domain>/        pure use-cases (catalog, basket, cite, budget, day)
  cli/             Typer commands, Rich, --json
  mcp/             FastMCP tools, same functions, no CLI import
scripts/check_code_quality.py
scripts/dogfood_run.py
fixtures/
docs/cli_playbook.md          # copy of this playbook
docs/WIRE.md
docs/objective_function.md
docs/code_quality.md
docs/data_engineering_standards.md
docs/rate_limit_analysis.md   # when the CLI dials a network
skills/<name>/SKILL.md
AGENTS.md
README.md        agent protocol first
```

Every new CLI copies this playbook to `docs/cli_playbook.md` on day one. When you change the bar here, update that file in each sibling repo the same day (or open a PR that does). `AGENTS.md` must link to `docs/cli_playbook.md`.

Mercadona sketch (names only):

- `merca/catalog` searches products.
- `merca/basket` adds lines. Add requires `--yes`.
- `checkout` prints the slot and stops. The human pays. Doctor field `pays: false`.

`pyproject.toml`: MIT, Python `>=3.10`, extras `[mcp]` and `[dev]` (`pytest`, `ruff`, `mypy`). Console script is the short command. Author: Dr. Berend Gort, berend.gort@gmail.com.

README agent section (required, matches `instruct`):

1. `pipx install '<dist>[mcp]'` from PyPI. Clone only when hacking.
2. `<cmd> doctor --json`. Never print tokens.
3. If `error_type: auth`, one human fix: paste the session cookie. Agents may pass `--cookie` without putting the value in the chat log.
4. `<cmd> instruct --json`, then do the task with `--json`.
5. Narrate the result. Do not dump raw JSON on the human.

Optional MCP: `{ "mcpServers": { "<name>": { "command": "<name>-mcp" } } }`. MCP is the same library. It is not a second product. Shell CLI is the default path (guru).

---

## 7. Agent contract

Envelope for every `--json` command and every MCP tool:

```text
ok: bool
api_version: int
data: object            when ok
error: str              when not ok
error_type: str         auth | ambiguous | not_found | rate_limited |
                        validation_error | unsupported | parse_error |
                        timeout | http_error | error
retryable: bool
```

`instruct --json` returns the recipe: objective, commands, which steps the agent may take alone, which need `--yes`, and what the human must finish in the real app.

Ambiguous input returns `error_type: ambiguous` plus `candidates`. Never silent first-match (guru spots, pakket cite, walla categories, LinkedIn leads).

`doctor --json` reports booleans: session present, network reachable, version, and the stop flags that matter (`pays`, `sends`, `clicks`). On a sandbox that cannot reach the API, unlock or print one `human_fix` recipe. Do not dump a tutorial before that attempt (guru unlock).

Auth and unsupported include `human_fix`. Never print cookie or token.

---

## 8. Writes

| Kind | Flag | Example |
|---|---|---|
| Read | none | search, item, instruct, doctor, act (decision only) |
| Mutate | `--yes` | cart add, send message, publish listing, delete |
| Pay / accept / place the real order / click the clock | never from a missing fixture | human finishes in the app; CLI sets `stopped_before_*` |

A loop may send negotiation text without a per-message prompt only when the objective says so (walla `pursue` and `desk`). It still never pays.

Preview/draft performs no network unless a named flag says so. `prepare --yes` that cannot send returns a draft with `stopped_before_send: true` and does not append the invite log.

Household automations call the CLI and assert the stop flag. They do not browser-automate around it.

---

## 9. Offline tests, then the parallel dogfood loop

Unit tests do not prove the CLI. After the gate is green, agents must drive the **installed command**.

### Offline first

- One parser test per fixture.
- CLI tests invoke Typer with `--json` and assert `ok` and `error_type` (auth missing, `--yes` missing, ambiguous).
- Polite / rate-limit tests from section 5 are in the default gate.
- `pytest -m "not live"` never touches the network.
- Live tests are marked `live` and stay out of the default gate. A write against production needs an env flag such as `WALLA_LIVE_WRITE=1`.

### Flow matrix

Build the matrix from `instruct` and `<cmd> --help`. One row per behavior:

- happy path
- empty result
- auth missing (`error_type: auth`, no secret in stdout)
- ambiguous id (`candidates`, no silent pick)
- validation error
- mutation without `--yes` (must refuse)
- mutation with `--yes` against a fixture or a dry-run, not a real charge
- rate limited (fake 429 → envelope)
- unsupported path when wire is missing (send, clock, pay)
- doctor / instruct shape, including stop flags

Seed pattern: `scripts/dogfood_run.py` runs one scenario as a subprocess of `.venv/bin/<cmd> --json` and writes a JSON report. Each new CLI gets the same script. One scenario, one process, one report file.

### Parallel agents

After the binary exists, launch one Cursor agent per matrix row. They run at the same time.

Each agent:

- Receives the binary path, the exact argv, and the expected `ok` / `error_type`.
- May only run the CLI. It must not edit code, must not pay, and must not place a real order.
- Returns: argv, exit code, parsed envelope, and one line on whether a human was asked to do agent work.

The parent agent:

- Reads every report.
- A failure becomes a fixture or a regression test, then a code fix. Do not "fix" by weakening the expected `error_type`.
- Re-run the failed rows, then the full matrix.
- Stop only when every row passes.

### CodeRabbit, then stop

When the matrix is green, review the diff. On a root commit with no useful parent, use an empty-parent `/tmp` clone (init, allow-empty on `main`, branch `review`, rsync source excluding `.git` / `.venv` / `*.egg-info`, then `coderabbit review --agent --base main`). Do not set git config. Do not force-push.

```bash
coderabbit review --agent --base-commit <sha-before-this-work>
# or --base main in the /tmp empty-parent method
```

Fix every finding, including minor ones, unless the finding is invalid after checking the code. Re-review until `review_completed` reports `findings: 0`. Trust that JSON over a stale `coderabbit review findings` dump. Free CLI allowance is 3 reviews; on rate limit wait the stated `waitTime` and retry.

Do not ship with a known finding left open because it is "minor". Do not invent hours, invite bodies, or pay paths to silence a finding; refuse with `unsupported` instead.

---

## 10. Ship only when the human asked

```bash
# bump version in pyproject.toml and the package __version__
python scripts/check_code_quality.py && ruff check . && mypy <package> && pytest -q -m "not live"
git add <files>
git commit
git push -u origin HEAD
# PyPI upload with the token already on the machine. Never print the token.
pipx install '<dist>[mcp]' --force
```

Deploy means PyPI **and** `git push` (guru commit `094fdc7`). Do not push and do not publish unless the human asked in this chat. Do not force-push `main`. Do not rebuild a published package without permission.

---

## 11. Definition of done

- Repo `berendgort/<name>-cli` exists. Visibility matches what the human asked (`PUBLIC` default; private only when stated).
- `docs/cli_playbook.md` is present (copy of this playbook). `AGENTS.md` links to it.
- `docs/objective_function.md` states the human outcome, the never-list, and polite rate limits.
- `docs/code_quality.md` and `docs/data_engineering_standards.md` match sections 2 and 3. `scripts/check_code_quality.py` enforces them.
- `docs/WIRE.md` matches fixtures. No invented body. Spacing / 429 knobs documented.
- Network dialers have polite spacing + offline rate-limit tests (section 5). Live probe is opt-in and bounded.
- `instruct --json` and the README agent section agree.
- The four-command gate is green.
- Every dogfood row passed under a real CLI subprocess.
- CodeRabbit on that diff reports zero findings.
- The human was not asked to install Python, pip, or click through GitHub unless the product truly needs one cookie paste.

---

## Learned

| Date | Pattern |
|---|---|
| 2026-10-09 | Empty wire catalog → live mutation stays `unsupported`. Do not invent invite POST, clock blocks, or pay. |
| 2026-10-09 | Stop flags in doctor and data: `pays`, `sends`, `clicks`, `stopped_before_pay` / `_send` / `_click` / `_submit`. Automations assert them. |
| 2026-10-09 | Private repo only when the human says so. Confirm with `gh repo view --json visibility`. |
| 2026-10-09 | CodeRabbit on a root commit needs an empty-parent `/tmp` review. Trust `review_completed` JSON. Wait out free-tier `waitTime`. |
| 2026-10-09 | Every CLI carries `docs/cli_playbook.md`. Rate-limit spacing, 429, Retry-After, and circuit are required and tested offline. |
