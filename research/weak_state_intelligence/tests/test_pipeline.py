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


def synthetic_panel():
    rows = []
    # m1: enters 1970, violent 1971 (within 24m)  m2: enters 1970, violent 1980
    # m3: enters 1975, ends 1978 no violence      m4: violent at entry
    # m5: enters 2011, censored                    m6: enters 1945 (left-truncated), censored
    spec = {"m1": (1970, 1971, 1971), "m2": (1970, 1980, 1980), "m3": (1975, 1978, None),
            "m4": (1990, 1995, 1990), "m5": (2011, 2012, None), "m6": (1945, 2012, None)}
    for mid, (a, b, v) in spec.items():
        for y in range(a, b + 1):
            rows.append({"movement_id": mid, "country_code": 100, "year": y,
                         "anti_state_violence": int(v is not None and y >= v)})
    return pd.DataFrame(rows)


class RiskSetTests(unittest.TestCase):
    def setUp(self):
        self.ep = brs.movement_episodes(synthetic_panel()).set_index("movement_id")

    def test_exit_types(self):
        self.assertEqual(self.ep.loc["m1", "exit_type"], "violence")
        self.assertEqual(self.ep.loc["m3", "exit_type"], "terminated")
        self.assertEqual(self.ep.loc["m5", "exit_type"], "right_censored")

    def test_violent_at_entry_excluded(self):
        self.assertFalse(self.ep.loc["m4", "previolence_eligible"])
        self.assertEqual(self.ep.loc["m4", "y24_annual_approx"], "not_applicable")

    def test_y24(self):
        self.assertEqual(self.ep.loc["m1", "y24_annual_approx"], "1")
        self.assertEqual(self.ep.loc["m2", "y24_annual_approx"], "0")
        self.assertEqual(self.ep.loc["m5", "y24_annual_approx"], "right_censored")
        self.assertTrue(self.ep.loc["m6", "left_truncated"])

    def test_risk_years_stop_at_event(self):
        rs = brs.risk_set_years(self.ep.reset_index())
        m1 = rs[rs["movement_id"] == "m1"]
        self.assertEqual(list(m1["year"]), [1970, 1971])
        self.assertEqual(m1["event"].sum(), 1)
        self.assertNotIn("m4", set(rs["movement_id"]))

    def test_flow_marks_unobservable_stages(self):
        ep = brs.add_weakness_stratum(self.ep.reset_index(), None)
        flow = brs.flow_table(ep)
        self.assertTrue(str(flow.loc[0, "govt_awareness"]).startswith("NA:"))
        self.assertEqual(int(flow.loc[0, "previolence_entries"]), 5)

    def test_cif_sums_below_one(self):
        ep = brs.add_weakness_stratum(self.ep.reset_index(), None)
        cif = brs.cumulative_incidence(ep)
        last = cif[cif["w_stratum"] == "all"].iloc[-1]
        self.assertLessEqual(last["cif_violence"] + last["cif_termination"], 1.0)

    def test_unconfirmed_source_refused(self):
        with self.assertRaises(SourceNotReady):
            load_source("DATA_SDM")


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
