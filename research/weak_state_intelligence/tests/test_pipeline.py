"""Unit tests on SYNTHETIC fixtures only. No synthetic value is ever written to
ledgers/ or outputs/ of the real project: every test runs in a temporary copy.

Run: python -I -m unittest discover -s tests   (from the project root)
"""
import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build_risk_set as brs  # noqa: E402
import draw_pilot  # noqa: E402
import gates  # noqa: E402
import validate_ledgers  # noqa: E402
from common import SourceNotReady, load_source, schemas  # noqa: E402


def _mov(mid, phases, prioract=0, start1=None, viol=(), priorviol=0, lookback=10, end_codes=None):
    """Synthetic SDM-like movement: inactive lookback rows, then one or two active phases.
    phases: list of (first_active_year, last_active_year)."""
    rows = []
    first = phases[0][0]
    end_codes = end_codes or [9999 if p[1] == 2012 else p[1] for p in phases]
    starts = [start1 if start1 is not None else phases[0][0]] + [p[0] for p in phases[1:]]
    for y in range(first - lookback, phases[-1][1] + 1):
        k = next((i + 1 for i, (a, b) in enumerate(phases) if a <= y <= b), 0)
        rows.append({"movement_id": mid, "movement_name": mid, "country_name": "Synthland", "country_code": 999,
                     "year": y, "active": int(k > 0), "phase1": int(k == 1), "phase2": int(k == 2),
                     "startdate1": starts[0], "enddate1": end_codes[0],
                     "startdate2": starts[1] if len(phases) > 1 else None,
                     "enddate2": end_codes[1] if len(phases) > 1 else None,
                     "prioract": prioract, "priorviol": priorviol if k else None,
                     "priorconflict": None, "anti_state_violence": (int(y in viol) if k else None),
                     "high_violence": 0 if k else None, "violsd_onset": None, "doublecount": None,
                     "sample": 0, "weight": None, "ucdp_terrconflict": 0})
    df = pd.DataFrame(rows)
    on = df["anti_state_violence"].eq(1) & ~df["anti_state_violence"].shift().eq(1)
    df.loc[df["active"] == 1, "violsd_onset"] = on.astype(int)
    return df


def synthetic_panel():
    return pd.concat([
        _mov("m1", [(1970, 1975)], viol=(1971,)),                    # primary, violence within 24m
        _mov("m2", [(1970, 1985)], viol=(1980,)),                    # primary, late violence
        _mov("m3", [(1975, 1978)]),                                  # primary, claim ended, no violence
        _mov("m4", [(1990, 1995)], viol=(1990,)),                    # violent in claim year
        _mov("m5", [(2011, 2012)]),                                  # primary, censored before t0+2
        _mov("m6", [(1945, 2012)], prioract=1, start1=1886),         # inherited (pre-1945)
        _mov("m7", [(1960, 1965), (1980, 2012)], viol=(1962, 1990)), # violent phase 1, resumed phase 2
        _mov("m8", [(1961, 1991)], end_codes=[8888]),                # host change exit
    ], ignore_index=True)


