"""Print columns, dtypes, ranges and example values of a raw file, to confirm
config/source_columns.json against the real data before any build step.

Usage: python -I src/inspect_source.py data/raw/DATA_SDM/<file>.csv
"""
import sys

import pandas as pd

df = pd.read_csv(sys.argv[1], low_memory=False)
print(f"rows={len(df)} cols={df.shape[1]}")
for c in df.columns:
    s = df[c]
    rng = f"[{s.min()} .. {s.max()}]" if pd.api.types.is_numeric_dtype(s) else ""
    ex = ", ".join(map(str, s.dropna().unique()[:4]))
    print(f"{c:<28} {str(s.dtype):<8} nulls={s.isna().sum():<6} {rng} e.g. {ex}")
