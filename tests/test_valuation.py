from datetime import date

import pytest

from pricewise.synthetic import generate
from pricewise.valuation import Item, Valuer, comparables
from pricewise.valuation.backtest import metrics, naive_out_of_fold, out_of_fold, time_split
from pricewise.valuation.ranges import Ranges


@pytest.fixture(scope="module")
def items():
    return generate(n=2_500, seed=11)


def test_the_synthetic_data_is_reproducible():
    assert generate(n=50, seed=3) == generate(n=50, seed=3)
    assert generate(n=50, seed=3) != generate(n=50, seed=4)


def test_folds_keep_every_listing_of_an_item_together(items):
    pred = out_of_fold(items, seed=1)
    assert len(pred) == len(items) and (pred > 0).all()


def test_a_row_level_split_flatters_the_model(items):
    """Relisted items on both sides of a row-level split leak: the honest,
    grouped error must be the larger one."""
    honest = metrics(items, out_of_fold(items, seed=1)).median_ape
    leaky = metrics(items, naive_out_of_fold(items, seed=1)).median_ape
    assert leaky < honest


def test_ranges_cover_about_what_they_promise(items):
    pred = out_of_fold(items, seed=2)
    ranges = Ranges.fit(items, pred)
    m = metrics(items, pred, ranges)
    assert 0.45 <= m.likely_coverage <= 0.55 and 0.75 <= m.wide_coverage <= 0.85


def test_the_model_beats_the_comparables_baseline_in_time(items):
    split = time_split(items, date(2025, 10, 1))
    assert split.test.median_ape < split.baseline.median_ape
    assert 0.6 <= split.test.wide_coverage <= 0.95


def test_estimate_has_a_point_inside_its_ranges(items):
    e = (
        Valuer()
        .fit(items)
        .estimate(Item("x", "x", "compact", 6, 90_000, date(2025, 12, 1), 0, "good"))
    )
    assert e.wide[0] <= e.likely[0] <= e.point <= e.likely[1] <= e.wide[1]


def test_comparables_ignore_the_same_item():
    a = Item("a", "g1", "estate", 5, 80_000, date(2025, 1, 1), 10_000)
    relist = Item("a2", "g1", "estate", 5.1, 80_000, date(2025, 2, 1), 9_800)
    others = [
        Item(f"o{k}", f"g{k + 2}", "estate", 5.5, 85_000, date(2025, 1, 1), 11_000)
        for k in range(3)
    ]
    assert [i.item_id for i in comparables.similar([relist, *others], a)] == ["o0", "o1", "o2"]
    assert comparables.estimate([relist, *others], a) == 11_000
