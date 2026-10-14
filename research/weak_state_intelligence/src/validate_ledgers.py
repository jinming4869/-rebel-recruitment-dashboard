"""Enforce ledger column contracts, controlled vocabularies and coding rules.

Exit code 1 on any violation. Run after every coding session.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, codes, read_ledger, schemas  # noqa: E402


def check_ledger(name: str, df: pd.DataFrame) -> list[str]:
    spec = schemas()[name]
    voc = codes()
    errs = []
    if list(df.columns) != spec["columns"]:
        errs.append(f"{name}: columns differ from schema")
        return errs
    for col in spec.get("required", []):
        blank = df.index[df[col].str.strip() == ""].tolist()
        if blank:
            errs.append(f"{name}: required '{col}' blank in rows {blank[:5]}")
    for col, vocab in spec.get("enums", {}).items():
        allowed = set(voc[vocab]) | set(voc["missingness"]) | {""}
        bad = df.loc[~df[col].isin(allowed), col]
        for i, v in bad.items():
            errs.append(f"{name}: row {i} {col}='{v}' not in {vocab}")
    if name == "belief_offer_event_ledger.csv":
        errs += _coding_rules(df)
    return errs


def _coding_rules(df: pd.DataFrame) -> list[str]:
    """Substantive rules from Protocol §Comparative archival pilot and App. B."""
    errs = []
    for i, r in df.iterrows():
        if r["belief_quote"] and r["doc_audience"] == "public":
            errs.append(f"ledger row {i}: belief taken from a public document (public threats are not private beliefs)")
        if r["belief_vs_benchmark"] == "optimistic":
            srcs = [s for s in r["benchmark_source_ids"].split(";") if s.strip()]
            if len(srcs) < 2:
                errs.append(f"ledger row {i}: 'optimistic' needs >=2 independent benchmark sources")
        if r["first_response"] == "verified_no_offer" and r["challenger_response"] not in ("", "not_applicable"):
            errs.append(f"ledger row {i}: challenger response coded although no offer was made")
        if r["challenger_response"] == "rejected" and r["acceptance_benchmark"] in ("", "none_credible"):
            errs.append(f"ledger row {i}: 'rejected' without credible acceptance evidence must be 'rejected_reason_unknown'")
        if r["first_response"] == "substantive_offer" and not r["offer_terms"].strip():
            errs.append(f"ledger row {i}: substantive_offer without terms")
        if r["input_component"] and r["belief_vs_benchmark"] not in ("",):
            errs.append(f"ledger row {i}: input-quality and belief error coded in the same row (blinding breach)")
        if r["coder_confidence"] in ("medium", "low") and not r["second_coder"].strip():
            errs.append(f"ledger row {i}: {r['coder_confidence']}-confidence code lacks blind second coder")
    return errs


def main(root: Path = ROOT) -> int:
    errs = []
    for name in schemas():
        if name.startswith("_"):
            continue
        errs += check_ledger(name, read_ledger(name, root))
    for e in errs:
        print("ERROR", e)
    print(f"{len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
