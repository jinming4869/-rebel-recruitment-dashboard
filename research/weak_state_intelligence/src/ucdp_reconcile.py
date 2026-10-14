"""Week 2: reconcile UCDP ACD 26.1 against the dedicated onset file 25.1 before combining.

For every intrastate conflict, compare the first year it appears in ACD 26.1 with the
onset year(s) the 25.1 onset file assigns in the overlapping years (<= 2024).
Writes outputs/ucdp_onset_reconciliation.csv; any row with status != 'agree' must be
resolved by hand (or the onset series rederived from 26.1) before analysis.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUTS, SourceNotReady, load_json, load_source, write_csv  # noqa: E402

OVERLAP_END = 2024


def acd_first_years(acd: pd.DataFrame, intrastate_types: list[int]) -> pd.DataFrame:
    a = acd[acd["type_of_conflict"].isin(intrastate_types) & (acd["year"] <= OVERLAP_END)]
    return (a.groupby("conflict_id").agg(acd_first_year=("year", "min"), gwno=("gwno", "first"))
             .reset_index())


def onset_conflict_years(onset: pd.DataFrame) -> pd.DataFrame:
    """Explode the onset file's conflict-id list to conflict-level onset years."""
    o = onset[onset["new_conflict_onset"] == 1].copy()
    o["conflict_id"] = o["conflict_ids"].astype(str).str.split(r"[,; ]+")
    o = o.explode("conflict_id")
    o = o[o["conflict_id"].str.strip() != ""]
    o["conflict_id"] = pd.to_numeric(o["conflict_id"], errors="coerce")
    return o.groupby("conflict_id")["year"].min().rename("onset_file_year").reset_index()


def reconcile(acd_first: pd.DataFrame, onset_years: pd.DataFrame) -> pd.DataFrame:
    m = acd_first.merge(onset_years, on="conflict_id", how="outer", indicator=True)
    m["status"] = "agree"
    m.loc[m["_merge"] == "left_only", "status"] = "missing_in_onset_25.1"
    m.loc[m["_merge"] == "right_only", "status"] = "missing_in_acd_26.1"
    both = m["_merge"] == "both"
    m.loc[both & (m["acd_first_year"] != m["onset_file_year"]), "status"] = "year_mismatch"
    return m.drop(columns="_merge").sort_values(["status", "conflict_id"])


def main() -> None:
    try:
        acd = load_source("DATA_UCDP_ACD")
        onset = load_source("DATA_UCDP_ONSET")
    except SourceNotReady as exc:
        print(f"NOT RUN: {exc}")
        sys.exit(2)
    types = load_json("source_columns.json")["DATA_UCDP_ACD"]["intrastate_types"]
    out = reconcile(acd_first_years(acd, types), onset_conflict_years(onset))
    write_csv(out, OUTPUTS / "ucdp_onset_reconciliation.csv")
    print(out["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
