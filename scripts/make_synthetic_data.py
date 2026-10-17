"""Write the synthetic dataset (fixed seed) to data/synthetic_items.csv."""

from pathlib import Path

from pricewise.synthetic import generate, write_csv

out = Path(__file__).resolve().parent.parent / "data" / "synthetic_items.csv"
out.parent.mkdir(exist_ok=True)
items = generate()
write_csv(items, out)
print(f"wrote {len(items)} synthetic listings to {out}")
