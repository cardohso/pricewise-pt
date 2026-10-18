"""The price model: Ridge regression on log price with per-category age and
usage slopes, plus gradient-boosted trees on its residuals once there is
enough data for them to add signal rather than noise."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge

from pricewise.valuation.items import Item, categorical, numeric

NUMERIC = ("age", "log_usage", "usage_per_year")
CATEGORICAL = ("category", "condition")
MIN_ROWS_FOR_TREES = 2_000


class Design:
    """Builds the design matrix; fitted on training items only (no peeking
    at test categories or scales)."""

    def fit(self, items: Sequence[Item]) -> Design:
        nums = np.array([[numeric(i)[k] for k in NUMERIC] for i in items], float)
        self.mean, self.std = nums.mean(axis=0), nums.std(axis=0) + 1e-9
        cats = [categorical(i) for i in items]
        self.levels = {n: sorted({c[n] for c in cats if c[n] is not None}) for n in CATEGORICAL}
        self.columns = (
            list(NUMERIC)
            + [f"{n}={v}" for n in CATEGORICAL for v in self.levels[n]]
            + [f"{c}*{k}" for c in self.levels["category"] for k in NUMERIC[:2]]
        )
        self._index = {c: j for j, c in enumerate(self.columns)}
        return self

    def transform(self, items: Sequence[Item]) -> np.ndarray:
        x = np.zeros((len(items), len(self.columns)))
        for r, item in enumerate(items):
            nums = (np.array([numeric(item)[k] for k in NUMERIC]) - self.mean) / self.std
            x[r, : len(NUMERIC)] = nums
            for name, value in categorical(item).items():
                j = self._index.get(f"{name}={value}")
                if j is not None:
                    x[r, j] = 1.0
            for k, value in zip(NUMERIC[:2], nums[:2], strict=True):
                j = self._index.get(f"{item.category}*{k}")
                if j is not None:
                    x[r, j] = value
        return x


@dataclass
class PriceModel:
    alpha: float = 1.0
    seed: int = 0

    def fit(self, items: Sequence[Item]) -> PriceModel:
        self.design = Design().fit(items)
        x, y = self.design.transform(items), np.log([i.price for i in items])
        self.ridge = Ridge(alpha=self.alpha).fit(x, y)
        self.trees = None
        if len(items) >= MIN_ROWS_FOR_TREES:
            residual = y - self.ridge.predict(x)
            self.trees = HistGradientBoostingRegressor(
                loss="absolute_error", max_iter=150, random_state=self.seed
            ).fit(x, residual)
        return self

    def predict(self, items: Sequence[Item]) -> np.ndarray:
        x = self.design.transform(items)
        log_price = self.ridge.predict(x)
        if self.trees is not None:
            log_price = log_price + self.trees.predict(x)
        return np.exp(log_price)
