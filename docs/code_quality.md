# Engineering Standard: The Korotkevich / Tourist Bar

Every line in `walla` must meet a competitive-programming bar: mathematical
clarity, modular purity, machine readability. Sprawling monoliths, circular
imports, hidden I/O on import, and ambiguous contracts are forbidden.

Automated enforcement: `python scripts/check_code_quality.py`

---

## 1. Architectural Layers & Dependency Hierarchy

Strict downward DAG. Lower ranks never import higher ranks. Cycles are fatal.

```
[10] walla.models          Pydantic DTOs only
[20] walla.http            curl_cffi client, polite spacing, headers
[30] walla.core            Envelope, errors, paths, dotenv, human_fix
[40] walla.search          Public look (search / item / categories)
[40] walla.account         Session, inbox, say, offer, favorites
[40] walla.hunter          Profile, watches, GRAB / LOOK / PASS
[50] walla.cli · walla.mcp Typer + FastMCP entrypoints
```

### Invariants

- **Zero Circular Dependencies**: No cycles at module or package level.
- **Downward Imports Only**: Higher layers may import lower; never reverse
  (e.g. `search` never imports `cli`, `models` never imports `core`).
- **Zero Import Side Effects**: No network, disk profile I/O, or client
  construction on import.
- **Facades**: Package `__init__.py` files stay thin re-exports.
- Use `if TYPE_CHECKING:` for type-only upward references.

---

## 2. Hard File Size Cap: <= 250 Lines of Code

No file in `walla/` exceeds **250 lines**. When a module approaches the limit,
split into single-responsibility submodules behind an `__init__.py` facade.

---

## 3. Functional Core, Imperative Shell

- Pure parsers, verdict math, and cookie parsers take data in and return data out.
- HTTP, disk session writes, and Typer I/O live in the shell.
- Fail closed (`ValueError` / typed `WallaError`) on invalid input.
- Prefer frozen pydantic models for domain transfers.

---

## 4. Credential Zero-Trust

- Never log, print, or persist `WALLAPOP_PW`.
- Never log a bearer access token or the NextAuth session cookie value.
- Session file (`~/.config/walla/session.json`) is mode `0600`.
- `doctor` reports `auth.configured` as a boolean, never the secret.
- Redacted fixtures only. No tokens in `fixtures/`.

---

## 5. Machine Readability & Type Enforcement

- `mypy --strict` passes with 0 errors across `walla/`.
- Every library module defines `__all__`.
- No unicode em-dash (`\u2014`) or en-dash (`\u2013`) in code or messages.
- No bare `print()` in application code (CLI banner / catch helpers may write
  to the Rich console; the quality script allowlists those files).

---

## 6. Verification Commands

```bash
python scripts/check_code_quality.py
ruff check .
mypy walla scripts/check_code_quality.py
pytest -q -m "not live"
```
