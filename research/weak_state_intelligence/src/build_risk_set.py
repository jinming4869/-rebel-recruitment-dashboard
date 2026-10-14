"""Week 2: build the SDM claimant risk set from movement PHASES, not movement IDs.

Audit of the real SDM file (2026-10-14) showed that the earlier rule "first row of a
groupid = claim entry" is wrong:
  * every groupid starts with up to ten INACTIVE policy-lookback rows (active==0, violsd missing);
  * 36 movements have a second phase of activity after a gap;
  * 108 movements were already active before coverage (prioract 1 = pre-1945,
    2 = colonial rule, 3 = previous non-colonial host); a host change creates a NEW groupid;
  * 65 movements are violent in their first active year; 19 carry priorviol==1;
  * SDM violsd_onset includes renewed onsets (217 onsets in 140 movements).

The unit is therefore an EPISODE = movement x phase under one host government, entered at
the first active year of the phase. Episodes are assigned to mutually exclusive populations:

  primary_first_claim    phase 1, claim start observed (prioract==0, startdate1 == first active
                         year), not violent in the claim year -> at risk of FIRST-EVER violence
  violent_in_claim_year  as above but violent in the claim year: ordering of claim and violence
                         is not resolvable from annual data; excluded from the previolence set
  inherited_claim        phase 1 with activity before coverage (pre-1945, colonial, prior host);
                         left-truncated, prior_violence flags whether violence predates coverage
  resumed_claim          phase 2 (new spell after the claim ended); recurrence population

Only primary_first_claim enters the first-ever escalation estimand. The others are kept as
separately labelled secondary populations and are never pooled into "first violence".

Annual timing: a claim year t0 has unknown month, so 24-month first violence is BOUNDED:
  y24_lower = violence in t0..t0+1 (certainly within 24 months)
  y24_upper = violence in t0..t0+2 (possibly within 24 months)
Everything here is DESCRIPTIVE; weak/strong stratum gaps are not causal contributions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DERIVED, LEDGERS, OUTPUTS, SourceNotReady, load_json, load_source, write_csv  # noqa: E402

SDM_END = 2012
WINDOWS = {"full_1945_2012": (1945, 2012), "gdp_supported_1961_2012": (1961, 2012),
           "post_cold_war_1990_2012": (1990, 2012)}
POPULATIONS = ["primary_first_claim", "violent_in_claim_year", "inherited_claim", "resumed_claim"]


def _flag(v) -> bool:
    return bool(pd.notna(v) and v == 1)


def _first(s: pd.Series):
    s = s.dropna()
    return s.iloc[0] if len(s) else np.nan


def movement_episodes(panel: pd.DataFrame, end_year: int = SDM_END) -> pd.DataFrame:
    """One row per movement x phase. panel uses logical SDM names (config/source_columns.json)."""
    p = panel.sort_values(["movement_id", "year"])
    rows = []
    for mid, g in p.groupby("movement_id", sort=False):
        prior_viol_cov = _flag(_first(g.loc[g["active"] == 1, "priorviol"])) or g["priorconflict"].notna().any()
        prioract = int(g["prioract"].iloc[0])
        phase1_violent = False
        for k in (1, 2):
            ph = g[(g["active"] == 1) & (g[f"phase{k}"] == 1)]
            if ph.empty:
                continue
            years = ph["year"].to_numpy()
            entry, last = int(years.min()), int(years.max())
            start = _first(ph[f"startdate{k}"])
            end_code = int(_first(ph[f"enddate{k}"]))
            viol_years = ph.loc[ph["anti_state_violence"] == 1, "year"]
            fv = int(viol_years.min()) if len(viol_years) else None
            violent_at_entry = fv == entry
            onset_years = ph.loc[ph["violsd_onset"] == 1, "year"].astype(int).tolist()
            terr = ph.loc[ph["ucdp_terrconflict"] == 1, "year"]

            left_trunc = k == 1 and (prioract > 0 or (pd.notna(start) and start < entry))
            if k == 2:
                population, prior_violence = "resumed_claim", phase1_violent or prior_viol_cov
            elif left_trunc:
                population, prior_violence = "inherited_claim", prior_viol_cov
            else:
                population = "violent_in_claim_year" if violent_at_entry else "primary_first_claim"
                prior_violence = False

            if fv is not None:
                exit_type, exit_year = "violence", fv
            elif end_code == 8888:
                exit_type, exit_year = "host_change", last
            elif end_code == 9999:
                exit_type, exit_year = "right_censored", end_year
            else:
                exit_type, exit_year = "claim_ended", end_code

            checks = []
            if len(years) != last - entry + 1:
                checks.append("gap_within_phase")
            if end_code not in (8888, 9999) and end_code != last:
                checks.append("enddate_ne_last_active")
            if end_code == 9999 and last != end_year:
                checks.append("ongoing_but_not_observed_to_end")
            if fv is not None and not violent_at_entry and fv not in onset_years:
                checks.append("first_violence_not_flagged_onset")
            if population == "primary_first_claim" and _flag(_first(ph["priorviol"])):
                checks.append("priorviol_in_primary")

            lo, hi = _y24_bounds(population, entry, fv, exit_type, exit_year, end_year)
            rows.append({
                "episode_id": f"{mid}-p{k}", "movement_id": mid,
                "movement_name": g["movement_name"].iloc[0], "country_name": g["country_name"].iloc[0],
                "country_code": int(g["country_code"].iloc[0]), "phase": k,
                "claim_start_year": int(start) if pd.notna(start) else None, "entry_year": entry,
                "prioract": prioract, "left_truncated": left_trunc, "prior_violence": prior_violence,
                "population": population, "violent_at_entry": violent_at_entry,
                "first_violence_year": fv, "sdm_onset_years": ";".join(map(str, onset_years)),
                "n_sdm_onsets_in_phase": len(onset_years),
                "end_code": end_code, "exit_type": exit_type, "exit_year": exit_year,
                "years_observed": exit_year - entry + 1, "last_active_year": last,
                "y24_lower": lo, "y24_upper": hi,
                "ucdp_terr_first_year_sdm": int(terr.min()) if len(terr) else None,
                "high_violence_ever": bool((ph["high_violence"] == 1).any()),
                "sdm_sample": _flag(_first(g["sample"])), "sdm_weight": _first(g["weight"]),
                "host_change_entry": bool(ph["doublecount"].isin([2, 4]).iloc[0]),
                "checks": ";".join(checks),
            })
            if fv is not None:
                phase1_violent = phase1_violent or k == 1
    return pd.DataFrame(rows)


def _y24_bounds(population, entry, fv, exit_type, exit_year, end_year):
    """(lower, upper) 24-month first-violence indicators; None = not determinable."""
    if population in ("violent_in_claim_year", "inherited_claim"):
        return None, None  # claim year unobserved or ordering unresolvable
    def ind(h):
        if fv is not None and fv <= entry + h:
            return 1
        if exit_type in ("claim_ended", "host_change") and exit_year < entry + h:
            return 0  # claim ended/host changed without violence: competing exit, flagged in exit_type
        return 0 if min(exit_year, end_year) >= entry + h else None
    return ind(1), ind(2)


def risk_set_years(episodes: pd.DataFrame) -> pd.DataFrame:
    """Episode-years at risk of violence, from entry to exit (inclusive)."""
    e = episodes[episodes["population"] != "violent_in_claim_year"]
    out = []
    for r in e.itertuples(index=False):
        for y in range(r.entry_year, r.exit_year + 1):
            out.append({"episode_id": r.episode_id, "population": r.population, "country_code": r.country_code,
                        "year": y, "t_since_entry": y - r.entry_year,
                        "event": int(r.exit_type == "violence" and y == r.exit_year),
                        "competing_exit": int(r.exit_type in ("claim_ended", "host_change") and y == r.exit_year)})
    return pd.DataFrame(out)


def cow_to_qog(code: int, year: int, overrides: list[dict]) -> int | None:
    for o in overrides:
        if o["sdm_ccode"] == code:
            return o["qog_ccodecow"] if year >= o["from_year"] else None
    return code


def add_weakness_stratum(episodes: pd.DataFrame, gdp: pd.DataFrame | None, overrides: list[dict] | None = None) -> pd.DataFrame:
    """W = log GDP per capita in entry_year-1, median split over primary_first_claim episodes
    with a known value. Primary: QoG wdi_gdpcapcon2015 (w_stratum). Sensitivity, never
    spliced: Maddison mad_gdppc (w_stratum_mad). Missing -> 'unknown' with gdp_missing_reason."""
    e = episodes.copy()
    if gdp is None:
        e["w_stratum"] = "not_computed"
        return e
    overrides = overrides or []
    e["qog_cow"] = [cow_to_qog(c, y - 1, overrides) for c, y in zip(e["country_code"], e["entry_year"])]
    g = gdp.dropna(subset=["country_code_cow"]).assign(country_code_cow=lambda d: d["country_code_cow"].astype(int))
    in_qog = set(g["country_code_cow"])
    for col, suffix in (("gdppc", ""), ("gdppc_maddison", "_mad")):
        lut = g.dropna(subset=[col]).set_index(["country_code_cow", "year"])[col].to_dict()
        val = pd.to_numeric(pd.Series([lut.get((c, y - 1)) if c is not None else None
                                       for c, y in zip(e["qog_cow"], e["entry_year"])], index=e.index))
        logv = np.log(val.where(val > 0))
        med = logv[e["population"] == "primary_first_claim"].median()
        e[f"log_gdppc_lag{suffix}"] = logv
        e[f"w_stratum{suffix}"] = np.where(logv.isna(), "unknown", np.where(logv <= med, "weak", "strong"))
        e.attrs[f"w_median_log_gdppc{suffix}"] = float(med) if pd.notna(med) else None
    e["gdp_missing_reason"] = np.select(
        [e["log_gdppc_lag"].notna(), e["qog_cow"].isna() | ~e["qog_cow"].isin(in_qog), e["entry_year"] - 1 < 1960],
        ["", "country_not_in_qog", "before_wdi_coverage_1960"], default="wdi_value_missing_for_country_year")
    return e


def _rate(k, n):
    return round(k / n, 3) if n else None


def flow_table(episodes: pd.DataFrame) -> pd.DataFrame:
    """Stage counts by population x weakness stratum. Stages the public files cannot
    observe are NA with a reason, never zero."""
    rows = []
    for pop in POPULATIONS:
        ep = episodes[episodes["population"] == pop]
        for stratum, g in [("all", ep)] + list(ep.groupby("w_stratum")):
            lo, hi = g["y24_lower"], g["y24_upper"]
            n_lo, n_hi = int(lo.notna().sum()), int(hi.notna().sum())
            rows.append({
                "population": pop, "w_stratum": stratum, "episodes": len(g),
                "countries": g["country_code"].nunique(),
                "prior_violence": int(g["prior_violence"].sum()),
                "govt_awareness": "NA:not_in_public_data",
                "first_offer_or_refusal": "NA:not_in_public_data (SDM con/accomm = enacted policy, sample only)",
                "exit_violence": int((g["exit_type"] == "violence").sum()),
                "exit_claim_ended": int((g["exit_type"] == "claim_ended").sum()),
                "exit_host_change": int((g["exit_type"] == "host_change").sum()),
                "right_censored": int((g["exit_type"] == "right_censored").sum()),
                "y24_lower_events": int((lo == 1).sum()), "y24_lower_known": n_lo,
                "y24_lower_rate": _rate(int((lo == 1).sum()), n_lo),
                "y24_upper_events": int((hi == 1).sum()), "y24_upper_known": n_hi,
                "y24_upper_rate": _rate(int((hi == 1).sum()), n_hi),
                "ucdp_terr_reached_sdm": int(g["ucdp_terr_first_year_sdm"].notna().sum()),
                "high_violence_ever": int(g["high_violence_ever"].sum()),
            })
    return pd.DataFrame(rows)


def cumulative_incidence(episodes: pd.DataFrame, horizon: int = 20, population: str = "primary_first_claim") -> pd.DataFrame:
    """Discrete-time Aalen-Johansen CIF: violence vs (claim end or host change), censoring at 2012."""
    out = []
    ep = episodes[episodes["population"] == population]
    for stratum, g in [("all", ep)] + list(ep.groupby("w_stratum")):
        dur = (g["exit_year"] - g["entry_year"]).to_numpy()
        typ = g["exit_type"].to_numpy()
        comp = np.isin(typ, ["claim_ended", "host_change"])
        surv, cif_v, cif_c = 1.0, 0.0, 0.0
        for t in range(horizon + 1):
            at_risk = int((dur >= t).sum())
            dv = int(((dur == t) & (typ == "violence")).sum())
            dc = int(((dur == t) & comp).sum())
            if at_risk:
                cif_v += surv * dv / at_risk
                cif_c += surv * dc / at_risk
                surv *= 1 - (dv + dc) / at_risk
            out.append({"population": population, "w_stratum": stratum, "years_since_entry": t, "at_risk": at_risk,
                        "violence_events": dv, "competing_exits": dc,
                        "cif_violence": round(cif_v, 4), "cif_competing": round(cif_c, 4)})
    return pd.DataFrame(out)


def country_crosswalk_audit(panel: pd.DataFrame, gdp: pd.DataFrame, overrides: list[dict]) -> pd.DataFrame:
    """Every SDM country code with its QoG match, names on both sides, and active-year coverage.
    Unmatched codes stay in the table (match_status != matched)."""
    g = gdp.dropna(subset=["country_code_cow"]).assign(country_code_cow=lambda d: d["country_code_cow"].astype(int))
    names = g.groupby("country_code_cow")["country_name"].agg(lambda x: "|".join(sorted(set(x))))
    gdp_years = g.dropna(subset=["gdppc"]).groupby("country_code_cow")["year"].agg(set)
    rows = []
    act = panel[panel["active"] == 1]
    for (code, cname), sub in act.groupby(["country_code", "country_name"]):
        years = sorted(sub["year"].unique())
        mapped = [cow_to_qog(int(code), int(y), overrides) for y in years]
        matched = [y for y, m in zip(years, mapped) if m is not None and m in names.index]
        with_gdp = [y for y, m in zip(years, mapped) if m is not None and (y in gdp_years.get(m, set()))]
        status = "matched" if len(matched) == len(years) else ("partial" if matched else "unmatched")
        rows.append({"sdm_ccode": int(code), "sdm_country": cname,
                     "qog_ccodecow": ";".join(sorted({str(m) for m in mapped if m is not None})),
                     "qog_names": names.get(next((m for m in mapped if m is not None), -1), ""),
                     "active_years": f"{years[0]}-{years[-1]}", "n_active_years": len(years),
                     "years_matched": len(matched), "years_with_wdi_gdp": len(with_gdp), "match_status": status,
                     "override": any(o["sdm_ccode"] == code for o in overrides)})
    return pd.DataFrame(rows).sort_values(["match_status", "sdm_ccode"])


def structural_audit(panel: pd.DataFrame, episodes: pd.DataFrame) -> dict:
    """Facts about the raw file that the old 'first row = entry' rule ignored."""
    first_rows = panel.sort_values(["movement_id", "year"]).groupby("movement_id").head(1)
    return {
        "rows": len(panel), "movements": int(panel["movement_id"].nunique()),
        "active_rows": int((panel["active"] == 1).sum()),
        "first_row_inactive_lookback": int((first_rows["active"] == 0).sum()),
        "movements_with_phase2": int(panel.loc[panel["phase2"] == 1, "movement_id"].nunique()),
        "prioract_counts": {str(k): int(v) for k, v in first_rows["prioract"].value_counts().sort_index().items()},
        "episodes_by_population": episodes["population"].value_counts().to_dict(),
        "episodes_with_checks": episodes.loc[episodes["checks"] != "", ["episode_id", "movement_name", "checks"]].to_dict("records"),
        "sdm_onsets_total": int((panel["violsd_onset"] == 1).sum()),
        "sdm_onsets_that_are_first_in_primary": int((episodes.loc[episodes["population"] == "primary_first_claim", "exit_type"] == "violence").sum()),
        "old_rule_entry_year_error_years_median": float((episodes.loc[episodes["phase"] == 1].set_index("movement_id")["entry_year"]
                                                         - first_rows.set_index("movement_id")["year"]).median()),
    }


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
    overrides = load_json("country_crosswalk.json")["overrides"]
    ep = add_weakness_stratum(movement_episodes(panel), gdp, overrides)
    if gdp is not None:
        write_csv(country_crosswalk_audit(panel, gdp, overrides), OUTPUTS / "country_crosswalk_audit.csv")
    write_csv(ep, DERIVED / "movement_episodes.csv")
    write_csv(risk_set_years(ep), DERIVED / "risk_set_episode_years.csv")
    flows = []
    for label, (lo, hi) in WINDOWS.items():
        sub = ep[(ep["entry_year"] >= lo) & (ep["entry_year"] <= hi)]
        flows.append(flow_table(sub).assign(window=label))
    write_csv(pd.concat(flows), LEDGERS / "risk_set_flow.csv")
    write_csv(cumulative_incidence(ep[ep["entry_year"] >= 1961]), OUTPUTS / "cumulative_incidence.csv")
    audit = structural_audit(panel, ep)
    audit["w_median_log_gdppc"] = ep.attrs.get("w_median_log_gdppc")
    audit["w_median_log_gdppc_mad"] = ep.attrs.get("w_median_log_gdppc_mad")
    prim = ep[ep["population"] == "primary_first_claim"]
    audit["primary_gdp_missing_reasons"] = prim["gdp_missing_reason"].replace("", "observed").value_counts().to_dict()
    audit["primary_gdp_missing_countries_1961_2012"] = (
        prim[(prim["gdp_missing_reason"] == "wdi_value_missing_for_country_year")]
        .groupby("country_name").size().sort_values(ascending=False).to_dict())
    sens = []
    for label, (lo, hi) in WINDOWS.items():
        sub = ep[(ep["entry_year"] >= lo) & (ep["entry_year"] <= hi)].assign(w_stratum=lambda d: d["w_stratum_mad"])
        sens.append(flow_table(sub).assign(window=label, gdp_series="mad_gdppc_sensitivity"))
    write_csv(pd.concat(sens), OUTPUTS / "risk_set_flow_maddison_sensitivity.csv")
    (OUTPUTS / "risk_set_audit.json").write_text(json.dumps(audit, indent=2, default=str))
    print(json.dumps({k: v for k, v in audit.items() if k != "episodes_with_checks"}, indent=1, default=str))
    print(f"episodes with structural check flags: {len(audit['episodes_with_checks'])}")


if __name__ == "__main__":
    main()
