# Recruitment Data Dashboard

`dashboard/index.html` is the primary interactive surface for the project. It opens directly through `file://` and also works when the repository is served locally.

## What it shows

- Recruitment Pool, Exposure, Organizational Demand, Recruitment Repertoire, Selection / Screening, Incorporation, and Violence / Behavior, with organizational and conflict/host-state conditions shown outside the linear stage sequence;
- aggregate H&W and SWAY microdata views that preserve their native risk sets and survey limitations;
- CROAD, RAID, RHRV, NSA, ESD, RQSI, RIG, UCDP, GDIS, M3, MLAD, and historical-biography derivatives with registered denominators and missing rules;
- a version-aware actor-candidate desk in which 382 exact integer overlaps remain review-only, while all seven cross-source surfaces accept only three tracked approvals and suppress undersupported ecology estimates;
- situated FARC, RUF, and LRA qualitative dossiers with nine locally stored objects, file-level Commons provenance, credits, licenses, sensitivity notes, and explicit interpretive limits;
- all 20 catalog records and their observed/documented geographic and temporal coverage.

English remains the main working language. Chinese subtitles and short warnings are used at high-value interpretive points rather than duplicating the entire interface.

The ranking bars and space-time points link directly to the selected source's world map. The charts compare archival coverage only; they do not add rows across incompatible units or estimate a recruitment-intensity index.

No respondent records, narrative report excerpts, or conflict-event rows are embedded in the browser payload.

## Rebuild

From the repository root:

```bash
make dashboard
make dashboard-check
```

`build_dashboard.py` reads canonical JSON and 22 registered analytical inputs directly from verified source containers or archive members. It writes `data/dashboard-data.js`. `validate_dashboard.py` reconciles all 20 catalog records, frozen baselines, version-aware actor status, nine qualitative objects, and the aggregate-only browser boundary.

Run `make data-qa` to validate the raw schema contracts, missing-data policy, derived measurements, entity decisions, 16 dataset audits, and media licenses/hashes before the dashboard build.

The world topology and local JavaScript libraries are preserved under `dashboard/data/` and `dashboard/vendor/`, so the dashboard does not depend on a CDN.
