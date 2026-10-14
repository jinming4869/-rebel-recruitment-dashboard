# Within-Country Pilot: Comparable Episodes, Archive Leads, Evidence Plan

*Drafted 2026-10-14 from the real SDM/SRDP files and the handoff's `WITHIN_COUNTRY_DESIGN.md` and `ARCHIVAL_LEADS.md`. Machine-readable companions: `ledgers/pilot_candidate_frame.csv` (every claimant in each frame, from `src/build_pilot_frame.py`), `ledgers/archive_leads.csv`, `ledgers/archival_search_log.csv`.*

> **Evidence labels used below.** **[SDM]** / **[SRDP]**: read from the registered data files. **[H-verified]**: the handoff preparer read the document text; this environment could not reopen it, because the archive hosts are blocked from the cloud build environment (logged as `environment_blocked`, not as an archive refusal). **[catalog]**: only the document's existence or title is known. **[sec-lit, verify]**: a date or fact from secondary historical literature that has not been checked against a primary source. It must be verified before coding.

## 1. Unit and outcome

The unit is a **government × named claimant organization × decision episode**. The episode opens at a dated demand or credible threat. It includes the government's earliest identifiable substantive offer, or its documented refusal. It closes at acceptance, peaceful continuation, first organized anti-state violence, or right-censoring. Central and state-level principals are recorded separately. Districts are nested evidence on information, deployment and violence; one national offer covering several districts counts as **one** decision.

The primary outcome is **first-ever** organized violence. Claims inherited from the colonial era (`inherited_claim`) and recurrence (`resumed_claim`, or episodes with earlier violence) are separate populations (see `src/build_risk_set.py`).

## 2. Primary pilot: India, Assam hill movements, 1960–1972

All SDM claimants active in the window and region, listed **before** reading outcome narratives (`pilot_candidate_frame.csv`):

| SDM movement | Population [SDM] | Window outcome [SDM] | Named organizations [SRDP, name-matched, unreviewed] | Design role |
|---|---|---|---|---|
| Mizos | primary_first_claim (claim 1947) | **first violence 1966** | Mizo National Front 1962–77 (state violence 1966); Mizo Union 1960–73 | **Positive** episode (MNF); within-movement contrast with the Mizo Union |
| Meghalayans (APHLC) | primary_first_claim (claim 1947) | **claim ended 1972 without violence** | *none in SRDP* | **Negative** comparator: bargaining under the same cabinet, ending in accommodation |
| Kuki | primary_first_claim (claim 1960) | no violence in window (first 1997) | *none in SRDP* | Negative comparator (thin records expected) |
| Bodos | primary_first_claim (claim 1967) | no violence in window (first 1989) | Bodo Sahitya Sabha 1973– | Negative comparator; late entry |
| Mikirs (Karbi) | inherited_claim (claim 1946) | no violence through 2012 | *none in SRDP* | Negative comparator; handoff lists a 1965 Mikir Hills file [catalog] |
| Tripuris | inherited_claim | first violence 1967 | (Tripura Upajati Juba Samiti from 1968) | Secondary positive; different principal (union territory) |
| Manipuri | inherited_claim | no violence in window (first 1978) | — | Context |
| Nagas | inherited_claim, **violent since 1952** | recurrence population | Naga National Council, etc. | **Excluded** from the first-onset comparison; the main source of a **reputation (R)** rival for Delhi's north-east policy |

**Why this frame.** One central cabinet and one state government (Assam) faced several hill claimants at the same time. Escalated and non-escalated episodes therefore share the national principal, the period, and the broad capacity environment. National proxies are identical across the claimants [Hanson–Sigman: milpercap 0.783, infcap 0.524 in 1960]. So any difference has to come from **claimant-specific** information, local force, demands, or rival mechanisms. That is the comparison the protocol needs and the cross-country data cannot supply.

**Known threats to comparability:**
- **Overlapping people:** APHLC and MNF may overlap through individual leaders (L. H. Lalmawia appears among the APHLC delegates in the 1963 minutes [H-verified]). Treating them as independent would be wrong.
- **Turnover:** prime-ministerial changes in 1964 and 1966 [sec-lit, verify] are a within-window confounder.
- **Different demands:** the MNF sought independence, while the APHLC sought a hill state within India [sec-lit, verify; SDM `claim` is coded only for sampled movements].
- **External support** (East Pakistan) for the MNF [sec-lit, verify].
- **A local shock:** the 1959–60 *mautam* famine in the Mizo district [sec-lit, verify] is both a grievance and a possible information shock.

### Dated chain to reconstruct, and what is already in hand

