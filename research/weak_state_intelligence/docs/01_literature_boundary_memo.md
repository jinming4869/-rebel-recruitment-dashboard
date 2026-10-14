# Literature Boundary Memo (Week 1 deliverable)

*Protocol v1.0 (SHA-256 `0e3a3155…cfd2ad`, archived as `docs/00_protocol_v1.0.md`) · drafted 2026-10-14 · status: DRAFT for PI sign-off*

> **Verification status.** Every citation below is from the protocol's own reference list (Appendix C). Page-level pin cites carried over from the protocol (Fearon 2010 pp. 40–42; Beardsley et al. 2017 p. 677) **have not yet been re-checked against the PDFs**, because this work environment cannot reach the publisher or DOI hosts. They are flagged `verify_pin = TRUE` in `ledgers/source_registry.csv`. No claim in this memo should be repeated in the decision memo until its registry row reads `verified`.

## 1. What this project claims, and what it does not

**Claim under test (the "information–offer" mechanism).** Among organized challengers observed *before* any armed action, a chronically weak incumbent's poor *challenger-specific* information inputs lead to (i) a directionally **optimistic** private assessment of relative strength or support, which leads to (ii) a first feasible offer **below** the challenger's contemporaneous acceptance threshold (or no offer at all), which leads to (iii) rejection and first organized violence within 24 months. The effect must hold net of local coercive capacity, reputation, commitment, rebel strategy, and state-penetration shocks.

**Not claimed as new:**
1. That weak states face more civil war (Fearon & Laitin 2003).
2. That incomplete information can cause bargaining failure in civil conflict (Fearon 2010; Beardsley et al. 2017).
3. That claim formation and escalation are separate stages (Bartusevičius & Gleditsch 2019; Germann & Sambanis 2021).

**The contribution, if any,** is (a) *direct, dated measurement* of the input → belief → offer → response chain, and (b) *adjudication* of that chain against named rival mechanisms in a denominator that includes disputes that never became violent. A well-measured null is a full answer.

## 2. Boundary map

