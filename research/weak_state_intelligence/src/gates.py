"""Week 5: evaluate the precommitted binary feasibility gate (Protocol §Precommitted gate).

Each gate is PASS, FAIL, or NOT_EVALUATED (missing evidence / missing PI attestation).
Overall: GO only if all five PASS; NO-GO if any FAIL; otherwise PENDING (the decision
memo cannot be issued yet). Writes outputs/gate_report.json and outputs/gate_report.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, read_ledger  # noqa: E402

PRIVATE = {"private_internal", "private_to_mediator"}
LEVELS = {"high", "medium", "low"}


def _date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.replace("", None), errors="coerce")


def dispute_chain(rows: pd.DataFrame) -> dict:
    """Apply construct-dictionary §E to all ledger rows of one dispute."""
    r = rows.assign(_d=_date(rows["event_date"]))
    comps = r.loc[r["input_level"].isin(LEVELS), "input_component"].unique()
    levels = r.loc[r["input_level"].isin(LEVELS), "input_level"]
    belief = r[(r["belief_quote"].str.strip() != "") & r["doc_audience"].isin(PRIVATE) & r["_d"].notna()]
    bench = r[r["belief_vs_benchmark"].isin(["optimistic", "calibrated_or_uncertain", "pessimistic"])
              & (r["benchmark_source_ids"].str.count(";") >= 1)]
    offer = r[(r["first_response"] == "substantive_offer") & (r["offer_terms"].str.strip() != "") & r["_d"].notna()]
    resp = r[r["challenger_response"].isin(["accepted", "rejected"]) & r["_d"].notna()]
    accept = r["acceptance_benchmark"].isin(["private_challenger_record", "mediator_record"]).any()
    outcome = r.loc[r["violence_24m"].isin(["anti_state_violence", "verified_no_violence_24m"]), "violence_24m"]
    explicit_refusal = (r["first_response"] == "explicit_refusal").any()

    offer_date = offer["_d"].min() if len(offer) else pd.NaT
    ordered = (len(belief) and len(offer) and len(resp)
               and belief["_d"].min() < offer_date <= resp["_d"].min())
    links = {
        "inputs_ge3": len(comps) >= 3,
        "private_belief_pre_offer": bool(len(belief) and len(offer) and belief["_d"].min() < offer_date),
        "triangulated_benchmark": len(bench) > 0,
        "dated_first_offer": len(offer) > 0,
        "dated_response": len(resp) > 0,
        "acceptance_evidence": bool(accept),
        "followup_24m": len(outcome) > 0,
        "temporal_order": bool(ordered),
    }
    order = {"low": 0, "medium": 1, "high": 2}
    i_level = None
    if len(comps) >= 3:
        med = sorted(order[v] for v in levels)[len(levels) // 2]
        i_level = {0: "low", 1: "medium", 2: "high"}[med]
    k = r.loc[r["k_level_pre_offer"].isin(LEVELS), "k_level_pre_offer"]
    return {
        "complete": all(links.values()),
        "missing_links": [k_ for k_, v in links.items() if not v],
        "escalating": bool((outcome == "anti_state_violence").any()) if len(outcome) else None,
        "explicit_refusal": bool(explicit_refusal),
        "I_level": i_level,
        "K_level": k.iloc[0] if len(k) else None,
        "optimistic": bool((r["belief_vs_benchmark"] == "optimistic").any()) if len(bench) else None,
    }


def gate_i(root: Path) -> dict:
    """(i) previolence claimant denominator that includes non-escalating episodes."""
    p = root / "ledgers" / "risk_set_flow.csv"
    flow = pd.read_csv(p) if p.exists() and p.stat().st_size else pd.DataFrame()
    if flow.empty:
        return {"status": "NOT_EVALUATED", "why": "risk_set_flow.csv empty (SDM not yet built)"}
    a = flow[(flow["population"] == "primary_first_claim") & (flow["w_stratum"] == "all")
             & (flow["window"] == "gdp_supported_1961_2012")]
    if a.empty:
        return {"status": "FAIL", "why": "no primary_first_claim row for 1961-2012"}
    r = a.iloc[0]
    non_esc = int(r["exit_claim_ended"] + r["exit_host_change"] + r["right_censored"])
    ok = int(r["episodes"]) > 0 and non_esc > 0 and int(r["exit_violence"]) > 0
    return {"status": "PASS" if ok else "FAIL",
            "evidence": {"episodes": int(r["episodes"]), "countries": int(r["countries"]),
                         "escalated": int(r["exit_violence"]), "non_escalated_or_censored": non_esc},
            "caveat": "self-determination claimants only; awareness and offers are not observed in public data"}


def gate_ii(chains: dict, sampling: pd.DataFrame) -> dict:
    if not chains:
        return {"status": "NOT_EVALUATED", "why": "no coded disputes in belief_offer_event_ledger.csv"}
    complete = [d for d, c in chains.items() if c["complete"]]
    esc = [d for d in complete if chains[d]["escalating"]]
    non = [d for d in complete if chains[d]["escalating"] is False]
    country = sampling.set_index("dispute_id")["country"].to_dict()
    countries = {country.get(d, "") for d in complete} - {""}
    ok = len(complete) >= 12 and len(esc) >= 4 and len(non) >= 4 and len(countries) >= 4
    return {"status": "PASS" if ok else "FAIL",
            "complete_chains": len(complete), "escalating": len(esc), "non_escalating": len(non),
            "countries": len(countries), "explicit_refusals_not_counted": sum(c["explicit_refusal"] for c in chains.values()),
            "missing_links_by_dispute": {d: c["missing_links"] for d, c in chains.items() if not c["complete"]}}


def gate_iii(chains: dict, attest: dict, root: Path) -> dict:
    cells = pd.DataFrame([{"I": c["I_level"], "K": c["K_level"]} for c in chains.values()
                          if c["I_level"] and c["K_level"]])
    if cells.empty:
        return {"status": "NOT_EVALUATED", "why": "no dispute with both I and K coded"}
    table = pd.crosstab(cells["I"], cells["K"])
    has = lambda i, k: int(table.loc[i, k]) if i in table.index and k in table.columns else 0  # noqa: E731
    off_diag = has("low", "high") > 0 and has("high", "low") > 0
    ep = root / "data" / "derived" / "movement_episodes.csv"
    w_ok = None
    if ep.exists():
        e = pd.read_csv(ep, dtype={"movement_id": str})
        w_ok = bool((e["w_stratum"].isin(["weak", "strong"])).any())
    att = attest.get("gate_iii_comparable_threat")
    status = "FAIL" if not off_diag or w_ok is False else (
        "PASS" if att and att.get("value") and w_ok else "NOT_EVALUATED")
    return {"status": status, "I_by_K": table.to_dict(), "off_diagonal_support": off_diag,
            "baseline_weakness_recoverable": w_ok, "pi_threat_comparability": att}


def selection_bounds(chains: dict, sampling: pd.DataFrame) -> dict:
    """Worst-case (Manski) bounds on the escalating-minus-non-escalating difference in the
    share of disputes with optimistic incumbent error, treating every selected dispute
    without a benchmarked belief as missing."""
    strat = sampling.set_index("dispute_id")["escalation_stratum"].to_dict()
    out = {}
    for s in ("escalating", "non_escalating"):
        ids = [d for d, v in strat.items() if v == s]
        obs = [chains[d]["optimistic"] for d in ids if d in chains and chains[d]["optimistic"] is not None]
        n, k = len(ids), sum(obs)
        out[s] = {"n_selected": n, "n_observed": len(obs),
                  "lo": k / n if n else None, "hi": (k + n - len(obs)) / n if n else None}
    e, ne = out["escalating"], out["non_escalating"]
    if None in (e["lo"], ne["lo"]):
        return {"per_stratum": out, "diff_bounds": None}
    return {"per_stratum": out, "diff_bounds": [e["lo"] - ne["hi"], e["hi"] - ne["lo"]]}


def gate_iv(chains: dict, sampling: pd.DataFrame, search: pd.DataFrame, attest: dict) -> dict:
    sel = set(sampling["dispute_id"])
    if not sel:
        return {"status": "NOT_EVALUATED", "why": "no pilot draw yet"}
    unsearched = sorted(sel - set(search["dispute_id"]))
    bounds = selection_bounds(chains, sampling)
    att = attest.get("gate_iv_bounds_acceptable")
    if unsearched:
        status = "FAIL"
    elif att is None:
        status = "NOT_EVALUATED"
    else:
        status = "PASS" if att.get("value") else "FAIL"
    return {"status": status, "unsearched_disputes": unsearched, "bounds": bounds, "pi_attestation": att}


def gate_v(root: Path, attest: dict) -> dict:
    p = root / "outputs" / "power_plan.json"
    if not p.exists():
        return {"status": "NOT_EVALUATED", "why": "outputs/power_plan.json missing (needs PI-fixed delta*)"}
    plan = json.loads(p.read_text())
    att = attest.get("gate_v_collection_plan_feasible")
    if att is None:
        return {"status": "NOT_EVALUATED", "power_plan": plan, "why": "PI attestation missing"}
    return {"status": "PASS" if att.get("value") else "FAIL", "power_plan": plan, "pi_attestation": att}


def evaluate(root: Path = ROOT) -> dict:
    ledger = read_ledger("belief_offer_event_ledger.csv", root)
    sampling = read_ledger("pilot_sampling.csv", root)
    search = read_ledger("archival_search_log.csv", root)
    attest = json.loads((root / "config" / "pi_attestations.json").read_text())
    chains = {d: dispute_chain(g) for d, g in ledger.groupby("dispute_id")}
    gates = {"i_denominator": gate_i(root), "ii_complete_chains": gate_ii(chains, sampling),
             "iii_overlap": gate_iii(chains, attest, root), "iv_selection": gate_iv(chains, sampling, search, attest),
             "v_power_plan": gate_v(root, attest)}
    statuses = [g["status"] for g in gates.values()]
    overall = "GO" if all(s == "PASS" for s in statuses) else "NO-GO" if "FAIL" in statuses else "PENDING"
    return {"overall": overall, "gates": gates}


def main() -> None:
    rep = evaluate()
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    (out / "gate_report.json").write_text(json.dumps(rep, indent=2, default=str))
    lines = [f"# Feasibility gate report\n\n**Overall: {rep['overall']}**\n", "| Gate | Status | Note |", "|---|---|---|"]
    for k, g in rep["gates"].items():
        lines.append(f"| {k} | {g['status']} | {g.get('why', '')} |")
    (out / "gate_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
