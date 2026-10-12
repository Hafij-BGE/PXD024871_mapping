#!/usr/bin/env python3
"""Workflow-associated composition signature in PXD004023, an external cohort.

Secondary analysis. Promoted into the repository by D054 **as it was run**, so
that the figures D046 reports have the code that produced them on the record.

Determinism (D055). An earlier version held peptides in `set`s, so the list
handed to `balance()` came out in a different order in every process and
`rng.choice` drew a different subsample each run despite a fixed seed. That is
why the figures D046 reported -- 0.6597 held-out AUROC, 0.5998 control, +0.0598
excess -- were one draw rather than a value: re-runs gave 0.0579 to 0.0625 for
the excess within the published 8-12 window. `units.json` already stores each
peptide set sorted, so holding the values as lists is both the fix and the
simpler code.

Two further weaknesses are also fixed here. The control averaged **5**
replicates and was reported to four decimals, a precision its standard error
did not support; it now averages N_CONTROL and carries an interval. And the
analysis and control arms shared one generator, so changing the replicate count
would have reshuffled the per-donor draws; each purpose now has its own stream
(D010, scripts/seeds.py).

**The numbers therefore differ from D046 and supersede it.** They differ for
three reasons at once -- determinism, the decoupled streams, and the control
count -- so no single-cause delta is quoted. D046's value was never
reproducible, so there is no stable figure to take a difference from.

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
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                              # noqa: E402
from train_cnn import cluster_ci                                    # noqa: E402

EXT = REPO/'data'/'external'/'PXD004023'
UNITS = EXT/'units.json'
OUT = REPO/'results'/'replication'/'px4023.json'

AA = 'ACDEFGHIKLMNPQRSTVWY'
IDX = {a: i for i, a in enumerate(AA)}
ELITE, QE = '2013_Elite_SCX', '2014_QEplus_unfrac'

N_CONTROL = 200          # D055; was 5, whose standard error exceeded the effect
NOMINAL = 0.99           # D008's level, which delivers about 95% at this n
B_BOOT = 10000

# One stream per purpose (D010, scripts/seeds.py). The arms were previously
# coupled through a single generator, so raising the control replicate count
# would have silently reshuffled the per-donor draws as well.
rng_sub = np.random.default_rng(seed('px4023_subsample'))
rng_ctl = np.random.default_rng(seed('px4023_control'))
rng_boot = np.random.default_rng(seed('px4023_bootstrap'))


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


def balance(a, b, rng, cap=120000):
    n = min(len(a), len(b), cap)
    return list(rng.choice(a, n, replace=False)), list(rng.choice(b, n, replace=False))


def main():
    if not UNITS.exists():
        sys.exit(f"missing {UNITS}\n"
                 f"It is not committed: see the module docstring and D054 section 4.\n"
                 f"Build it locally:  ./scripts/fetch_px4023.sh mzid && "
                 f"python3 scripts/extract_px4023.py")

    # D055: sorted lists, not sets. units.json already stores each value sorted;
    # holding them as sets reintroduced hash-dependent iteration order, which is
    # what made this analysis irreproducible.
    U = {tuple(k.split('|')): sorted(v)
         for k, v in json.loads(UNITS.read_text()).items()}
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
            tr_a, tr_b = balance(tr_a, tr_b, rng_sub)
            Xtr = comp(tr_a + tr_b)
            ytr = np.array([1]*len(tr_a) + [0]*len(tr_b))
            w = lda(Xtr, ytr)
            te_a, te_b = balance(get(held, ELITE), get(held, QE), rng_sub)
            Xte = comp(te_a + te_b)
            yte = np.array([1]*len(te_a) + [0]*len(te_b))
            a = auroc(yte, Xte @ w)
            per.append(a)
            print(f'{held:6s} {len(get(held, ELITE)):8d} {len(get(held, QE)):8d}   {a:.4f}')
        per = np.array(per)
        # Interval over DONORS, the independent sampling unit, by the project's
        # method of record (train_cnn.cluster_ci, D008). Six clusters is few;
        # the interval is correspondingly wide and that is the honest width.
        a_lo, a_hi = cluster_ci(per, rng_boot, B=B_BOOT, nominal=NOMINAL)
        print(f'{"MEAN":6s} {"":8s} {"":8s}   {per.mean():.4f}  '
              f'(sd {per.std(ddof=1):.4f}, min {per.min():.4f}, max {per.max():.4f})')
        print(f'{"":6s} {"":8s} {"":8s}   nominal-{NOMINAL:.0%} over donors '
              f'[{a_lo:.4f}, {a_hi:.4f}]')

        # Control: random halves of donors, pooled across workflows, as in the
        # frozen procedure. D055 raises this from 5 replicates to N_CONTROL --
        # at 5 the standard error of the mean exceeded the effect it bounds.
        ctrls = []
        for _ in range(N_CONTROL):
            p = list(rng_ctl.permutation(both))
            # D055: sorted lists, not sets. Iterating a set of donor names is
            # hash-ordered, which fed `balance` a differently ordered pool and
            # left the control arm alone irreproducible after the first fix.
            h1, h2 = sorted(p[:len(p)//2]), sorted(p[len(p)//2:])
            ga = [s for d in h1 for e in (ELITE, QE) for s in get(d, e)]
            gb = [s for d in h2 for e in (ELITE, QE) for s in get(d, e)]
            ga, gb = balance(ga, gb, rng_ctl)
            X = comp(ga + gb)
            y = np.array([1]*len(ga) + [0]*len(gb))
            n = len(y)//2
            idx = rng_ctl.permutation(len(y))
            tr, te = idx[:n], idx[n:]
            ctrls.append(auroc(y[te], X[te] @ lda(X[tr], y[tr])))
        ctrls = np.array(ctrls)
        q = (1-NOMINAL)/2*100
        c_lo, c_hi = np.percentile(ctrls, [q, 100-q])
        c_se = ctrls.std(ddof=1)/np.sqrt(len(ctrls))
        print(f'CONTROL random halves of donors: {ctrls.mean():.4f}  '
              f'(sd {ctrls.std(ddof=1):.4f}, se {c_se:.4f}, {len(ctrls)} replicates)')
        print(f'{"":32s} {NOMINAL:.0%} of replicates in [{c_lo:.4f}, {c_hi:.4f}]')

        # Excess. The two arms resample different things -- donors on one side,
        # random splits on the other -- so the interval is built by resampling
        # both independently rather than pretending they are paired.
        bd = per[rng_boot.integers(0, per.size, size=(B_BOOT, per.size))].mean(axis=1)
        bc = ctrls[rng_boot.integers(0, ctrls.size, size=(B_BOOT, ctrls.size))].mean(axis=1)
        e_lo, e_hi = np.percentile(bd - bc, [q, 100-q])
        excess = float(per.mean() - ctrls.mean())
        above = int((per > ctrls.mean()).sum())
        print(f'EXCESS over control: {excess:+.4f}  '
              f'nominal-{NOMINAL:.0%} [{e_lo:+.4f}, {e_hi:+.4f}]')
        print(f'  donors above the control mean: {above} of {len(per)}')
        return {
            'window': tag,
            'n_donors': len(per),
            'per_donor_auroc': {d: float(v) for d, v in zip(both, per)},
            'mean_auroc': float(per.mean()),
            'sd_auroc': float(per.std(ddof=1)),
            'auroc_ci': [float(a_lo), float(a_hi)],
            'control_mean': float(ctrls.mean()),
            'control_sd': float(ctrls.std(ddof=1)),
            'control_se': float(c_se),
            'control_n_replicates': int(len(ctrls)),
            'control_interval': [float(c_lo), float(c_hi)],
            'excess': excess,
            'excess_ci': [float(e_lo), float(e_hi)],
            'donors_above_control_mean': above,
        }

    report = {
        'supersedes': 'D046 figures, which were one draw from a '
                      'hash-order-dependent procedure and not reproducible',
        'decision': 'D055',
        'interval_method': f'cluster bootstrap over donors for the AUROC arm '
                           f'(train_cnn.cluster_ci, D008); percentile over '
                           f'{N_CONTROL} replicates for the control; the excess '
                           f'resamples both arms independently, B={B_BOOT}. '
                           f'CAVEAT: the two arms are NOT independent -- the '
                           f'control draws halves of the same donors -- so the '
                           f'excess interval is likely narrower than a correct '
                           f'one. And D008/L5 measured nominal-99% coverage at '
                           f'ten units, not six; coverage here is unverified '
                           f'(D055 section 2a).',
        'nominal': NOMINAL,
        'seeds': {'subsample': seed('px4023_subsample'),
                  'control': seed('px4023_control'),
                  'bootstrap': seed('px4023_bootstrap')},
        'caveat': 'Instrument, acquisition year and SCX fractionation are '
                  'perfectly confounded in this cohort (95 against 65, no '
                  'exceptions). SCX separates peptides by charge, a function of '
                  'composition. This measures acquisition workflow and cannot '
                  'attribute a signature to the instrument.',
        'windows': [],
    }
    for window in ((8, 12), None):
        report['windows'].append(run(window))

    print('\n=== length distribution by workflow (donors with both) ===')
    lengths = {}
    for e, lab in ((ELITE, 'Elite/SCX 2013'), (QE, 'QEplus/unfrac 2014')):
        c = Counter(len(s) for d in both for s in U[(d, e)])
        tot = sum(c.values())
        lengths[e] = {'n': tot, 'pct': {str(L): 100*c[L]/tot for L in range(8, 13)}}
        print(f'{lab:22s} n={tot:7d}  ' +
              ' '.join(f'{L}:{100*c[L]/tot:.1f}%' for L in range(8, 13)))
    report['length_distribution'] = lengths
    report['donors_with_both_workflows'] = both

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + '\n')
    print(f'\nwrote {OUT}')
    print('Deterministic: identical output under any PYTHONHASHSEED. The '
          'acquisition-workflow confound stands; see report["caveat"].')


if __name__ == '__main__':
    main()
