"""Session and messaging models."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = (
    "Conversation",
    "Message",
    "OfferQuote",
    "SessionData",
)


class SessionData(BaseModel):
    schema_version: int = 1
    access_token: str | None = None
    refresh_token: str | None = None
    session_cookie: str | None = None
    device_id: str | None = None
    user_id: str | None = None
    micro_name: str | None = None
    expires_at: float | None = None


class Conversation(BaseModel):
    id: str
    item_id: str | None = None
    item_title: str | None = None
    other_user: str | None = None
    unread: int = 0
    last_message: str | None = None


class Message(BaseModel):
    id: str | None = None
    text: str
    from_self: bool = False
    created_at: int | None = None


class OfferQuote(BaseModel):
    item_id: str
    offer_eur: float
    protection_eur: float
    shipping_eur: float
    total_eur: float
    within_pickup: bool = True
