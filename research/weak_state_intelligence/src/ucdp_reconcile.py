"""Week 2: reconcile UCDP onset 25.1 with ACD 25.1 (same vintage) and ACD 26.1 (newer vintage).

Three comparisons, kept separate so vintage revisions are not confused with code errors:
  A. onset 25.1 conflict-level (v1) newconf rows  vs  first intrastate year in ACD 25.1
     -> should agree by construction; disagreements are definitional or file anomalies.
  B. ACD 25.1  vs  ACD 26.1 first intrastate year per conflict_id (overlap years <= 2024)
     -> differences are vintage revisions (added, dropped, or re-dated conflicts).
  C. onset 25.1 country-level (v2) newconf country-years  vs  country-years in which ACD 25.1
     shows a conflict_id's first intrastate year (location = gwno_a).

Intrastate = type_of_conflict 3 or 4 (UCDP onset codebook 25.1). Writes
outputs/ucdp_reconciliation_{A,B,C}.csv and outputs/ucdp_reconciliation_summary.json.
Nothing is silently resolved; every non-'agree' row needs a human decision.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUTS, SourceNotReady, load_json, load_source, write_csv  # noqa: E402

OVERLAP_END = 2024


def acd_first_years(acd: pd.DataFrame, intrastate_types: list[int]) -> pd.DataFrame:
    """First year each conflict_id is coded intrastate (type 3/4), plus first year of any type
    so conflicts that changed type are visible."""
    a = acd[acd["year"] <= OVERLAP_END]
    any_first = a.groupby("conflict_id")["year"].min().rename("first_year_any_type")
    intra = a[a["type_of_conflict"].isin(intrastate_types)]
    first = intra.sort_values("year").groupby("conflict_id").agg(
        first_intrastate_year=("year", "min"), gwno=("gwno", "first"), side_b=("side_b", "first"),
        territory_name=("territory_name", "first"))
    return first.join(any_first, how="left").reset_index()


def onset_newconf(onset: pd.DataFrame) -> pd.DataFrame:
    o = onset[onset["new_conflict_onset"] == 1].copy()
    o["conflict_id"] = pd.to_numeric(o["conflict_ids"].astype(str).str.strip(), errors="coerce")
    bad = o["conflict_id"].isna()
    if bad.any():
        raise ValueError(f"{int(bad.sum())} newconf rows have non-numeric conflict_ids; inspect before reconciling")
    return o.groupby("conflict_id").agg(onset_year=("year", "min"), onset_gwno=("gwno", "first"),
                                        n_newconf_rows=("year", "size")).reset_index()


def compare(left: pd.DataFrame, right: pd.DataFrame, lcol: str, rcol: str, lname: str, rname: str) -> pd.DataFrame:
    m = left.merge(right, on="conflict_id", how="outer", indicator=True, suffixes=("", "_r"))
    m["status"] = "agree"
    m.loc[m["_merge"] == "left_only", "status"] = f"only_in_{lname}"
    m.loc[m["_merge"] == "right_only", "status"] = f"only_in_{rname}"
    both = m["_merge"] == "both"
    m.loc[both & (m[lcol] != m[rcol]), "status"] = "year_mismatch"
    return m.drop(columns="_merge").sort_values(["status", "conflict_id"])


def country_level_check(country_onset: pd.DataFrame, acd_first: pd.DataFrame) -> pd.DataFrame:
    """C: country-years flagged newconf in the country-level file vs ACD-derived
    country-years containing a conflict's first intrastate year."""
    c = country_onset[country_onset["new_conflict_onset"] == 1][["gwno", "year"]].copy()
    c["gwno"] = c["gwno"].astype(str).str.strip()
    c["in_onset_country_file"] = True
    a = acd_first.assign(gwno=acd_first["gwno"].astype(str).str.split(",").str[0].str.strip(),
                         year=acd_first["first_intrastate_year"])
    a = a.groupby(["gwno", "year"])["conflict_id"].apply(lambda s: ";".join(map(str, sorted(s)))).reset_index()
    a["in_acd_first_year"] = True
    m = c.merge(a, on=["gwno", "year"], how="outer")
    m["status"] = "agree"
    m.loc[m["in_acd_first_year"].isna(), "status"] = "onset_file_only"
    m.loc[m["in_onset_country_file"].isna(), "status"] = "acd_only"
    return m.sort_values(["status", "gwno", "year"])


def _acd_only_explained(C: pd.DataFrame, onset_c: pd.DataFrame) -> str:
    o = onset_c.assign(gwno=onset_c["gwno"].astype(str).str.strip()).sort_values(["gwno", "year"])
    o["prev_has"] = o.groupby("gwno")["conflict_ids"].shift().astype(str).str.strip().replace({"nan": "", "None": ""}) != ""
    a = C[C["status"] == "acd_only"].merge(o[["gwno", "year", "prev_has"]], on=["gwno", "year"], how="left")
    return f"{int(a['prev_has'].fillna(False).sum())} of {len(a)}"


def main() -> None:
    try:
        acd26 = load_source("DATA_UCDP_ACD")
        acd25 = load_source("DATA_UCDP_ACD_251")
        onset = load_source("DATA_UCDP_ONSET")
        onset_c = load_source("DATA_UCDP_ONSET_COUNTRY")
    except SourceNotReady as exc:
        print(f"NOT RUN: {exc}")
        sys.exit(2)
    types = load_json("source_columns.json")["DATA_UCDP_ACD"]["intrastate_types"]
    f25, f26 = acd_first_years(acd25, types), acd_first_years(acd26, types)
    oc = onset_newconf(onset)
    A = compare(oc, f25, "onset_year", "first_intrastate_year", "onset_25_1", "acd_25_1")
    B = compare(f25, f26, "first_intrastate_year", "first_intrastate_year_r", "acd_25_1", "acd_26_1")
    C = country_level_check(onset_c, f25)
    for k, df in {"A": A, "B": B, "C": C}.items():
        write_csv(df, OUTPUTS / f"ucdp_reconciliation_{k}.csv")
    summary = {
        "A_onset25_vs_acd25": A["status"].value_counts().to_dict(),
        "B_acd25_vs_acd26": B["status"].value_counts().to_dict(),
        "C_country_onset25_vs_acd25_first_years": C["status"].value_counts().to_dict(),
        "acd26_conflicts_first_intrastate_2025": int((f26["first_intrastate_year"] == 2025).sum()),
        "conflicts_changing_type_acd26": int((f26["first_year_any_type"] < f26["first_intrastate_year"]).sum()),
        "onset_conflict_file_newconf_rows": int(len(oc)),
        "onset_country_file_newconf_rows": int((onset_c["new_conflict_onset"] == 1).sum()),
        "country_file_newconf_identical_to_onset1": bool((onset_c["new_conflict_onset"] == onset_c["onset1"]).all()),
        "C_acd_only_with_conflict_in_prior_year": _acd_only_explained(C, onset_c),
        "interpretation": (
            "A: same-vintage conflict-level onsets agree with ACD 25.1. B: one 2024 conflict (Jubaland) is dropped in 26.1. "
            "C: in the country-level file newconf equals onset1 row-for-row, i.e. it marks every country onset after >=1 "
            "peace year (including restarts), contrary to the codebook's 'new conflict' wording; ACD-only rows are new IDs "
            "starting while another conflict was ongoing, which version 2 excludes by design. Use the conflict-level file "
            "for 'new conflict' and never read country-file newconf as first-ever conflict."),
    }
    (OUTPUTS / "ucdp_reconciliation_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
