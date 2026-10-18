"""ISV (Imposto sobre Veículos) for a used passenger car from another EU state.

    ISV = max(minimum, (engine + CO2 components) × (1 − age reduction) × regime)
          + diesel particle surcharge

Engine component: Código do ISV art. 7, tabela A. CO2 component: same
article, by fuel and homologation standard (NEDC or WLTP). Age reduction:
art. 11, tabela D. Reduced regimes for hybrids: art. 8. Amounts are rounded
half-up to the cent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pricewise.tax import tables
from pricewise.tax.vehicle import Fuel, Vehicle

EXACT, ESTIMATED = "exact", "estimated"


def D(x) -> Decimal:
    return Decimal(str(x))


def money(x: Decimal) -> float:
    """Euros, rounded half-up to the cent."""
    return float(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February
        return d.replace(year=d.year + years, day=28)


def age_reduction(first_registration: date, on: date, t: dict) -> float:
    """Tabela D: "até 1 ano" = up to and including one year of use."""
    for years, reduction in t["age_reduction"]:
        if years is None or on <= add_years(first_registration, years):
            return reduction
    raise AssertionError("unreachable")


def guess_standard(first_registration: date) -> list[str]:
    """Unknown homologation standard: NEDC up to 2017, WLTP from 2020,
    either in 2018–2019 (computed both ways)."""
    if first_registration.year <= 2017:
        return ["nedc"]
    if first_registration.year >= 2020:
        return ["wltp"]
    return ["nedc", "wltp"]


@dataclass(frozen=True)
class IsvBreakdown:
    total: float
    engine: float  # after age reduction and regime factor
    co2: float
    reduction: float  # age reduction applied (0.10–0.80)
    regime: str  # "normal" | "electric" | "plugin_hybrid" | "hybrid"
    regime_factor: float
    minimum_applied: bool
    particle_surcharge: float
    particle_kind: str  # exact | estimated
    co2_standard: str
    standard_kind: str  # exact | estimated
    alternative_total: float | None = None  # the other standard, when it's unknown
    flags: list[str] = field(default_factory=list)


def _regime(v: Vehicle, t: dict) -> tuple[str, float]:
    if v.fuel is Fuel.ELECTRIC:
        return "electric", 0.0
    if v.fuel in (Fuel.PLUGIN_HYBRID, Fuel.HYBRID):
        key = "plugin_hybrid" if v.fuel is Fuel.PLUGIN_HYBRID else "hybrid"
        rule = t["regimes"][key]
        max_co2 = rule["max_co2"]
        if key == "plugin_hybrid" and (v.euro_norm or "").lower().replace(" ", "") in (
            "6e-bis",
            "euro6e-bis",
        ):
            max_co2 = rule["max_co2_euro_6e_bis"]
        if (
            (v.electric_range_km or 0) >= rule["min_range_km"]
            and v.co2_g_km is not None
            and v.co2_g_km < max_co2
        ):
            return key, rule["factor"]
    return "normal", 1.0


def _particles(v: Vehicle, t: dict) -> tuple[float, str]:
    if v.tax_fuel != "diesel" or v.fuel is Fuel.ELECTRIC:
        return 0.0, EXACT
    if v.particles_g_km is None:  # unknown: assume it's due
        return t["particle_surcharge"], ESTIMATED
    due = v.particles_g_km >= t["particle_threshold_g_km"]
    return (t["particle_surcharge"] if due else 0.0), EXACT


def _compute(v: Vehicle, standard: str, on: date, t: dict) -> IsvBreakdown:
    regime, factor = _regime(v, t)
    surcharge, particle_kind = _particles(v, t)
    if regime == "electric":
        return IsvBreakdown(0.0, 0.0, 0.0, 0.0, regime, 0.0, False, 0.0, EXACT, standard, EXACT)
    if v.cc is None or v.co2_g_km is None:
        raise ValueError("ISV needs the engine size (cc) and CO2 (g/km)")
    reduction = age_reduction(v.first_registration, on, t)
    _, rate, deduction = tables.bracket(t["engine"], v.cc)
    engine = D(v.cc) * D(rate) - D(deduction)
    _, rate, deduction = tables.bracket(t["co2"][v.tax_fuel][standard], v.co2_g_km)
    co2 = D(v.co2_g_km) * D(rate) - D(deduction)
    keep = (1 - D(reduction)) * D(factor)
    # Components are rounded for display; the total rounds the exact sum.
    subtotal = money((engine + co2) * keep)
    minimum_applied = subtotal < t["minimum"]
    base = t["minimum"] if minimum_applied else subtotal
    return IsvBreakdown(
        money(D(base) + D(surcharge)),
        money(engine * keep),
        money(co2 * keep),
        reduction,
        regime,
        factor,
        minimum_applied,
        surcharge,
        particle_kind,
        standard,
        EXACT,
    )


def isv(v: Vehicle, on: date, *, year: int = tables.CURRENT_YEAR) -> IsvBreakdown:
    """ISV due for ``v`` if declared on ``on``. An unknown homologation
    standard is computed both ways where both are possible; the higher is
    returned (``alternative_total`` holds the other)."""
    t = tables.load("isv", year)
    if v.co2_standard in ("nedc", "wltp"):
        result = _compute(v, v.co2_standard, on, t)
    else:
        options = [_compute(v, s, on, t) for s in guess_standard(v.first_registration)]
        worst = max(options, key=lambda b: b.total)
        other = min(options, key=lambda b: b.total)
        result = IsvBreakdown(
            **{
                **worst.__dict__,
                "standard_kind": ESTIMATED,
                "alternative_total": other.total if len(options) > 1 else None,
                "flags": [],
            }
        )
    flags = list(result.flags)
    if result.standard_kind == ESTIMATED and result.regime != "electric":
        flags.append(
            "CO2 standard (NEDC/WLTP) assumed from the registration date: "
            "confirm it on the certificate of conformity"
        )
    if result.particle_kind == ESTIMATED and result.particle_surcharge:
        flags.append("diesel particle value unknown: check field V.5 of the registration document")
    if result.minimum_applied:
        flags.append(f"ISV minimum (€{t['minimum']:.0f}) applied")
    return IsvBreakdown(**{**result.__dict__, "flags": flags})
