"""Shared paths, controlled vocabularies, hashing and source loading.

Raw files under data/raw/ are immutable: nothing in src/ writes there except
fetch_sources.py on first download.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
LEDGERS = ROOT / "ledgers"
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
OUTPUTS = ROOT / "outputs"


class SourceNotReady(RuntimeError):
    """A required raw source is missing or its column map is unconfirmed."""


def load_json(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as fh:
        return json.load(fh)


def codes() -> dict:
    return load_json("codes.json")


def schemas() -> dict:
    return load_json("ledger_schemas.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_sha256(df: pd.DataFrame) -> str:
    """Hash of the CSV serialisation in its given row order (records the exact frame drawn from)."""
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def load_source(source_id: str, root: Path = ROOT, allow_unconfirmed: bool = False) -> pd.DataFrame:
    """Load a raw source and rename its columns to logical names.

    Refuses to run if the column map has not been confirmed against the
    source's own codebook, so a guessed column name cannot silently produce
    numbers.
    """
    spec = load_json("source_columns.json")[source_id]
    if not spec.get("confirmed") and not allow_unconfirmed:
        raise SourceNotReady(
            f"{source_id}: column map in config/source_columns.json is unconfirmed. "
            f"Check it against the codebook, then set confirmed=true."
        )
    files = sorted(glob.glob(str(root / spec["file_glob"])))
    if not files:
        raise SourceNotReady(f"{source_id}: no file matches {spec['file_glob']} (download pending).")
    if len(files) > 1:
        raise SourceNotReady(f"{source_id}: {len(files)} files match; freeze exactly one version.")
    df = pd.read_csv(files[0], low_memory=False)
    mapping = {raw: logical for logical, raw in spec["columns"].items() if raw}
    missing = [raw for raw in mapping if raw not in df.columns]
    if missing:
        raise SourceNotReady(f"{source_id}: columns {missing} not in {files[0]}; fix the column map.")
    return df[list(mapping)].rename(columns=mapping)


def read_ledger(name: str, root: Path = ROOT) -> pd.DataFrame:
    return pd.read_csv(root / "ledgers" / name, dtype=str, keep_default_na=False)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
