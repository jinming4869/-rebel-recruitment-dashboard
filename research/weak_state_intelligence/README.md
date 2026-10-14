# Weak-State Intelligence Feasibility Study

This directory runs the research protocol *Why Do Weak States Face More Rebellion?* (v1.0, archived in `docs/00_protocol_v1.0.md`). It is separate from the recruitment dashboard in `../../dashboard/`.

## Status (2026-10-14)

**Gate report: PENDING.** No original-data analysis has been run yet. The data hosts (UCDP, SDM, PA-X, DOI resolvers) are blocked by the build environment's network policy. As the protocol requires, the gap is reported and not filled: every script that needs data stops with `NOT RUN` instead of producing numbers.

| Week | Deliverable | Status |
|---|---|---|
| 1 | Literature boundary memo | Drafted: `docs/01_literature_boundary_memo.md` (two pin cites still to verify) |
| 1 | Source registry | `ledgers/source_registry.csv` (25 rows; data rows `pending_download`) |
| 1 | Construct dictionary / codebook | `docs/02_construct_dictionary.md`, `config/codes.json` |
| 1 | Smallest meaningful effect δ\* | **PI decision**, after the full risk-set baseline rate is known |
| 1 | Dated causal graph | `docs/03_causal_graph.md` |
| 2 | Risk-set flow, competing risks | Code ready: `src/build_risk_set.py` (blocked on SDM) |
| 2 | UCDP 26.1 vs onset 25.1 reconciliation | Code ready: `src/ucdp_reconcile.py` (blocked on UCDP) |
| 2 | Movement–actor crosswalk | Schema ready: `ledgers/movement_actor_crosswalk.csv` (human review only) |
| 3 | Prespecified 24-dispute draw | Code ready: `src/draw_pilot.py`; design frozen in `config/pilot_design.json`; **coercion proxy needs PI choice** |
| 3 | Archival search log | Schema ready: `ledgers/archival_search_log.csv` |
| 4 | Belief–offer event ledger, case traces, rival matrix | Schema + validator + templates (`docs/04_…`, `docs/05_…`) |
| 5 | GO / NO-GO gate evaluation | `src/gates.py` implements gates (i)–(v); `docs/06_decision_memo_template.md` |
| 5 | Power / sample size | `src/power_sim.py` (needs PI inputs) |

## How to unblock Week 2

1. Get the raw files, using **either** option:
   - allow these hosts in the cloud environment's network settings: `ucdp.uu.se`, `michagermann.github.io`, `researchdata.bath.ac.uk`, `doi.org`, `journals.sagepub.com`; then run `python3 -I src/fetch_sources.py download <SOURCE_ID> <url>`
   - **or** upload files you already have, then run `python3 -I src/fetch_sources.py register <SOURCE_ID> <path>`. This copies the file into `data/raw/<SOURCE_ID>/` and records its SHA-256, date and filename in the registry.
2. Run `python3 -I src/inspect_source.py data/raw/<SOURCE_ID>/<file>.csv` and check `config/source_columns.json` against the real columns and the codebook. Then set `"confirmed": true`.
3. Run `make risk-set ucdp gates`.

Needed for Week 2: SDM (public, 1945–2012), UCDP ACD 26.1, UCDP Dyadic 26.1, UCDP onset 25.1, and a lagged GDP-per-capita series (PI to choose PWT, Maddison or WDI). Optional: ICI (pilot stratifier), SRDP (tactic timing), GeoSDM.

## Decisions reserved for the PI

- δ\* and the precision rule (`docs/02_construct_dictionary.md` §G)
- Coercion proxy for pilot stratification (`config/pilot_design.json`)
- GDP-per-capita source
- Attestations for gates (iii), (iv) and (v) (`config/pi_attestations.json`); `gates.py` will not pass these gates without them
- Sign-off of the memo and construct dictionary (this freezes the coding rules)

## Guarantees built into the code

- Column maps must be confirmed before anything runs, so a wrong guess fails loudly.
- Raw files are immutable and hashed; re-drawing the pilot is refused once a draw exists.
- `unknown`, `verified_no_offer`, `not_applicable` and `right_censored` are never merged.
- The validator rejects: beliefs taken from public documents; "optimistic" codes with fewer than two benchmark sources; `rejected` without acceptance evidence; information-quality and belief-error codes in the same row (a blinding breach); and medium- or low-confidence codes without a second coder.
- Tests (`make test`) run only on synthetic fixtures inside temporary directories. No synthetic value can reach `ledgers/` or `outputs/`.
