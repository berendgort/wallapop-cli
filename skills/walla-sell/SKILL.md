---
name: walla-sell
description: >
  Sell on Wallapop.es. Use when the user drops photos, wants a listing, or
  wants buyer chats negotiated. Publishes with walla sell --yes after the
  questions are answered, then walla desk replies to buyers. The human accepts
  the sale in the app.
license: MIT
---

# Sell

Do not ask the human to type buyer replies. Desk sends those.

```bash
walla sell ./shot1.jpg ./shot2.jpg --json
```

Ask every question in `data.questions`, then publish once:

```bash
walla sell ./shot1.jpg ./shot2.jpg \
  --title "…" --desc "…" --eur 40 \
  --category 10105 --root 12579 --condition good \
  --floor 35 --yes --json
```

`--floor` is the lowest EUR desk may accept. Omit it to hold the asking price.
Category ids come from `walla categories --json`.

Then:

```bash
walla desk --json
```

Desk reads the inbox once and answers buyers. Repeat desk until `stack.best`
is a sell row. Show the title, agreed EUR, `stack.why`, and the item link.

The human accepts the sale in the Wallapop app. `walla unsell <id> --yes` deletes
a listing. Never mark the item sold from walla.
