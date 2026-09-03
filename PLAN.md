# Rebel Recruitment Dashboard Plan

## Purpose

Provide a desktop research workbench that explains recruitment as a linked process rather than as a list of datasets or paper replications:

`Recruitment Pool → Exposure → Organizational Demand → Recruitment Repertoire → Selection / Screening → Incorporation → Violence / Behavior`

Each stage answers one bounded question. Recruitability is not a separate stage; organizational capacity, territorial control, civilian relations, external support, conflict intensity, state repression, and host-state context are conditions shaping the full process rather than additional linear stages.

## Delivered surfaces

- Individual-level H&W comparisons across entry, faction composition, and RUF abduction/volunteering margins, using `pWEIGHT` and survey-location bootstrap intervals.
- Beber–Blattman age-response small multiples for capture, release, weapons, threats, indoctrination, safety, and loyalty.
- A repertoire layer combining H&W money/safety/ties, Beber–Blattman coercive incorporation, RAID appeals, CROAD adult coercion, and RHRV reporting without joining people across cases.
- Lightweight demand and screening stages that expose the archive's current measurement gaps rather than relabeling capacity or observed recruit composition as direct evidence.
- Version-labeled exact-ID candidate registry plus tracked approvals; downstream cross-source profiles, networks, bridges, and ecology surfaces are restricted to the three approved descriptive anchors.
- FARC default profile; RUF/LRA case bridges; a non-state-recipient external-support network and country-year context explorer; CROAD × RAID and CROAD × RHRV bridges kept as separate descriptive overlap surfaces.
- Comparative state military-labor boundary views (MLAD, M³, Abramson–Qiu), an evidence coverage lens, disk-backed notes, and aggregate CSV exports.

## Non-negotiable interpretation rules

- The browser receives aggregates only: no respondent, event, or narrative rows.
- Stable RAID attributes never become annual switching claims.
- RHRV `unreported` is not behavioral absence.
- Conscription is not treated as abduction, and recruitment is not reduced to a voluntary/forced binary.
- Cross-source joins require tracked approval in addition to a version-labeled numeric-ID candidate; no silent fuzzy match.
- Matrices are descriptive Spearman/φ associations with cluster-aware bootstrap intervals, not causal estimates.
- Every analytical chart card exports its currently displayed browser-safe aggregate CSV; the four home-page thumbnails are navigation summaries rather than independent analytical cards.
- The interface intentionally has no mobile mode; it is a minimum-1180px desktop workbench and works under both `file://` and local HTTP.

## Verification

`python3 dashboard/validate_dashboard.py` verifies payload schema, H&W fixed counts, CROAD 390-dyad / 1,709-dyad-year baselines, FARC/RUF/LRA IDs, audited overlap baselines, aggregate-only constraints, all 59 archived files, and required dashboard surfaces. Browser QA verifies filters, case synchronization, network/profile links, map selection, note filtering, exports, and console cleanliness.
