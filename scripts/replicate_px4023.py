#!/usr/bin/env python3
"""Workflow-associated composition signature in PXD004023, an external cohort.

Secondary analysis. Promoted into the repository by D054 **as it was run**, so
that the figures D046 reports have the code that produced them on the record.

=============================== WARNING ================================
THIS SCRIPT IS NOT DETERMINISTIC, AND IS COMMITTED IN THAT STATE ON PURPOSE.

`U` holds peptides in `set`s of strings. `get()` iterates one, so the list
handed to `balance()` comes out in a different order in every process, because
Python randomises string hashing per process. `rng.choice` then draws a
different subsample each run even though `rng` is seeded.

It is the same defect D053 fixed in scripts/leakage_audit.py. The figures in
D046 -- 0.6597 held-out AUROC, 0.5998 control, +0.0598 excess -- are therefore
one draw, not a reproducible value: re-runs give 0.0579 to 0.0625 for the
excess within the published 8-12 window. The direction and the 6-of-6 donor
count hold in every run.

Two further weaknesses, recorded here rather than silently carried:
  * the control averages 5 replicates and is reported to four decimals. Its
    standard error is larger than the effect it bounds.
  * there is no interval on anything.

Q1-002 fixes all three. It is a separate task so that its diff shows exactly
what changed, against code that is already under checksum. **Do not cite output
from this version.**
========================================================================

Input:  data/external/PXD004023/units.json, written by
        scripts/extract_px4023.py. **Not committed** -- it holds derived peptide
        sequences from a third-party deposit and the redistribution position for
        PXD004023 is not established (D054 section 4). Run the extractor locally
        first; this script exits if the file is absent.

Method, held to scripts/leakage_audit.py: 20-dimensional amino-acid
composition, fractions, no positional information; Fisher linear discriminant,
closed form; class balance by subsampling to the smaller arm; AUROC with
midrank tie correction.

One deliberate strengthening over the frozen procedure: evaluation is
leave-one-donor-out, so a donor's peptides appear in training or in test, never
both. The PXD024871 procedure pools and splits at the peptide level. This is
harder, not easier.

What this can and cannot support. In PXD004023 the instrument is completely
confounded with acquisition year and with SCX fractionation -- 95 runs Orbitrap
Elite / 2013 / fractionated against 65 Q Exactive Plus / 2014 / unfractionated,
with no run breaking the pattern (data/external/PXD004023/runmap.csv). SCX
fractionation separates peptides by charge, which is a direct function of
amino-acid composition, the exact feature space used here. A positive result
supports "the acquisition workflow leaves a learnable signature in peptide
sequence" and **cannot** attribute it to the instrument.
"""

import json, sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
EXT = REPO/'data'/'external'/'PXD004023'
UNITS = EXT/'units.json'

AA = 'ACDEFGHIKLMNPQRSTVWY'
IDX = {a: i for i, a in enumerate(AA)}
ELITE, QE = '2013_Elite_SCX', '2014_QEplus_unfrac'
SEED = 20261012
rng = np.random.default_rng(SEED)


def comp(seqs):
    X = np.zeros((len(seqs), 20))
    for i, s in enumerate(seqs):
        for ch in s:
            j = IDX.get(ch)
            if j is not None:
                X[i, j] += 1
        n = X[i].sum()
        if n:
            X[i] /= n
    return X


def lda(X, y):
    X1, X0 = X[y == 1], X[y == 0]
    m1, m0 = X1.mean(0), X0.mean(0)
    Sw = np.cov(np.vstack([X1-m1, X0-m0]).T) + np.eye(20)*1e-6
    return np.linalg.solve(Sw, m1-m0)


def auroc(y, s):
    o = np.argsort(s, kind='mergesort')
    ss, yy = s[o], y[o]
    r = np.empty(len(s))
    i = 0
    while i < len(s):
        j = i
        while j+1 < len(s) and ss[j+1] == ss[i]:
            j += 1
        r[i:j+1] = 0.5*(i+j) + 1
        i = j+1
    n1 = yy.sum()
    n0 = len(yy) - n1
    return float('nan') if n1 == 0 or n0 == 0 else \
        (r[yy == 1].sum() - n1*(n1+1)/2)/(n1*n0)


