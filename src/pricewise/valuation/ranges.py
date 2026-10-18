"""Uncertainty ranges from the model's own out-of-fold errors.

A "likely" range (25th–75th percentile of log errors: half of similar items
land inside) and a "wide" one (10th–90th: eight in ten). Errors spread more
for some segments than others (older items vary more), so quantiles are kept
per category and age band, falling back to coarser groups when a segment has
too few errors to be trusted.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from pricewise.valuation.items import Item, age_band

LIKELY, WIDE = (0.25, 0.75), (0.10, 0.90)
MIN_SEGMENT = 20


def _keys(item: Item) -> list[str]:
    band = age_band(item)
    return [f"{item.category}|{band}", f"*|{band}", item.category]


@dataclass
class Ranges:
    bands: dict[str, dict[tuple, tuple[float, float]]]
    fallback: dict[tuple, tuple[float, float]]

    @classmethod
    def fit(cls, items: Sequence[Item], predicted: Sequence[float]) -> Ranges:
        errors: dict[str, list[float]] = defaultdict(list)
        everything = []
        for item, p in zip(items, predicted, strict=True):
            e = math.log(item.price / p)
            everything.append(e)
            for k in _keys(item):
                errors[k].append(e)
        q = lambda es, qs: tuple(float(v) for v in np.quantile(es, qs))  # noqa: E731
        bands = {
            k: {LIKELY: q(es, LIKELY), WIDE: q(es, WIDE)}
            for k, es in errors.items()
            if len(es) >= MIN_SEGMENT
        }
        return cls(bands, {LIKELY: q(everything, LIKELY), WIDE: q(everything, WIDE)})

    def band(self, item: Item, which: tuple = LIKELY) -> tuple[float, float]:
        for k in _keys(item):
            if k in self.bands:
                return self.bands[k][which]
        return self.fallback[which]

    def interval(self, item: Item, point: float, which: tuple = LIKELY) -> tuple[float, float]:
        lo, hi = self.band(item, which)
        return point * math.exp(lo), point * math.exp(hi)
