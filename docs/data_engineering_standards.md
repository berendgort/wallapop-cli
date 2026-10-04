# Data Engineering Standard: The Gray / Stonebraker Bar

Every stored fact in `walla` has one writer, one clock, and an idempotent sink.
Dual-writes and invented live-API shapes are forbidden.

Jim Gray: put all the eggs in one basket and watch that basket. Exactly-once
delivery across two systems does not exist. At-least-once plus an idempotent
sink does.

Code shape: [`code_quality.md`](code_quality.md). Wire truth: [`WIRE.md`](WIRE.md).

---

## 1. Modes (one mode per fact)

| Mode | What | Mutability | Clock |
|---|---|---|---|
| Working | `profile.json`, `watches.json`, `session.json` | mutable | user lifetime |
| Archive | redacted fixtures under `fixtures/` | append on capture | repo life |
| Live | `api.wallapop.com` responses | read | request |

There is no database in v1. Do not stand up Postgres, Redis, or a second
warehouse copy of listings. The live API is not a second source of truth for
parsers: fixtures are.

---

## 2. Hard Constraints

### One writer, no dual-write

A fact has one commit. Writing profile to disk *and* inventing a parallel cache
file for the same fields is a defect.

### Declared grain

- Profile: one home point, one search radius, one pickup radius.
- Watch: one keyword query + optional filters; seen listing ids are a set.
- Session: tokens / cookie fields only. Never the password.
- Fixture: one captured response shape, secrets redacted, `schema_version` in
  the companion parser module docstring.

### Schema-on-write

Pydantic models are the contract. Unknown wire keys are ignored by consumers;
required fields fail closed. Breaking change = bump `api_version` on the
CLI/MCP envelope and update `docs/WIRE.md`.

### Idempotent sinks

- Session save overwrites the same path.
- Watch `check` diffs new ids against the stored set and merges; re-running
  with the same results yields an empty new list.
- Fixture capture scripts overwrite named files intentionally.

---

## 3. Functional Core, Imperative Shell

Pure:

- Listing parsers, category parsers, GRAB / LOOK / PASS scoring
- Cookie export parsers, JWT expiry reads (unverified claims)

Shell:

- HTTP via `walla.http`
- Profile / session / watch file I/O
- CLI and MCP

---

## 4. Credential hygiene

- Working session holds access/refresh or NextAuth cookie. Password never
  lands on disk.
- Archive fixtures never contain tokens, cookies, or passwords.
- Trace with non-secret ids (`listing.id`, `conversation.id`).

---

## 5. Verification

```bash
python scripts/check_code_quality.py
pytest -q tests/test_parsers.py tests/test_session_store.py tests/test_watches.py
```
