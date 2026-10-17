"""ISV examples worked out by hand from the 2026 tables (Código do ISV
arts. 7, 8 and 11). Each comment shows the arithmetic."""

from datetime import date

import pytest

from pricewise.tax import Fuel, Vehicle, isv
from pricewise.tax.isv import age_reduction, guess_standard
from pricewise.tax.tables import load

ON = date(2026, 10, 1)


def test_petrol_wltp():
    # First registered 2019-06-15, declared 2026-10-01: over 7 years -> 65% off.
    # Engine 1199 cc (<= 1250): 1199 × 1.18 − 850.69 = 564.13
    # CO2 125 g/km petrol WLTP (<= 130): 125 × 5.27 − 619.17 = 39.58
    # (564.13 + 39.58) × 0.35 = 211.2985 -> €211.30
    v = Vehicle(date(2019, 6, 15), Fuel.PETROL, cc=1199, co2_g_km=125, co2_standard="wltp")
    b = isv(v, ON)
    assert (b.total, b.reduction, b.engine, b.co2) == (211.30, 0.65, 197.45, 13.85)
    assert not b.flags


def test_diesel_particles_exact_and_unknown():
    # 2020-03-01 -> over 6 years -> 60% off.
    # Engine 1598 cc (> 1250): 1598 × 5.61 − 6194.88 = 2769.90
    # CO2 115 g/km diesel WLTP (<= 120): 115 × 18.96 − 1906.19 = 274.21
    # (2769.90 + 274.21) × 0.40 = 1217.644 -> €1,217.64
    base = dict(fuel=Fuel.DIESEL, cc=1598, co2_g_km=115, co2_standard="wltp")
    clean = isv(Vehicle(date(2020, 3, 1), particles_g_km=0.0005, **base), ON)
    dirty = isv(Vehicle(date(2020, 3, 1), particles_g_km=0.002, **base), ON)
    unknown = isv(Vehicle(date(2020, 3, 1), **base), ON)
    assert clean.total == 1217.64
    assert dirty.total == 1217.64 + 500                      # surcharge at >= 0.001 g/km
    assert unknown.total == 1717.64 and unknown.particle_kind == "estimated"
    assert any("V.5" in f for f in unknown.flags)


def test_the_minimum_applies():
    # 2012 -> over 10 years -> 80% off. Engine 998 × 1.09 − 849.03 = 238.79;
    # CO2 95 NEDC (<= 99): 95 × 4.62 − 427 = 11.90; (250.69) × 0.20 = 50.14 < €100.
    v = Vehicle(date(2012, 1, 10), Fuel.PETROL, cc=998, co2_g_km=95, co2_standard="nedc")
    b = isv(v, ON)
    assert b.total == 100.0 and b.minimum_applied


def test_electric_pays_nothing():
    assert isv(Vehicle(date(2021, 1, 1), Fuel.ELECTRIC), ON).total == 0.0


def test_unknown_standard_is_computed_both_ways_where_both_are_possible():
    v = Vehicle(date(2018, 9, 1), Fuel.PETROL, cc=1199, co2_g_km=125)
    b = isv(v, ON)
    nedc = isv(Vehicle(date(2018, 9, 1), Fuel.PETROL, cc=1199, co2_g_km=125,
                       co2_standard="nedc"), ON).total
    wltp = isv(Vehicle(date(2018, 9, 1), Fuel.PETROL, cc=1199, co2_g_km=125,
                       co2_standard="wltp"), ON).total
    assert b.total == max(nedc, wltp) and b.alternative_total == min(nedc, wltp)
    assert b.standard_kind == "estimated" and b.flags
    assert guess_standard(date(2016, 1, 1)) == ["nedc"]
    assert guess_standard(date(2021, 1, 1)) == ["wltp"]


def test_age_reduction_boundaries():
    t = load("isv")
    first = date(2020, 5, 10)
    assert age_reduction(first, date(2021, 5, 10), t) == 0.10      # "até 1 ano" inclusive
    assert age_reduction(first, date(2021, 5, 11), t) == 0.20
    assert age_reduction(first, date(2040, 1, 1), t) == 0.80


@pytest.mark.parametrize("euro, co2, expected", [
    ("6d", 60, "normal"),            # 60 g/km is over the general 50 g/km limit
    ("6e-bis", 60, "plugin_hybrid"),  # Lei 73-A/2025: 80 g/km for Euro 6e-bis
])
def test_plugin_hybrid_regime(euro, co2, expected):
    v = Vehicle(date(2024, 3, 1), Fuel.PLUGIN_HYBRID, cc=1498, co2_g_km=co2,
                co2_standard="wltp", euro_norm=euro, electric_range_km=60)
    assert isv(v, ON).regime == expected


def test_the_tables_cite_the_law():
    for tax in ("isv", "iuc"):
        sources = " ".join(load(tax)["sources"])
        assert "Código" in sources and "Diário da República" in sources
