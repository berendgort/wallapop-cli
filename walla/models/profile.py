"""Category and profile models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = (
    "Aggression",
    "Category",
    "Profile",
)

Aggression = Literal["soft", "fair", "firm"]


class Category(BaseModel):
    id: int
    name: str
    icon: str | None = None
    vertical_id: str | None = None
    subcategories: list[Category] = Field(default_factory=list)


class Profile(BaseModel):
    schema_version: int = 1
    lat: float | None = None
    lon: float | None = None
    km: float = 30.0
    pickup_km: float = 30.0
    label: str | None = None
    max_price: float | None = None
    budget: float | None = None
    aggressiveness: Aggression = "fair"
    must_match: list[str] = Field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def spend_cap(self) -> float | None:
        return self.budget if self.budget is not None else self.max_price

    def intake_prompt(self) -> str:
        return (
            "lat=41.39 lon=2.17 km=30 pickup_km=30 label=Barcelona "
            "budget=250 aggressiveness=fair must=kite"
        )
