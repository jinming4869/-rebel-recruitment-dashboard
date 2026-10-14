# Amendment log

Any change to sampling rules, coding rules, column maps, or gate criteria after the Week 1 freeze is logged here **before** it takes effect: date, author, what changed, why, and whether any outcome data had been seen.

| Date | Author | Change | Reason | Outcomes seen? |
|---|---|---|---|---|
| 2026-10-14 | Claude (RA) | Risk-set unit changed from movement ID to movement x phase; entry = first active year of a phase; populations primary_first_claim / violent_in_claim_year / inherited_claim / resumed_claim; 24-month outcome reported as lower/upper bounds. | Real SDM audit: inactive lookback rows, two-phase movements, prior activity and host-change successors, recurrent onsets (docs/08_findings_report.md section 1). Correction of construction errors, not a hypothesis change. | Yes: SDM violence years were visible while the code was audited. No information, belief, or offer outcomes exist yet. |
| 2026-10-14 | Claude (RA) | Pilot moved from a 24-dispute global random draw to structured within-country frames (config/pilot_frames.json), listing ALL claimants per country-period; global draw code kept but not run. | Handoff WITHIN_COUNTRY_DESIGN.md sets government x claimant episodes as the primary unit; national-proxy strata show near-empty high-information escalation cells. | SDM outcome years are listed in the frame (they define the escalated/non-escalated contrast); no archival content has been read. PI must sign off. |
| 2026-10-14 | Claude (RA) | Country join SDM ccode -> QoG ccodecow with one reviewed override (Germany 260 -> 255 from 1991). | QoG ccode is ISO numeric. | No |
