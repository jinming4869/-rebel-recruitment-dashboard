"""Freeze a raw source: download (or register a manually obtained file), hash it,
and record URL/version/date/filename/SHA-256 in ledgers/source_registry.csv.

Usage:
  python -I src/fetch_sources.py download DATA_UCDP_ACD <url>
  python -I src/fetch_sources.py register DATA_SDM /path/to/manually_downloaded.csv

Raw files are immutable: an existing file with a different hash is an error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import LEDGERS, RAW, sha256  # noqa: E402


def _record(source_id: str, path: Path, url: str) -> None:
    reg_path = LEDGERS / "source_registry.csv"
    reg = pd.read_csv(reg_path, dtype=str, keep_default_na=False)
    if source_id not in set(reg["source_id"]):
        sys.exit(f"{source_id} is not in the source registry; add a row first.")
    i = reg.index[reg["source_id"] == source_id][0]
    reg.loc[i, "download_url"] = url
    reg.loc[i, "download_date"] = dt.date.today().isoformat()
    reg.loc[i, "original_filename"] = path.name
    reg.loc[i, "sha256"] = sha256(path)
    reg.loc[i, "status"] = "frozen"
    reg.to_csv(reg_path, index=False)
    print(f"{source_id}: frozen {path.name} sha256={reg.loc[i, 'sha256']}")


def _place(source_id: str, src: Path) -> Path:
    dest_dir = RAW / source_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        if sha256(dest) != sha256(src):
            sys.exit(f"{dest} exists with a different hash; raw files are immutable.")
        return dest
    shutil.copy2(src, dest)
    if dest.suffix == ".zip":
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(dest_dir)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("source_id")
    d.add_argument("url")
    r = sub.add_parser("register")
    r.add_argument("source_id")
    r.add_argument("path", type=Path)
    a = ap.parse_args()

    if a.cmd == "download":
        tmp = RAW / "_incoming" / Path(a.url.split("?")[0]).name
        tmp.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(a.url, tmp)
        dest = _place(a.source_id, tmp)
        tmp.unlink()
        _record(a.source_id, dest, a.url)
    else:
        dest = _place(a.source_id, a.path)
        _record(a.source_id, dest, f"manual:{a.path.name}")


if __name__ == "__main__":
    main()