| # | Work | What it already establishes | Where it stops (our margin) | Implication for design |
|---|------|-----------------------------|-----------------------------|------------------------|
| 1 | **Fearon & Laitin (2003)**, APSR 97(1) | Low income per capita predicts onset. It is read partly as a proxy for weak capacity to deter or defeat insurgency, including poor local information for counterinsurgency. | Information enters as a *counterinsurgency* input after rebellion starts. It is not a measured *prewar estimate* that sets a settlement offer. Uses a country-year design, so it cannot time within-country escalation. | Use lagged log GDP per capita as the **baseline-weakness** anchor so results connect to F&L. Never treat GDP as the information treatment. |
| 2 | **Fearon (2010)**, WDR background paper (pp. 40–42 per protocol, *pin unverified*) | Asks directly why governments facing strong opposition don't adjust their terms. Proposes incomplete information, commitment problems, and opposition error. | Verbal and theoretical only. It does not show that weak incumbents err in a *specific direction* or measure offers. | Our H1 (directional optimism) and H2 (offer transmission) are the testable form of this conjecture. Commitment and rebel error become explicit rivals. |
| 3 | **Beardsley, Cunningham & White (2017)**, BJPolS (p. 677 per protocol, *pin unverified*) | Suggests that an incumbent who underestimates conflict costs may offer too little. Tests UNSC conflict-prevention attention in self-determination disputes. | The outcome-level test is about *intervention*. Belief → offer → response is never observed. | The information mechanism cannot be claimed as novel; cite this as precedent. UNSC/mediator arrival is a candidate *process* observation, **not** an instrument, because it also changes pressure and guarantees. |
| 4 | **Cunningham (2013)**, AJPS | Opposition fragmentation creates uncertainty about which concession will suffice, raising conflict risk. | The uncertainty sits on the challenger side (who must be satisfied?), not in the incumbent's estimate of strength. | Code **fragmentation** (number of factions, rival claimants) as a confounder of offer adequacy. It is part of `Q` / challenger structure in the DAG. |
| 5 | **Bartusevičius & Gleditsch (2019)**, IO 73(1) | Two-stage model: contested incompatibility, then armed violence. Predictors differ by stage. | The second stage is not opened up into the beliefs and offers of the bargaining interaction. | Stage-splitting alone is **not** novel. Our stage accounting (claim → awareness → offer → violence → UCDP threshold) is descriptive infrastructure, not the contribution. |
| 6 | **Germann & Sambanis (2021)**, IO 75(1) | Within SDMs, political exclusion and lost autonomy predict *escalation* conditional on a claim. | Grievance and status mechanisms, not information. | Exclusion and lost autonomy are **pre-treatment confounders**. Lost autonomy also falls under the state-penetration rival (`S`). |
| 7 | **Walter (2006)**, AJPS | Governments facing many potential separatists refuse concessions to build a reputation. | The refusal is *deliberate and informed*, not a belief error. | **Reputation rival:** look for private discussion of a feasible deal rejected because of precedent. Count other potential claimants in the same state. |
| 8 | **Walter (2007)**, APSA-CP newsletter | Links state weakness to violence through reputation and commitment problems. | Offers a weak-state pathway that runs *without* misinformation. | Shows that "weak state → war" has non-information channels inside the same paradigm. These must be tested head to head. |
| 9 | **Grigoryan (2015)**, IS 39(4) | Concessions can strengthen future separatism, so governments may coerce instead. | A future power shift (commitment) explains nonconcession under accurate beliefs. | **Commitment rival:** record any documented expectation that a concession empowers the challenger. |
| 10 | **Thomas, Reed & Wolford (2016)**, IO 70(3) | Rebels may make deliberately infeasible demands to provoke rejection or signal resolve. | Escalation is *challenger-driven*. | **Rebel-strategy rival:** acceptance thresholds must come from private or mediator evidence, **never** inferred from rejection. |
| 11 | **Malone & Spaniel (2021)**, R&P 8(1) | Theory: under some kinds of uncertainty, higher stakes can induce *safer* (more generous) proposer offers. | A theoretical counterexample, not evidence about weak civil-war governments. | **Cautious-offers rival:** wide internal uncertainty can lead to *generous* or delayed offers. Low precision alone predicts no direction. |
| 12 | **Ying (2021)**, JCR 65(2–3) | Expanding state presence and penetration can provoke local conflict. | Explains violence after a capacity *shock*, not under chronic weakness. | **State-penetration rival (`S`):** date state-expansion events and exclude or stratify episodes where mobilization follows them. |
| 13 | **Lewis & Rangazas (2026)**, PoP 24(S1) | Peripheral rebellions can grow from criminal or bandit groups that are invisible before overt violence. | Shows our SDM frame **misses** some onset pathways. | Scope restriction: results apply to the *explicit self-determination claim pathway*. They do not cover all civil-war origins. |
| 14 | **Malone (2022)**, ISQ 66(3) | Armed-group organizational data. | Starts *after* an armed group forms. | Cannot serve as a previolence denominator. Use for linkage only. |
| 15 | **Brambor et al. (2020)**, CPS | Information Capacity Index built from census, civil registration and statistics. | A *national administrative* measure, not intelligence about a named challenger. | Usable only as a **stratifier** for the pilot draw and as an upstream predictor, after validation against archival input quality. |
| 16 | **Sambanis, Germann & Schädel (2018)**, JCR 62(3) | SDM universe 1945–2012, most never violent. Government-response detail exists only for a **random subsample**. | Coded accommodations are not first *rejected offers*. | The risk-set denominator. Response variables must be **weighted** by the subsample design. |
| 17 | **Cunningham et al. (2025)**, JPR 62 (SRDP update) | Organization-year tactics and demands, 1960–2020. | Organizations sit inside a narrower movement universe. | Auxiliary **timing** source only, never a denominator. |

## 3. Head-to-head discriminating observations

Every pilot trace must code the following evidence. It is reproduced in `docs/04_rival_mechanism_matrix.md`.

| Mechanism | Belief state | Offer state | What would favor it over the information mechanism |
|-----------|--------------|-------------|------------------------------------------------------|
| **Information (favored)** | Optimistic, outside the benchmark interval | Below the acceptance threshold | Corrections that revise beliefs, then offers, *before* K/R/C/Q/S change |
| Military incapacity (K) | Calibrated | Realistic | Accurate assessment, but unable to deploy or enforce locally |
| Reputation (R) | Calibrated | Deliberately low | Private records of precedent concerns. No revision after an information gain. |
| Commitment (C) | Calibrated | Low or none | Documented expectation of a future power shift or unenforceable deal. Guarantees change behavior. |
| Rebel strategy (Q) | Calibrated | Feasible | Challenger's minimum lies above any feasible offer (private or mediator evidence) |
| Cautious offers | Wide uncertainty | Generous or delayed | Low precision **without** optimism; generous first offer |
| State penetration (S) | Any | Any | Mobilization timed to state expansion; no prior comparable challenger |

## 4. Gaps this memo cannot close

1. **The smallest effect that would matter (δ\*) is not set here.** The protocol (App. A) assigns it to the PI, using the *full risk-set* baseline 24-month escalation rate. That rate is not yet computed (blocked on data access; see `README.md`). `src/power_sim.py` takes δ\* as an input and never chooses it.
2. **No verified instrument.** Elections, censuses, roads and mediators are *process observations only*.
3. **The construct of "challenger-specific information quality" has no off-the-shelf dataset.** It exists only through archival coding (`docs/02_construct_dictionary.md`, §I).

## 5. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Research assistant | | | |
| Principal investigator | | | |

Sampling and coding rules are frozen when **both** rows are signed. No pilot outcomes may be inspected before that.
