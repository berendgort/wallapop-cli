---
name: walla
description: >
  When the user pastes github.com/berendgort/wallapop-cli, wants Wallapop.es
  search, inbox, offers, or chat: install walla from the private clone, run
  doctor/login from WALLAPOP_USER/WALLAPOP_PW, then look / offer / talk with
  walla … --json. Never scrape HTML. Never print the password.
license: MIT
---

# walla — agent skill (follow exactly)

## Bootstrap

```bash
pipx install -e '.[mcp]'   # in the clone
walla doctor --json
walla login --json         # reads .env; on auth failure use --cookies
walla instruct --json
```

## Loop

- Look → `walla search` / `walla item`
- Talk → `walla inbox` / `walla thread` / `walla say … --yes`
- Offer → `walla offer … --eur N --yes`

Reads are safe. Sends need confirm. Narrate GRAB/LOOK/PASS + item URLs.
