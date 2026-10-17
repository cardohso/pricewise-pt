"""When did a listed item go, and did it go quickly?

Listings are seen through repeated searches. An item missing from a search
proves nothing unless that search was *complete* (it reached the end of its
results); a page that failed to load would otherwise look like a sale. So an
item is only "gone" after it is missing from ``GONE_AFTER`` complete searches
in a row, and its exit is placed between the last search that saw it and the
first that missed it.
"""

from pricewise.lifecycle.tracker import GONE_AFTER, Exit, Search, Tracker, quick_exits

__all__ = ["GONE_AFTER", "Exit", "Search", "Tracker", "quick_exits"]
