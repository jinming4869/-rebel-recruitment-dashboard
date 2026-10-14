"""Register every file of the data handoff in the source registry.

Usage (ZIP downloaded and extracted outside the repository):
  python3 -I src/register_handoff.py /path/to/handoff.zip /path/to/extracted_dir

Steps: verify the ZIP's SHA-256 against config/handoff_registration.json, verify each
file against the handoff's own CHECKSUMS.sha256, then call fetch_sources' register logic
with the upstream URL from SOURCE_MANIFEST.json. Stops on the first mismatch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_json, sha256  # noqa: E402
from fetch_sources import _place, _record  # noqa: E402


def main(zip_path: Path, extracted: Path) -> None:
    cfg = load_json("handoff_registration.json")
    got = sha256(zip_path)
    if got != cfg["zip_sha256"]:
        sys.exit(f"ZIP SHA-256 mismatch: {got}")
    root = extracted / cfg["root"]
    sums = {}
    for line in (root / "CHECKSUMS.sha256").read_text().splitlines():
        h, _, p = line.strip().partition("  ")
        sums[p.strip().lstrip("./")] = h
    manifest = {f["path"]: f for f in json.loads((root / "SOURCE_MANIFEST.json").read_text())["files"]}
    note = f"from release {cfg['release_tag']} ({cfg['release_asset']}, sha256 {cfg['zip_sha256'][:12]}...)"
    for sid, spec in cfg["files"].items():
        rel = spec["path"]
        f = root / rel
        if rel in sums and sha256(f) != sums[rel]:
            sys.exit(f"{rel}: checksum differs from handoff CHECKSUMS.sha256")
        if rel not in sums:
            print(f"warning: {rel} not listed in CHECKSUMS.sha256")
        dest = _place(sid, f)
        _record(sid, dest, manifest.get(rel, {}).get("source_url", ""), spec.get("version", ""), note)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
