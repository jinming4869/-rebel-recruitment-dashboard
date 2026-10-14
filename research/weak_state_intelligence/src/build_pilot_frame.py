"""Within-country pilot frames and provisional national-strata support.

1. ledgers/pilot_candidate_frame.csv: for each frame in config/pilot_frames.json, every SDM
   episode of that host country that is active during the window, with its population
   (from build_risk_set), dated SDM outcome within the window, SRDP organizations whose
   SRDP group name equals the SDM group name (UNREVIEWED name match, never an ID join),
   and national context (Hanson-Sigman milpercap / infcap, QoG GDP) at window start.
2. outputs/provisional_strata_support.csv: counts of primary_first_claim episodes (1961-2012)
   by PROVISIONAL national information (infcap) x national force (milpercap) x escalation
   stratum. These are national proxies; they do not measure challenger-specific
   information or local deployable force and cannot pass gate (iii). Nothing is drawn.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DERIVED, LEDGERS, OUTPUTS, SourceNotReady, load_json, load_source, write_csv  # noqa: E402


def _norm(t: str) -> str:
    return str(t).split("(")[0].strip().lower().rstrip("s")


def srdp_orgs_by_group(srdp: pd.DataFrame, country: str, group: str, lo: int, hi: int) -> str:
    x = srdp[(srdp["country_name"] == country) & (srdp["group"].map(_norm) == _norm(group))]
    x = x[(x["year"] >= lo) & (x["year"] <= hi)]
    if x.empty:
        return ""
    g = x.groupby(["org_id", "org_name"]).agg(y0=("year", "min"), y1=("year", "max"),
                                             v=("violence_state", lambda v: x.loc[v[v == 1].index, "year"].min()))
    return "; ".join(f"{n} [{int(a)}-{int(b)}{', violence ' + str(int(v)) if pd.notna(v) else ''}]"
                     for (_, n), (a, b, v) in g.iterrows())


def pilot_frame(episodes: pd.DataFrame, srdp: pd.DataFrame, hs: pd.DataFrame | None, frames: list[dict]) -> pd.DataFrame:
    rows = []
    for f in frames:
        lo, hi = f["window"]
        e = episodes[(episodes["country_code"] == f["country_code"]) & (episodes["entry_year"] <= hi)
                     & (episodes["last_active_year"] >= lo)]
        if f.get("region_filter"):
            e = e[e["movement_name"].isin(f["region_filter"])]
        ctx = {}
        if hs is not None:
            h = hs[(hs["country_code_cow"] == f["country_code"]) & (hs["year"] == max(lo, 1960))]
            if len(h):
                ctx = {"natl_milpercap_at_start": round(float(h["milpercap"].iloc[0]), 3) if pd.notna(h["milpercap"].iloc[0]) else None,
                       "natl_infcap_at_start": round(float(h["infcap"].iloc[0]), 3) if pd.notna(h["infcap"].iloc[0]) else None}
        for r in e.itertuples(index=False):
            fv = r.first_violence_year
            if pd.notna(fv) and lo <= fv <= hi:
                window_outcome = f"first_violence_in_phase_{int(fv)}"
            elif pd.notna(fv) and fv < lo:
                window_outcome = f"already_violent_since_{int(fv)} (recurrence population)"
            elif r.exit_type == "claim_ended" and r.exit_year <= hi:
                window_outcome = f"claim_ended_{int(r.exit_year)}_without_violence"
            else:
                window_outcome = "no_violence_in_window"
            rows.append({"frame_id": f["frame_id"], "frame_role": f["role"], "episode_id": r.episode_id,
                         "movement_id": r.movement_id, "movement": r.movement_name, "country": r.country_name,
                         "population": r.population, "sdm_claim_start": r.claim_start_year, "sdm_entry_year": r.entry_year,
                         "prioract": r.prioract, "prior_violence": r.prior_violence,
                         "sdm_first_violence_year": fv, "sdm_exit": f"{r.exit_type}:{int(r.exit_year)}",
                         "window_outcome": window_outcome, "sdm_random_sample": r.sdm_sample,
                         "srdp_orgs_name_matched_unreviewed": srdp_orgs_by_group(srdp, r.country_name, r.movement_name, lo - 5, hi + 5),
                         **ctx})
    return pd.DataFrame(rows)


def provisional_strata(episodes: pd.DataFrame, hs: pd.DataFrame) -> pd.DataFrame:
    e = episodes[(episodes["population"] == "primary_first_claim") & (episodes["entry_year"] >= 1961)].copy()
    lut = hs.dropna(subset=["country_code_cow"]).assign(c=lambda d: d["country_code_cow"].astype(int)).set_index(["c", "year"])
    for col in ("infcap", "milpercap"):
        v = [lut[col].get((c, y - 1), np.nan) for c, y in zip(e["country_code"], e["entry_year"])]
        e[col] = pd.to_numeric(pd.Series(v, index=e.index))
        med = e[col].median()
        e[f"{col}_stratum"] = np.where(e[col].isna(), "unknown", np.where(e[col] <= med, "low", "high"))
    e["escalation_stratum"] = np.where(e["exit_type"] == "violence", "escalating", "non_escalating")
    t = e.groupby(["infcap_stratum", "milpercap_stratum", "escalation_stratum"]).agg(
        episodes=("episode_id", "size"), countries=("country_code", "nunique")).reset_index()
    t["note"] = "PROVISIONAL national proxies (Hanson-Sigman 1960-2015); not challenger-specific information or local force"
    return t


def main() -> None:
    ep_path = DERIVED / "movement_episodes.csv"
    if not ep_path.exists():
        print("NOT RUN: run src/build_risk_set.py first.")
        sys.exit(2)
    episodes = pd.read_csv(ep_path)
    try:
        srdp = load_source("DATA_SRDP")
        hs = load_source("DATA_HS_CAPACITY")
    except SourceNotReady as exc:
        print(f"NOT RUN: {exc}")
        sys.exit(2)
    frames = load_json("pilot_frames.json")["frames"]
    pf = pilot_frame(episodes, srdp, hs, frames)
    write_csv(pf, LEDGERS / "pilot_candidate_frame.csv")
    write_csv(provisional_strata(episodes, hs), OUTPUTS / "provisional_strata_support.csv")
    print(pf[["frame_id", "movement", "population", "window_outcome"]].to_string(index=False))


if __name__ == "__main__":
    main()
