# Weak-State Intelligence Feasibility Study

This directory implements the protocol *Why Do Weak States Face More Rebellion?* (`docs/00_protocol_v1.0.md`). It is separate from the recruitment dashboard in `../../dashboard/`. The principal empirical unit is a **government × specific claimant × bargaining episode**; district observations are nested evidence about intelligence, coercive deployment, and escalation. Cross-country datasets define a transparent risk set and descriptive context, but cannot by themselves identify a government's private beliefs or bargaining offer.

## Current status (14 October 2026, after data registration)

**Feasibility gate: PENDING (gate i PASS; gates ii-v not evaluated).** The handoff release ([tag `weak-state-intelligence-handoff-2026-10-14`](https://github.com/jinming4869/-rebel-recruitment-dashboard/releases/tag/weak-state-intelligence-handoff-2026-10-14), ZIP SHA-256 `7b0e6cfd142eff6c95b6a928ac747f16c0cea17a7225bb6bcf72a4654ad5e1a8`) is registered: 29 files are frozen in `ledgers/source_registry.csv` with upstream URLs and hashes, each checked against the handoff's `CHECKSUMS.sha256`. The column maps in `config/source_columns.json` were confirmed against the real files and codebooks.

**Start with `docs/08_findings_report.md`** for the real-data results, the unresolved mismatches, and the GO / NO-GO / PENDING reasoning. **`docs/07_within_country_pilot.md`** gives the pilot comparisons, archive leads and stop rule.

The headline points:
- **Risk set rebuilt around SDM movement phases.** The old "first row = entry" rule placed entry a median of 10 years early, because of the inactive lookback rows.
- **Primary first-claim frame, 1961–2012:** 271 episodes in 88 countries; the 24-month first-violence rate is 3.3–5.9 % (bounded).
- **UCDP:** conflict-level onset 25.1 agrees fully with ACD 25.1. One conflict is dropped in 26.1. The country-level `newconf` field does not match its codebook definition.
- **No dated belief–offer chain has been coded yet.** The archive hosts are unreachable from the cloud build environment.

## Reproduce

```bash
# outside Git: download the release ZIP and extract it, e.g. to /tmp/handoff/x
make register ZIP=/tmp/handoff/handoff.zip DIR=/tmp/handoff/x   # verifies hashes, copies into data/raw/ (gitignored)
make all     # tests, ledger validation, risk set, UCDP reconciliation, SDM-UCDP link candidates, pilot frame, gates
```

## Next actions (in order)

1. **PI:** set δ\* from the full-risk-set baseline (3.3–5.9 %; `ledgers/risk_set_flow.csv`). Sign off the pilot frames and search terms. Choose the local-coercion measure.
2. **Archive work** on the India frame, following `docs/07_within_country_pilot.md` §4, with every search logged in `ledgers/archival_search_log.csv`. Use the 6-week stop rule in §5.
3. Human review of `outputs/sdm_ucdp_link_candidates.csv` into `ledgers/movement_actor_crosswalk.csv`, and of SRDP-to-SDM organization matches.
4. Resolve the items in `docs/08_findings_report.md` §6.

## Existing project components

| Component | Location | Status |
|---|---|---|
| Protocol and theory boundary | `docs/00_protocol_v1.0.md`, `docs/01_literature_boundary_memo.md` | Fearon (2010) pin corrected to pp. 41–42; the Beardsley et al. p. 677 pin is still unverified. |
| Source and construct rules | `ledgers/source_registry.csv`, `docs/02_construct_dictionary.md`, `config/codes.json`, `config/country_crosswalk.json` | Registry frozen with real hashes and URLs. |
| Dated causal graph | `docs/03_causal_graph.md` | Drafted. |
| Claimant risk set and UCDP check | `src/build_risk_set.py`, `src/ucdp_reconcile.py`, `src/sdm_ucdp_link.py` | Run on real data; outputs in `ledgers/risk_set_flow.csv` and `outputs/`. |
| Movement–actor crosswalk | `ledgers/movement_actor_crosswalk.csv` | Schema present; manual review required. |
| Pilot and case evidence | `src/build_pilot_frame.py`, `ledgers/pilot_candidate_frame.csv`, `ledgers/archive_leads.csv`, `ledgers/archival_search_log.csv`, `docs/07_within_country_pilot.md` | Frames built; 14 leads; no document coded yet. |
| GO / NO-GO evaluation | `src/gates.py`, `config/pi_attestations.json` | PENDING until evidence and PI attestations exist. |
| Tests | `make test` | Synthetic fixtures only; do not mistake a pass for empirical validation. |

The PI must still specify the smallest meaningful effect after the baseline rate is known, choose a defensible local-coercion measure for pilot stratification, and sign off on gates (iii)–(v). The handoff recommends QoG January 2026 `wdi_gdpcapcon2015` as the primary GDP-per-capita control for supported years; it does not fill missing 1945–1959 observations.
