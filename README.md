# pricewise-pt

**Price estimates with honest uncertainty, evaluated the way they'll be used, plus Portugal's vehicle tax rules (ISV/IUC) as tested code.**

## In 30 seconds

- **Uncertainty you can trust.** Every estimate comes with a *likely* range (50%) and a *wide* range (80%), fitted from the model's own out-of-fold errors, per segment. On held-out data they cover 50.0% and 79.8%, i.e. what they promise.
- **Evaluation that can't be fooled.** Cross-validation is grouped by item, so a relisted item never sits on both sides of a split. A time split trains on the past and tests on the future. The model has to beat a comparables baseline, and does.
- **Real-world rules as code.** The ISV and IUC calculators follow the Código do ISV and Código do IUC article by article, with versioned tables that cite the law and tests worked out by hand from it.
- **Data quality first.** Lifecycle inference only counts *complete* observations: a page that failed to load is never mistaken for an item that went.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                          # 25 tests, offline
.venv/bin/python examples/backtest.py     # the table below (~30 s)
.venv/bin/python examples/estimate.py     # one estimate, one tax calculation
.venv/bin/python scripts/make_synthetic_data.py   # writes data/synthetic_items.csv
```

Python 3.11+, numpy and scikit-learn. No network access, no external data.

## What's inside

| Package | What it does |
|---|---|
| `pricewise.valuation` | A Ridge model on log price (per-category age and usage slopes), boosted trees on its residuals above 2,000 rows, uncertainty ranges from out-of-fold errors, a comparables baseline, and the backtest. |
| `pricewise.tax` | ISV (registration tax) and IUC (yearly circulation tax) for a used car first registered elsewhere in the EU. |
| `pricewise.lifecycle` | When a listed item went, from repeated, possibly incomplete, searches, and whether it went quickly. |
| `pricewise.synthetic` | A synthetic market (fixed seed) so all of the above runs anywhere. |

## How the backtest works

1. **Grouped 5-fold cross-validation.** Each listing is predicted by a model trained without it *and without any other listing of the same item* (`group_id`). A plain row-level split puts relisted copies on both sides and reports an error that is too good. The leaky version is run alongside to show the gap.
2. **Ranges from out-of-fold errors.** The 25th–75th and 10th–90th percentiles of log errors, kept per category and age band (older items vary more), with fallbacks when a segment is small. In-sample errors would give ranges that are far too narrow.
3. **Coverage check.** The share of true prices inside each range should be close to 50% and 80%. If it isn't, the ranges are lying.
4. **Time split.** Fit on everything listed before a date and test on everything after, with the ranges fitted on the training period only.
5. **Baseline.** The median price of comparable items (same category, age within a year, usage within 20%, never the same item). If the model doesn't beat this, it isn't worth having.

## Results on synthetic data

> **Synthetic data.** These numbers come from `pricewise.synthetic` (made-up prices, seed 7). They show the method behaves as intended. They say nothing about accuracy on any real market.

```
                                       n  median err  within 15%  in 50% range  in 80% range
Grouped 5-fold (honest)             4604       10.2%       65.9%         50.0%         79.8%
Row-level 5-fold (leaky)            4604       10.0%       66.8%             —             —
Comparables baseline                4551       11.2%       62.8%             —             —
Time split, test after 2025-10-01   1224       10.0%       66.8%         47.5%         78.3%
Comparables, same split             1205       11.6%       62.7%             —             —
```

Reading it:
- The ranges are calibrated: 50.0% / 79.8% in cross-validation, 47.5% / 78.3% on the future period.
- The model beats the comparables baseline by about 1–1.6 points of median error, and can price items the baseline can't (too few comparables).
- The leak is real but small here, because only about 15% of the synthetic items are relisted. With more duplicates it grows, and it always points the same way: too optimistic.

## Tax rules

```python
from datetime import date
from pricewise.tax import Fuel, Vehicle, isv, iuc

v = Vehicle(date(2019, 6, 15), Fuel.PETROL, cc=1199, co2_g_km=125, co2_standard="wltp")
isv(v, date(2026, 10, 1)).total   # 211.3  (engine + CO2 components, 65% age reduction)
iuc(v).total                      # 111.46 per year
```

- **Covers:** engine and CO2 components (NEDC and WLTP), the age reduction table, the reduced regimes for hybrids and plug-in hybrids (including the Euro 6e-bis limit from the Orçamento do Estado 2026), the diesel particle surcharge, the €100 minimum and IUC category B.
- **Flags assumptions:** an unknown homologation standard is computed both ways where both are possible, and an unknown particle value is assumed to be due, with a note on which document field to check.
- **Sources:** the tables (`src/pricewise/tax/tables/*.json`) cite the articles they come from, in the Código do ISV and Código do IUC as published in the *Diário da República*.

> **Not tax advice.** The figures are for illustration. Tax law changes: check the current law, or the Autoridade Tributária, before relying on any number here.

## Limitations

- **Synthetic data:** results on real data will differ, probably for the worse.
- **Asking prices, not sale prices:** the valuation models asking prices. Turning those into sale prices needs observed sales.
- **Ranges and time:** they assume the future errors look like the past ones. The time split checks this, but only over one cutoff.
- **Tax scope:** IUC category A (cars first registered before July 2007) and taxes other than ISV/IUC aren't covered.

## Licence

MIT. See `LICENSE`.
