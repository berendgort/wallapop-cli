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
walla categories --find escritorio --json
walla sell ./shot1.jpg ./shot2.jpg --title "Escritorio madera" --suggest --json
```

`--suggest` (or draft with `--title` and no `--category`) asks Wallapop to prefill
`category_leaf_id` from title+photos. Ask remaining `data.questions`, then:

```bash
walla sell ./shot1.jpg ./shot2.jpg \
  --title "…" --desc "…" --eur 40 \
  --category escritorio --condition good \
  --floor 35 --yes --json
```

`--category` accepts a leaf id **or** name tokens. `--root` is optional.
`--floor` is the lowest EUR desk may accept.

Then:

```bash
walla desk --watch --seconds 45 --rounds 12 --json
```

Desk answers buyers until `stack.best` converges or rounds end. Show the title,
agreed EUR, `stack.why`, and the item link.

The human accepts the sale in the Wallapop app. `walla unsell <id> --yes` deletes
a listing. Never mark the item sold from walla.
