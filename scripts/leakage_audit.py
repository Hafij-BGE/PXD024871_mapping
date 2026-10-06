#!/usr/bin/env python3
"""G5 — leakage and confound audit on the frozen dataset.

Runs before the split exists, so it measures what the split will have to
handle rather than checking a split already made.

Two questions decide whether the §25 claim is testable at all:

1. How much sequence leakage does a unit-disjoint split actually incur? 10.20%
   of rows are shared across units, but what reaches a given test partition
   depends on which units land where, so it is a distribution, not a number.

2. Is the instrument confound learnable FROM THE PEPTIDES? D005 established
   that platform and unit cannot be separated by any split. That is only fatal
   if the peptides themselves carry a platform signature -- if they do, a model
   evaluated on held-out units is partly being tested on platform transfer.
"""

import csv, json, random, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from negative_diagnostic import comp, auroc   # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DER, OUT = REPO/'data'/'derived', REPO/'results'/'qc'
SEED = 20261006
N_SPLITS = 2000


def lda_auroc(A, B, rng):
    XA, XB = comp(A), comp(B)
    na, nb = len(XA)//2, len(XB)//2
    trA, teA, trB, teB = XA[:na], XA[na:], XB[:nb], XB[nb:]
    mu1, mu0 = trA.mean(0), trB.mean(0)
    S = np.cov(np.vstack([trA-mu1, trB-mu0]).T) + np.eye(20)*1e-6
    w = np.linalg.solve(S, mu1-mu0)
    y = np.concatenate([np.ones(len(teA)), np.zeros(len(teB))])
    return float(auroc(y, np.concatenate([teA @ w, teB @ w])))


def main():
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    by_unit = defaultdict(set)
    with (DER/'POSITIVES.csv').open(newline='') as fh:
        for r in csv.DictReader(fh):
            by_unit[r['unit_id']].add(r['sequence'])
    units = sorted(by_unit)
    inst = {r['unit_id']: r['instruments']
            for r in csv.DictReader((DER/'UNITS.csv').open(newline=''))}
    print(f"units {len(units)}; positives per unit {len(by_unit[units[0]]):,}")

    # ---- 1. leakage under random unit-disjoint splits ---------------------
    occur = Counter()
    for u in units:
        for s in by_unit[u]:
            occur[s] += 1
    k_test = max(1, round(len(units) * 0.2))
    fracs = []
    for _ in range(N_SPLITS):
        test = set(rng.sample(units, k_test))
        tr = set().union(*(by_unit[u] for u in units if u not in test))
        te = set().union(*(by_unit[u] for u in test))
        fracs.append(len(te & tr) / len(te))
    fracs = np.array(fracs)
    print(f"\n=== 1. sequence leakage under a unit-disjoint split "
          f"({k_test} test units, {N_SPLITS} random splits) ===")
    print(f"  test positives also present in training:")
    print(f"    mean {100*fracs.mean():.2f}%   median {100*np.median(fracs):.2f}%"
          f"   min {100*fracs.min():.2f}%   max {100*fracs.max():.2f}%")
    print(f"    5th-95th percentile {100*np.percentile(fracs,5):.2f}% - "
          f"{100*np.percentile(fracs,95):.2f}%")

    # ---- 2. is platform learnable from the peptides? ----------------------
    groups = defaultdict(list)
    for u in units:
        key = 'LTQ' if 'LTQ' in inst[u] else 'Lumos'
        groups[key] += list(by_unit[u])
    print(f"\n=== 2. is the instrument learnable from sequence alone? ===")
    for k, v in groups.items():
        print(f"  {k:<6} {len(v):,} positives from "
              f"{sum(1 for u in units if ('LTQ' in inst[u]) == (k=='LTQ'))} units")
    n = min(len(groups['LTQ']), len(groups['Lumos']), 120000)
    a = rng.sample(groups['LTQ'], n); b = rng.sample(groups['Lumos'], n)
    plat = lda_auroc(a, b, nprng)
    print(f"  composition-only AUROC, LTQ vs Lumos positives: {plat:.4f}")

    ll = Counter(len(s) for s in groups['LTQ'])
    lm = Counter(len(s) for s in groups['Lumos'])
    tl, tm = sum(ll.values()), sum(lm.values())
    print("  length distribution by platform:")
    for L in sorted(set(ll) | set(lm)):
        print(f"    {L:>2}: LTQ {100*ll[L]/tl:5.2f}%   Lumos {100*lm[L]/tm:5.2f}%"
              f"   diff {100*(ll[L]/tl - lm[L]/tm):+5.2f}pp")

    # control: two random halves of units, same test
    half = rng.sample(units, len(units)//2)
    ga = [s for u in half for s in by_unit[u]]
    gb = [s for u in units if u not in half for s in by_unit[u]]
    n2 = min(len(ga), len(gb), 120000)
    ctrl = lda_auroc(rng.sample(ga, n2), rng.sample(gb, n2), nprng)
    print(f"\n  CONTROL, random half of units vs the other half: {ctrl:.4f}")
    print(f"  excess attributable to platform: {plat-ctrl:+.4f}")

    json.dump({'seed': SEED, 'n_splits': N_SPLITS, 'test_units': k_test,
               'leakage_mean_pct': float(100*fracs.mean()),
               'leakage_median_pct': float(100*np.median(fracs)),
               'leakage_min_pct': float(100*fracs.min()),
               'leakage_max_pct': float(100*fracs.max()),
               'leakage_p5_pct': float(100*np.percentile(fracs,5)),
               'leakage_p95_pct': float(100*np.percentile(fracs,95)),
               'platform_auroc_composition': plat,
               'random_unit_half_control_auroc': ctrl,
               'platform_excess_over_control': plat-ctrl,
               'length_pct_LTQ': {str(L): 100*ll[L]/tl for L in sorted(ll)},
               'length_pct_Lumos': {str(L): 100*lm[L]/tm for L in sorted(lm)}},
              open(OUT/'leakage_audit.json','w'), indent=1)
    print(f"\nwrote {OUT/'leakage_audit.json'}")


if __name__ == '__main__':
    main()
