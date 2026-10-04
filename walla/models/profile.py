"""Category and profile models."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = (
    "Category",
    "Profile",
)


class Category(BaseModel):
    id: int
    name: str
    icon: str | None = None
    vertical_id: str | None = None


class Profile(BaseModel):
    schema_version: int = 1
    lat: float | None = None
    lon: float | None = None
    km: float = 30.0
    pickup_km: float = 30.0
    label: str | None = None
    max_price: float | None = None
    budget: float | None = None

    @property
    def ready(self) -> bool:
        return self.lat is not None and self.lon is not None

    def intake_prompt(self) -> str:
        return (
            "lat=41.39 lon=2.17 km=30 pickup_km=30 label=Barcelona budget=250"
        )
