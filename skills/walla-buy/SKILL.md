---
name: walla-buy
description: >
  Buy on Wallapop.es without asking the human to send messages. Use when the
  user wants to find an item, negotiate, watch seller replies, or hear which
  offer to take. Runs walla pursue and walla desk. The human only closes the
  deal in the app.
license: MIT
---

# Buy

Do not ask the human to approve text, pick a chat, or press send.
`walla pursue` and `walla desk` send the messages.

```bash
walla pursue "tabla cabrinha 10m" --json
walla desk --json
```

1. `pursue` searches Spain-wide inside the budget, messages the best GRAB/LOOK
   listings, and stores them. `--local` only if the human asked for nearby or pickup.
2. `desk` reads the inbox **once**, replies where the seller spoke, and moves
   the price toward agreement without going over the ceiling.
3. Repeat `walla desk --json` when you need a fresh read. Do not call
   `walla inbox` once per chat.
4. When `stack.best` is set, show the human:
   - the title and agreed EUR
   - `stack.why`
   - a markdown link to `url`
   - the other converged rows, cheaper first
5. Stop. The human pays or meets in the Wallapop app.

`walla negotiate <id>` is a draft if you need to inspect one number.
Do not use `walla say` or `walla offer` for this loop.
