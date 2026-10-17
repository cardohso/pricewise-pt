"""How good are the estimates, measured honestly.

- **Grouped k-fold**: every listing is predicted by a model that never saw
  it, *nor any other listing of the same item*. With duplicates (an item
  relisted, or listed in two places), a plain row-level split puts copies on
  both sides and the error looks better than it is; ``naive_out_of_fold``
  exists to show by how much.
- **Time split**: train on what was listed before a date, test on what came
  after, as the estimates are used in practice.
- Reported: median absolute percentage error, the share within 15%, and how
  often the true price falls inside the likely (50%) and wide (80%) ranges,
  which should be close to 50% and 80% if the ranges are honest. The
  comparables baseline is reported alongside: the model must beat it.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from pricewise.valuation import comparables
from pricewise.valuation.items import Item
from pricewise.valuation.model import PriceModel
from pricewise.valuation.ranges import LIKELY, WIDE, Ranges

FOLDS = 5


def _folds(keys: Sequence[str], folds: int, seed: int) -> dict[str, int]:
    unique = sorted(set(keys))
    order = np.random.default_rng(seed).permutation(len(unique))
    return {unique[j]: n % folds for n, j in enumerate(order)}


def out_of_fold(items: Sequence[Item], *, folds: int = FOLDS, seed: int = 0,
                group: bool = True) -> np.ndarray:
    """A prediction for every item from a model trained without its fold.
    Folds are drawn by ``group_id`` (all listings of an item together)."""
    keys = [i.group_id if group else i.item_id for i in items]
    fold_of = _folds(keys, folds, seed)
    pred = np.zeros(len(items))
    for k in range(folds):
        test = [n for n, key in enumerate(keys) if fold_of[key] == k]
        train = [items[n] for n, key in enumerate(keys) if fold_of[key] != k]
        if not test or not train:
            continue
        pred[test] = PriceModel(seed=seed).fit(train).predict([items[n] for n in test])
    return pred


def naive_out_of_fold(items: Sequence[Item], **kw) -> np.ndarray:
    """Row-level folds, duplicates ignored: the leaky way, for comparison."""
    return out_of_fold(items, group=False, **kw)


@dataclass(frozen=True)
class Metrics:
    n: int
    median_ape: float            # median |predicted / actual − 1|
    within_15: float             # share within 15%
    likely_coverage: float | None = None   # should be ~0.50
    wide_coverage: float | None = None     # should be ~0.80


def metrics(items: Sequence[Item], predicted: Sequence[float],
            ranges: Ranges | None = None) -> Metrics:
    ape = [abs(p / i.price - 1) for i, p in zip(items, predicted)]
    cover = None, None
    if ranges is not None:
        def inside(which):
            hits = [lo <= i.price <= hi for i, p in zip(items, predicted)
                    for lo, hi in [ranges.interval(i, p, which)]]
            return sum(hits) / len(hits)
        cover = inside(LIKELY), inside(WIDE)
    return Metrics(len(ape), statistics.median(ape), sum(a <= 0.15 for a in ape) / len(ape),
                   *cover)


def comparables_baseline(items: Sequence[Item], pool: Sequence[Item]) -> Metrics:
    """The comparables median, on the items it can price at all."""
    by_category: dict[str, list[Item]] = {}
    for i in pool:
        by_category.setdefault(i.category, []).append(i)
    pairs = [(i, comparables.estimate(by_category.get(i.category, []), i)) for i in items]
    priced = [(i, e) for i, e in pairs if e is not None]
    return metrics([i for i, _ in priced], [e for _, e in priced])


@dataclass(frozen=True)
class TimeSplit:
    cutoff: date
    train: int
    test: Metrics
    baseline: Metrics


def time_split(items: Sequence[Item], cutoff: date, *, seed: int = 0) -> TimeSplit:
    """Fit (model and ranges) on items listed before ``cutoff``; score the
    rest. Ranges come from the training items' out-of-fold errors."""
    train = [i for i in items if i.listed_on < cutoff]
    test = [i for i in items if i.listed_on >= cutoff]
    if not train or not test:
        raise ValueError("the cutoff leaves no training or no test items")
    ranges = Ranges.fit(train, out_of_fold(train, seed=seed))
    pred = PriceModel(seed=seed).fit(train).predict(test)
    return TimeSplit(cutoff, len(train), metrics(test, pred, ranges),
                     comparables_baseline(test, train))


def report(items: Sequence[Item], *, cutoff: date, seed: int = 0) -> str:
    grouped = out_of_fold(items, seed=seed)
    ranges = Ranges.fit(items, grouped)
    g = metrics(items, grouped, ranges)
    n = metrics(items, naive_out_of_fold(items, seed=seed))
    b = comparables_baseline(items, items)
    t = time_split(items, cutoff, seed=seed)
    pct = lambda x: "—" if x is None else f"{x:.1%}"  # noqa: E731
    rows = [("Grouped 5-fold (honest)", g), ("Row-level 5-fold (leaky)", n),
            ("Comparables baseline", b), (f"Time split, test after {cutoff}", t.test),
            ("Comparables, same split", t.baseline)]
    lines = [f"{'':34}{'n':>6}{'median err':>12}{'within 15%':>12}{'in 50% range':>14}"
             f"{'in 80% range':>14}"]
    for name, m in rows:
        lines.append(f"{name:34}{m.n:>6}{m.median_ape:>12.1%}{m.within_15:>12.1%}"
                     f"{pct(m.likely_coverage):>14}{pct(m.wide_coverage):>14}")
    return "\n".join(lines)