def balance(a, b, cap=120000):
    n = min(len(a), len(b), cap)
    return list(rng.choice(a, n, replace=False)), list(rng.choice(b, n, replace=False))


def main():
    if not UNITS.exists():
        sys.exit(f"missing {UNITS}\n"
                 f"It is not committed: see the module docstring and D054 section 4.\n"
                 f"Build it locally:  ./scripts/fetch_px4023.sh mzid && "
                 f"python3 scripts/extract_px4023.py")

    U = {tuple(k.split('|')): set(v) for k, v in json.loads(UNITS.read_text()).items()}
    donors = sorted({d for d, _ in U})
    both = [d for d in donors if (d, ELITE) in U and (d, QE) in U]
    print('donors with both workflows:', both)

    def run(window):
        tag = f'{window[0]}-{window[1]}' if window else 'all lengths'

        def get(d, e):
            s = U[(d, e)]
            return [x for x in s if window is None or window[0] <= len(x) <= window[1]]

        print(f'\n{"="*66}\nWINDOW: {tag}\n{"="*66}')
        print(f'{"donor":6s} {"Elite":>8s} {"QEplus":>8s}   held-out AUROC')
        per = []
        for held in both:
            tr_a = [s for d in both if d != held for s in get(d, ELITE)]
            tr_b = [s for d in both if d != held for s in get(d, QE)]
            tr_a, tr_b = balance(tr_a, tr_b)
            Xtr = comp(tr_a + tr_b)
            ytr = np.array([1]*len(tr_a) + [0]*len(tr_b))
            w = lda(Xtr, ytr)
            te_a, te_b = balance(get(held, ELITE), get(held, QE))
            Xte = comp(te_a + te_b)
            yte = np.array([1]*len(te_a) + [0]*len(te_b))
            a = auroc(yte, Xte @ w)
            per.append(a)
            print(f'{held:6s} {len(get(held, ELITE)):8d} {len(get(held, QE)):8d}   {a:.4f}')
        per = np.array(per)
        print(f'{"MEAN":6s} {"":8s} {"":8s}   {per.mean():.4f}  '
              f'(sd {per.std(ddof=1):.4f}, min {per.min():.4f}, max {per.max():.4f})')

        # Control, as in the frozen procedure: random halves of donors, pooled
        # across workflows. Five replicates only -- see the docstring.
        ctrls = []
        for _ in range(5):
            p = list(rng.permutation(both))
            h1, h2 = set(p[:len(p)//2]), set(p[len(p)//2:])
            ga = [s for d in h1 for e in (ELITE, QE) for s in get(d, e)]
            gb = [s for d in h2 for e in (ELITE, QE) for s in get(d, e)]
            ga, gb = balance(ga, gb)
            X = comp(ga + gb)
            y = np.array([1]*len(ga) + [0]*len(gb))
            n = len(y)//2
            idx = rng.permutation(len(y))
            tr, te = idx[:n], idx[n:]
            ctrls.append(auroc(y[te], X[te] @ lda(X[tr], y[tr])))
        print(f'CONTROL random halves of donors: {np.mean(ctrls):.4f} '
              f'(sd {np.std(ctrls, ddof=1):.4f}, {len(ctrls)} replicates)')
        print(f'EXCESS over control: {per.mean()-np.mean(ctrls):+.4f}')
        return per.mean(), float(np.mean(ctrls))

    for window in ((8, 12), None):
        run(window)

    print('\n=== length distribution by workflow (donors with both) ===')
    for e, lab in ((ELITE, 'Elite/SCX 2013'), (QE, 'QEplus/unfrac 2014')):
        c = Counter(len(s) for d in both for s in U[(d, e)])
        t = sum(c.values())
        print(f'{lab:22s} n={t:7d}  ' +
              ' '.join(f'{L}:{100*c[L]/t:.1f}%' for L in range(8, 13)))

    print('\nNOT DETERMINISTIC. Do not cite these numbers; see the docstring and '
          'D054. Q1-002 supersedes this script.')


if __name__ == '__main__':
    main()
