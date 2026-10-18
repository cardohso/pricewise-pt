"""The baseline every model has to beat: the median price of similar items
(same category, age within a year, usage within 20%)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from pricewise.valuation.items import Item

AGE_TOLERANCE = 1.0
USAGE_TOLERANCE = 0.20
MIN_COMPARABLES = 3


def similar(pool: Sequence[Item], target: Item) -> list[Item]:
    return [
        i
        for i in pool
        if i.group_id != target.group_id
        and i.category == target.category
        and abs(i.age_years - target.age_years) <= AGE_TOLERANCE
        and abs(i.usage - target.usage) <= USAGE_TOLERANCE * max(target.usage, 1.0)
    ]


def estimate(pool: Sequence[Item], target: Item) -> float | None:
    comps = similar(pool, target)
    return statistics.median(i.price for i in comps) if len(comps) >= MIN_COMPARABLES else None
