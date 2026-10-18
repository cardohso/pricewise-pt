"""What is being priced: one listing of an item."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Item:
    item_id: str
    group_id: str  # listings of the same physical item share it
    category: str
    age_years: float
    usage: float  # e.g. distance travelled or hours of use
    listed_on: date
    price: float
    condition: str | None = None  # "good" | "fair" | "poor" | None (unknown)


def age_band(item: Item) -> str:
    return "<5y" if item.age_years < 5 else "5-10y" if item.age_years < 10 else "10y+"


def numeric(item: Item) -> dict[str, float]:
    age = max(item.age_years, 0.25)
    return {
        "age": age,
        "log_usage": math.log1p(max(item.usage, 0.0)),
        "usage_per_year": item.usage / age / 10_000,
    }


def categorical(item: Item) -> dict[str, str | None]:
    return {"category": item.category, "condition": item.condition}
