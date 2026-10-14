# Construct Dictionary and Codebook (Week 1 deliverable)

*Status: DRAFT for PI sign-off. Controlled vocabularies are machine-readable in `config/codes.json`, and `src/validate_ledgers.py` enforces them.*

Notation follows Protocol Appendix A. Unit: **government–challenger–month** (archival file); **movement–incumbent–year** (quantitative risk set).

## A. Population and clock

| Construct | Definition | Source | Rule |
|---|---|---|---|
| **Eligible claimant** | An SDM movement with an independently recorded organized demand, observed before any anti-state violence. | SDM (Sambanis et al. 2018) | Entry = first independently recorded demand year (month where available). Exit = first anti-state violence, claim termination, or right-censoring (2012 for public SDM). |
| **Clock start (t₀)** | Date of the independently observed demand. | SDM, then archives | **Never** UCDP onset, government awareness, or first negotiation. Selecting on awareness selects on treatment. |
| **Y₂₄** | First anti-state organized armed action in (t₀, t₀+24 months]. | Archives, UCDP, SRDP | Distinct from crossing the UCDP 25-death threshold, which is recorded separately. |
| **UCDP threshold** | ≥25 battle-related deaths in a calendar year in a state-based conflict. | UCDP ACD/Dyadic 26.1 | A separate later stage. Not a bargaining outcome. |

## B. Treatment and mechanism links

### I — Challenger-specific information quality (*treatment*)

Coded **only from pre-decision inputs**. Coders working on *I* are blind to *B* error and *Y*: the ledger columns are hidden in the coding workbook (see §F).

| Component | High | Low | Evidence |
|---|---|---|---|
| Field-report coverage | Regular reports from the claimed territory before the decision | None, or only capital-based | Dated reports, report series |
| Informant network | Documented sources inside or near the challenger | None documented | Internal memos, later declassified files |
| Reporting latency | Events reach the capital within weeks | Months, or only through the press | Event date vs. report-receipt date |
| Corroboration | ≥2 independent channels on the same construct | Single channel | Cross-referenced files |
| Decision-maker receipt | Assessment is shown reaching the office that sets offers | No evidence of receipt | Routing slips, minutes |

Each component is coded `high/medium/low/unknown`. The ordinal summary is *I* = median of the non-unknown components, and it is only reported when ≥3 components are non-unknown. Otherwise *I* = `unknown`.

### B — Private incumbent assessment

- Must be **private and pre-decision** (audience = `private_internal` or `private_to_mediator`). Public rhetoric is never treated as *B*.
- Record the **exact quotation**, construct (`manpower`, `arms`, `territorial_reach`, `local_support`, `war_duration_cost`, `victory_odds`), date, author, and recipient.
- Military capability and local support are recorded in **separate rows**.

### [T^L, T^U] — Triangulated benchmark

- ≥2 independent contemporaneous sources on the **same pre-existing construct**. Sources can be third-party governments, NGOs, journalists, or the challenger's own internal records.
- Record each source's estimate and uncertainty. Interval = [min, max] across sources after mapping to the same ordinal scale, using a blind written mapping (`docs/ordinal_mapping.md`, to be written before coding).
- **Later military outcomes are never benchmarks.** One third-party estimate alone does not establish misperception.

### Belief error (directional)

`optimistic` only if *B* lies **outside** [T^L, T^U] on the government-favoring side. `calibrated_or_uncertain` if *B* lies inside the interval or the sources are not independent. Ordinal differences are **not** converted into probabilities.

### O — First offer

- `substantive_offer` requires **dated terms in the relevant issue space**, the offering authority, and implementability.
- `explicit_refusal` is a separate branch. It does **not** count toward the GO gate's 12 complete chains.
- `verified_no_offer` requires documented absence (e.g., minutes recording a decision not to engage). If a search finds no offer, the code is `unknown`.

### Acceptance threshold

Only `private_challenger_record` or `mediator_record` evidence establishes what the challenger would have accepted. If neither exists, the code is `rejected_reason_unknown`. A rejection alone never establishes insufficiency.

## C. Conditioning and rival constructs

| Symbol | Construct | Measurement | Timing caution |
|---|---|---|---|
| **K** | Locally deployable coercive capacity | Forces and logistics in or near the claimed territory **before** the offer; national military personnel kept as a separate proxy | Do not condition on troop deployments made *after* the threat was noticed (risk of mediator or collider bias) |
| **W** | Baseline weakness | Lagged log GDP per capita (anchor to F&L 2003), plus separate lagged extraction, administration, and statistical-information (ICI) measures | Report each separately. They are not synonyms. |
| **R** | Reputation concern | Count of other active or potential claimants in the state; private precedent statements | |
| **C** | Commitment problem | Documented expectation of a future power shift; unenforceable terms; guarantees offered or absent | |
| **Q** | Challenger strategy and structure | Fragmentation (Cunningham 2013), outside support, demand feasibility | |
| **S** | State-penetration shock | Dated expansions of state presence, rights changes, or extraction in the claimed territory | |
| **X** | Pre-treatment confounders | Exclusion and lost autonomy (Germann & Sambanis 2021), group size, terrain, prior conflict | |

## D. Five-stage state machine (Protocol App. B)

```
(1) claim ──► (2) awareness ∈ {aware, not_aware, unknown}
              │
              ▼
          (3) first response ∈ {substantive_offer, explicit_refusal, verified_no_offer, unknown}
              │                                     │
              ▼ (only if a decision was communicated) ▼
          (4) challenger ∈ {accepted, rejected, rejected_reason_unknown, unknown, not_applicable}
              │
              ▼
          (5) 24-month outcome ∈ {anti_state_violence, government_initiated_violence,
                                  verified_no_violence_24m, unknown, right_censored}
          (+) later UCDP threshold crossing / cessation, recorded separately
```

`unknown`, `not_observed`, `not_applicable`, `verified_no_offer`, a zero concession, and `right_censored` are **distinct** values and are never merged.

## E. Complete offer chain (GO-gate unit)

A dispute counts toward gate (ii) only if **all** of the following hold:

1. *I* ≠ unknown (≥3 dated pre-decision input components)
2. A private *B* dated before *O*
3. A benchmark interval from ≥2 independent contemporaneous sources on the same construct
4. stage3 = `substantive_offer` with dated terms
5. A dated challenger response (stage 4 ∈ {accepted, rejected})
6. acceptance_benchmark ≠ `none_credible`
7. stage5 ∈ {anti_state_violence, verified_no_violence_24m} with a date or documented 24-month follow-up

`src/gates.py` implements this rule exactly.

## F. Blinding and reliability

- Separate coding passes, in this order: (1) *I* inputs; (2) *B* and benchmark; (3) *O*, response, and *Y*. Coders in pass 1 do not see later columns.
- A blind second coder reviews every element with coder confidence `medium` or `low`. Disagreements are adjudicated in the ledger, and the original codes are retained.
- Revisions after Week 4 may correct **coding errors only**, never hypotheses.

## G. Pre-declared quantities (PI to fill before any outcome analysis)

| Quantity | Value | Set by | Date |
|---|---|---|---|
| δ\* (minimum meaningful 24-month risk difference) | _pending: requires full risk-set baseline rate_ | PI | |
| Required one-sided bound for NO | _pending_ | PI | |
| ICC assumptions (country, movement) for power | _pending_ | PI | |
