---
name: walla
description: >
  Router for Wallapop.es. Use when the user pastes github.com/berendgort/wallapop-cli
  or the task is mixed. Install walla, run doctor, have the human walla login
  (paste the session cookie), then follow skills/walla-buy or skills/walla-sell.
  Never scrape HTML. Never print cookies or tokens. Never pay or accept a deal.
license: MIT
---

# walla — router

One CLI does the work. Skills only say which command to run.

```bash
pipx install 'walla-cli[mcp]'
walla doctor --json
walla instruct --json
```

If `auth.session` is false, the human runs `walla login` and pastes the cookie.
If `mandate.budget` is null and this is a buy, ask once:

```bash
walla setup --lat 41.39 --lon 2.17 --km 30 --budget 400 \
  --aggression fair --must "kite cabrinha" --json
```

| Task | Skill |
|------|--------|
| Find items, message sellers, follow the inbox, pick a price | `skills/walla-buy/SKILL.md` |
| Publish a listing, answer buyers, pick a price | `skills/walla-sell/SKILL.md` |

The human closes the deal in the Wallapop app. walla never pays and never taps Accept.
