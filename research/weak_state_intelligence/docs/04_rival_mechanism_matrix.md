# Rival-Mechanism Matrix (filled per case in Week 4)

Template: one column per pilot dispute, filled from `ledgers/belief_offer_event_ledger.csv`. Every cell must name ledger row IDs. If no evidence exists, the cell reads `unknown`; it is never left blank.

## Diagnostic evidence per mechanism

| Mechanism | Diagnostic observation | Ledger field(s) | Supports | Undermines |
|---|---|---|---|---|
| **Information (I→B→O)** | Optimistic B outside benchmark; low offer; correction → belief → offer revision before K/R/C/Q/S change | `belief_vs_benchmark`, `offer_terms`, `revision_*` | All three present, in that order | Calibrated B; correction without offer revision |
| **K: military incapacity** | Accurate assessment, realistic offer, unable to enforce or suppress locally | `local_forces_pre_offer`, `belief_vs_benchmark` | Calibrated B + realistic O + enforcement failure | Optimistic B |
| **R: reputation** | Private precedent talk; feasible deal rejected; no revision after an information gain | `rival_flags=R_reputation`, quote | Documented precedent rationale | Revision after information gain |
| **C: commitment** | Specific enforcement objection or expected empowerment, under accurate beliefs | `rival_flags=C_commitment` | Guarantee changes behavior | No enforcement discussion |
| **Q: rebel strategy** | Challenger's minimum lies above any feasible offer | `acceptance_benchmark`, `acceptable_terms_quote` | Private or mediator evidence of an infeasible minimum | Challenger would have accepted the offer at hand |
| **Cautious offers** | Wide uncertainty; generous or delayed first offer | `belief_uncertainty`, `offer_terms` | Low precision without optimism | Directional optimism |
| **S: state penetration** | Mobilization follows dated state expansion | `s_shock_date` vs `claim_date` | Claim after shock; no prior challenger | Claim predates any shock |

## Per-case matrix

| Dispute ID | Info | K | R | C | Q | Cautious | S | Verdict for case | Coder | 2nd coder |
|---|---|---|---|---|---|---|---|---|---|---|
| _(filled in Week 4)_ | | | | | | | | | | |

Case verdicts are `consistent_with_info`, `rival_<X>`, `mixed`, or `indeterminate`. They are **never** aggregated into a population frequency, because the pilot is outcome-balanced by design.