class RiskSetTests(unittest.TestCase):
    def setUp(self):
        self.ep = brs.movement_episodes(synthetic_panel()).set_index("episode_id")

    def test_entry_is_first_active_year_not_lookback_row(self):
        self.assertEqual(self.ep.loc["m1-p1", "entry_year"], 1970)

    def test_populations(self):
        pop = self.ep["population"]
        self.assertEqual(pop["m1-p1"], "primary_first_claim")
        self.assertEqual(pop["m4-p1"], "violent_in_claim_year")
        self.assertEqual(pop["m6-p1"], "inherited_claim")
        self.assertEqual(pop["m7-p2"], "resumed_claim")
        self.assertTrue(self.ep.loc["m7-p2", "prior_violence"])

    def test_recurrence_is_not_first_violence(self):
        # m7's 1990 violence belongs to the resumed phase, never to a first-claim episode
        self.assertEqual(self.ep.loc["m7-p1", "first_violence_year"], 1962)
        self.assertEqual(self.ep.loc["m7-p2", "first_violence_year"], 1990)
        self.assertNotEqual(self.ep.loc["m7-p2", "population"], "primary_first_claim")

    def test_exits(self):
        self.assertEqual(self.ep.loc["m3-p1", "exit_type"], "claim_ended")
        self.assertEqual(self.ep.loc["m5-p1", "exit_type"], "right_censored")
        self.assertEqual(self.ep.loc["m8-p1", "exit_type"], "host_change")

    def test_y24_bounds(self):
        e = self.ep
        self.assertEqual((e.loc["m1-p1", "y24_lower"], e.loc["m1-p1", "y24_upper"]), (1, 1))
        self.assertEqual((e.loc["m2-p1", "y24_lower"], e.loc["m2-p1", "y24_upper"]), (0, 0))
        self.assertEqual(e.loc["m5-p1", "y24_lower"], 0)
        self.assertTrue(pd.isna(e.loc["m5-p1", "y24_upper"]))
        self.assertTrue(pd.isna(e.loc["m6-p1", "y24_lower"]))  # inherited: claim year unobserved

    def test_no_structural_flags_on_clean_fixture(self):
        self.assertEqual(set(self.ep["checks"]), {""})

    def test_risk_years_stop_at_event(self):
        rs = brs.risk_set_years(self.ep.reset_index())
        m1 = rs[rs["episode_id"] == "m1-p1"]
        self.assertEqual(list(m1["year"]), [1970, 1971])
        self.assertNotIn("m4-p1", set(rs["episode_id"]))

    def test_flow_marks_unobservable_stages(self):
        ep = brs.add_weakness_stratum(self.ep.reset_index(), None)
        flow = brs.flow_table(ep)
        row = flow[(flow["population"] == "primary_first_claim") & (flow["w_stratum"] == "all")].iloc[0]
        self.assertTrue(str(row["govt_awareness"]).startswith("NA:"))
        self.assertEqual(int(row["episodes"]), 6)  # m1 m2 m3 m5 m7-p1 m8

    def test_cif_sums_below_one(self):
        ep = brs.add_weakness_stratum(self.ep.reset_index(), None)
        last = brs.cumulative_incidence(ep).iloc[-1]
        self.assertLessEqual(last["cif_violence"] + last["cif_competing"], 1.0)

    def test_gdp_override_and_no_imputation(self):
        ep = self.ep.reset_index().assign(country_code=260)
        gdp = pd.DataFrame({"country_code_cow": [255, 255], "year": [1990, 1969], "gdppc": [100.0, 50.0],
                            "gdppc_maddison": [None, None]})
        ov = [{"sdm_ccode": 260, "qog_ccodecow": 255, "from_year": 1991}]
        out = brs.add_weakness_stratum(ep, gdp, ov).set_index("episode_id")
        self.assertEqual(out.loc["m1-p1", "w_stratum"], "unknown")  # 1969 < override start
        self.assertEqual(out.loc["m1-p1", "gdp_missing_reason"], "country_not_in_qog")

    def test_unconfirmed_source_refused(self):
        with self.assertRaises(SourceNotReady):
            load_source("DATA_ICI")


