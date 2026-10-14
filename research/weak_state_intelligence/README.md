# Weak-State Intelligence Feasibility Study

This directory implements the protocol *Why Do Weak States Face More Rebellion?* (`docs/00_protocol_v1.0.md`). It is separate from the recruitment dashboard in `../../dashboard/`. The principal empirical unit is a **government × specific claimant × bargaining episode**; district observations are nested evidence about intelligence, coercive deployment, and escalation. Cross-country datasets define a transparent risk set and descriptive context, but cannot by themselves identify a government's private beliefs or bargaining offer.

## Current status (14 October 2026)

**Data handoff available; analysis and feasibility gate still PENDING.** The public-source files are now in the [GitHub Release handoff](https://github.com/jinming4869/-rebel-recruitment-dashboard/releases/tag/weak-state-intelligence-handoff-2026-10-14). [Download the English ZIP](https://github.com/jinming4869/-rebel-recruitment-dashboard/releases/download/weak-state-intelligence-handoff-2026-10-14/Weak_State_Intelligence_Handoff_2026-10-14.zip) (141,491,322 bytes; SHA-256 `7b0e6cfd142eff6c95b6a928ac747f16c0cea17a7225bb6bcf72a4654ad5e1a8`). The files have **not yet been registered or analyzed in this repository**. The original network-blocked status is therefore superseded by a transfer-and-schema task, not by completed results.

The archive starts with `README.md`, `WITHIN_COUNTRY_DESIGN.md`, `DATA_MAP.md`, `SOURCE_MANIFEST.json`, and `CHECKSUMS.sha256`. It contains SDM, SRDP, MSDD, UCDP/PRIO 26.1 and onset 25.1, QoG GDP, Hanson–Sigman capacity inputs, codebooks, and archival leads. Use the **research branch for code** and the Release asset for data. The Release's automatically generated source-code archives are not substitutes for this branch.

## Immediate execution order

1. Download the ZIP and check its SHA-256. Read its `WITHIN_COUNTRY_DESIGN.md` and `DATA_MAP.md` before changing the receiving code. Extract the source files outside Git history.
2. Inspect `config/source_columns.json` and `src/common.py` against the actual files. The present column mappings are **unconfirmed guesses**. The verified source-side names include SDM `groupid`, `ccode`, `active`, `violsd`, `violsd_onset`, `sample`, and `weight`; ACD `gwno_a`; and QoG `ccode` plus `wdi_gdpcapcon2015`. The handoff's `DATA_MAP.md` lists the rest. Preserve the distinct UCDP 25.1 and 26.1 vintages.
3. Repair the risk-set construction before running it on SDM: the public SDM CSV includes inactive/lookback rows, multiple phases, earlier violence, and possible host changes. The current `src/build_risk_set.py` groups by movement ID and treats the first row as entry; that assumption must be audited against `active`, phase, and prior-history fields. Do not turn recurrence or left-truncated movements into first-ever violence.
4. Register inputs using the source IDs already defined in `config/source_columns.json`: `python3 -I src/fetch_sources.py register <SOURCE_ID> <file>`. Confirm each mapping only after inspection; keep unmatched country and claimant crosswalk records visible. Then, from this directory, run `make test validate risk-set ucdp gates`. These outputs are descriptive and reconciliation checks, not an information-mechanism estimate.
5. Begin the within-country pilot and archive search described in the ZIP. The first target is comparable government–claimant episodes, including non-escalating claimants; code dated pre-decision information, private threat assessment, benchmark, first substantive offer/refusal, claimant reply, and subsequent violence. Log failed searches and unobserved offers rather than coding them as zero.

## Existing project components

| Component | Location | Status |
|---|---|---|
| Protocol and theory boundary | `docs/00_protocol_v1.0.md`, `docs/01_literature_boundary_memo.md` | Drafted; two page citations still require verification. |
| Source and construct rules | `ledgers/source_registry.csv`, `docs/02_construct_dictionary.md`, `config/codes.json` | Source registry predates the Release; update actual file registrations and hashes. |
| Dated causal graph | `docs/03_causal_graph.md` | Drafted. |
| Claimant risk set and UCDP check | `src/build_risk_set.py`, `src/ucdp_reconcile.py` | Code present; real-data output not yet produced. |
| Movement–actor crosswalk | `ledgers/movement_actor_crosswalk.csv` | Schema present; manual review required. |
| Pilot and case evidence | `src/draw_pilot.py`, `ledgers/archival_search_log.csv`, case templates | Ready for source- and case-specific revision. |
| GO / NO-GO evaluation | `src/gates.py`, `config/pi_attestations.json` | PENDING until evidence and PI attestations exist. |
| Tests | `make test` | Synthetic fixtures only; do not mistake a pass for empirical validation. |

The PI must still specify the smallest meaningful effect after the baseline rate is known, choose a defensible local-coercion measure for pilot stratification, and sign off on gates (iii)–(v). The handoff recommends QoG January 2026 `wdi_gdpcapcon2015` as the primary GDP-per-capita control for supported years; it does not fill missing 1945–1959 observations.
