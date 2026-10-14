"""Week 5 (if GO): simulate precision for the 24-month first-violence risk difference
Delta = P(Y24|low I) - P(Y24|high I), with outcomes clustered by country.

The PI must supply delta* (smallest meaningful risk difference) and the baseline rate
from the FULL risk set (never the outcome-balanced pilot). This script never picks them.

Reports, for each candidate number of countries:
  p_yes : P(lower 95% bound > delta*) when true Delta = --true-delta
  p_no  : P(upper 95% bound < delta*) when true Delta = 0
Analysis model: linear-probability difference in means with CR1 cluster-robust SE.

Example:
  python -I src/power_sim.py --delta-star 0.10 --baseline 0.15 --true-delta 0.20 \
      --icc 0.10 --per-country 3 --countries 20 40 60 80 --recoverable 60
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
Z = 1.959964


def simulate_once(rng, n_countries, per_country, baseline, delta, icc, share_low=0.5):
    """Logit-scale country random intercept; the latent ICC sets its variance
    (so realised marginal rates drift slightly from the nominal ones when icc > 0)."""
    sigma2 = icc * (np.pi ** 2 / 3) / (1 - icc) if icc > 0 else 0.0
    u = rng.normal(0, np.sqrt(sigma2), n_countries)
    country = np.repeat(np.arange(n_countries), per_country)
    low_i = rng.random(country.size) < share_low
    p_base = np.where(low_i, baseline + delta, baseline)
    logit = np.log(p_base / (1 - p_base)) + u[country]
    y = rng.random(country.size) < 1 / (1 + np.exp(-logit))
    return y.astype(float), low_i.astype(float), country


def rd_cr1(y, x, cluster):
    """Risk difference (slope of LPM) with CR1 cluster-robust SE."""
    X = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    groups = np.unique(cluster)
    for g in groups:
        s = X[cluster == g].T @ e[cluster == g]
        meat += np.outer(s, s)
    G, n, k = len(groups), len(y), 2
    adj = G / (G - 1) * (n - 1) / (n - k)
    V = adj * bread @ meat @ bread
    return beta[1], float(np.sqrt(V[1, 1]))


def power(n_countries, per_country, baseline, delta_star, true_delta, icc, sims, seed):
    rng = np.random.default_rng(seed)
    yes = no = 0
    for _ in range(sims):
        y, x, c = simulate_once(rng, n_countries, per_country, baseline, true_delta, icc)
        b, se = rd_cr1(y, x, c)
        yes += (b - Z * se) > delta_star
        y, x, c = simulate_once(rng, n_countries, per_country, baseline, 0.0, icc)
        b, se = rd_cr1(y, x, c)
        no += (b + Z * se) < delta_star
    return yes / sims, no / sims


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delta-star", type=float, required=True)
    ap.add_argument("--baseline", type=float, required=True, help="full-risk-set 24m first-violence rate")
    ap.add_argument("--true-delta", type=float, required=True)
    ap.add_argument("--icc", type=float, default=0.1)
    ap.add_argument("--per-country", type=int, default=3)
    ap.add_argument("--countries", type=int, nargs="+", required=True)
    ap.add_argument("--recoverable", type=int, default=None, help="projected recoverable complete chains")
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--write", action="store_true", help="write outputs/power_plan.json")
    a = ap.parse_args()
    if not 0 < a.baseline < 1 or not 0 < a.baseline + a.true_delta < 1:
        sys.exit("baseline and baseline+true_delta must lie in (0, 1)")
    rows = []
    for g in a.countries:
        p_yes, p_no = power(g, a.per_country, a.baseline, a.delta_star, a.true_delta, a.icc, a.sims, a.seed)
        rows.append({"countries": g, "n": g * a.per_country, "p_yes": p_yes, "p_no": p_no})
        print(f"countries={g:>4} n={g * a.per_country:>5}  P(YES|true)={p_yes:.3f}  P(NO|null)={p_no:.3f}")
    plan = {"inputs": vars(a), "grid": rows}
    ok = [r for r in rows if r["p_yes"] >= 0.8 and r["p_no"] >= 0.8]
    plan["required_n"] = ok[0]["n"] if ok else None
    if a.recoverable is not None:
        plan["recoverable"] = a.recoverable
        plan["feasible"] = bool(ok) and ok[0]["n"] <= a.recoverable
        print(f"required n={plan['required_n']} vs recoverable={a.recoverable} -> feasible={plan['feasible']}")
    if a.write:
        (ROOT / "outputs").mkdir(exist_ok=True)
        (ROOT / "outputs" / "power_plan.json").write_text(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
