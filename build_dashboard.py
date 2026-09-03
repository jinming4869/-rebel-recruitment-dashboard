#!/usr/bin/env python3
"""Build the content-first recruitment dashboard payload."""

import json

from analysis_pipeline import OUTPUT, ROOT, main


if __name__ == "__main__":
    payload = main()
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/")
    OUTPUT.write_text(f"window.RECRUITMENT_DASHBOARD = {serialized};\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT.relative_to(ROOT)} with "
        f"{len(payload['actorProfiles'])} actor profiles and "
        f"{len(payload['supportNetwork']['yearEdges'])} support-network year edges."
    )
