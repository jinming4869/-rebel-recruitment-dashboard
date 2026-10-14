"""Week 3: draw the 24 pilot disputes BEFORE inspecting archive richness.

The full random order of every cell is written out at draw time, so replacements are
predetermined and auditable. Selection probabilities are recorded because the
outcome-balanced pilot must never be used unweighted for escalation rates.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DERIVED, LEDGERS, frame_sha256, load_json, schemas, write_csv  # noqa: E402


def allocate(cell_sizes: dict[str, int], n_total: int) -> dict[str, int]:
    """Equal allocation, capped by cell size; shortfall goes one at a time to the cell
    with the largest remaining frame (ties: cell name)."""
    cells = sorted(cell_sizes)
    base = n_total // len(cells)
    alloc = {c: min(base, cell_sizes[c]) for c in cells}
    remaining = n_total - sum(alloc.values())
    while remaining > 0:
        spare = {c: cell_sizes[c] - alloc[c] for c in cells if cell_sizes[c] > alloc[c]}
        if not spare:
            break  # frame smaller than n_total: draw everything
        c = sorted(spare, key=lambda k: (-spare[k], k))[0]
        alloc[c] += 1
        remaining -= 1
    return alloc


def draw(frame: pd.DataFrame, n_total: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """frame needs: dispute_id, info_stratum, coercion_stratum, escalation_stratum.
    Returns (pilot_sampling rows, full per-cell random order)."""
    f = frame.sort_values("dispute_id").reset_index(drop=True)
    f["cell"] = f["info_stratum"] + "|" + f["coercion_stratum"] + "|" + f["escalation_stratum"]
    sizes = f["cell"].value_counts().to_dict()
    alloc = allocate(sizes, n_total)
    rng = np.random.default_rng(seed)
    orders = []
    for cell in sorted(sizes):
        g = f[f["cell"] == cell]
        perm = g.iloc[rng.permutation(len(g))].copy()
        perm["draw_order"] = range(1, len(perm) + 1)
        perm["frame_size_in_cell"] = len(g)
        perm["n_allocated"] = alloc[cell]
        perm["selection_probability"] = alloc[cell] / len(g)
        orders.append(perm)
    order = pd.concat(orders, ignore_index=True)
    picked = order[order["draw_order"] <= order["n_allocated"]].copy()
    picked["status"] = "selected"
    picked["replacement_for"] = ""
    picked["replacement_reason"] = ""
    return picked, order


def main() -> None:
    design = load_json("pilot_design.json")
    frame_path = DERIVED / "pilot_frame.csv"
    if not frame_path.exists():
        print("NOT RUN: data/derived/pilot_frame.csv is missing. It is built from movement_episodes.csv "
              "plus the info and coercion proxies once the PI has fixed the coercion proxy "
              "(config/pilot_design.json).")
        sys.exit(2)
    existing = pd.read_csv(LEDGERS / "pilot_sampling.csv", dtype=str)
    if len(existing):
        sys.exit("pilot_sampling.csv already holds a draw; re-drawing is not allowed (log an amendment).")
    frame = pd.read_csv(frame_path, dtype={"dispute_id": str})
    picked, order = draw(frame, design["n_total"], design["rng_seed"])
    picked["rng_seed"] = design["rng_seed"]
    picked["frame_sha256"] = frame_sha256(frame)
    picked["drawn_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    cols = schemas()["pilot_sampling.csv"]["columns"]
    write_csv(picked.reindex(columns=cols), LEDGERS / "pilot_sampling.csv")
    write_csv(order, DERIVED / "pilot_frame_order.csv")
    print(picked.groupby("cell").size().to_string())


if __name__ == "__main__":
    main()