class UcdpReconcileTests(unittest.TestCase):
    def test_vintage_and_type_handling(self):
        import ucdp_reconcile as ur
        acd = pd.DataFrame({"conflict_id": [1, 1, 2, 3], "year": [1950, 1951, 1960, 1970],
                            "type_of_conflict": [2, 3, 3, 4], "gwno": ["1", "1", "2", "3"],
                            "side_b": "x", "territory_name": "t"})
        f = ur.acd_first_years(acd, [3, 4]).set_index("conflict_id")
        self.assertEqual(f.loc[1, "first_intrastate_year"], 1951)   # type changed 2 -> 3
        self.assertEqual(f.loc[1, "first_year_any_type"], 1950)
        onset = pd.DataFrame({"new_conflict_onset": [1, 1], "conflict_ids": ["1", "2 "], "year": [1951, 1961], "gwno": [1, 2]})
        out = ur.compare(ur.onset_newconf(onset), f.reset_index(), "onset_year", "first_intrastate_year", "on", "acd")
        st = out.set_index("conflict_id")["status"]
        self.assertEqual(st[1], "agree")
        self.assertEqual(st[2], "year_mismatch")
        self.assertEqual(st[3], "only_in_acd")

    def test_non_numeric_ids_refused(self):
        import ucdp_reconcile as ur
        with self.assertRaises(ValueError):
            ur.onset_newconf(pd.DataFrame({"new_conflict_onset": [1], "conflict_ids": ["1-99"], "year": [1966], "gwno": [750]}))


class LinkTests(unittest.TestCase):
    def test_corrupted_old_ids_flagged_and_country_checked(self):
        import sdm_ucdp_link as sl
        sdm = pd.DataFrame({"movement_id": [1, 2], "movement_name": ["A", "B"], "country_name": ["India", "Iran"],
                            "ucdp_conflictid_old": ["Jan 99", "1-6"], "ucdp_territoryname": ["Mizoram", "Kurdistan"],
                            "year": [1966, 1946], "active": [1, 1], "ucdp_terrconflict": [1, 1]})
        acd = pd.DataFrame({"conflict_id": [296, 271], "territory_name": ["Mizoram", "Kurdistan"], "location": ["India", "Iraq"],
                            "year": [1966, 1961], "type_of_conflict": [3, 3], "incompatibility": [1, 1]})
        out = sl.candidates(sdm, acd).set_index("movement_name")
        self.assertFalse(out.loc["A", "old_id_wellformed"])
        self.assertEqual(out.loc["A", "candidate_status"], "territory_and_country_match")
        self.assertEqual(out.loc["B", "candidate_status"], "territory_match_country_differs")
        self.assertEqual(set(out["review_status"]), {"unreviewed"})


class PilotDrawTests(unittest.TestCase):
    def frame(self):
        rows = []
        n = 0
        for i in ("high", "low"):
            for k in ("high", "low"):
                for e in ("escalating", "non_escalating"):
                    size = 2 if (i, k, e) == ("low", "high", "escalating") else 6
                    for _ in range(size):
                        n += 1
                        rows.append({"dispute_id": f"d{n:03d}", "info_stratum": i,
                                     "coercion_stratum": k, "escalation_stratum": e})
        return pd.DataFrame(rows)

    def test_allocation_and_reproducibility(self):
        a, _ = draw_pilot.draw(self.frame(), 24, 7)
        b, _ = draw_pilot.draw(self.frame(), 24, 7)
        self.assertEqual(len(a), 24)
        self.assertEqual(list(a["dispute_id"]), list(b["dispute_id"]))
        small = a[a["cell"] == "low|high|escalating"]
        self.assertEqual(len(small), 2)
        self.assertAlmostEqual(small["selection_probability"].iloc[0], 1.0)

    def test_full_order_kept_for_replacement(self):
        _, order = draw_pilot.draw(self.frame(), 24, 7)
        self.assertEqual(len(order), len(self.frame()))