| Link | Mizo / MNF (positive) | APHLC / Meghalaya (negative) | Mikir, Kuki (negatives) |
|---|---|---|---|
| Claim / threat date | MNF formed 1961 [sec-lit, verify; SRDP first year 1962]; memorandum demanding independence 1965 [sec-lit, verify] | APHLC hill-state demand 1960 [sec-lit, verify]; active in 1962 [H-verified L01] | **to collect** |
| Information inputs (I) | Shastri→Chaliha, 8 Nov 1962: no troops in the Mizo District; need to **build** an intelligence system [H-verified L03]; 1965 CMS 171/1965 MNF file and CMS 132/65 Special Police Report [catalog L05] | Governor's letter recommends waiting to gauge APHLC strength [H-verified L01] | Mikir Hills file 1965 [catalog L05]; NAI search [L07] |
| Private assessment (B) | **Not yet found.** 1965 CMS files are the best lead | Governor's caution [L01] is a recommendation under uncertainty, not a strength estimate | **to collect** |
| Independent pre-offer benchmark | **Not yet found** (press, church, diplomatic sources; L08) | **to collect** | **to collect** |
| First substantive offer or refusal (O) | Autonomy and language measures mooted in the Nov 1962 letter [H-verified L03]; whether any offer reached the MNF is unknown | 3 May 1962 refusal of a separate state plus alternatives [H-verified L02]; 4 Oct 1963 autonomy proposal [H-verified L04] | **to collect** |
| Claimant response | **to collect** | Concern that informal assurances lacked constitutional guarantee [H-verified L04] (**commitment** signal) | **to collect** |
| Outcome | First violence 1966 [SDM; SRDP]; uprising Feb–Mar 1966 [sec-lit, verify] | No violence; claim ended 1972 [SDM]; Meghalaya statehood 1970/72 [sec-lit, verify] | No violence in window [SDM] |
| Local force (K) | "No troops" in the Mizo District, Nov 1962 [H-verified L03]: **K and I deficits are documented together** | **to collect** | **to collect** |
| Reputation (R) / commitment (C) | Naga precedent (Nagaland statehood 1963 [sec-lit, verify]) is the obvious R channel; search for private precedent talk | Commitment concern explicit in 1963 [L04] | — |

**What the verified material already implies.** The only verified private MNF-related text shows an information deficit and a force deficit **in the same letter**. The peaceful comparator's records show **caution under uncertainty**: wait and gauge strength. Neither is evidence of the signed, optimistic error that the strong hypothesis needs. The India case is an archive test, not a confirmed positive case.

## 3. Secondary frames

| Frame | Claimants [SDM] | Usable for | Hard limits |
|---|---|---|---|
| **Pakistan 1971–77** | Baluchis (inherited; first violence 1973 under Pakistan), Pashtuns (inherited; violent since 1960, so recurrence), Sindhis and Saraikis (primary; no violence), Bengalis (1971, separate war) | Reputation probe: one federal executive, two NAP-led provincial governments, divergent violence | No Baluch organization in SRDP before 1980. The National Awami Party is coded only under the Pashtuns, so one organization spans both claims. US records [L09, L10] are third-party. The documented June 1973 offer comes **after** onset. Neither Baluch nor Pashtun is a first-claim episode. |
| **UK 1966–72** | NI Catholics (primary; claim 1948, first violence 1969), Scots and Welsh (inherited, never violent) | Hard negative and measurement test of the "ignorance" account [L11, L12] | Strong state, so it cannot estimate a weak-state effect. London and Stormont are distinct principals. Scotland and Wales are poor matches. SRDP group "Catholics" was not auto-matched to SDM (names differ). |
| **Philippines 1966–72** | Moros (primary; claim 1968, first violence 1970) | Candidate second positive with a short claim-to-violence interval; MIM 1968–70 → MNLF 1970 [SRDP] | Archive availability unknown [L13]. The 2008 MOA-AD [L14] is a veto/commitment check inside an ongoing war, not an onset case. |

## 4. Evidence-collection plan (4–6 weeks of archival reconnaissance)

1. **Freeze before reading.** Commit `pilot_candidate_frame.csv` and the search terms. Use the same terms and repositories for escalated and peaceful claimants (Mizo, APHLC, Mikir, Kuki): claimant and organization names, district names, "intelligence", "special police", "autonomy", "hill state", for 1960–1967.
2. **Log every search** in `archival_search_log.csv`, including empty results, refusals and exemptions under the Public Records Act 1993 and security-agency rules. Survival of records in peaceful versus violent episodes is an explicit output (gate iv).
3. **Repositories, in order:**
   - Assam State Archives, CM Secretariat files CMS 171/1965, 132/65 and the Mikir Hills file [L05];
   - NAI Abhilekh Patal, MHA SR(R) series [L07];
   - Nehru Archive correspondence around L01–L04;
   - Rajya Sabha / Lok Sabha debates [L06] (public statements only);
   - independent benchmarks: regional press, church and missionary archives, UK and US diplomatic reporting [L08].
4. **Code in three blind passes** (`docs/02_construct_dictionary.md` §F):
   - Pass 1: information inputs only.
   - Pass 2: private belief and benchmark, mapped with `docs/ordinal_mapping.md` written in advance.
   - Pass 3: offer, response, outcome, and the rival flags K, R and C.
   - A second coder reviews every medium- or low-confidence code.
5. **Code peaceful episodes with equal effort.** An APHLC chain that is as complete as the MNF chain is required. Without it, the comparison collapses into a single case study.
6. **Within-episode test.** Look for a documented report arrival that revised beliefs and then offers, while local forces, demands and guarantees stayed approximately fixed. Use another claimant under the same cabinet whose estimate did not change as a negative control.

## 5. Stop rule (decides the archival identification gate)

By the end of week 6, the pilot must deliver **for at least the Mizo and APHLC episodes**:
- (a) a dated pre-offer private threat assessment;
- (b) an independent pre-offer benchmark on the same construct;
- (c) a concrete first offer or a documented refusal, with terms;
- (d) local-force evidence at the decision date;
- (e) a rival-mechanism memo (`docs/04_rival_mechanism_matrix.md`) with evidence both for and against information error.

If (a)–(d) cannot be obtained for **both** an escalated and a non-escalated episode, the answer to "can the strong misperception mechanism be directly tested here?" is **NO** for this frame. The project then falls back to the narrower outputs listed in `docs/08_findings_report.md` §5.
