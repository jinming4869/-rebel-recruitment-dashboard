#!/usr/bin/env python3
"""Deterministic browser-safe aggregates for the recruitment dashboard."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from input_registry import read_input


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "dataset" / "raw"
OUTPUT = ROOT / "dashboard" / "data" / "dashboard-data.js"
CROSSWALK_OUTPUT = ROOT / "dataset" / "derived" / "actor_entity_candidates.csv"
SEED = 20260901
BOOTSTRAP_REPS = 240

LOCAL_DATA_IDS = {
    "CROAD", "RAID", "RHRV", "UCDP-DYADIC", "UCDP-ACTOR", "UCDP-GED", "UCDP-ESD",
    "HW2008", "BB2013", "AQ-BRITISH", "GDIS", "NSA", "RQSI", "RIG", "M3", "MLAD",
}

META = {
    "CROAD": {"family": "Rebel recruitment", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "RAID": {"family": "Rebel recruitment", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "RHRV": {"family": "Rebel abuses & recruitment", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "UCDP-DYADIC": {"family": "Conflict backbone", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "UCDP-ACTOR": {"family": "Actor backbone", "accessClass": "local-data", "spatialClass": "Cross-national actors"},
    "UCDP-GED": {"family": "Conflict events", "accessClass": "local-data", "spatialClass": "Global event locations"},
    "UCDP-ESD": {"family": "External support", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "HW2008": {"family": "Individual recruitment", "accessClass": "local-data", "spatialClass": "Single-country survey", "timelineStart": 2003, "timelineEnd": 2003, "timelineBasis": "survey year"},
    "BB2013": {"family": "Individual recruitment", "accessClass": "local-data", "spatialClass": "Multi-country replication bundle", "timelineBasis": "retrospective; no canonical row-year span"},
    "AQ-BRITISH": {"family": "Historical recruitment", "accessClass": "local-data", "spatialClass": "Historical individual case", "timelineStart": 1936, "timelineEnd": 1939, "timelineBasis": "Spanish Civil War period"},
    "GDIS": {"family": "Exogenous shocks", "accessClass": "local-data", "spatialClass": "Global disaster locations"},
    "NSA": {"family": "Rebel organization", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "RQSI": {"family": "Rebel governance", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "RIG": {"family": "Rebel governance", "accessClass": "local-data", "spatialClass": "Cross-national conflict"},
    "M3": {"family": "State militarization", "accessClass": "local-data", "spatialClass": "Global state panel"},
    "MLAD": {"family": "Military labor systems", "accessClass": "local-data", "spatialClass": "Historical state panel"},
    "EGMR": {"family": "State recruitment", "accessClass": "documentation", "spatialClass": "Cross-national ethnic groups", "timelineStart": 1946, "timelineEnd": 2010, "timelineBasis": "documented universe"},
    "REGPLUS": {"family": "Rebel governance", "accessClass": "blocked", "spatialClass": "Cross-national territorial conflicts", "timelineStart": 1989, "timelineEnd": 2020, "timelineBasis": "documented universe"},
    "TERR-CONTROL": {"family": "Data gap", "accessClass": "gap", "spatialClass": "Needed: organization–place–time", "timelineBasis": "no dataset"},
    "HIST-MIL-LABOR": {"family": "Archive lead", "accessClass": "gap", "spatialClass": "Case-specific archive", "timelineBasis": "case not selected"},
}

APPEALS = {
    "islamist_appeals": "Islamist", "other_rel_appeals": "Other religious",
    "left_appeals": "Leftist", "anti_resource_appeals": "Anti-resource exploitation",
    "gov_violence_appeals": "Government violence", "feminist_appeals": "Feminist",
    "other_appeals": "Other", "ethnic_nat_appeals": "Ethnic-nationalist",
    "anti_intervention_appeals": "Anti-intervention", "gov_grievance_appeals": "Government grievance",
}
RHRV_VIOLATIONS = {
    "rkillings": "Killings", "rtorture": "Torture", "rdetention": "Detention",
    "rproperty": "Property violations", "rsexual": "Sexual violence",
    "rdisplace": "Displacement", "rrestrict": "Movement restrictions",
}
RQSI_POL = ["Pol_Flag", "Pol_OrgGov", "Pol_Elect", "Pol_Gov", "Pol_Border", "Pol_ID", "Pol_PolWing", "Pol_AttemptIO", "Pol_JoinIO", "Pol_Embassy", "Pol_Media", "Pol_Constitution"]
RQSI_ECON = ["Econ_Currency", "Econ_IllegalNet", "Econ_NegResource", "Econ_Treaty", "Econ_Tax"]
RQSI_SOC = ["Soc_Edu", "Soc_Health", "Soc_Infra", "Soc_Trans", "Soc_Law", "Soc_Sec", "Soc_Jus", "Soc_House", "Soc_Rep", "Soc_Aid"]
RQSI_GOV = ["Gov_in_Exile", "LocalGov", "NationalGov", "PaperNatGov"]
RIG_CORE = ["codeconduct", "peercomplaints", "investigativebranch", "tribunalproceedings", "publicproceedings", "deathpenalty", "incarceration", "reprimandpromotion", "familypunishments"]
ESD_TYPES = {
    "ext_x": "Troops", "ext_y": "Joint operations", "ext_w": "Weapons",
    "ext_m": "Materiel/logistics", "ext_t": "Training", "ext_f": "Funding",
    "ext_i": "Intelligence", "ext_l": "Territory access", "ext_o": "Other",
}


def clean_places(values: Iterable) -> list[str]:
    places: set[str] = set()
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        for part in str(value).split(","):
            part = " ".join(part.strip().split())
            if part and part.lower() not in {"nan", "none", "unknown"}:
                places.add(part)
    return sorted(places)


def clean_ucdp_conflict_locations(values: Iterable) -> list[str]:
    components: list[str] = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        components.extend(str(value).split(":", 1)[0].split(" - "))
    return clean_places(components)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def appeal_count(frame: pd.DataFrame) -> pd.Series:
    """Count RAID appeal items only for rows with all 10 registered items observed."""
    values = frame[list(APPEALS)].apply(pd.to_numeric, errors="coerce")
    return values.sum(axis=1).where(values.notna().all(axis=1))


def years(series: pd.Series) -> tuple[int | None, int | None]:
    values = numeric(series).dropna()
    return (None, None) if values.empty else (int(values.min()), int(values.max()))


def date_years(series: pd.Series) -> tuple[int | None, int | None]:
    values = pd.to_datetime(series, errors="coerce").dropna()
    return (None, None) if values.empty else (int(values.dt.year.min()), int(values.dt.year.max()))


def finite(value, digits=4):
    if value is None or pd.isna(value) or not np.isfinite(value):
        return None
    return round(float(value), digits)


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & (weights > 0)
    if not mask.any():
        return float("nan")
    return float(np.average(numeric(values[mask]), weights=numeric(weights[mask])))


def weighted_summary(values: pd.Series, weights: pd.Series, clusters: pd.Series | None = None, seed: int = SEED) -> dict:
    mask = values.notna() & weights.notna() & (weights > 0)
    x = numeric(values[mask]).to_numpy(float)
    w = numeric(weights[mask]).to_numpy(float)
    if not len(x):
        return {"value": None, "lower": None, "upper": None, "n": 0, "missingRate": 1}
    mean = float(np.average(x, weights=w))
    variance = float(np.average((x - mean) ** 2, weights=w))
    neff = (w.sum() ** 2) / np.square(w).sum() if np.square(w).sum() else len(x)
    lower, upper, uncertainty = None, None, "effective-n normal interval"
    if clusters is not None:
        sample = pd.DataFrame({"value": numeric(values[mask]), "weight": numeric(weights[mask]), "cluster": clusters[mask]}).dropna()
        unique = sample["cluster"].unique()
        if len(unique) >= 3:
            rng = np.random.default_rng(seed)
            grouped = {key: part for key, part in sample.groupby("cluster")}
            estimates = []
            for _ in range(BOOTSTRAP_REPS):
                draw = pd.concat([grouped[key] for key in rng.choice(unique, size=len(unique), replace=True)], ignore_index=True)
                estimates.append(float(np.average(draw["value"], weights=draw["weight"])))
            lower, upper = finite(np.quantile(estimates, .025)), finite(np.quantile(estimates, .975))
            uncertainty = "survey-location cluster bootstrap"
    if lower is None or upper is None:
        se = math.sqrt(variance / max(neff, 1))
        lower, upper = finite(mean - 1.96 * se), finite(mean + 1.96 * se)
    return {"value": finite(mean), "lower": lower, "upper": upper, "n": int(len(x)), "effectiveN": finite(neff, 1), "missingRate": finite(1 - len(x) / len(values)), "uncertainty": uncertainty}


def battery_score(frame: pd.DataFrame, fields: list[str], minimum_fraction: float = .8) -> pd.DataFrame:
    """Comparable descriptive item share, available only with >=80% item exposure."""
    values = frame[fields].apply(pd.to_numeric, errors="coerce")
    observed = values.notna().sum(axis=1)
    required = math.ceil(len(fields) * minimum_fraction)
    score = values.mean(axis=1, skipna=True).where(observed >= required)
    return pd.DataFrame({"score": score, "observed": observed, "total": len(fields), "complete": observed == len(fields)})


def weighted_smd(frame: pd.DataFrame, variable: str, group: str, one, zero, weight="pWEIGHT") -> float:
    part = frame[frame[group].isin([one, zero])][[variable, group, weight]].dropna()
    if part.empty or part[group].nunique() < 2:
        return float("nan")
    a, b = part[part[group] == one], part[part[group] == zero]
    ma, mb = weighted_mean(a[variable], a[weight]), weighted_mean(b[variable], b[weight])
    va = np.average((numeric(a[variable]) - ma) ** 2, weights=numeric(a[weight]))
    vb = np.average((numeric(b[variable]) - mb) ** 2, weights=numeric(b[weight]))
    denom = math.sqrt((va + vb) / 2)
    return 0 if denom == 0 else float((ma - mb) / denom)


def bootstrap_smd(frame: pd.DataFrame, variable: str, group: str, one, zero, cluster: str, seed: int) -> tuple[float | None, float | None]:
    part = frame[frame[group].isin([one, zero])][[variable, group, "pWEIGHT", cluster]].dropna()
    clusters = part[cluster].unique()
    if len(clusters) < 3:
        return None, None
    rng = np.random.default_rng(seed)
    grouped = {key: sub for key, sub in part.groupby(cluster)}
    values = []
    for _ in range(BOOTSTRAP_REPS):
        sample = pd.concat([grouped[key] for key in rng.choice(clusters, size=len(clusters), replace=True)], ignore_index=True)
        value = weighted_smd(sample, variable, group, one, zero)
        if np.isfinite(value):
            values.append(value)
    return (finite(np.quantile(values, .025)), finite(np.quantile(values, .975))) if len(values) >= 20 else (None, None)


def spearman_cell(frame: pd.DataFrame, x: str, y: str, cluster: str | None = None, seed: int = SEED) -> dict:
    columns = [x, y] + ([cluster] if cluster else [])
    part = frame[columns].copy()
    part[x], part[y] = numeric(part[x]), numeric(part[y])
    part = part.dropna(subset=[x, y])
    cluster_count = int(part[cluster].nunique()) if cluster else None
    too_small = len(part) < 8 or (cluster_count is not None and cluster_count < 8)
    if too_small or part[x].nunique() < 2 or part[y].nunique() < 2:
        reason = "fewer than 8 approved actors" if cluster_count is not None and cluster_count < 8 else "fewer than 8 complete observations or no variation"
        return {"value": None, "lower": None, "upper": None, "n": int(len(part)), "clusters": cluster_count, "suppressionReason": reason, "metric": "φ" if set(part[x].unique()).issubset({0, 1}) and set(part[y].unique()).issubset({0, 1}) else "ρ"}
    binary_pair = set(part[x].unique()).issubset({0, 1}) and set(part[y].unique()).issubset({0, 1})
    statistic = lambda sample: float(pearsonr(sample[x], sample[y]).statistic) if binary_pair else float(spearmanr(sample[x], sample[y]).statistic)
    rho = statistic(part)
    rng = np.random.default_rng(seed)
    boots = []
    if cluster:
        keys = part[cluster].dropna().unique()
        grouped = {key: sub for key, sub in part.groupby(cluster)}
        for _ in range(BOOTSTRAP_REPS):
            sample = pd.concat([grouped[key] for key in rng.choice(keys, size=len(keys), replace=True)], ignore_index=True)
            if sample[x].nunique() > 1 and sample[y].nunique() > 1:
                boots.append(statistic(sample))
    else:
        for _ in range(BOOTSTRAP_REPS):
            sample = part.iloc[rng.integers(0, len(part), len(part))]
            if sample[x].nunique() > 1 and sample[y].nunique() > 1:
                boots.append(statistic(sample))
    boots = [value for value in boots if np.isfinite(value)]
    return {"value": finite(rho), "lower": finite(np.quantile(boots, .025)) if boots else None, "upper": finite(np.quantile(boots, .975)) if boots else None, "n": int(len(part)), "clusters": cluster_count, "suppressionReason": None, "metric": "φ" if binary_pair else "ρ"}


def normalize_name(value) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def clean_actor_name(value) -> str:
    text = str(value or "").strip()
    if any(0x80 <= ord(character) <= 0x9F for character in text):
        try:
            text = text.encode("latin1").decode("cp1252")
        except UnicodeError:
            pass
    return " ".join(text.split())


def mode_numeric(values: pd.Series, mapping: dict[str, float]) -> float | None:
    coded = values.astype(str).str.lower().str.strip().map(mapping).dropna()
    return None if coded.empty else float(coded.mode().iloc[0])


def load_sources() -> dict[str, pd.DataFrame]:
    croad_dyad = read_input("croad_dyad").replace([np.inf, -np.inf], np.nan)
    croad_years = read_input("croad_years").replace([np.inf, -np.inf], np.nan)
    croad_replication = read_input("croad_replication").replace([np.inf, -np.inf], np.nan)
    m3 = read_input("m3")
    m3["com_mil_serv_gen"] = numeric(m3["com_mil_serv_gen"]).replace({-888: np.nan, 99: np.nan})
    return {
        "croad_dyad": croad_dyad,
        "croad_years": croad_years,
        "croad_replication": croad_replication,
        "hw": read_input("hw"),
        "bb": read_input("bb"),
        "bb_groups": read_input("bb_groups"),
        "raid": read_input("raid"),
        "raid_cs": read_input("raid_cs"),
        "raid_rep": read_input("raid_rep"),
        "rhrv": read_input("rhrv"),
        "rqsi": read_input("rqsi"),
        "rig": read_input("rig"),
        "nsa": read_input("nsa"),
        "esd_ay": read_input("esd_ay"),
        "esd_ty": read_input("esd_ty"),
        "dyadic": read_input("dyadic"),
        "actors": read_input("actors"),
        "ged": read_input("ged", usecols=["year", "side_b_new_id", "side_b", "gwnoa", "country", "type_of_violence", "best", "deaths_civilians"]),
        "gdis": read_input("gdis"),
        "m3": m3,
        "mlad": read_input("mlad"),
        "aq": read_input("aq"),
    }


def build_hw(hw: pd.DataFrame) -> dict:
    data = hw.copy()
    data["AGE"] = numeric(data["age2"]) * 10
    variables = {
        "MUD": "Mud-wall household", "EDUCATION": "Lack of education access",
        "NOPARTY": "No party support", "SLPP": "SLPP support", "Mende": "Mende identity",
        "pctvillaccessfootboat": "Village foot/boat access", "FARMER": "Farmer",
        "STUDENT": "Student", "gender": "Male", "AGE": "Age in 2003",
    }
    data["_faction"] = np.where(data["RUF2"] == 1, 1, np.where(data["CDF"] == 1, 0, np.nan))
    data["_form"] = np.where(data["M_RUF"] == 1, 1, np.where(data["M_RUF"] == 2, 0, np.nan))
    margins = [
        ("Entry", "EXCOM", 1, 0, "Ex-combatant − comparison sample"),
        ("Faction", "_faction", 1, 0, "RUF − CDF among major-faction fighters"),
        ("Recruitment form", "_form", 1, 0, "RUF abductee − RUF volunteer"),
    ]
    heat = []
    for vi, (variable, label) in enumerate(variables.items()):
        for mi, (margin, group, one, zero, contrast) in enumerate(margins):
            lower, upper = bootstrap_smd(data, variable, group, one, zero, "EXC_SURV_LOC", SEED + vi * 10 + mi)
            part = data[data[group].isin([one, zero])][[variable, group]].dropna()
            heat.append({"variable": label, "margin": margin, "contrast": contrast, "value": finite(weighted_smd(data, variable, group, one, zero)), "lower": lower, "upper": upper, "n": int(len(part))})
    groups = {"Comparison": data["EXCOM"] == 0, "RUF abductee": data["M_RUF"] == 1, "RUF volunteer": data["M_RUF"] == 2, "CDF": data["CDF"] == 1}
    profiles = []
    for name, mask in groups.items():
        for variable, label in variables.items():
            profiles.append({"group": name, "variable": label, **weighted_summary(data.loc[mask, variable], data.loc[mask, "pWEIGHT"], data.loc[mask, "EXC_SURV_LOC"], SEED + len(profiles))})
    motives = []
    for side, mask, fields in [
        ("RUF", data["RUF2"] == 1, {"Money offered": "RUFMONEY", "Safer inside": "RUFsafer", "Contact through friends": "RUFFRIENDS"}),
        ("CDF", data["CDF"] == 1, {"Money offered": "CDFMONEY", "Safer inside": "CDFsafer", "Contact through friends": "CDFFRIENDS"}),
    ]:
        for label, field in fields.items():
            motives.append({"group": side, "mechanism": label, **weighted_summary(data.loc[mask, field], data.loc[mask, "pWEIGHT"], data.loc[mask, "EXC_SURV_LOC"], SEED + 200 + len(motives))})
    grid = []
    for (mud, education), part in data.groupby(["MUD", "EDUCATION"], dropna=False):
        if pd.notna(mud) and pd.notna(education):
            grid.append({"mud": int(mud), "education": int(education), **weighted_summary(part["EXCOM"], part["pWEIGHT"], part["EXC_SURV_LOC"], SEED + 300 + len(grid))})
    missing = [{"variable": label, "missingRate": finite(data[variable].isna().mean()), "n": int(data[variable].notna().sum())} for variable, label in variables.items()]
    return {
        "sample": {"rows": 1227, "excombatants": int((data.EXCOM == 1).sum()), "comparison": int((data.EXCOM == 0).sum()), "rufAbductees": int((data.M_RUF == 1).sum()), "rufVolunteers": int((data.M_RUF == 2).sum()), "cdf": int((data.CDF == 1).sum())},
        "marginHeatmap": heat, "profiles": profiles, "motives": motives,
        "educationPoverty": grid, "missingness": missing,
    }


def age_summary(frame: pd.DataFrame, outcome: str, label: str, weight="i_weight") -> list[dict]:
    rows = []
    for age, part in frame.groupby("abd_age"):
        if 5 <= age <= 30:
            rows.append({"age": int(age), "outcome": label, **weighted_summary(part[outcome], part[weight])})
    values = {row["age"]: row for row in rows}
    for row in rows:
        near = [values[a] for a in range(row["age"] - 1, row["age"] + 2) if a in values and values[a]["value"] is not None]
        row["smooth"] = finite(np.average([x["value"] for x in near], weights=[max(x["n"], 1) for x in near])) if near else None
    return rows


def build_bb(bb: pd.DataFrame, groups: pd.DataFrame) -> dict:
    data = bb[(numeric(bb["abd"]) == 1) & (numeric(bb["found"]) == 1) & (numeric(bb["abd_age"]).between(5, 30))].copy()
    data["release_first_month"] = np.where(data["released"].notna() & data["abd_lgth"].notna(), ((numeric(data["released"]) == 1) & (numeric(data["abd_lgth"]) <= 1)).astype(float), np.nan)
    for source, target in [("gun_keep", "gun_keep_alt"), ("safer", "safer_alt"), ("loyal", "loyal_alt")]:
        data[target] = numeric(data[source])
    data.loc[numeric(data["phase2"]) == 1, "gun_keep_alt"] = np.nan
    outcomes = [
        ("release_first_month", "Released in first month"), ("abd_lgth", "Months abducted"),
        ("gun_mo", "Months before gun"), ("gun_keep_alt", "Allowed to keep gun"),
        ("safer_alt", "Felt safer inside LRA"), ("loyal_alt", "Felt loyalty to LRA"),
        ("indoctrinate", "Received indoctrination"), ("threats", "Received threats"),
    ]
    age_series = [row for field, label in outcomes for row in age_summary(data, field, label)]
    group_data = groups.copy()
    group_data["forced"] = np.where(numeric(group_data["recruitment"]) >= 1, 1, 0)
    group_data["childShare"] = numeric(group_data["childsoldier"]).map({0: .025, 1: .125, 2: .3, 3: .5, 4: .7})
    group_compare = []
    for forced, part in group_data.groupby("forced"):
        vals = part["childShare"].dropna()
        group_compare.append({"group": ">20% coerced" if forced else "<20% coerced", "value": finite(vals.mean()), "median": finite(vals.median()), "n": int(vals.size), "values": [finite(x) for x in vals]})
    missing = [{"variable": label, "missingRate": finite(data[field].isna().mean()), "n": int(data[field].notna().sum())} for field, label in outcomes]
    return {"sample": {"abductedInterviewees": int(len(data)), "rebelOrganizations": int(len(group_data))}, "ageSeries": age_series, "groupComparison": group_compare, "missingness": missing}


def build_catalog(s: dict[str, pd.DataFrame]) -> tuple[list[dict], dict]:
    m3 = s["m3"]
    cow_lookup = {int(code): str(name) for code, name in zip(m3["country_cown"], m3["countryname_standard"]) if pd.notna(code) and pd.notna(name)}
    observed: dict[str, dict] = {}
    mappings = [
        ("CROAD", s["croad_years"], "year", clean_places(s["croad_years"]["location"].unique())),
        ("RAID", s["raid"], "year", clean_places(cow_lookup.get(int(code)) for code in s["raid"]["ccode"].dropna().unique())),
        ("RHRV", s["rhrv"], "year", clean_places(s["rhrv"]["location"].unique())),
        ("UCDP-DYADIC", s["dyadic"], "year", clean_places(s["dyadic"]["location"].unique())),
        ("UCDP-GED", s["ged"], "year", clean_places(s["ged"]["country"].unique())),
        ("GDIS", s["gdis"], "year", clean_places(s["gdis"]["country"].unique())),
        ("RQSI", s["rqsi"], "Year", clean_places(s["rqsi"]["Location"].unique())),
        ("RIG", s["rig"], "year", clean_places(s["rig"]["Location"].unique())),
        ("M3", m3, "year", clean_places(m3["countryname_standard"].unique())),
        ("MLAD", s["mlad"], "year", clean_places(cow_lookup.get(int(code)) for code in s["mlad"]["ccode"].dropna().unique())),
    ]
    for key, frame, year_col, countries in mappings:
        start, end = years(frame[year_col])
        observed[key] = {"actualRows": int(len(frame)), "observedStart": start, "observedEnd": end, "countries": countries}
    observed["UCDP-ACTOR"] = {"actualRows": int(len(s["actors"])), "countries": clean_places(s["actors"]["Location"].dropna().unique())}
    start, end = years(s["esd_ty"]["year"])
    observed["UCDP-ESD"] = {"actualRows": int(len(s["esd_ty"])), "observedStart": start, "observedEnd": end, "countries": clean_ucdp_conflict_locations(s["esd_ty"]["location"].unique())}
    observed["HW2008"] = {"actualRows": 1227, "observedStart": 2003, "observedEnd": 2003, "countries": ["Sierra Leone"]}
    observed["BB2013"] = {"actualRows": 1293, "countries": ["Colombia", "Liberia", "Sierra Leone", "Uganda"]}
    observed["AQ-BRITISH"] = {"actualRows": int(len(s["aq"])), "observedStart": 1936, "observedEnd": 1939, "countries": ["Spain", "United Kingdom"]}
    nsa_start, _ = date_years(s["nsa"]["startdate"]); _, nsa_end = date_years(s["nsa"]["enddate"])
    observed["NSA"] = {"actualRows": int(len(s["nsa"])), "observedStart": nsa_start, "observedEnd": nsa_end, "countries": clean_places(s["nsa"]["side_a"].unique())}

    with (ROOT / "dataset" / "file-manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    files_by_dataset: dict[str, list[dict]] = defaultdict(list)
    for row in manifest:
        files_by_dataset[row["dataset_id"]].append(row)
    datasets = json.loads((ROOT / "content" / "datasets.json").read_text(encoding="utf-8"))
    catalog = []
    for dataset in datasets:
        item = dict(dataset); item.update(META[dataset["id"]]); item.update(observed.get(dataset["id"], {}))
        files = files_by_dataset.get(dataset["id"], [])
        item["fileCount"] = len(files); item["fileBytes"] = sum(int(row["bytes"]) for row in files); item["countryCount"] = len(item.get("countries", []))
        if "timelineStart" not in item and item.get("observedStart") is not None:
            item.update({"timelineStart": item["observedStart"], "timelineEnd": item["observedEnd"], "timelineBasis": "observed local rows"})
        item["isLocalData"] = dataset["id"] in LOCAL_DATA_IDS
        catalog.append(item)
    dated = [item for item in catalog if item.get("timelineStart") is not None]
    summary = {
        "catalogRecords": len(catalog), "localData": sum(x["accessClass"] == "local-data" for x in catalog),
        "documentation": sum(x["accessClass"] == "documentation" for x in catalog), "blocked": sum(x["accessClass"] == "blocked" for x in catalog),
        "gaps": sum(x["accessClass"] == "gap" for x in catalog), "principalFiles": len(manifest),
        "principalBytes": sum(int(row["bytes"]) for row in manifest), "earliest": min(x["timelineStart"] for x in dated), "latest": max(x["timelineEnd"] for x in dated),
    }
    return catalog, summary


def build_crosswalk(s: dict[str, pd.DataFrame]) -> tuple[list[dict], set[int], set[int]]:
    actors = s["actors"].copy(); actors["ActorId"] = numeric(actors["ActorId"]).astype("Int64")
    canonical = {int(row.ActorId): clean_actor_name(row.NameData) for row in actors[["ActorId", "NameData"]].dropna(subset=["ActorId"]).itertuples()}
    source_specs = [
        ("CROAD", "v1.2025", "UCDP actor ID v22.1", s["croad_dyad"], "side_b_id", "side_b"),
        ("RAID", "author-release-2023", "UCDP/NSA-derived actor ID version undocumented", s["raid"], "new_side_b_id", "groupname_nsa"),
        ("RHRV", "Dataverse-v3.0", "older UCDP actor ID version undocumented", s["rhrv"], "sidebid", "sidebname"),
        ("RQSI", "JPR-release-2022", "UCDP actor ID version undocumented", s["rqsi"], "actorid", "SideB.x"),
        ("RIG", "author-release", "UCDP actor ID version undocumented", s["rig"], "actorid", "groupname"),
        ("ESD", "v18.1", "UCDP actor ID v18.1", s["esd_ay"][numeric(s["esd_ay"]["actor_nonstate"]) == 1], "actor_id", "actor_name"),
    ]
    names: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    candidate_records = []
    for source, release, namespace, frame, id_col, name_col in source_specs:
        for actor_id, name in frame[[id_col, name_col]].dropna(subset=[id_col]).drop_duplicates().itertuples(index=False):
            actor_id = int(actor_id)
            cleaned = clean_actor_name(name) if pd.notna(name) else ""
            if cleaned:
                names[actor_id][source].add(cleaned)
            else:
                names[actor_id][source]
            candidate_records.append({"source_dataset": source, "source_release": release, "source_namespace": namespace, "source_actor_id": actor_id, "source_actor_name": cleaned, "target_release": "UCDP v26.1", "target_actor_id": actor_id if actor_id in canonical else "", "target_actor_name": canonical.get(actor_id, ""), "match_method": "exact integer in versioned/declared namespace", "mapping_status": "candidate" if actor_id in canonical else "unresolved-target"})

    with (ROOT / "dataset" / "crosswalks" / "actor-review-decisions.csv").open(newline="", encoding="utf-8") as handle:
        decisions = {int(row["actor_id"]): row for row in csv.DictReader(handle)}
    rows, descriptive_candidates, approved = [], set(), set()
    for actor_id in sorted(names):
        source_names = names[actor_id]
        aliases = sorted({name for values in source_names.values() for name in values})
        decision = decisions.get(actor_id)
        canon = (decision or {}).get("canonical_name") or canonical.get(actor_id) or (aliases[0] if aliases else f"Actor {actor_id}")
        if decision:
            status = decision["decision"]
        elif actor_id in canonical and len(source_names) >= 2:
            status = "exact-id candidate"
        elif len(source_names) >= 2:
            status = "unresolved"
        else:
            status = "single-source candidate"
        eligible = actor_id in canonical and len(source_names) >= 2 and status != "rejected"
        if eligible:
            descriptive_candidates.add(actor_id)
        if status == "approved":
            approved.add(actor_id)
        rows.append({"actorId": actor_id, "canonicalName": canon, "status": status, "descriptiveEligible": eligible, "downstreamEligible": actor_id in approved, "sources": sorted(source_names), "aliases": aliases, "targetRelease": "UCDP v26.1", "targetActorId": actor_id if actor_id in canonical else None, "reviewer": decision.get("reviewer") if decision else None, "reviewDate": decision.get("review_date") if decision else None, "rationale": decision.get("rationale") if decision else "Exact integer overlap is a candidate only; no human approval recorded."})
    CROSSWALK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with CROSSWALK_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        fields = ["source_dataset", "source_release", "source_namespace", "source_actor_id", "source_actor_name", "target_release", "target_actor_id", "target_actor_name", "match_method", "mapping_status"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(candidate_records)
    return rows, descriptive_candidates, approved


def build_crosswalk_audit(s: dict[str, pd.DataFrame]) -> dict:
    """Explicit overlap baselines; no name-only or fuzzy matches are admitted."""
    croad_actor = set(numeric(s["croad_dyad"]["side_b_id"]).dropna().astype(int))
    raid_actor = set(numeric(s["raid_cs"]["new_side_b_id"]).dropna().astype(int))
    rhrv_actor = set(numeric(s["rhrv"]["sidebid"]).dropna().astype(int))
    esd_actor = set(numeric(s["esd_ay"].loc[numeric(s["esd_ay"]["actor_nonstate"]) == 1, "actor_id"]).dropna().astype(int))
    rqsi_actor = set(numeric(s["rqsi"]["actorid"]).dropna().astype(int))
    rig_actor = set(numeric(s["rig"]["actorid"]).dropna().astype(int))
    raid_dyads = set(numeric(s["raid"]["dyadid"]).dropna().astype(int))
    nsa_dyads = set(numeric(s["nsa"]["dyadid"]).dropna().astype(int))
    rhrv_years = set(zip(numeric(s["rhrv"]["sidebid"]).dropna().astype(int), numeric(s["rhrv"].loc[numeric(s["rhrv"]["sidebid"]).notna(), "year"]).dropna().astype(int)))
    esd_years = set(zip(numeric(s["esd_ay"]["actor_id"]).dropna().astype(int), numeric(s["esd_ay"].loc[numeric(s["esd_ay"]["actor_id"]).notna(), "year"]).dropna().astype(int)))
    return {
        "method": "Versioned numeric-ID equality generates descriptive candidates only; approval requires a tracked review decision. Aliases never create silent joins.",
        "croadRaidActors": len(croad_actor & raid_actor),
        "croadRhrvActors": len(croad_actor & rhrv_actor),
        "raidNsaDyads": len(raid_dyads & nsa_dyads),
        "raidRhrvActors": len(raid_actor & rhrv_actor),
        "raidEsdActors": len(raid_actor & esd_actor),
        "rqsiRigActors": len(rqsi_actor & rig_actor),
        "rhrvEsdActorYears": len(rhrv_years & esd_years),
    }


def prepare_organization_rows(s: dict[str, pd.DataFrame], approved: set[int]) -> dict:
    raid = s["raid_cs"].copy(); raid["actorId"] = numeric(raid["new_side_b_id"])
    raid = raid[raid["actorId"].isin(approved)]
    raid["appealBreadth"] = appeal_count(raid)
    croad = s["croad_dyad"].copy(); croad["actorId"] = numeric(croad["side_b_id"])
    croad = croad.groupby("actorId", as_index=False).agg(croadCoercive=("coercive_recruit", "max"), croadForced=("forced_recruit", "max"), croadInvoluntary=("involuntary_recruit", "max"), croadConscription=("conscription", "max"))
    raid = raid.merge(croad, on="actorId", how="left")
    rep = s["raid_rep"][["new_actor_id", "reb_strength_ord", "group_name"]].rename(columns={"new_actor_id": "actorId", "reb_strength_ord": "rebelStrength", "group_name": "groupName"})
    raid = raid.merge(rep, on="actorId", how="left")

    raid_dyads = s["raid"][["new_side_b_id", "dyadid"]].drop_duplicates().rename(columns={"new_side_b_id": "actorId"})
    nsa = s["nsa"].copy(); nsa["dyadid"] = numeric(nsa["dyadid"])
    cap_rows = []
    strength_map = {"much weaker": 1, "weaker": 2, "parity": 3, "stronger": 4, "much stronger": 5}; ordinal = {"low": 1, "moderate": 2, "high": 3}; yesno = {"no": 0, "yes": 1}
    for actor_id, dyad_id in raid_dyads.itertuples(index=False):
        part = nsa[nsa["dyadid"] == dyad_id]
        cap_rows.append({"actorId": int(actor_id), "nsaEpisodes": int(len(part)), "nsaStrength": mode_numeric(part["rebstrength"], strength_map), "mobilization": mode_numeric(part["mobcap"], ordinal), "fightingCapacity": mode_numeric(part["fightcap"], ordinal), "territorialControl": finite(part["terrcont"].astype(str).str.lower().map(yesno).max()), "centralControl": finite(part["centcontrol"].astype(str).str.lower().map(yesno).max())})
    raid = raid.merge(pd.DataFrame(cap_rows), on="actorId", how="left")
    esd = s["esd_ay"].copy(); esd["actorId"] = numeric(esd["actor_id"])
    esd_agg = esd.groupby("actorId").agg(externalSupport=("ext_sup", "mean"), supportDiversity=("ext_sum", "mean"), funding=("ext_f", "mean"), weapons=("ext_w", "mean"), training=("ext_t", "mean")).reset_index()
    raid = raid.merge(esd_agg, on="actorId", how="left")
    rqsi = s["rqsi"].copy(); rqsi["actorId"] = numeric(rqsi["actorid"])
    rqsi_score = battery_score(rqsi, RQSI_POL + RQSI_ECON + RQSI_SOC + RQSI_GOV)
    rqsi["governanceItemShare"], rqsi["governanceObserved"] = rqsi_score["score"], rqsi_score["observed"]
    raid = raid.merge(rqsi.groupby("actorId")[["governanceItemShare", "governanceObserved"]].mean().reset_index(), on="actorId", how="left")
    rig = s["rig"].copy(); rig["actorId"] = numeric(rig["actorid"])
    rig_score = battery_score(rig, RIG_CORE)
    rig["disciplineItemShare"], rig["disciplineObserved"] = rig_score["score"], rig_score["observed"]
    raid = raid.merge(rig.groupby("actorId")[["disciplineItemShare", "disciplineObserved"]].mean().reset_index(), on="actorId", how="left")
    outcomes = {"croadCoercive": "CROAD · adult coercion", "croadForced": "CROAD · forced recruitment", "croadConscription": "CROAD · conscription", "forced_recruit": "RAID · forced recruitment", "appealBreadth": "Appeal breadth", "ethnic_nat_appeals": "Ethnic-nationalist appeal", "gov_grievance_appeals": "Government-grievance appeal"}
    conditions = {"rebelStrength": "Rebel strength", "mobilization": "Mobilization capacity", "territorialControl": "Territorial control", "supportDiversity": "External-support diversity", "funding": "Funding support", "weapons": "Weapons support", "governanceItemShare": "Governance item share (≥80% observed)", "disciplineItemShare": "Discipline item share (≥80% observed)"}
    matrix = [{"outcome": ol, "outcomeKey": o, "condition": cl, "conditionKey": c, **spearman_cell(raid, o, c, seed=SEED + oi * 20 + ci)} for oi, (o, ol) in enumerate(outcomes.items()) for ci, (c, cl) in enumerate(conditions.items())]
    keep = ["actorId"] + list(outcomes) + list(conditions)
    rows = [{key: finite(value) if key != "actorId" else int(value) for key, value in row.items()} for row in raid[keep].dropna(subset=["actorId"]).to_dict("records")]
    return {"matrix": matrix, "rows": rows, "outcomes": outcomes, "conditions": conditions}


def prepare_actor_year_rows(s: dict[str, pd.DataFrame], approved: set[int]) -> dict:
    r = s["rhrv"].copy(); r["actorId"] = numeric(r["sidebid"]); r["year"] = numeric(r["year"])
    r = r[r["actorId"].isin(approved)]
    r = r.groupby(["actorId", "year"], as_index=False).agg(recruitmentState=("rrecruitment_s", "max"), recruitmentAmnesty=("rrecruitment_a", "max"), gwno=("gwnoa", "first"))
    croad = s["croad_years"].copy(); croad["actorId"] = numeric(croad["side_b_id"]); croad["year"] = numeric(croad["year"])
    croad = croad[croad["actorId"].isin(approved)]
    croad = croad.groupby(["actorId", "year"], as_index=False).agg(croadCoercive=("coercive_recruit", "max"), croadForced=("forced_recruit", "max"), croadConscription=("conscription", "max"))
    e = s["esd_ay"].copy(); e["actorId"] = numeric(e["actor_id"]); e["year"] = numeric(e["year"])
    e = e[e["actorId"].isin(approved)]
    e = e.groupby(["actorId", "year"], as_index=False).agg(supportDiversity=("ext_sum", "mean"), funding=("ext_f", "max"), weapons=("ext_w", "max"), training=("ext_t", "max"))
    q = s["rqsi"].copy(); q["actorId"] = numeric(q["actorid"]); q["year"] = numeric(q["Year"])
    q = q[q["actorId"].isin(approved)]
    q_score = battery_score(q, RQSI_POL + RQSI_ECON + RQSI_SOC + RQSI_GOV)
    q["governanceItemShare"] = q_score["score"]
    q = q.groupby(["actorId", "year"], as_index=False)["governanceItemShare"].mean()
    g = s["rig"].copy(); g["actorId"] = numeric(g["actorid"]); g["year"] = numeric(g["year"])
    g = g[g["actorId"].isin(approved)]
    g_score = battery_score(g, RIG_CORE)
    g["disciplineItemShare"] = g_score["score"]
    g = g.groupby(["actorId", "year"], as_index=False)["disciplineItemShare"].mean()
    ged = s["ged"].copy(); ged["actorId"] = numeric(ged["side_b_new_id"]); ged["year"] = numeric(ged["year"])
    ged = ged[ged["actorId"].isin(approved)]
    ged = ged.groupby(["actorId", "year"], as_index=False).agg(events=("best", "size"), fatalities=("best", "sum"), civilianFatalities=("deaths_civilians", "sum"))
    m3 = s["m3"][["country_cown", "year", "com_mil_serv"]].rename(columns={"country_cown": "gwno", "com_mil_serv": "stateConscription"})
    frame = r.merge(croad, on=["actorId", "year"], how="outer").merge(e, on=["actorId", "year"], how="left").merge(q, on=["actorId", "year"], how="left").merge(g, on=["actorId", "year"], how="left").merge(ged, on=["actorId", "year"], how="left").merge(m3, on=["gwno", "year"], how="left")
    frame["logFatalities"] = np.log1p(numeric(frame["fatalities"]))
    outcomes = {"recruitmentState": "Recruitment report · State", "recruitmentAmnesty": "Recruitment report · Amnesty", "croadCoercive": "CROAD · adult coercion", "croadForced": "CROAD · forced recruitment", "croadConscription": "CROAD · conscription"}
    conditions = {"supportDiversity": "External-support diversity", "funding": "Funding support", "weapons": "Weapons support", "governanceItemShare": "Governance item share (≥80% observed)", "disciplineItemShare": "Discipline item share (≥80% observed)", "logFatalities": "Conflict fatalities · log", "stateConscription": "State conscription"}
    matrix = [{"outcome": ol, "outcomeKey": o, "condition": cl, "conditionKey": c, **spearman_cell(frame, o, c, cluster="actorId", seed=SEED + 100 + oi * 20 + ci)} for oi, (o, ol) in enumerate(outcomes.items()) for ci, (c, cl) in enumerate(conditions.items())]
    keep = ["actorId", "year"] + list(outcomes) + list(conditions)
    rows = [{key: (int(value) if key in {"actorId", "year"} and pd.notna(value) else finite(value)) for key, value in row.items()} for row in frame[keep].dropna(subset=["actorId", "year"]).to_dict("records")]
    return {"matrix": matrix, "rows": rows, "outcomes": outcomes, "conditions": conditions}


def build_croad(s: dict[str, pd.DataFrame], approved: set[int]) -> dict:
    """Aggregate CROAD without exposing locations or coder notes to the browser."""
    dyad = s["croad_dyad"].copy()
    annual = s["croad_years"].copy()
    fields = [("coercive_recruit", "Any adult coercion"), ("forced_recruit", "Forced recruitment"), ("involuntary_recruit", "Involuntary recruitment"), ("conscription", "Conscription")]
    distribution = []
    for field, label in fields:
        values = numeric(dyad[field]).dropna()
        distribution.append({"measure": label, "share": finite(values.mean()), "positive": int((values == 1).sum()), "n": int(len(values))})
    annual_rows = []
    for year, part in annual.groupby("year"):
        for field, label in fields:
            if field not in part:
                continue
            values = numeric(part[field]).dropna()
            annual_rows.append({"year": int(year), "measure": label, "share": finite(values.mean()) if len(values) else None, "positive": int((values == 1).sum()), "n": int(len(values))})
    onsets = numeric(dyad["onset_recruit_year"]).dropna().astype(int).value_counts().sort_index()
    pledges = numeric(dyad["pledge"]).dropna().astype(int).value_counts().sort_index()
    confidence = numeric(dyad["certainty_source_croad"]).dropna().astype(int).value_counts().sort_index()
    dyad_rows = dyad[["side_b_id", "dyadid_ucdp22", "coercive_recruit", "forced_recruit", "involuntary_recruit", "conscription", "onset_recruit_year", "pledge", "pledge_year", "coercive_stop", "certainty_source_croad"]].copy()
    dyad_rows["actorId"] = numeric(dyad_rows["side_b_id"])
    actor_status = dyad_rows.groupby("actorId", as_index=False).agg(croadCoercive=("coercive_recruit", "max"), croadForced=("forced_recruit", "max"), croadConscription=("conscription", "max"))
    approved_actor_status = actor_status[actor_status["actorId"].isin(approved)]
    raid = s["raid_cs"][["new_side_b_id", "forced_recruit"]].rename(columns={"new_side_b_id": "actorId", "forced_recruit": "raidForced"})
    raid["actorId"] = numeric(raid["actorId"])
    raid_bridge = approved_actor_status.merge(raid, on="actorId", how="inner")
    rhrv = s["rhrv"].copy(); rhrv["actorId"] = numeric(rhrv["sidebid"])
    rhrv = rhrv.groupby("actorId", as_index=False).agg(stateReported=("rrecruitment_s", lambda x: finite((numeric(x).dropna() > 0).mean()) if numeric(x).notna().any() else None), amnestyReported=("rrecruitment_a", lambda x: finite((numeric(x).dropna() > 0).mean()) if numeric(x).notna().any() else None), rhrvYears=("year", "nunique"))
    rhrv_bridge = approved_actor_status.merge(rhrv, on="actorId", how="inner")
    return {
        "sample": {"dyads": int(dyad["dyadid_ucdp22"].nunique()), "actors": int(dyad["side_b_id"].nunique()), "dyadYears": int(len(annual)), "missingDyads": int(numeric(dyad["coercive_recruit"]).isna().sum()), "switchingDyads": int((annual.groupby("dyadid_ucdp22")["coercive_recruit"].apply(lambda x: numeric(x).dropna().nunique()) > 1).sum())},
        "distribution": distribution,
        "annual": annual_rows,
        "onsets": [{"year": int(year), "n": int(n)} for year, n in onsets.items()],
        "pledges": [{"code": int(code), "n": int(n)} for code, n in pledges.items()],
        "certainty": [{"code": int(code), "n": int(n)} for code, n in confidence.items()],
        "actorRows": [{key: (int(value) if key in {"actorId", "dyadid_ucdp22"} and pd.notna(value) else finite(value)) for key, value in row.items()} for row in dyad_rows.dropna(subset=["actorId"]).to_dict("records")],
        "raidBridge": [{key: (int(value) if key == "actorId" else finite(value)) for key, value in row.items()} for row in raid_bridge.to_dict("records")],
        "rhrvBridge": [{key: (int(value) if key in {"actorId", "rhrvYears"} else finite(value)) for key, value in row.items()} for row in rhrv_bridge.to_dict("records")],
    }


def build_repertoire(s: dict[str, pd.DataFrame], approved: set[int]) -> dict:
    raid = s["raid_cs"].copy()
    appeal_rows = []
    for field, label in APPEALS.items():
        all_values = numeric(raid[field])
        forced = numeric(raid.loc[numeric(raid["forced_recruit"]) == 1, field]).dropna()
        not_forced = numeric(raid.loc[numeric(raid["forced_recruit"]) == 0, field]).dropna()
        diff = forced.mean() - not_forced.mean()
        se = math.sqrt((forced.mean() * (1 - forced.mean()) / max(len(forced), 1)) + (not_forced.mean() * (1 - not_forced.mean()) / max(len(not_forced), 1)))
        appeal_rows.append({"appeal": label, "prevalence": finite(all_values.mean()), "forced": finite(forced.mean()), "notForced": finite(not_forced.mean()), "difference": finite(diff), "lower": finite(diff - 1.96 * se), "upper": finite(diff + 1.96 * se), "n": int(all_values.notna().sum())})
    rhrv = s["rhrv"].copy()
    annual = []
    for year, part in rhrv.groupby("year"):
        for source, field in [("State", "rrecruitment_s"), ("Amnesty", "rrecruitment_a")]:
            values = numeric(part[field]).dropna()
            annual.append({"year": int(year), "source": source, "reportedShare": finite((values > 0).mean()), "frequentShare": finite((values >= 2).mean()), "n": int(len(values)), "missingRate": finite(part[field].isna().mean())})
    agreement = []
    for (state, amnesty), part in rhrv.groupby(["rrecruitment_s", "rrecruitment_a"], dropna=False):
        agreement.append({"state": None if pd.isna(state) else int(state), "amnesty": None if pd.isna(amnesty) else int(amnesty), "n": int(len(part))})
    cooccurrence = []
    for source, suffix in [("State", "s"), ("Amnesty", "a")]:
        for root, label in RHRV_VIOLATIONS.items():
            cooccurrence.append({"source": source, "violation": label, **spearman_cell(rhrv, f"rrecruitment_{suffix}", f"{root}_{suffix}", cluster="sidebid", seed=SEED + len(cooccurrence))})
    raid_actor = raid[["new_side_b_id", "forced_recruit"]].rename(columns={"new_side_b_id": "actorId"})
    raid_actor = raid_actor[numeric(raid_actor["actorId"]).isin(approved)]
    rr = rhrv.copy(); rr["actorId"] = numeric(rr["sidebid"])
    bridge_rows = []
    for actor_id, part in rr.groupby("actorId"):
        raid_match = raid_actor[numeric(raid_actor["actorId"]) == actor_id]
        if pd.isna(actor_id) or raid_match.empty:
            continue
        row = {"actorId": int(actor_id), "raidForced": int(raid_match.iloc[0]["forced_recruit"])}
        for label, field in [("State", "rrecruitment_s"), ("Amnesty", "rrecruitment_a")]:
            values = numeric(part[field]).dropna(); key = label.lower()
            row[f"{key}ReportedShare"] = finite((values > 0).mean()) if len(values) else None
            row[f"{key}Max"] = int(values.max()) if len(values) else None; row[f"{key}N"] = int(len(values))
        bridge_rows.append(row)
    return {"appeals": appeal_rows, "rhrvAnnual": annual, "sourceAgreement": agreement, "violationCooccurrence": cooccurrence, "measurementBridge": bridge_rows}


def track_records(frame: pd.DataFrame, actor: str, year: str, value_build: Callable[[pd.Series], dict]) -> dict[int, list[dict]]:
    output: dict[int, list[dict]] = defaultdict(list)
    for (actor_id, yr), part in frame.groupby([actor, year]):
        if pd.notna(actor_id) and pd.notna(yr):
            output[int(actor_id)].append({"year": int(yr), **value_build(part.iloc[0] if len(part) == 1 else part)})
    return output


def build_profiles(s: dict[str, pd.DataFrame], crosswalk: list[dict], approved: set[int]) -> list[dict]:
    names = {row["actorId"]: row["canonicalName"] for row in crosswalk}
    raid = s["raid_cs"].copy(); raid["actorId"] = numeric(raid["new_side_b_id"]); raid["appealBreadth"] = appeal_count(raid)
    raid_map = {}
    for row in raid.itertuples():
        aid = int(row.actorId)
        raid_map[aid] = {"forcedRecruit": finite(row.forced_recruit), "appealBreadth": finite(row.appealBreadth), "appeals": [label for field, label in APPEALS.items() if getattr(row, field) == 1], "start": int(row.start_year) if pd.notna(row.start_year) else None, "end": int(row.end_year) if pd.notna(row.end_year) else None}
    croad = s["croad_dyad"].copy(); croad["actorId"] = numeric(croad["side_b_id"])
    croad_map = {}
    for actor_id, part in croad.groupby("actorId"):
        if pd.isna(actor_id):
            continue
        croad_map[int(actor_id)] = {"coercive": finite(numeric(part["coercive_recruit"]).max()), "forced": finite(numeric(part["forced_recruit"]).max()), "involuntary": finite(numeric(part["involuntary_recruit"]).max()), "conscription": finite(numeric(part["conscription"]).max()), "onset": finite(numeric(part["onset_recruit_year"]).min(), 0), "pledges": int((numeric(part["pledge"]) > 0).sum())}

    r = s["rhrv"].copy(); r["actorId"] = numeric(r["sidebid"]); r["year"] = numeric(r["year"])
    r = r.groupby(["actorId", "year"], as_index=False).agg(state=("rrecruitment_s", "max"), amnesty=("rrecruitment_a", "max"), gwno=("gwnoa", "first"))
    r_tracks = track_records(r, "actorId", "year", lambda row: {"state": finite(row["state"]), "amnesty": finite(row["amnesty"]), "gwno": finite(row["gwno"], 0)})
    e = s["esd_ay"].copy(); e["actorId"] = numeric(e["actor_id"]); e["year"] = numeric(e["year"])
    e = e.groupby(["actorId", "year"], as_index=False).agg(supporters=("ext_count", "max"), diversity=("ext_sum", "mean"), funding=("ext_f", "max"), weapons=("ext_w", "max"), training=("ext_t", "max"), gwno=("gwno_a", "first"))
    e_tracks = track_records(e, "actorId", "year", lambda row: {key: finite(row[key]) for key in ["supporters", "diversity", "funding", "weapons", "training", "gwno"]})
    q = s["rqsi"].copy(); q["actorId"] = numeric(q["actorid"]); q["year"] = numeric(q["Year"])
    for label, fields in [("political", RQSI_POL), ("economic", RQSI_ECON), ("social", RQSI_SOC), ("government", RQSI_GOV)]:
        score = battery_score(q, fields)
        q[label], q[f"{label}Observed"] = score["score"], score["observed"]
    overall = battery_score(q, RQSI_POL + RQSI_ECON + RQSI_SOC + RQSI_GOV)
    q["overall"], q["overallObserved"] = overall["score"], overall["observed"]
    q_fields = ["political", "economic", "social", "government", "overall", "overallObserved"]
    q = q.groupby(["actorId", "year"], as_index=False)[q_fields].mean()
    q_tracks = track_records(q, "actorId", "year", lambda row: {key: finite(row[key]) for key in q_fields})
    g = s["rig"].copy(); g["actorId"] = numeric(g["actorid"]); g["year"] = numeric(g["year"])
    discipline = battery_score(g, RIG_CORE)
    g["itemShare"], g["observedItems"] = discipline["score"], discipline["observed"]
    g = g.groupby(["actorId", "year"], as_index=False).agg(itemShare=("itemShare", "mean"), observedItems=("observedItems", "mean"), code=("codeconduct", "max"), tribunal=("tribunalproceedings", "max"), deathPenalty=("deathpenalty", "max"), incarceration=("incarceration", "max"))
    g_tracks = track_records(g, "actorId", "year", lambda row: {key: finite(row[key]) for key in ["itemShare", "observedItems", "code", "tribunal", "deathPenalty", "incarceration"]})
    ged = s["ged"].copy(); ged["actorId"] = numeric(ged["side_b_new_id"]); ged["year"] = numeric(ged["year"])
    ged = ged.groupby(["actorId", "year"], as_index=False).agg(events=("best", "size"), fatalities=("best", "sum"), civilian=("deaths_civilians", "sum"))
    ged_tracks = track_records(ged, "actorId", "year", lambda row: {key: finite(row[key]) for key in ["events", "fatalities", "civilian"]})

    m3_lookup = {(int(row.country_cown), int(row.year)): row for row in s["m3"].dropna(subset=["country_cown", "year"]).itertuples()}
    disasters = s["gdis"].groupby(["gwno", "year"]).agg(disasters=("disasterno", "nunique"), types=("disastertype", lambda x: sorted(set(map(str, x.dropna()))))).reset_index()
    disaster_lookup = {(int(row.gwno), int(row.year)): {"disasters": int(row.disasters), "types": row.types} for row in disasters.dropna(subset=["gwno", "year"]).itertuples()}
    profiles = []
    for aid in sorted(approved):
        tracks = {"recruitment": r_tracks.get(aid, []), "support": e_tracks.get(aid, []), "governance": q_tracks.get(aid, []), "discipline": g_tracks.get(aid, []), "violence": ged_tracks.get(aid, [])}
        host_year = {}
        for row in tracks["support"] + tracks["recruitment"]:
            if row.get("gwno") is not None:
                host_year[row["year"]] = int(row["gwno"])
        context = []
        for yr, gwno in sorted(host_year.items()):
            m = m3_lookup.get((gwno, yr)); d = disaster_lookup.get((gwno, yr))
            context.append({"year": yr, "stateConscription": finite(m.com_mil_serv) if m is not None else None, "serviceMin": finite(m.com_mil_serv_dur_min) if m is not None else None, "disasters": d["disasters"] if d is not None else None, "types": d["types"] if d is not None else []})
        year_set = {row["year"] for values in tracks.values() for row in values} | {row["year"] for row in context}
        coverage = [key for key, values in tracks.items() if values] + (["RAID"] if aid in raid_map else []) + (["CROAD"] if aid in croad_map else [])
        profiles.append({"actorId": aid, "name": names.get(aid, f"Actor {aid}"), "start": min(year_set) if year_set else None, "end": max(year_set) if year_set else None, "sourceCoverage": coverage, "raid": raid_map.get(aid), "croad": croad_map.get(aid), "tracks": tracks, "context": context})
    return profiles


def build_network(esd: pd.DataFrame, approved: set[int]) -> dict:
    frame = esd[(numeric(esd["actor_nonstate"]) == 1) & (numeric(esd["ext_sup"]) == 1)].copy()
    frame["recipientId"] = numeric(frame["actor_id"]); frame["supporterId"] = numeric(frame["ext_id"]); frame["year"] = numeric(frame["year"])
    frame = frame[frame["recipientId"].isin(approved)]
    edges = []
    group_cols = ["supporterId", "ext_name", "ext_nonstate", "recipientId", "actor_name", "year"]
    for keys, part in frame.groupby(group_cols, dropna=False):
        supporter_id, supporter, supporter_nonstate, recipient_id, recipient, year = keys
        types = [label for field, label in ESD_TYPES.items() if numeric(part[field]).max() == 1]
        edges.append({"supporterId": int(supporter_id), "supporter": str(supporter), "supporterNonstate": bool(supporter_nonstate == 1), "recipientId": int(recipient_id), "recipient": str(recipient), "year": int(year), "types": types, "alleged": bool(numeric(part["ext_alleged"]).max() == 1)})
    counts = Counter(label for row in edges for label in row["types"])
    return {"yearEdges": edges, "typeCounts": [{"type": key, "n": value} for key, value in counts.most_common()]}


def build_context(s: dict[str, pd.DataFrame]) -> dict:
    r = s["rhrv"].copy(); r["gwno"] = numeric(r["gwnoa"]); r["year"] = numeric(r["year"])
    r_rows = []
    for (gwno, year), part in r.groupby(["gwno", "year"]):
        st, am = numeric(part["rrecruitment_s"]).dropna(), numeric(part["rrecruitment_a"]).dropna()
        r_rows.append({"gwno": int(gwno), "year": int(year), "activeDyads": int(len(part)), "stateReportedShare": finite((st > 0).mean()) if len(st) else None, "amnestyReportedShare": finite((am > 0).mean()) if len(am) else None})
    base = pd.DataFrame(r_rows)
    ged = s["ged"].copy(); ged["gwno"] = numeric(ged["gwnoa"]); ged["year"] = numeric(ged["year"])
    ged = ged.groupby(["gwno", "year"], as_index=False).agg(events=("best", "size"), fatalities=("best", "sum"), civilianFatalities=("deaths_civilians", "sum"))
    gdis = s["gdis"].groupby(["gwno", "year"], as_index=False).agg(disasters=("disasterno", "nunique"), disasterLocations=("geo_id", "nunique"), disasterTypes=("disastertype", lambda x: "|".join(sorted(set(map(str, x.dropna()))))))
    m3 = s["m3"][["country_cown", "countryname_standard", "country_iso3c", "year", "com_mil_serv", "com_mil_serv_dur_min", "com_mil_serv_dur_max"]].rename(columns={"country_cown": "gwno", "countryname_standard": "country", "country_iso3c": "iso3", "com_mil_serv": "stateConscription", "com_mil_serv_dur_min": "serviceMin", "com_mil_serv_dur_max": "serviceMax"})
    merged = base.merge(ged, on=["gwno", "year"], how="left").merge(gdis, on=["gwno", "year"], how="left").merge(m3, on=["gwno", "year"], how="left")
    rows = []
    integer_keys = {"gwno", "year", "activeDyads", "events", "fatalities", "civilianFatalities", "disasters", "disasterLocations"}
    for row in merged.to_dict("records"):
        clean = {}
        for key, value in row.items():
            if pd.isna(value): clean[key] = None
            elif key in integer_keys: clean[key] = int(value)
            elif isinstance(value, (int, float, np.number)): clean[key] = finite(value)
            else: clean[key] = value
        rows.append(clean)
    ged_keys = set(zip(ged["gwno"].dropna().astype(int), ged["year"].dropna().astype(int)))
    gdis_keys = set(zip(gdis["gwno"].dropna().astype(int), gdis["year"].dropna().astype(int)))
    m3_keys = set(zip(m3["gwno"].dropna().astype(int), m3["year"].dropna().astype(int)))
    rhrv_keys = set(zip(base["gwno"].dropna().astype(int), base["year"].dropna().astype(int)))
    common_sources = len(rhrv_keys & ged_keys & gdis_keys & m3_keys)
    complete = sum(row.get("disasters") is not None and row.get("stateConscription") is not None for row in rows)
    dy = s["dyadic"].groupby("year").agg(dyads=("dyad_id", "nunique"), highIntensity=("intensity_level", lambda x: int((numeric(x) >= 2).sum()))).reset_index()
    conflict = [{"year": int(row.year), "dyads": int(row.dyads), "highIntensity": int(row.highIntensity)} for row in dy.itertuples()]
    disasters = s["gdis"]["disastertype"].value_counts().rename_axis("type").reset_index(name="locations")
    return {"countryYears": rows, "commonSourceCountryYears": int(common_sources), "completeCountryYears": int(complete), "conflictTrend": conflict, "disasterTypes": [{"type": str(row.type), "locations": int(row.locations)} for row in disasters.itertuples()]}


def build_boundaries(s: dict[str, pd.DataFrame]) -> dict:
    mlad = s["mlad"].copy(); mlad["year"] = numeric(mlad["year"])
    mlad["system"] = mlad["conscript_sys"].replace({"NA": np.nan, "": np.nan})
    shares = []
    for year, part in mlad.groupby("year"):
        total = len(part)
        observed = int(part["system"].notna().sum())
        for system, n in part["system"].value_counts().items():
            shares.append({"year": int(year), "system": str(system), "share": finite(n / total), "n": int(n), "total": int(total)})
        shares.append({"year": int(year), "system": "Missing / not classified", "share": finite((total - observed) / total), "n": int(total - observed), "total": int(total)})
    transitions = Counter()
    for _, part in mlad.sort_values("year").groupby("ccode"):
        previous_year, previous_system = None, None
        for row in part[["year", "system"]].dropna().sort_values("year").itertuples(index=False):
            current_year, current_system = int(row.year), str(row.system)
            if previous_year is not None and current_year == previous_year + 1 and previous_system != current_system:
                transitions[(previous_system, current_system)] += 1
            previous_year, previous_system = current_year, current_system
    m3 = s["m3"].copy(); m3_trend = []
    for year, part in m3.groupby("year"):
        observed = numeric(part["com_mil_serv"]).dropna(); cons = part[numeric(part["com_mil_serv"]) == 1]
        m3_trend.append({"year": int(year), "conscriptionShare": finite(observed.mean()) if len(observed) else None, "n": int(len(observed)), "maleOnly": int((numeric(cons["com_mil_serv_gen"]) == 0).sum()), "allGenders": int((numeric(cons["com_mil_serv_gen"]) == 1).sum())})
    durations = numeric(m3.loc[numeric(m3["com_mil_serv"]) == 1, "com_mil_serv_dur_min"]).dropna().round().value_counts().sort_index()
    aq = s["aq"].copy(); aq["arrivalDate"] = pd.to_datetime(aq["arrival"], errors="coerce", dayfirst=True); aq["death"] = aq["deathDate"].notna().astype(int)
    occupations = aq["ocupation"].fillna("Unknown").replace("", "Unknown").value_counts().head(15)
    politics = aq["pOrg"].fillna("No organization recorded").replace("", "No organization recorded").value_counts().head(12)
    arrivals = aq.dropna(subset=["arrivalDate"]).groupby(aq["arrivalDate"].dt.to_period("M")).size()
    return {
        "mladShares": shares, "mladTransitions": [{"from": a, "to": b, "n": n} for (a, b), n in transitions.most_common()],
        "m3Trend": m3_trend, "m3Durations": [{"months": int(month), "n": int(n)} for month, n in durations.items() if month >= 0],
        "aqOccupations": [{"category": str(k), "n": int(v)} for k, v in occupations.items()],
        "aqPolitics": [{"category": str(k), "n": int(v)} for k, v in politics.items()],
        "aqArrivals": [{"month": str(period), "n": int(n)} for period, n in arrivals.items()],
        "aqSummary": {"rows": int(len(aq)), "deathsRecorded": int(aq["death"].sum()), "arrivalDates": int(aq["arrivalDate"].notna().sum())},
    }


def build_secondary(s: dict[str, pd.DataFrame]) -> dict:
    nsa_capacity = []
    for field, label in [("rebstrength", "Relative strength"), ("mobcap", "Mobilization capacity"), ("terrcont", "Territorial control"), ("centcontrol", "Central control")]:
        for category, n in s["nsa"][field].fillna("Missing").value_counts().items():
            nsa_capacity.append({"measure": label, "category": str(category), "n": int(n)})
    rqsi_prevalence = []
    for field in RQSI_POL + RQSI_ECON + RQSI_SOC + RQSI_GOV:
        values = numeric(s["rqsi"][field]).dropna(); rqsi_prevalence.append({"institution": field, "share": finite(values.mean()), "n": int(len(values))})
    rig_prevalence = []
    for field in RIG_CORE:
        values = numeric(s["rig"][field]).dropna(); rig_prevalence.append({"institution": field, "share": finite(values.mean()), "n": int(len(values))})
    return {"nsaCapacity": nsa_capacity, "rqsiInstitutions": rqsi_prevalence, "rigInstitutions": rig_prevalence}


def main() -> dict:
    sources = load_sources()
    catalog, summary = build_catalog(sources)
    crosswalk, descriptive_candidates, approved = build_crosswalk(sources)
    notes = json.loads((ROOT / "content" / "research-notes.json").read_text(encoding="utf-8"))
    qualitative = json.loads((ROOT / "content" / "qualitative-cases.json").read_text(encoding="utf-8"))
    return {
        "meta": {"releaseDate": "2026-09-02", "version": "audit-hardened-v3", "defaultActor": 743, "caseShortcuts": [743, 532, 488], "bootstrapReps": BOOTSTRAP_REPS},
        "coverage": {"summary": summary, "catalog": catalog},
        "micro": {"hw": build_hw(sources["hw"]), "bb": build_bb(sources["bb"], sources["bb_groups"])},
        "repertoire": {**build_repertoire(sources, approved), "croad": build_croad(sources, approved)},
        "crosswalk": {"rows": crosswalk, "descriptiveCandidates": len(descriptive_candidates), "approved": len(approved), "downstreamPolicy": "approved-only", "file": "dataset/derived/actor_entity_candidates.csv", "reviewFile": "dataset/crosswalks/actor-review-decisions.csv", "audit": build_crosswalk_audit(sources)},
        "ecology": {"organization": prepare_organization_rows(sources, approved), "actorYear": prepare_actor_year_rows(sources, approved)},
        "actorProfiles": build_profiles(sources, crosswalk, approved),
        "supportNetwork": build_network(sources["esd_ty"], approved),
        "context": {**build_context(sources), **build_secondary(sources)},
        "boundaries": build_boundaries(sources),
        "qualitative": qualitative,
        "notes": notes,
    }


if __name__ == "__main__":
    data = main()
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    OUTPUT.write_text(f"window.RECRUITMENT_DASHBOARD = {serialized};\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} · {len(data['actorProfiles'])} actor profiles · {len(data['supportNetwork']['yearEdges'])} network-year edges.")