def _write(root, name, rows):
    cols = schemas()[name]["columns"]
    with open(root / "ledgers" / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def complete_dispute(did, escalate, i_level="low", k_level="high"):
    base = {"dispute_id": did, "coder": "rA", "coder_confidence": "high"}
    rows = [dict(base, row_id=f"{did}-i{j}", stage="inputs", event_date="1980-01-01",
                 input_component=c, input_level=i_level)
            for j, c in enumerate(["field_report_coverage", "informant_network", "corroboration"])]
    rows += [
        dict(base, row_id=f"{did}-b", stage="belief", event_date="1980-03-01", belief_construct="manpower",
             belief_quote="(synthetic)", doc_audience="private_internal", belief_vs_benchmark="optimistic",
             benchmark_source_ids="S1;S2", k_level_pre_offer=k_level),
        dict(base, row_id=f"{did}-o", stage="offer", event_date="1980-05-01",
             first_response="substantive_offer", offer_terms="(synthetic terms)"),
        dict(base, row_id=f"{did}-r", stage="response", event_date="1980-06-01",
             challenger_response="rejected", acceptance_benchmark="mediator_record"),
        dict(base, row_id=f"{did}-y", stage="outcome", event_date="1981-01-01",
             violence_24m="anti_state_violence" if escalate else "verified_no_violence_24m"),
    ]
    return rows


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "config", self.tmp / "config")
        shutil.copytree(ROOT / "ledgers", self.tmp / "ledgers")
        (self.tmp / "outputs").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_empty_project_is_pending(self):
        rep = gates.evaluate(self.tmp)
        self.assertEqual(rep["overall"], "PENDING")

    def test_chain_rules(self):
        rows = complete_dispute("x1", True)
        c = gates.dispute_chain(pd.DataFrame(rows).reindex(
            columns=schemas()["belief_offer_event_ledger.csv"]["columns"]).fillna(""))
        self.assertTrue(c["complete"], c["missing_links"])
        # offer dated before the belief breaks temporal order
        rows[4]["event_date"] = "1980-02-01"
        c = gates.dispute_chain(pd.DataFrame(rows).reindex(
            columns=schemas()["belief_offer_event_ledger.csv"]["columns"]).fillna(""))
        self.assertFalse(c["complete"])

    def test_gate_ii_thresholds(self):
        rows, samp = [], []
        for n in range(12):
            did = f"s{n:02d}"
            esc = n % 2 == 0
            rows += complete_dispute(did, esc, i_level="low" if n % 3 else "high",
                                     k_level="high" if n % 3 else "low")
            samp.append({"dispute_id": did, "country": f"C{n % 5}", "cell": "c", "selection_probability": "1",
                         "rng_seed": "1", "status": "selected",
                         "escalation_stratum": "escalating" if esc else "non_escalating"})
        _write(self.tmp, "belief_offer_event_ledger.csv", rows)
        _write(self.tmp, "pilot_sampling.csv", samp)
        rep = gates.evaluate(self.tmp)
        self.assertEqual(rep["gates"]["ii_complete_chains"]["status"], "PASS")
        self.assertTrue(rep["gates"]["iii_overlap"]["off_diagonal_support"])
        self.assertEqual(rep["gates"]["iv_selection"]["status"], "FAIL")  # nothing searched
        self.assertEqual(rep["overall"], "NO-GO")

    def test_validator_catches_public_belief_and_bare_rejection(self):
        bad = complete_dispute("v1", True)
        bad[3]["doc_audience"] = "public"
        bad[5]["acceptance_benchmark"] = "none_credible"
        _write(self.tmp, "belief_offer_event_ledger.csv", bad)
        errs = validate_ledgers.check_ledger("belief_offer_event_ledger.csv",
                                             pd.read_csv(self.tmp / "ledgers" / "belief_offer_event_ledger.csv",
                                                         dtype=str, keep_default_na=False))
        text = " ".join(errs)
        self.assertIn("public document", text)
        self.assertIn("rejected_reason_unknown", text)

    def test_real_ledgers_are_valid(self):
        self.assertEqual(validate_ledgers.main(ROOT), 0)


class PowerTests(unittest.TestCase):
    def test_runs_and_bounds(self):
        import power_sim
        p_yes, p_no = power_sim.power(30, 3, 0.15, 0.10, 0.25, 0.1, 50, 1)
        self.assertTrue(0 <= p_yes <= 1 and 0 <= p_no <= 1)


if __name__ == "__main__":
    unittest.main()
