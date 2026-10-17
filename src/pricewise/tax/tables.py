"""Versioned tax tables: one JSON file per tax and year, with its legal sources."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

TABLES_DIR = Path(__file__).parent / "tables"
CURRENT_YEAR = 2026


@cache
def load(tax: str, year: int = CURRENT_YEAR) -> dict:
    path = TABLES_DIR / f"{tax}_{year}.json"
    if not path.exists():
        raise FileNotFoundError(f"no {tax.upper()} tables for {year} ({path.name})")
    return json.loads(path.read_text(encoding="utf-8"))


def bracket(rows: list[list], value: float) -> list:
    """The first row whose upper bound (inclusive) covers ``value``; a null
    upper bound means "and above"."""
    for row in rows:
        if row[0] is None or value <= row[0]:
            return row
    raise ValueError(f"no bracket for {value}")
