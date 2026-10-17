"""Backtest the valuation on the synthetic data and print the table."""

from datetime import date

from pricewise.synthetic import generate
from pricewise.valuation.backtest import report

print(report(generate(), cutoff=date(2025, 10, 1)))
