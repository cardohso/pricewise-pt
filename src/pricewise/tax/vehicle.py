"""The vehicle, as the tax rules see it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Fuel(Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    PLUGIN_HYBRID = "plugin_hybrid"
    ELECTRIC = "electric"


@dataclass(frozen=True)
class Vehicle:
    first_registration: date              # first registration anywhere in the EU/EEA
    fuel: Fuel
    cc: int | None = None                 # engine size; None only for electric cars
    co2_g_km: float | None = None         # combined value from the certificate of conformity
    co2_standard: str | None = None       # "nedc" | "wltp" | None (unknown)
    euro_norm: str | None = None          # e.g. "6d", "6e-bis"
    particles_g_km: float | None = None   # diesel: field V.5 of the registration document
    electric_range_km: int | None = None  # plug-in hybrids
    hybrid_base_fuel: Fuel = Fuel.PETROL  # which CO2 table a hybrid uses

    @property
    def tax_fuel(self) -> str:
        """Which CO2 table applies: "diesel" or "petrol"."""
        if self.fuel is Fuel.DIESEL:
            return "diesel"
        if self.fuel in (Fuel.HYBRID, Fuel.PLUGIN_HYBRID):
            return "diesel" if self.hybrid_base_fuel is Fuel.DIESEL else "petrol"
        return "petrol"
