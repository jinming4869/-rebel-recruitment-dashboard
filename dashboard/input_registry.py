"""Read analytical inputs only through the frozen input registry."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "dataset" / "analysis-inputs.csv"


def registry() -> dict[str, dict[str, str]]:
    with REGISTRY_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row["input_key"]: row for row in rows}


def input_bytes(key: str) -> tuple[bytes, dict[str, str]]:
    row = registry()[key]
    path = ROOT / row["container_path"]
    if row["member_path"]:
        with zipfile.ZipFile(path) as archive:
            return archive.read(row["member_path"]), row
    return path.read_bytes(), row


def read_input(key: str, *, usecols=None) -> pd.DataFrame:
    data, row = input_bytes(key)
    source = io.BytesIO(data)
    fmt = row["format"]
    if fmt == "stata":
        return pd.read_stata(source, convert_categoricals=False)
    if fmt == "xlsx":
        return pd.read_excel(source)
    if fmt == "tsv-latin1":
        return pd.read_csv(source, sep="\t", encoding="latin1", low_memory=False, usecols=usecols)
    if fmt == "csv-latin1":
        return pd.read_csv(source, encoding="latin1", low_memory=False, usecols=usecols)
    if fmt == "csv":
        return pd.read_csv(source, low_memory=False, usecols=usecols)
    raise ValueError(f"Unsupported registered input format: {fmt}")
