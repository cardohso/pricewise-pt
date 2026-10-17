"""A synthetic market, so everything here runs without real data.

Each category has its own base price and depreciation. Prices fall with age
and usage, condition moves them, and the noise grows with age (old items
vary more). About 15% of items are listed twice (a relisting a few weeks
later, a little cheaper): the duplicates a row-level split leaks. Prices
drift up slowly over the year, which a time split has to cope with.

The numbers are made up. Results on this data say nothing about any real
market; they show that the method behaves as it should.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np

from pricewise.valuation.items import Item

CATEGORIES = {        # name: (base price, yearly depreciation, usage elasticity)
    "compact": (19_000, 0.11, 0.10),
    "hatchback": (15_000, 0.12, 0.09),
    "crossover": (24_000, 0.10, 0.11),
    "estate": (21_000, 0.12, 0.12),
    "electric": (30_000, 0.15, 0.16),
}
CONDITION = {"good": 1.05, "fair": 1.0, "poor": 0.85}
START = date(2025, 1, 1)
DRIFT_PER_DAY = 0.0002          # ~7% a year
RELIST_SHARE = 0.15


def generate(n: int = 4_000, seed: int = 7) -> list[Item]:
    rng = np.random.default_rng(seed)
    names = list(CATEGORIES)
    items: list[Item] = []
    for k in range(n):
        cat = names[rng.integers(len(names))]
        base, dep, elasticity = CATEGORIES[cat]
        age = float(rng.uniform(0.5, 15))
        usage = float(max(1_000, age * rng.lognormal(math.log(14_000), 0.35)))
        condition = rng.choice(list(CONDITION), p=[0.3, 0.55, 0.15])
        listed = START + timedelta(days=int(rng.integers(0, 365)))
        noise = rng.normal(0, 0.06 + 0.012 * age)
        price = (base * math.exp(-dep * age) * (usage / (age * 14_000)) ** -elasticity
                 * CONDITION[condition] * math.exp(DRIFT_PER_DAY * (listed - START).days)
                 * math.exp(noise))
        price = round(max(price, 500), -1)
        hidden = None if rng.random() < 0.2 else str(condition)     # not every ad says
        group = f"g{k}"
        items.append(Item(f"i{k}", group, cat, round(age, 2), round(usage), listed, price,
                          hidden))
        if rng.random() < RELIST_SHARE:
            later = listed + timedelta(days=int(rng.integers(14, 60)))
            items.append(Item(f"i{k}r", group, cat, round(age + (later - listed).days / 365, 2),
                              round(usage), later, round(price * rng.uniform(0.94, 1.0), -1),
                              hidden))
    return items


def write_csv(items: list[Item], path) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "group_id", "category", "age_years", "usage", "listed_on",
                    "price", "condition"])
        for i in items:
            w.writerow([i.item_id, i.group_id, i.category, i.age_years, i.usage,
                        i.listed_on.isoformat(), i.price, i.condition or ""])


def read_csv(path) -> list[Item]:
    import csv
    with open(path, encoding="utf-8") as f:
        return [Item(r["item_id"], r["group_id"], r["category"], float(r["age_years"]),
                     float(r["usage"]), date.fromisoformat(r["listed_on"]), float(r["price"]),
                     r["condition"] or None) for r in csv.DictReader(f)]
