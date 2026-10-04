# Why these numbers

One clock for outbound Wallapop dials. The polite client
([`walla/http/polite.py`](../walla/http/polite.py)) serializes requests with
`WALLA_MIN_INTERVAL` (default **1.0 s**), keeps a short TTL cache
(`WALLA_CACHE_TTL`, default 60 s), and opens a Forbidden circuit on 403.

## Observed

Live probe (`pytest -m live` / `scripts/probe_rate.py`) against
`GET /api/v3/search` with browser-like headers (2026-10-04, ES IP):

- Eight spaced reads at 1 s completed without 429.
- On 429 the client raises `error_type: rate_limited`, `retryable: true`, and
  `retry_after_s` from `Retry-After` when present.
- Missing `Retry-After` still backs off via tenacity (bounded attempts).

Do not blast. Do not loop offers or chat sends. Reads may be exercised many
times during development; writes once against a safe target.

## Knobs

| Env | Default | Role |
|---|---|---|
| `WALLA_MIN_INTERVAL` | 1.0 | Minimum seconds between dials |
| `WALLA_CACHE_TTL` | 60 | GET response cache |
| `WALLA_CIRCUIT_TTL` | 3600 | Stop window after 403 |
| `WALLA_CACHE_MAX` | 256 | Cache entry cap |
