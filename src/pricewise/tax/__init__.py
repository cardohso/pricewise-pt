"""Portuguese vehicle taxes for a used passenger car brought in from another
EU state: ISV (registration tax, paid once) and IUC (yearly circulation tax).

For illustration only, not tax advice. The tables (``tables/*.json``) cite
the articles of the Código do ISV and Código do IUC they come from.
"""

from pricewise.tax.isv import IsvBreakdown, isv
from pricewise.tax.iuc import CategoryANotSupported, IucBreakdown, iuc
from pricewise.tax.vehicle import Fuel, Vehicle

__all__ = ["CategoryANotSupported", "Fuel", "IsvBreakdown", "IucBreakdown", "Vehicle", "isv",
           "iuc"]
