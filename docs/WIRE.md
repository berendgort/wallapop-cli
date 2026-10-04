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

`GET https://api.wallapop.com/api/v3/categories` — top-level tree.

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

Writes that fail closed as `error_type: unsupported` until fixtures exist.

## Rate limits

Default spacing: `WALLA_MIN_INTERVAL=1.0` s. Honor `Retry-After` on 429.
Repeated 403 opens a circuit (`WALLA_CIRCUIT_TTL`). See
[`rate_limit_analysis.md`](rate_limit_analysis.md).
