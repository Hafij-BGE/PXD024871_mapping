#!/usr/bin/env python3
"""Where does adding positives per unit stop buying precision?

D024 asks for a per-unit cap chosen from a precision curve rather than from a
compute table. The estimand is the mean per-unit average precision; its variance
is (between-unit variance + within-unit sampling variance) / K. K is fixed at 52
by the data, so the only term a cap touches is the within-unit one. Once that is
small against the between-unit term, more positives per unit change nothing.

Same binormal model as run-001, so the two are comparable: d_i ~ N(d_bar, tau^2),
positives ~ N(d_i, 1), negatives ~ N(0, 1).
"""

import json, sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from power_analysis import average_precision, estimand   # noqa: E402

SEED = 20261006
OUT = Path(__file__).resolve().parent.parent / 'results' / 'power'
CAPS = [500, 1000, 2500, 5000, 10000, 20000, 40000]
TAUS = [0.10, 0.25, 0.50]
RATIO = 1                      # 1:1, the D002 direction favoured on three grounds
N_UNITS = 52
N_SIM = 400


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    d_bar = float(np.sqrt(2) * norm.ppf(0.80))
    pi = 1.0 / (1.0 + RATIO)
    rows = []

    print(f"binormal, mean per-unit AUROC 0.80, class ratio 1:{RATIO}, {N_UNITS} units")
    print("\n  cap     within-unit SD   between-unit SD   within/between   "
          "SD of mean   marginal gain")
    prev = None
    for cap in CAPS:
        # within-unit sampling SD: same d, repeated draws
        aps = []
        for _ in range(N_SIM):
            d = d_bar
            s = np.concatenate([d + rng.standard_normal(cap),
                                rng.standard_normal(cap * RATIO)])
            y = np.concatenate([np.ones(cap), np.zeros(cap * RATIO)])
            aps.append(average_precision(y, s))
        sd_within = float(np.std(aps, ddof=1))

        for tau in TAUS:
            # between-unit SD of the TRUE per-unit AP
            ds = d_bar + tau * norm.ppf((np.arange(2000) + 0.5) / 2000)
            true_aps = [estimand(d, 0.0, pi) for d in ds[::20]]
            sd_between = float(np.std(true_aps, ddof=1))
            sd_mean = float(np.sqrt(sd_between**2 + sd_within**2) / np.sqrt(N_UNITS))
            rows.append({'cap': cap, 'tau': tau, 'ratio': RATIO,
                         'sd_within_unit': sd_within, 'sd_between_unit': sd_between,
                         'within_over_between': sd_within / sd_between,
                         'sd_of_mean': sd_mean})
            if tau == 0.25:
                gain = '' if prev is None else f"{100*(prev-sd_mean)/prev:+6.2f}%"
                print(f"  {cap:>6,}   {sd_within:>14.5f}   {sd_between:>15.5f}   "
                      f"{sd_within/sd_between:>14.3f}   {sd_mean:>10.5f}   {gain:>13}")
                prev = sd_mean

    print("\n  within/between < 0.3 means within-unit noise contributes <5% of the")
    print("  variance of the mean: beyond that point a larger cap is spent on nothing.")
    for tau in TAUS:
        sub = [r for r in rows if r['tau'] == tau]
        hit = next((r for r in sub if r['within_over_between'] < 0.3), None)
        print(f"    tau={tau}: threshold reached at cap "
              f"{hit['cap']:,}" if hit else f"    tau={tau}: not reached within tested caps")

    json.dump({'seed': SEED, 'model': 'binormal, as run-001', 'n_units': N_UNITS,
               'ratio': RATIO, 'n_sim': N_SIM, 'rows': rows},
              open(OUT / 'subsample_curve.json', 'w'), indent=1)
    print(f"\nwrote {OUT/'subsample_curve.json'}")


if __name__ == '__main__':
    main()
