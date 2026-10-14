# Real-Data Results, Limitations, and Feasibility Assessment

*Run 2026-10-14 on the handoff release `weak-state-intelligence-handoff-2026-10-14` (ZIP SHA-256 `7b0e6cfd…ad5e1a8`; all 29 registered files also matched the handoff's inner `CHECKSUMS.sha256`). Reproduce with `make register ZIP=… DIR=…` then `make all`. Every number below comes from a committed output file named in brackets.*

> **Nothing in this report is causal evidence for the information mechanism.** The quantitative results describe who claims, who escalates, and how the public datasets fit together. Synthetic-fixture test passes check code behavior only. The weak/strong differences are national descriptive associations of exactly the kind the protocol says cannot identify private beliefs or offers.

## 1. What changed in the code, and why

| Problem found in the real files | Old behavior | Repair |
|---|---|---|
| Every one of the 464 SDM `groupid`s starts with up to 10 **inactive policy-lookback rows** (`active==0`, `violsd` missing) | First row treated as claim entry, so entry fell a **median of 10 years early** | Entry = first active year of each **phase** [`outputs/risk_set_audit.json`] |
| 36 movements have a **second phase** after a gap | Phases merged into one spell | Episode = movement × phase; phase 2 is its own `resumed_claim` population |
| 109 movements were active **before coverage** (`prioract` 1 = pre-1945, 18; 2 = colonial, 61; 3 = previous host, 30); a host change creates a **new `groupid`** with no predecessor link | Treated as new claims | `inherited_claim` population (left-truncated, with a prior-violence flag); kept out of the first-ever estimand |
| `violsd_onset` counts renewed onsets (217 onsets in 140 movements) | Any onset could be read as first violence | Only 54 onsets are first-ever violence in observed first claims; the rest are recurrence or inherited |
| 36 first claims are **violent in their claim year** | Silently entered the risk set | Separate `violent_in_claim_year` population (claim and violence cannot be ordered in annual data) |
| Annual data cannot place "24 months" | Single approximation | **Bounds**: lower = violence by t0+1 (certainly within 24 m); upper = by t0+2 (possibly within 24 m) |
| QoG `ccode` is ISO numeric, not COW; Germany 260/255 | Name/number guess | Join through `ccodecow` with one reviewed override (Germany from 1991); Kosovo and South Vietnam stay unmatched [`outputs/country_crosswalk_audit.csv`] |
| UCDP country onset file pads the header (`' conflict_ids'`) | Parse failure risk | Header-only whitespace strip |

Structural checks (gaps inside phases, end-date versus last active year, first violence not flagged as an SDM onset, `priorviol` in primary episodes) return **zero** flags on the real file.

## 2. Descriptive risk-set results [`ledgers/risk_set_flow.csv`, `outputs/cumulative_incidence.csv`]

**Populations (1945–2012, 500 episodes from 464 movements):**

| Population | Episodes |
|---|---|
| Primary first claims | 319 |
| Inherited claims | 109 |
| Violent in claim year | 36 |
| Resumed claims | 36 |

**Primary first claims, GDP-supported window 1961–2012:** 271 episodes in 88 countries.

| Outcome | Episodes |
|---|---|
| Escalated to first violence | 37 |
| Claim ended without violence | 65 |
| Host change | 15 |
| Right-censored at 2012 | 154 |

**24-month first-violence rate** (bounded, all primary 1961–2012): **3.3 % (lower) to 5.9 % (upper)**, from 9 and 16 events respectively. This is the full-risk-set baseline the PI needs to set δ\*. It is **not** taken from the outcome-balanced pilot.

**By baseline weakness** (lagged log WDI GDP per capita, median split among primary episodes):

| Stratum | Episodes | 24-m lower | 24-m upper | Cumulative violence at 20 years |
|---|---|---|---|---|
| Weak | 83 | 7.2 % | 12.0 % | 25.2 % |
| Strong | 83 | 0.0 % | 1.2 % | 4.9 % |
| Unknown GDP | 105 | 2.9 % | 4.8 % | 9.6 % |

**Sensitivity check.** Splitting on Maddison GDP instead, kept as a separate specification and never spliced, gives the same direction: 7.1–11.8 % (weak) versus 0–1.1 % (strong) [`outputs/risk_set_flow_maddison_sensitivity.csv`].

**Interpretation limits:**
- The counts are tiny: 10 versus 1 upper-bound events.
- GDP is missing **non-randomly** for 102 primary episodes; 64 of them are Soviet-era claims, because WDI has no USSR series [`risk_set_audit.json`].
- The stratum gap is the familiar national correlation. It says nothing about *where* in the chain weakness acts.

**Stages the public data cannot observe.** Government awareness, first offers or refusals, and claimant replies are reported as `NA` with reasons, never as zero. SDM `con`/`accomm` record enacted policy for the 106-movement random sample (68 primary episodes). They are not first rejected offers.

## 3. UCDP reconciliation [`outputs/ucdp_reconciliation_*.csv`, `…_summary.json`]

| Check | Result | Status |
|---|---|---|
| A. Onset 25.1 conflict-level `newconf` vs ACD 25.1 first intrastate year | 230/230 agree | resolved |
| B. ACD 25.1 vs ACD 26.1 first intrastate year | 229 agree; conflict 16379 (Jubaland, 2024) present in 25.1 and **absent in 26.1** | vintage revision; **unresolved**, needs UCDP release-note check |
| C. Onset 25.1 **country-level** `newconf` vs ACD-derived new-conflict country-years | 147 agree; 159 onset-file-only; 64 ACD-only | Explained, but a **documentation discrepancy remains** (see below) |

The C result breaks down as follows:
- In the country file, `newconf` equals `onset1` in **every** row (12,606 rows). It therefore flags every restart after one peace year, not only new conflicts, contrary to the codebook wording.
- All 64 ACD-only rows are new conflict IDs that start while another conflict was ongoing in the prior year. Version 2 excludes these by design.

Rule adopted: use the conflict-level file for "new conflict", and never read country-file `newconf` as a first-ever onset.

**SDM ↔ UCDP links** [`outputs/sdm_ucdp_link_candidates.csv`, all `unreviewed`]. SDM stores old-style UCDP IDs. **26 of 91** movement links carry IDs corrupted by spreadsheet date conversion (e.g. Mizos `Jan 99`, Iranian Kurds `01. Jun`, Latvians `01. Dez`). Matching on territory produces 130 candidate rows for the 91 links. 85 rows match territory plus country. 40 rows (from 11 links) match the territory name in a different country, e.g. Kurdistan, Nagaland in Myanmar, and 28 spurious "Islamic State" rows. Five links have no territory match: Western Sahara (Morocco, Mauritania), Chechnya, Kukiland, and Ogaden/Bale. None of these links has been accepted into `movement_actor_crosswalk.csv`.

## 4. Within-country pilot and identification evidence [`docs/07_within_country_pilot.md`, `ledgers/pilot_candidate_frame.csv`, `ledgers/archive_leads.csv`]

The pilot frames list every SDM claimant in each frame before outcome narratives are read:
- **India, north-east, 1960–72:** Mizo (positive, 1966) against Meghalaya/APHLC (claim ended 1972 without violence), plus Kuki, Bodo and Mikir negatives under the same cabinet.
- Secondary frames: Pakistan 1971–77, UK 1966–72, Philippines 1966–72.

**State of the dated chain:** no episode yet has a coded private pre-offer strength estimate together with an independent benchmark. The archive hosts could not be reached from this environment, so no document text was re-verified here; two attempts are logged as `environment_blocked`.

The evidence that is verified (by the handoff preparer) points two ways:
- The 8 Nov 1962 Shastri→Chaliha letter documents an **information deficit and a force deficit together** for the Mizo District.
- The peaceful APHLC record shows **caution under uncertainty** ("wait and gauge strength") and an explicit **commitment** concern in 1963.

Both are as consistent with the rival accounts as with the information account.

**Comparison with the rival accounts as the evidence now stands:**

| Account | Evidence for | Evidence against | What would discriminate |
|---|---|---|---|
| Information error (optimistic B → low O) | Government admits it lacked an intelligence system on the Mizo District (1962) | No optimistic private estimate found; the peaceful comparator shows caution, not overconfidence | 1965 CMS files with a dated MNF strength estimate, plus an independent benchmark |
| Weak local coercion (K) | "No troops" in the Mizo District (1962); national proxies equal across claimants, so the local K difference is the live margin | Same letter shows awareness, so not pure ignorance | Deployment records by district at decision dates |
| Reputation (R) | Concurrent Naga insurgency is a plausible precedent concern | No private precedent statement found yet | Private minutes citing the Naga or other claimants |
| Commitment (C) | APHLC 1963 concern over the lack of constitutional guarantees | Peaceful outcome after statehood suggests credible guarantees mattered | Whether the MNF ever received a comparable guaranteed offer |

**National-proxy positivity screen** [`outputs/provisional_strata_support.csv`; Hanson–Sigman `infcap` × `milpercap`, primary 1961–2012]: escalations in the high-information stratum number **0** (with high force) and **1** (with low force). This uses national administrative proxies, which are the wrong construct, but it already warns that "high information, escalating" cells will be thin in any draw.

**Precision illustration** (not a δ\* choice; `src/power_sim.py`, baseline 5.9 %, ICC 0.1, 3 episodes per country):
- If **all** ~270 primary episodes were fully coded: P(YES | true Δ = 0.10, δ\* = 0.05) ≈ 0.26 and P(NO | Δ = 0) ≈ 0.39.
- Adequate precision needs either δ\* ≈ 0.10 with true Δ ≈ 0.20, or roughly 900 episodes.

A population-scale causal estimate of the information channel is therefore unattainable from the SDM claimant universe at modest effects, even with perfect archives.

## 5. Feasibility assessment

**Answer: STILL PENDING. It is not GO, and NO-GO cannot be declared yet.**

| Gate | Status | Basis |
|---|---|---|
| (i) Previolence denominator with non-escalating disputes | **PASS** | 271 primary first-claim episodes, 37 escalated, 234 non-escalated or censored (1961–2012) |
| (ii) ≥12 complete chains (≥4 escalated, ≥4 not, ≥4 countries) | NOT EVALUATED: **0** coded chains | No private assessment or benchmark yet; archives not read |
| (iii) Information × force overlap at comparable threat | NOT EVALUATED | National proxies are the wrong construct and show thin high-information escalation cells |
| (iv) Archive-availability ledger and selection bounds | NOT EVALUATED | Search plan exists; only two blocked attempts logged |
| (v) Power and collection plan with a fixed δ\* | NOT EVALUATED | Baseline now known (3.3–5.9 %); δ\* is the PI's decision |

**What would turn this into a decision:**
- **NO-GO for the strong information mechanism** if the India stop rule fails, i.e. no dated private estimate plus benchmark plus first offer plus local-force record for **both** the Mizo and APHLC episodes by week 6. A NO-GO from access failure is not a substantive refutation.
- **Archive-level GO** only if both chains are complete and a second frame (Philippines or Pakistan) yields at least one more comparable pair.
- Even then, the realistic product is **process-tracing evidence across a few matched episodes**, not a population share of the weak-state gradient. Gate (v) will fail for any modest δ\* (see §4).

**Narrower studies that remain possible now:**
1. A stage-accounting paper on the SDM claimant universe, with corrected first-claim, inherited and recurrence populations and bounded 24-month outcomes.
2. A documentation of SDM/UCDP linkage and vintage problems.
3. A historical case study of north-east India bargaining that adjudicates information, local coercion, reputation and commitment, whatever the information verdict turns out to be.

## 6. Unresolved items

1. Jubaland (UCDP 16379) dropped between ACD 25.1 and 26.1: check the UCDP release notes.
2. The UCDP 25.1 country-onset `newconf` definition contradicts the codebook text: query UCDP or keep the conflict-level file.
3. 130 SDM–UCDP candidate rows (91 links) await human review; 26 corrupted SDM IDs should be reported to the SDM authors.
4. Non-random GDP missingness (USSR) in the primary frame.
5. SRDP lacks organizations for APHLC, Mikir, Kuki and 1970s Baloch claimants. These organizational records must come from archives.
6. MSDD (1991–2015) is registered but not used: it cannot inform the 1960s pilot, and mediation presence is not an offer.
7. The Beardsley et al. (2017) p. 677 pin cite remains unverified. Fearon (2010) is corrected to pp. 41–42.
8. **PI decisions:** δ\*; the local-coercion measure; attestations for gates (iii)–(v); sign-off on the pilot frames and search terms.
