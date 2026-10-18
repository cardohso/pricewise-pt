"""IUC (Imposto Único de Circulação), one year, category B.

    IUC = (engine + CO2 + high-CO2 extra) × year coefficient + diesel extra

Código do IUC art. 10. The first registration anywhere in the EU/EEA
decides the category and the coefficient (Lei 119/2019). Category A (first
registered before 2007-07-01) is not supported.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pricewise.tax import tables
from pricewise.tax.isv import D, guess_standard, money
from pricewise.tax.vehicle import Fuel, Vehicle


class CategoryANotSupported(ValueError):
    """First registered before July 2007 (IUC category A)."""


@dataclass(frozen=True)
class IucBreakdown:
    total: float
    engine: float
    co2: float
    co2_extra: float
    coefficient: float
    diesel_extra: float
    co2_standard: str


def iuc(v: Vehicle, *, year: int = tables.CURRENT_YEAR) -> IucBreakdown:
    t = tables.load("iuc", year)
    if v.fuel is Fuel.ELECTRIC:
        return IucBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, v.co2_standard or "wltp")
    if v.first_registration < date.fromisoformat(t["category_b_from"]):
        raise CategoryANotSupported(
            f"first registered {v.first_registration}: IUC category A is not supported"
        )
    if v.cc is None or v.co2_g_km is None:
        raise ValueError("IUC needs the engine size (cc) and CO2 (g/km)")
    standard = v.co2_standard or guess_standard(v.first_registration)[-1]
    engine = tables.bracket(t["engine"], v.cc)[1]
    co2 = tables.bracket(t["co2"][standard], v.co2_g_km)[1]
    extra = 0.0
    if v.first_registration >= date.fromisoformat(t["co2_extra_from"]):
        extra = tables.bracket(t["co2_extra"][standard], v.co2_g_km)[1]
    coefficient = tables.bracket(t["coefficient"], v.first_registration.year)[1]
    diesel = tables.bracket(t["diesel_extra"], v.cc)[1] if v.tax_fuel == "diesel" else 0.0
    total = money((D(engine) + D(co2) + D(extra)) * D(coefficient) + D(diesel))
    return IucBreakdown(total, engine, co2, extra, coefficient, diesel, standard)
