---
name: walla
description: >
  When the user pastes github.com/berendgort/wallapop-cli, wants Wallapop.es
  search, inbox, offers, or chat: install walla, run doctor, have the human
  walla login (paste session cookie), then look / negotiate / talk with
  walla … --json. Never scrape HTML. Never print cookies or tokens. Never pay.
license: MIT
---

# walla — agent skill (follow exactly)

## Bootstrap

```bash
pipx install 'walla-cli[mcp]'   # PyPI: https://pypi.org/project/walla-cli/
walla doctor --json
# If auth.session is false: ask human to run `walla login` and paste cookie
walla instruct --json           # read mandate + hitl.ladder
```

If `mandate.budget` is null, ask once:

```bash
walla setup --lat 41.39 --lon 2.17 --km 30 --budget 400 \
  --aggression fair --must "kite cabrinha" --json
```

## Loop (efficient HITL)

1. Search inside mandate: `walla search "…" --json`
   Optional shortlist share: `--export md,csv,html,pdf --out ./shortlist`
   or later `walla export --format md,csv,html,pdf --out ./shortlist --json`.
2. One GRAB → `walla negotiate <id> --json`. Several GRABs → ask human to pick an id.
3. Show opening + offer_eur + walk_away. Human approves text and EUR.
4. Only then: `walla say … --yes` or `walla offer … --eur N --yes`
5. **Stop.** Human pays or meets in the Wallapop app. `--yes` never means buy.

Reads and negotiate drafts are safe. Sends need confirm. Narrate GRAB/LOOK/PASS + URLs.
