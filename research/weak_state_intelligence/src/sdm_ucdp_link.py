"""Candidate SDM-movement -> UCDP 26.1 conflict links, for HUMAN REVIEW only.

SDM embeds old-style UCDP conflict IDs ('1-192'; some corrupted by spreadsheet date
conversion, e.g. 'Jan 99') plus a territory name. ACD 26.1 uses new numeric IDs with no
old-ID column, so a link is proposed only when the SDM territory name equals an ACD
territory name for an intrastate territorial conflict (incompatibility 1) in the same
country, with year overlap reported as evidence. Numeric-ID equality is never used.

Writes outputs/sdm_ucdp_link_candidates.csv. Nothing here is written to the reviewed
movement_actor_crosswalk.csv ledger.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUTS, SourceNotReady, load_source, write_csv  # noqa: E402

OLD_ID = re.compile(r"^\d+-\d+$")


def _norm(t) -> str:
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


def candidates(sdm: pd.DataFrame, acd: pd.DataFrame) -> pd.DataFrame:
    s = sdm[sdm["active"] == 1].dropna(subset=["ucdp_conflictid_old"])
    sl = s.groupby(["movement_id", "movement_name", "country_name", "ucdp_conflictid_old"]).agg(
        territory=("ucdp_territoryname", "first"),
        sdm_terr_years=("year", lambda y: f"{y.min()}-{y.max()}"),
        sdm_terr_conflict_years=("ucdp_terrconflict", lambda v: int((v == 1).sum()))).reset_index()
    a = acd[acd["type_of_conflict"].isin([3, 4]) & (acd["incompatibility"] == 1)].copy()
    a["tn"] = a["territory_name"].map(_norm)
    ag = a.groupby(["conflict_id", "tn"]).agg(acd_territory=("territory_name", "first"), acd_location=("location", "first"),
                                             acd_years=("year", lambda y: f"{y.min()}-{y.max()}"),
                                             acd_n_years=("year", "size")).reset_index()
    rows = []
    for r in sl.itertuples(index=False):
        hits = ag[ag["tn"] == _norm(r.territory)] if pd.notna(r.territory) else ag.iloc[0:0]
        id_ok = bool(OLD_ID.match(str(r.ucdp_conflictid_old)))
        base = {"sdm_movement_id": r.movement_id, "movement_name": r.movement_name, "country": r.country_name,
                "sdm_old_ucdp_id": r.ucdp_conflictid_old, "old_id_wellformed": id_ok,
                "sdm_territory": r.territory, "sdm_active_years_with_link": r.sdm_terr_years,
                "sdm_years_coded_ucdp_terrconflict": r.sdm_terr_conflict_years}
        if hits.empty:
            rows.append({**base, "ucdp26_conflict_id": None, "candidate_status": "no_territory_match"})
        for h in hits.itertuples(index=False):
            same_country = _norm(r.country_name)[:5] in _norm(h.acd_location)
            rows.append({**base, "ucdp26_conflict_id": h.conflict_id, "acd_territory": h.acd_territory,
                         "acd_location": h.acd_location, "acd_years": h.acd_years, "acd_n_years": h.acd_n_years,
                         "candidate_status": "territory_and_country_match" if same_country else "territory_match_country_differs"})
    out = pd.DataFrame(rows)
    out["review_status"] = "unreviewed"
    return out.sort_values(["candidate_status", "country", "movement_name"])


def main() -> None:
    try:
        sdm = load_source("DATA_SDM")
        acd = load_source("DATA_UCDP_ACD")
    except SourceNotReady as exc:
        print(f"NOT RUN: {exc}")
        sys.exit(2)
    raw = pd.read_csv(Path(__file__).resolve().parents[1] / "data/raw/DATA_SDM/SDM.csv", usecols=["groupid", "year", "ucdp_territoryname"])
    sdm = sdm.merge(raw.rename(columns={"groupid": "movement_id"}), on=["movement_id", "year"], how="left")
    loc = pd.read_csv(Path(__file__).resolve().parents[1] / "data/raw/DATA_UCDP_ACD/UcdpPrioConflict_v26_1.csv", usecols=["conflict_id", "year", "location"])
    acd = acd.merge(loc, on=["conflict_id", "year"], how="left")
    out = candidates(sdm, acd)
    write_csv(out, OUTPUTS / "sdm_ucdp_link_candidates.csv")
    per_link = out.drop_duplicates(["sdm_movement_id", "sdm_old_ucdp_id"])
    print("SDM movement-UCDP links:", len(per_link), "| malformed old IDs:", int((~per_link["old_id_wellformed"]).sum()))
    print(out.drop_duplicates(["sdm_movement_id", "sdm_old_ucdp_id", "candidate_status"])["candidate_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
