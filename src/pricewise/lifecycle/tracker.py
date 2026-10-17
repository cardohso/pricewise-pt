"""Item lifecycles from repeated, possibly incomplete, searches."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

GONE_AFTER = 2           # complete searches in a row that must miss an item


@dataclass(frozen=True)
class Search:
    at: datetime
    segment: str                     # what the search covered (a category, a region…)
    seen: frozenset[str]             # item ids it returned
    complete: bool                   # reached the end of its results


@dataclass
class _State:
    segment: str
    first_seen: datetime
    last_seen: datetime
    misses: list[datetime] = field(default_factory=list)   # complete searches since last seen


@dataclass(frozen=True)
class Exit:
    item_id: str
    first_seen: datetime
    window: tuple[datetime, datetime]    # it went between these: last seen, first missed

    @property
    def days_listed(self) -> float:
        return (self.window[0] - self.first_seen) / timedelta(days=1)

    @property
    def window_days(self) -> float:
        return (self.window[1] - self.window[0]) / timedelta(days=1)


class Tracker:
    """Feed searches in time order; read who is active and who has gone."""

    def __init__(self, gone_after: int = GONE_AFTER) -> None:
        self.gone_after = gone_after
        self._active: dict[str, _State] = {}
        self.exits: dict[str, Exit] = {}

    def feed(self, searches: Iterable[Search]) -> Tracker:
        for s in sorted(searches, key=lambda s: s.at):
            self._feed(s)
        return self

    def _feed(self, s: Search) -> None:
        for item_id in s.seen:
            if item_id in self.exits:            # back after all: it never went
                gone = self.exits.pop(item_id)
                self._active[item_id] = _State(s.segment, gone.first_seen, s.at)
            state = self._active.setdefault(item_id, _State(s.segment, s.at, s.at))
            state.last_seen, state.misses = s.at, []
        if not s.complete:
            return                               # proves nothing about who is missing
        for item_id, state in list(self._active.items()):
            if state.segment != s.segment or item_id in s.seen:
                continue
            state.misses.append(s.at)
            if len(state.misses) >= self.gone_after:
                self.exits[item_id] = Exit(item_id, state.first_seen,
                                           (state.last_seen, state.misses[0]))
                del self._active[item_id]

    @property
    def active(self) -> set[str]:
        return set(self._active)


def quick_exits(exits: Iterable[Exit], *, max_days: float = 30,
                max_window_days: float = 3) -> list[Exit]:
    """Items that went soon after appearing, and whose exit is known within a
    few days: the ones most likely to have found a taker rather than been
    withdrawn after months unsold."""
    return [e for e in exits if e.days_listed <= max_days and e.window_days <= max_window_days]
