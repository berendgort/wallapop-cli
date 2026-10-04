# Wire capture — Wallapop consumer API

Unofficial. Captured against `es.wallapop.com` / `api.wallapop.com` (2026-10-04).
Re-verify before trusting after a long gap.

## Headers (public)

Required: `X-DeviceOS: 0`. Browser `User-Agent` + `Origin`/`Referer` of
`https://es.wallapop.com` work. Do not invent an `X-Signature` for search.

## Search

`GET https://api.wallapop.com/api/v3/search`

Params: `source=search_box`, `keywords`, `latitude`, `longitude`, `order_by`
(`most_relevance` | `newest` | `closest` | price variants), optional
`min_sale_price`, `max_sale_price`, `category_id`, `next_page`.

Response: `data.section.payload.items[]` (40/page), `meta.next_page` opaque JWT.
Item fields include `id`, `title`, `description`, `price.amount`, `web_slug`,
`location`, `reserved.flag`, `shipping`, `created_at`.

Public URL: `https://es.wallapop.com/item/<web_slug>`.

## Item

`GET https://api.wallapop.com/api/v3/items/{id}` — detail with
`title.original`, `description.original`, `slug`, `share_url`, `user`, counters.

## Categories

`GET https://api.wallapop.com/api/v3/categories` — nested tree
(`subcategories[]`). CLI: `walla categories --find escritorio --json` returns
`leaf_id` + `root_id`. Sell accepts `--category <leaf-or-name>`; `--root` is
optional.

After `current_step=photo`, the steps `draft` may include `category_leaf_id`
(title+photo hint). `GET /api/v3/suggested-item-data/{upload_id}` often returns
empty HTTP 200; still poll before `loading`. CLI: `walla sell … --title …
--suggest` (explicit only; draft without `--suggest` does not upload).
`walla desk --watch` polls the inbox until `stack.best` converges.

## Auth

`POST https://api.wallapop.com/api/v3/access/login` with
`{"username","password"}` — live probe returned **HTTP 400 empty body**
(`x-wallapop-service: auth`) for the configured account. Treat as MFA /
Keycloak. Fallback: import `__Secure-next-auth.session-token` and mint via
`GET https://es.wallapop.com/api/auth/session` → `{ token }`.

Refresh: `POST /api/v3/access/refresh` with `{ refresh_token }` when password
login ever succeeds.

## Messaging / offers (auth)

- Open chat (listing **Chat** button): `POST /api/v3/conversations`
  body `{ "item_id": "<hash>" }` → `{ conversation_id, item_id, other_user_id, channel }`.
- Inbox: `GET /bff/messaging/inbox?page_size=&max_messages=` (not `/api/v3/conversations`, 405).
- Send text: PubNub publish after `GET /api/v3/instant-messaging/token`
  (REST `…/messages` is 404). See `walla.account.chat.publish_text`.
- Offers: `POST /api/v3/delivery/buyer/offers` with
  `{offer_id, offer_price_amount, offer_price_currency, item_ids}`.
  Requires header `X-AppVersion` (without it Wallapop returns a generic HTTP 400).
  Fixture: `fixtures/offer_buyer_request.json`. The old
  `{item_id, amount, currency}` body returns **HTTP 400** — forbidden.
  Some sellers disable offers → **409** `offer creation not allowed`; fall back to chat text.
- Favorites: `/api/v3/users/me/favorites`, `/api/v3/items/{id}/favorite`

## Sell / Vender (auth)

Browser: `https://es.wallapop.com/app/catalog/upload/consumer-goods`.

1. `POST /api/v3/steps` `{mode:{action:"upload",id:<uuid>}}` → step `title`
2. `POST /api/v3/steps` `current_step=title` draft `{title}` → `photo`
3. `POST /api/v3/upload/{upload_id}/pictures` multipart `file` → **204**
4. `POST /api/v3/steps` `current_step=photo` → `category`
5. `POST /api/v3/steps` `current_step=category` draft
   `{title, category_leaf_id, root_category_id}` (**ids as strings**) → `loading`
6. Poll `GET /api/v3/suggested-item-data/{upload_id}` (404 then empty 200)
7. `POST /api/v3/steps` `current_step=loading` → `listing`
8. Create: `POST /api/v3/items` multipart `image` + `item` (JSON string).
   Header **`Accept: application/vnd.upload-v2+json`** (without it → HTTP 405).
   Extra photos: `POST /api/v3/items/{id}/picture2` multipart `image` + `order`.
9. Delete: `DELETE /api/v3/items/{id}` → 204.

Fixture: `fixtures/sell_item_request.json` / `walla.account.sell_wire.build_item_body`.

Every CLI call (method, path, auth, body) is listed in `fixtures/wire_contracts.json`.
`scripts/check_code_quality.py` fails if `walla/account`, `walla/search`, or `walla/http`
grows a `/api/` or `/bff/` literal that the catalog does not list.
CLI: `walla sell photo.jpg … --yes` (draft without `--yes`).

Writes that fail closed as `error_type: unsupported` until fixtures exist.

## Rate limits

Default spacing: `WALLA_MIN_INTERVAL=1.0` s. Honor `Retry-After` on 429.
Repeated 403 opens a circuit (`WALLA_CIRCUIT_TTL`). See
[`rate_limit_analysis.md`](rate_limit_analysis.md).
