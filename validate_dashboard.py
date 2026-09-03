#!/usr/bin/env python3
"""Static, schema, and fixed-baseline checks for the recruitment workbench."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_keys(item: dict, keys: set[str], label: str) -> None:
    require(keys <= set(item), f"{label} missing keys: {sorted(keys-set(item))}")


datasets = json.loads((ROOT / "content" / "datasets.json").read_text(encoding="utf-8"))
payload_text = (ROOT / "dashboard" / "data" / "dashboard-data.js").read_text(encoding="utf-8")
prefix = "window.RECRUITMENT_DASHBOARD = "
require(payload_text.startswith(prefix), "dashboard payload prefix is missing")
payload = json.loads(payload_text[len(prefix):].strip().rstrip(";"))

TOP = {"meta", "coverage", "micro", "repertoire", "crosswalk", "ecology", "actorProfiles", "supportNetwork", "context", "boundaries", "qualitative", "notes"}
require_keys(payload, TOP, "payload")
require_keys(payload["coverage"], {"summary", "catalog"}, "coverage")
catalog, summary = payload["coverage"]["catalog"], payload["coverage"]["summary"]
source_ids, payload_ids = {item["id"] for item in datasets}, {item["id"] for item in catalog}
require(source_ids == payload_ids, f"catalog mismatch: source-only={source_ids-payload_ids}, payload-only={payload_ids-source_ids}")
require(len(catalog) == 20, "dashboard must expose all 20 catalog records")
require(summary["localData"] == 16, "expected 16 locally acquired releases after CROAD acquisition")
require(summary["principalFiles"] == 59, "expected 59 verified principal files after CROAD acquisition")
require((summary["earliest"], summary["latest"]) == (1800, 2025), "unexpected evidence timeline")
local = [item for item in catalog if item["accessClass"] == "local-data"]
require(all(item["fileCount"] > 0 for item in local), "local data record without an archived file")

hw = payload["micro"]["hw"]["sample"]
require((hw["rows"], hw["excombatants"], hw["comparison"], hw["rufAbductees"], hw["rufVolunteers"]) == (1227, 1043, 184, 330, 46), "H&W sample baseline changed")
actors = {item["actorId"]: item for item in payload["actorProfiles"]}
for actor_id, name in [(743, "FARC"), (532, "RUF"), (488, "LRA")]:
    require(actor_id in actors and actors[actor_id]["name"] == name, f"actor profile baseline missing: {name}")
audit = payload["crosswalk"]["audit"]
require(audit == {
    "method": "Versioned numeric-ID equality generates descriptive candidates only; approval requires a tracked review decision. Aliases never create silent joins.",
    "croadRaidActors": 224, "croadRhrvActors": 319,
    "raidNsaDyads": 232, "raidRhrvActors": 224, "raidEsdActors": 232,
    "rqsiRigActors": 167, "rhrvEsdActorYears": 1323,
}, "crosswalk overlap baseline changed; audit the join before accepting a new value")
require(payload["crosswalk"]["descriptiveCandidates"] == 382, "exact-ID descriptive-candidate baseline changed")
require(payload["crosswalk"]["approved"] == 3, "human-approved actor anchor baseline changed")
require(payload["crosswalk"]["downstreamPolicy"] == "approved-only", "cross-source eligibility policy changed")
require(payload["repertoire"]["croad"]["sample"] == {"dyads": 390, "actors": 351, "dyadYears": 1709, "missingDyads": 5, "switchingDyads": 46}, "CROAD release baseline changed")

qualitative = payload["qualitative"]
require({case["actorId"] for case in qualitative["cases"]} == {743, 532, 488}, "qualitative actor anchors changed")
require(sum(len(case["objects"]) for case in qualitative["cases"]) == 9, "expected nine reviewed qualitative objects")

require(len(payload["ecology"]["organization"]["matrix"]) > 0, "organization ecology matrix is empty")
require(len(payload["ecology"]["actorYear"]["matrix"]) > 0, "actor-year ecology matrix is empty")
approved = {488, 532, 743}
require(set(actors) == approved, "profiles must be limited to tracked approved anchors")
surface_ids = {
    "organization ecology": {row["actorId"] for row in payload["ecology"]["organization"]["rows"]},
    "actor-year ecology": {row["actorId"] for row in payload["ecology"]["actorYear"]["rows"]},
    "RAID-RHRV bridge": {row["actorId"] for row in payload["repertoire"]["measurementBridge"]},
    "CROAD-RAID bridge": {row["actorId"] for row in payload["repertoire"]["croad"]["raidBridge"]},
    "CROAD-RHRV bridge": {row["actorId"] for row in payload["repertoire"]["croad"]["rhrvBridge"]},
    "support network": {row["recipientId"] for row in payload["supportNetwork"]["yearEdges"]},
}
for surface, actor_ids in surface_ids.items():
    require(actor_ids <= approved, f"{surface} contains an actor without tracked approval")
require(len(payload["supportNetwork"]["yearEdges"]) == 102, "approved-anchor support-network baseline changed")
require(all(cell["value"] is None and cell["suppressionReason"] for block in payload["ecology"].values() for cell in block["matrix"]), "small approved-actor ecology estimates must remain suppressed")
require(payload["context"]["commonSourceCountryYears"] >= 500, "four-source country-year intersection unexpectedly sparse")
require(payload["context"]["completeCountryYears"] >= 500, "analysis-ready country-year intersection unexpectedly sparse")
require(len(payload["boundaries"]["mladShares"]) > 500, "MLAD aggregate is empty")
require(len(payload["notes"]) >= 4, "research-note rendering source is empty")
raw_fields = {"respondent_id", "interview_text", "event_id", "longitude", "latitude", "whereabouts"}


def walk_keys(value):
    if isinstance(value, dict):
        yield from value
        for nested in value.values():
            yield from walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk_keys(nested)


require(not (set(walk_keys(payload)) & raw_fields), "browser payload may expose raw micro/event/narrative data")

with (ROOT / "dataset" / "file-manifest.csv").open(newline="", encoding="utf-8") as handle:
    manifest = list(csv.DictReader(handle))
require(len(manifest) == 59, "file manifest row count changed")
for row in manifest:
    path = ROOT / row["local_path"]
    require(path.exists(), f"manifest path missing: {row['local_path']}")
    require(path.stat().st_size == int(row["bytes"]), f"manifest byte mismatch: {row['local_path']}")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], f"manifest hash mismatch: {row['local_path']}")

html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
for marker in [
    'id="system"', 'id="recruitable"', 'id="exposure"', 'id="demand"',
    'id="repertoires"', 'id="selection"', 'id="incorporation"', 'id="behavior"',
    'id="ecology"', 'id="profiles"', 'id="context"', 'id="boundaries"',
    'id="coverage"', 'id="notes"', 'id="support-network"', 'id="coverage-map"',
    'id="note-list"', 'id="qualitative-case"', 'data/dashboard-data.js', 'data/world.js', 'vendor/d3.min.js', 'dashboard.js',
]:
    require(marker in html, f"dashboard marker missing: {marker}")
for claim in [
    "Who constitutes the potential manpower pool?",
    "Who is actually exposed to recruitment efforts or organizational reach?",
    "What kinds and quantities of manpower does the organization need?",
    "Through what instruments does the organization acquire manpower?",
    "Who is selected, accepted, targeted, exempted, or excluded?",
    "How are recruits trained, assigned, disciplined, socialized, and integrated?",
    "What downstream behavior follows?",
    "How does a nascent armed group first come into being?",
    "Conscription ≠ abduction",
    "Conditions shape every stage.",
    "关键概念：Exposure",
    "未报告不等于行为不存在",
]:
    require(claim in html, f"recruitment-process claim missing: {claim}")
for path in [
    ROOT / "dashboard" / "index.html", ROOT / "dashboard" / "dashboard.js",
    ROOT / "dashboard" / "data" / "dashboard-data.js", ROOT / "dashboard" / "data" / "world.js",
    ROOT / "dashboard" / "vendor" / "d3.min.js", ROOT / "dashboard" / "vendor" / "topojson-client.min.js",
]:
    require(path.exists() and path.stat().st_size > 0, f"dashboard dependency missing: {path.relative_to(ROOT)}")

print("PASS: narrative schema, micro baselines, version-aware crosswalk, licensed qualitative layer, aggregate-only payload, and 59 archived files.")
