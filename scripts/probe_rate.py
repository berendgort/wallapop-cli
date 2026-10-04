#!/usr/bin/env python3
"""Bounded live rate probe. Stops at first 429. Does not hammer."""

from __future__ import annotations

import json
import sys

from walla.core.exceptions import WallaRateLimitError
from walla.http.client import HttpClient
from walla.http.polite import reset_polite


def main() -> int:
    reset_polite()
    client = HttpClient()
    results: list[dict[str, object]] = []
    for i in range(10):
        try:
            client.get(
                "/api/v3/search",
                params={
                    "source": "search_box",
                    "keywords": "silla",
                    "latitude": 41.39,
                    "longitude": 2.17,
                },
                use_cache=False,
            )
            results.append({"i": i, "status": 200})
        except WallaRateLimitError as exc:
            results.append(
                {
                    "i": i,
                    "status": 429,
                    "retry_after_s": exc.retry_after_s,
                }
            )
            break
        except Exception as exc:  # noqa: BLE001
            results.append({"i": i, "error": str(exc)})
            break
    print(json.dumps({"ok": True, "results": results}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
