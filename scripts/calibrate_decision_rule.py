#!/usr/bin/env python3
"""Calibrate the §25 decision rule (D008).

Two things are needed and only one is a choice.

First, the interval must be honest. run-001 F3 found nominal 95% cluster
bootstrap intervals achieve only ~90% coverage at 10 held-out units, so a rule
tested against a nominal 95% lower bound is stricter in name than in fact. This
finds the nominal level that DELIVERS 95%.

Second, the threshold. The reference is not chance: D002 measured a
composition-only model reaching AP 0.597 against these negatives, so the lift
is over 0.597.

Conditions are the frozen ones: 10 test units, 1:1, 10,000 positives per unit.
"""

import json, sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from power_analysis import average_precision, estimand   # noqa: E402
from seeds import seed                                   # noqa: E402

OUT = Path(__file__).resolve().parent.parent/'results'/'power'
K, RATIO, NPOS = 10, 1, 10_000
FLOOR = 0.597
N_SIM, B = 500, 2000
NPOS_SIM = 1500          # per-unit draw for the simulation; within-unit noise at
                         # the real 10,000 is smaller still, so this is conservative


def study(K, d_bar, tau, rng):
    d = d_bar + tau*rng.standard_normal(K)
    aps = np.empty(K)
    for i in range(K):
        s = np.concatenate([d[i] + rng.standard_normal(NPOS_SIM),
                            rng.standard_normal(NPOS_SIM*RATIO)])
        y = np.concatenate([np.ones(NPOS_SIM), np.zeros(NPOS_SIM*RATIO)])
        aps[i] = average_precision(y, s)
    return aps


def boot_lo(aps, alpha, rng, B=B):
    idx = rng.integers(0, aps.size, size=(B, aps.size))
    return float(np.percentile(aps[idx].mean(axis=1), 100*alpha))


def main():
    rng = np.random.default_rng(seed('bootstrap'))
    pi = 1/(1+RATIO)
    d_bar = float(np.sqrt(2)*norm.ppf(0.80))

    print(f"=== 1. what nominal level delivers 95% actual coverage? (K={K}, 1:{RATIO}) ===")
    print("  tau    nominal 95%   nominal 97.5%   nominal 99%")
    cal = {}
    for tau in (0.10, 0.25, 0.50):
        target = estimand(d_bar, tau, pi)
        cov = {a: 0 for a in (0.025, 0.0125, 0.005)}
        for _ in range(N_SIM):
            aps = study(K, d_bar, tau, rng)
            idx = rng.integers(0, K, size=(B, K))
            reps = aps[idx].mean(axis=1)
            for a in cov:
                lo, hi = np.percentile(reps, [100*a, 100*(1-a)])
                cov[a] += (lo <= target <= hi)
        cal[tau] = {f"{1-2*a:.3f}": cov[a]/N_SIM for a in cov}
        print(f"  {tau:<5}  {cov[0.025]/N_SIM:>10.3f}   {cov[0.0125]/N_SIM:>12.3f}"
              f"   {cov[0.005]/N_SIM:>11.3f}")

    print("\n=== 2. power at candidate thresholds, interval calibrated to 97.5% nominal ===")
    print(f"  floor = {FLOOR} (composition-only, D002)")
    print("  true AUROC  true AP   lift over floor   power vs +0.05   power vs +0.10")
    rows = []
    for auroc in (0.70, 0.75, 0.80, 0.85, 0.90):
        db = float(np.sqrt(2)*norm.ppf(auroc))
        true = estimand(db, 0.25, pi)
        rej = {0.05: 0, 0.10: 0}
        for _ in range(N_SIM):
            aps = study(K, db, 0.25, rng)
            lo = boot_lo(aps, 0.0125, rng)
            for d in rej:
                rej[d] += lo > FLOOR + d
        rows.append({'auroc': auroc, 'true_ap': true, 'lift': true-FLOOR,
                     'power_05': rej[0.05]/N_SIM, 'power_10': rej[0.10]/N_SIM})
        print(f"  {auroc:>9.2f}   {true:>6.4f}   {true-FLOOR:>+14.4f}   "
              f"{rej[0.05]/N_SIM:>13.2f}   {rej[0.10]/N_SIM:>14.2f}")

    print("\n=== 3. false positive rate at the floor (true AP = floor) ===")
    d_floor = float(np.sqrt(2)*norm.ppf(0.6085))
    fp = {0.05: 0, 0.10: 0, 0.0: 0}
    for _ in range(N_SIM):
        aps = study(K, d_floor, 0.25, rng)
        lo = boot_lo(aps, 0.0125, rng)
        for d in fp:
            fp[d] += lo > FLOOR + d
    for d in sorted(fp):
        print(f"  threshold floor+{d:.2f}: false positive rate {fp[d]/N_SIM:.3f}")

    json.dump({'K': K, 'ratio': RATIO, 'floor': FLOOR, 'n_sim': N_SIM, 'B': B,
               'npos_sim': NPOS_SIM, 'coverage_calibration': cal,
               'power': rows,
               'false_positive_at_floor': {str(k): v/N_SIM for k, v in fp.items()}},
              open(OUT/'decision_rule.json', 'w'), indent=1)
    print(f"\nwrote {OUT/'decision_rule.json'}")


if __name__ == '__main__':
    main()
