"""Estimate one item and show its ranges, then the taxes on a vehicle."""

from datetime import date

from pricewise.synthetic import generate
from pricewise.tax import Fuel, Vehicle, isv, iuc
from pricewise.valuation import Item, Valuer

valuer = Valuer().fit(generate())
item = Item("x", "x", "compact", age_years=6, usage=90_000, listed_on=date(2025, 12, 1),
            price=0, condition="good")
e = valuer.estimate(item)
print(f"point €{e.point:,.0f} · likely €{e.likely[0]:,.0f}–{e.likely[1]:,.0f} · "
      f"80% €{e.wide[0]:,.0f}–{e.wide[1]:,.0f} · comparables "
      + (f"€{e.comparables:,.0f}" if e.comparables else "none"))

v = Vehicle(date(2019, 6, 15), Fuel.PETROL, cc=1199, co2_g_km=125, co2_standard="wltp")
print(f"ISV €{isv(v, date(2026, 10, 1)).total:,.2f} · IUC €{iuc(v).total:,.2f} a year "
      "(illustration only, not tax advice)")
