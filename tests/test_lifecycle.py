from datetime import datetime, timedelta

from pricewise.lifecycle import Search, Tracker, quick_exits

T0 = datetime(2025, 3, 1, 9)


def s(day, seen, complete=True, segment="a"):
    return Search(T0 + timedelta(days=day), segment, frozenset(seen), complete)


def test_gone_only_after_two_complete_searches_miss_it():
    t = Tracker().feed([s(0, {"x", "y"}), s(1, {"y"}), s(2, {"y"})])
    assert "x" in t.exits and t.active == {"y"}
    e = t.exits["x"]
    assert e.window == (T0, T0 + timedelta(days=1))  # last seen .. first missed


def test_an_incomplete_search_proves_nothing():
    t = Tracker().feed(
        [s(0, {"x", "y"}), s(1, {"y"}, complete=False), s(2, {"y"}, complete=False), s(3, {"y"})]
    )
    assert "x" not in t.exits  # only one complete miss


def test_a_search_of_another_segment_says_nothing_about_this_one():
    t = Tracker().feed([s(0, {"x"}), s(1, set(), segment="b"), s(2, set(), segment="b")])
    assert t.active == {"x"}


def test_an_item_that_comes_back_never_went():
    t = Tracker().feed([s(0, {"x"}), s(1, set()), s(2, set()), s(3, {"x"})])
    assert "x" not in t.exits and t.active == {"x"}


def test_quick_exits():
    t = Tracker().feed(
        [
            s(0, {"fast", "slow"}),
            s(1, {"slow"}),
            s(2, {"slow"}),
            *(s(d, {"slow"}) for d in range(7, 60, 7)),
            s(57, set()),
            s(58, set()),
        ]
    )
    quick = {e.item_id for e in quick_exits(t.exits.values())}
    assert quick == {"fast"} and t.exits["slow"].days_listed == 56  # gone, but slowly
