"""IUC examples worked out by hand from the 2026 tables (Código do IUC art. 10)."""

from datetime import date

import pytest

from pricewise.tax import CategoryANotSupported, Fuel, Vehicle, iuc


def test_petrol():
    # 1199 cc (<= 1250): 31.77; CO2 125 WLTP (<= 140): 65.15; extra 0 (<= 205);
    # 2019 coefficient 1.15: (31.77 + 65.15) × 1.15 = 111.458 -> €111.46
    v = Vehicle(date(2019, 6, 15), Fuel.PETROL, cc=1199, co2_g_km=125, co2_standard="wltp")
    assert iuc(v).total == 111.46


def test_diesel_extra_is_outside_the_coefficient():
    # 1598 cc (<= 1750): 63.74; CO2 115 WLTP: 65.15; (128.89) × 1.15 = 148.2235;
    # + diesel extra (<= 1750) 10.07 = 158.2935 -> €158.29
    v = Vehicle(date(2020, 3, 1), Fuel.DIESEL, cc=1598, co2_g_km=115, co2_standard="wltp")
    b = iuc(v)
    assert (b.total, b.diesel_extra) == (158.29, 10.07)


def test_high_co2_extra_from_2017():
    # 2018, 1998 cc (<= 2500): 127.35; CO2 230 WLTP (<= 260): 212.04 + extra 31.77;
    # (127.35 + 212.04 + 31.77) × 1.15 = 426.834 -> €426.83
    v = Vehicle(date(2018, 2, 1), Fuel.PETROL, cc=1998, co2_g_km=230, co2_standard="wltp")
    assert iuc(v).total == 426.83


def test_category_a_and_electric():
    with pytest.raises(CategoryANotSupported):
        iuc(Vehicle(date(2006, 12, 1), Fuel.PETROL, cc=1400, co2_g_km=150))
    assert iuc(Vehicle(date(2022, 1, 1), Fuel.ELECTRIC)).total == 0.0
