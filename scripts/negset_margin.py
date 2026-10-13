#!/usr/bin/env python3
"""An interval on the negative-set selection margin (D064).

D002 chose set C over set A on composition-only AUROC 0.6085 against 0.6120 --
a margin of 0.0035 reported as a point estimate with no interval. The choice is
preregistered and is not revised here. What this adds is the interval the
original comparison lacked, so a reader can see how much the margin supports.

Protocol is negative_diagnostic.py's own: a uniform 60,000-peptide sample of the
observed union as positives, length-matched unobserved decoys as negatives,
closed-form LDA on 20-dimensional amino-acid composition fitted on the first
half and scored on the second, midrank AUROC.

The bootstrap is paired on the positives, which are literally the same peptides
in both arms, and resamples each arm's negatives independently, because index j
in set A has no correspondence to index j in set C.

Deterministic: fixed seeds, tracked inputs only. Classified BYTES in
scripts/regen_check.py.
"""

import csv, gzip, json, random, sys
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
import negative_diagnostic as ND                        # noqa: E402

OUT = REPO/'results'/'qc'/'negset_margin.json'
AA, N, SEED = ND.AA, ND.N, ND.SEED
B_BOOT = 10000
NOMINAL = 0.99


def auroc(y, s):
    """Midrank AUROC. Identical to negative_diagnostic.auroc, which computes the
    same midranks in a Python loop; agreement is asserted below before use."""
    r = rankdata(s, method='average')
    n1 = y.sum(); n0 = y.size - n1
    return float((r[y == 1].sum() - n1*(n1+1)/2) / (n1*n0))


def lda_halves(pos, neg):
    Xp, Xn = ND.comp(pos), ND.comp(neg)
    a, b = len(Xp)//2, len(Xn)//2
    trP, teP, trN, teN = Xp[:a], Xp[a:], Xn[:b], Xn[b:]
    mu1, mu0 = trP.mean(0), trN.mean(0)
    S = np.cov(np.vstack([trP-mu1, trN-mu0]).T) + np.eye(20)*1e-6
    w = np.linalg.solve(S, mu1-mu0)
    return teP @ w, teN @ w


def main():
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)

    observed = set()
    for p in sorted(ND.PEP.glob('*.csv.gz')):
        with gzip.open(p, 'rt', newline='') as fh:
            for r in csv.DictReader(fh):
                observed.add(r['sequence'])
    pos = rng.sample(sorted(observed), N)
    lengths = [len(s) for s in pos]
    prot = ND.read_proteome()
    pool = [s for s in prot if len(s) >= 13]

    def draw(src, n):
        out = []
        while len(out) < n:
            s = src[nprng.integers(len(src))]
            L = lengths[len(out) % len(lengths)]
            if len(s) <= L:
                continue
            i = int(nprng.integers(0, len(s)-L))
            c = s[i:i+L]
            if c not in observed and set(c) <= set(AA):
                out.append(c)
        return out

    setA = draw(pool, N)

    # Set B is not used here, but negative_diagnostic.py builds it between A and
    # C and consumes the random.Random stream doing so. Reproducing that
    # consumption is what makes set C below identical to the frozen one, and
    # therefore what makes this an interval on the preregistered margin rather
    # than on a fresh draw. The assertion further down is the check.
    nb = 0
    for q in pos:
        for _ in range(8):
            l = list(q); rng.shuffle(l)
            if ''.join(l) not in observed:
                nb += 1; break
        if nb >= N:
            break

    src = set()
    obs_sample = rng.sample(sorted(observed), 40000)
    for s in pool:
        if len(src) > 4000:
            break
        for o in obs_sample[:2000]:
            if o in s:
                src.add(s); break
    srcC = sorted(src) or pool[:4000]
    setC = draw(srcC, N)

    arms, pts = {}, {}
    for name, neg in (('A', setA), ('C', setC)):
        p_, n_ = lda_halves(pos, neg)
        arms[name] = (p_, n_)
        y = np.concatenate([np.ones(p_.size), np.zeros(n_.size)])
        sc = np.concatenate([p_, n_])
        ref = float(ND.auroc(y, sc))
        assert abs(ref - auroc(y, sc)) < 1e-12, 'estimator mismatch'
        cp = ND.comp(pos).mean(0); cn = ND.comp(neg).mean(0)
        pts[name] = {'auroc_composition_only': ref,
                     'total_abs_divergence_pp': float(100*np.abs(cn-cp).sum())}

    # The margin is the preregistered one only if both arms reproduce the frozen
    # diagnostic. Checked, not assumed.
    frozen = json.loads((REPO/'results'/'qc'/'negative_diagnostic.json').read_text())
    for nm in ('A', 'C'):
        want = frozen['results'][nm]['auroc_composition_only']
        got = pts[nm]['auroc_composition_only']
        assert abs(want - got) < 1e-12, (
            f'set {nm} does not reproduce negative_diagnostic.json: '
            f'{got!r} vs {want!r}')

    brng = np.random.default_rng(SEED)
    npos, nneg = arms['A'][0].size, arms['A'][1].size
    y = np.concatenate([np.ones(npos), np.zeros(nneg)])
    d = np.empty(B_BOOT)
    for b in range(B_BOOT):
        ip = brng.integers(0, npos, npos)          # shared -> paired
        a_ = {}
        for k in ('A', 'C'):
            inn = brng.integers(0, nneg, nneg)     # independent per arm
            a_[k] = auroc(y, np.concatenate([arms[k][0][ip], arms[k][1][inn]]))
        d[b] = a_['A'] - a_['C']
    q = (1.0 - NOMINAL) / 2 * 100
    lo, hi = np.percentile(d, [q, 100-q])

    rec = {
        'decision': 'D064',
        'what_this_is': ('the interval D002 did not report on the margin that '
                         'selected the negative set. The choice is preregistered '
                         'and is not revised.'),
        'protocol': ("negative_diagnostic.py's: uniform 60,000-peptide sample of "
                     'the union as positives, length-matched unobserved decoys, '
                     'closed-form LDA on 20-dim composition, first half fits and '
                     'second half scores, midrank AUROC'),
        'n_per_class': N, 'seed': SEED, 'B': B_BOOT, 'nominal': NOMINAL,
        'bootstrap': ('paired on positives, which are the same peptides in both '
                      'arms; each arm resamples its own negatives independently'),
        'n_source_proteins_setC': len(srcC),
        'reproduces_negative_diagnostic': True,
        'arms': pts,
        'margin_A_minus_C': {
            'point': pts['A']['auroc_composition_only']
                     - pts['C']['auroc_composition_only'],
            'ci99': [float(lo), float(hi)],
            'crosses_zero': bool(lo <= 0.0 <= hi)},
        'reading': ('A margin whose interval crosses zero does not establish that '
                    'set C is the harder set. D002 is sound on its stated '
                    'rationale -- same expression context -- and that rationale, '
                    'not this margin, is what the choice rests on.'),
    }
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    for k, v in pts.items():
        print(f"  set {k}  AUROC {v['auroc_composition_only']:.4f}  "
              f"divergence {v['total_abs_divergence_pp']:.3f}pp")
    print(f"  A - C  {rec['margin_A_minus_C']['point']:+.4f}  "
          f"[{lo:+.4f}, {hi:+.4f}]  "
          f"{'crosses zero' if rec['margin_A_minus_C']['crosses_zero'] else 'excludes zero'}")
    print(f"  set C source proteins: {len(srcC):,}")
    print(f'wrote {OUT.relative_to(REPO)}')


if __name__ == '__main__':
    main()
