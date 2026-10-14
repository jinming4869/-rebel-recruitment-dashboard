"""Week 2: build the previolence claimant risk set from SDM and describe stage flow.

Outputs (only when real, confirmed sources are present):
  data/derived/risk_set_movement_years.csv
  data/derived/movement_episodes.csv
  ledgers/risk_set_flow.csv            -- stage counts by capacity stratum
  outputs/cumulative_incidence.csv     -- competing risks: violence vs termination

Everything here is DESCRIPTIVE. Stage-specific differences by weakness stratum are
not causal contributions (Protocol §Quantitative risk set).

Timing caveat: public SDM is annual, so "violence within 24 months" is approximated
by first violent year <= entry year + 2 (an upper bound on a true 24-month window)
and flagged `y24_annual_approx`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DERIVED, LEDGERS, OUTPUTS, SourceNotReady, load_source, write_csv  # noqa: E402

SDM_START, SDM_END = 1945, 2012
ANALYSIS_WINDOW = (1960, 2012)          # overlap with SRDP/UCDP 26.1 (Protocol §Quantitative)
POST_COLD_WAR_WINDOW = (1990, 2012)     # separately labelled descriptive window


def movement_episodes(panel: pd.DataFrame, end_year: int = SDM_END, start_year: int = SDM_START) -> pd.DataFrame:
    """One row per movement: entry, exit type and timing.

    panel needs: movement_id, country_code, year, anti_state_violence (0/1).
    """
    p = panel.sort_values(["movement_id", "year"])
    rows = []
    for mid, g in p.groupby("movement_id", sort=False):
        first = int(g["year"].min())
        last = int(g["year"].max())
        viol_years = g.loc[g["anti_state_violence"] == 1, "year"]
        first_viol = int(viol_years.min()) if len(viol_years) else None
        violent_at_entry = first_viol == first
        if first_viol is not None:
            exit_type, exit_year = "violence", first_viol
        elif last < end_year:
            exit_type, exit_year = "terminated", last
        else:
            exit_type, exit_year = "right_censored", end_year
        if violent_at_entry:
            y24 = "not_applicable"
        elif first_viol is not None and first_viol - first <= 2:
            y24 = "1"
        elif first + 2 > end_year and first_viol is None:
            y24 = "right_censored"
        elif exit_type == "terminated" and last - first < 2:
            y24 = "0_terminated_before_24m"
        else:
            y24 = "0"
        rows.append({
            "movement_id": mid,
            "country_code": g["country_code"].iloc[0],
            "entry_year": first,
            "left_truncated": first == start_year,
            "violent_at_entry": violent_at_entry,
            "previolence_eligible": not violent_at_entry,
            "first_violence_year": first_viol,
            "exit_type": exit_type,
            "exit_year": exit_year,
            "years_at_risk": exit_year - first + 1,
            "y24_annual_approx": y24,
        })
    return pd.DataFrame(rows)


def risk_set_years(episodes: pd.DataFrame) -> pd.DataFrame:
    """Movement-years at risk of first violence (previolence eligible only)."""
    e = episodes[episodes["previolence_eligible"]]
    out = []
    for r in e.itertuples(index=False):
        for y in range(r.entry_year, r.exit_year + 1):
            out.append({"movement_id": r.movement_id, "country_code": r.country_code, "year": y,
                        "t_since_entry": y - r.entry_year,
                        "event": int(r.exit_type == "violence" and y == r.exit_year),
                        "terminated": int(r.exit_type == "terminated" and y == r.exit_year)})
    return pd.DataFrame(out)


def add_weakness_stratum(episodes: pd.DataFrame, gdp: pd.DataFrame | None) -> pd.DataFrame:
    """Baseline weakness W = log GDPpc lagged one year before entry; split at the
    median of eligible movements. Missing GDP -> stratum 'unknown' (kept, not dropped)."""
    e = episodes.copy()
    if gdp is None:
        e["w_stratum"] = "not_computed"
        return e
    g = gdp.assign(year=gdp["year"] + 1)  # value from year t-1 attached to year t
    e = e.merge(g.rename(columns={"year": "entry_year"}), on=["country_code", "entry_year"], how="left")
    e["log_gdppc_lag"] = np.log(e["gdppc"].where(e["gdppc"] > 0))
    med = e.loc[e["previolence_eligible"], "log_gdppc_lag"].median()
    e["w_stratum"] = np.where(e["log_gdppc_lag"].isna(), "unknown",
                              np.where(e["log_gdppc_lag"] <= med, "weak", "strong"))
    return e.drop(columns=["gdppc"])


def flow_table(episodes: pd.DataFrame, ucdp_matched: set | None = None) -> pd.DataFrame:
    """Stage counts by weakness stratum. Stages not observable in public data are
    reported as NA with an explicit reason rather than zero."""
    rows = []
    for stratum, g in [("all", episodes)] + list(episodes.groupby("w_stratum")):
        elig = g[g["previolence_eligible"]]
        y24 = elig["y24_annual_approx"]
        row = {
            "w_stratum": stratum,
            "movements": len(g),
            "violent_at_entry_excluded": int(g["violent_at_entry"].sum()),
            "left_truncated_1945": int(elig["left_truncated"].sum()),
            "previolence_entries": len(elig),
            "govt_awareness": "NA:not_in_public_SDM",
            "first_offer_or_refusal": "NA:requires_weighted_SDM_response_subsample",
            "first_violence": int((elig["exit_type"] == "violence").sum()),
            "terminated_no_violence": int((elig["exit_type"] == "terminated").sum()),
            "right_censored": int((elig["exit_type"] == "right_censored").sum()),
            "y24_violence": int((y24 == "1").sum()),
            "y24_no_violence": int(y24.str.startswith("0").sum()),
            "y24_censored": int((y24 == "right_censored").sum()),
            "ucdp_threshold": (int(elig["movement_id"].isin(ucdp_matched).sum())
                               if ucdp_matched is not None else "NA:crosswalk_not_reviewed"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def cumulative_incidence(episodes: pd.DataFrame, horizon: int = 10) -> pd.DataFrame:
    """Discrete-time Aalen–Johansen CIF for violence vs termination (competing),
    right-censoring at SDM end. By weakness stratum."""
    out = []
    for stratum, g in [("all", episodes)] + list(episodes.groupby("w_stratum")):
        e = g[g["previolence_eligible"]]
        dur = (e["exit_year"] - e["entry_year"]).to_numpy()
        typ = e["exit_type"].to_numpy()
        surv, cif_v, cif_t = 1.0, 0.0, 0.0
        for t in range(horizon + 1):
            at_risk = int((dur >= t).sum())
            dv = int(((dur == t) & (typ == "violence")).sum())
            dtm = int(((dur == t) & (typ == "terminated")).sum())
            if at_risk:
                cif_v += surv * dv / at_risk
                cif_t += surv * dtm / at_risk
                surv *= 1 - (dv + dtm) / at_risk
            out.append({"w_stratum": stratum, "years_since_entry": t, "at_risk": at_risk,
                        "violence_events": dv, "terminations": dtm,
                        "cif_violence": round(cif_v, 4), "cif_termination": round(cif_t, 4)})
    return pd.DataFrame(out)


def main() -> None:
    try:
        panel = load_source("DATA_SDM")
    except SourceNotReady as exc:
        print(f"NOT RUN: {exc}\nNo numbers were produced (Protocol: report the gap, do not fill it).")
        sys.exit(2)
    try:
        gdp = load_source("DATA_GDPPC")
    except SourceNotReady as exc:
        print(f"Weakness strata skipped: {exc}")
        gdp = None
    ucdp_matched = None
    xw_path = LEDGERS / "movement_actor_crosswalk.csv"
    xw = pd.read_csv(xw_path, dtype=str, keep_default_na=False)
    reviewed = xw[xw["match_confidence"].isin(["exact_reviewed", "probable_reviewed"]) & (xw["ucdp_conflict_id"] != "")]
    if len(reviewed):
        ucdp_matched = set(reviewed["sdm_movement_id"])

    ep = add_weakness_stratum(movement_episodes(panel), gdp)
    write_csv(ep, DERIVED / "movement_episodes.csv")
    write_csv(risk_set_years(ep), DERIVED / "risk_set_movement_years.csv")
    flows = []
    for label, (lo, hi) in {"full_1945_2012": (SDM_START, SDM_END), "analysis_1960_2012": ANALYSIS_WINDOW,
                            "post_cold_war_1990_2012": POST_COLD_WAR_WINDOW}.items():
        sub = ep[(ep["entry_year"] >= lo) & (ep["entry_year"] <= hi)]
        flows.append(flow_table(sub, ucdp_matched).assign(window=label))
    write_csv(pd.concat(flows), LEDGERS / "risk_set_flow.csv")
    write_csv(cumulative_incidence(ep), OUTPUTS / "cumulative_incidence.csv")
    print("risk set built; see ledgers/risk_set_flow.csv")


if __name__ == "__main__":
    main()
