"""Fit once, then estimate any item: a point estimate and two ranges."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pricewise.valuation import comparables
from pricewise.valuation.backtest import out_of_fold
from pricewise.valuation.items import Item
from pricewise.valuation.model import PriceModel
from pricewise.valuation.ranges import LIKELY, WIDE, Ranges


@dataclass(frozen=True)
class Estimate:
    point: float
    likely: tuple[float, float]  # half of similar items land inside
    wide: tuple[float, float]  # eight in ten do
    comparables: float | None  # the baseline's opinion, if it has one


class Valuer:
    def __init__(self, seed: int = 0) -> None:
        self.seed = seed

    def fit(self, items: Sequence[Item]) -> Valuer:
        self.pool = list(items)
        self.model = PriceModel(seed=self.seed).fit(self.pool)
        # Ranges come from out-of-fold errors: in-sample errors are too small.
        self.ranges = Ranges.fit(self.pool, out_of_fold(self.pool, seed=self.seed))
        return self

    def estimate(self, item: Item) -> Estimate:
        point = float(self.model.predict([item])[0])
        return Estimate(
            point,
            self.ranges.interval(item, point, LIKELY),
            self.ranges.interval(item, point, WIDE),
            comparables.estimate(self.pool, item),
        )
