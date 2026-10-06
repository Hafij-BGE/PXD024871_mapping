#!/usr/bin/env python3
"""Can each candidate negative set be separated from positives on composition alone?

D002 lists three negative constructions and selects none. The decisive risk is
that a model scores well by learning amino-acid composition rather than anything
about presentation. This measures that directly: fit the optimal LINEAR
classifier on 20-dimensional composition only, with no positional information,
and report held-out AUROC.

AUROC near 0.5 means composition carries no signal, so any performance the CNN
achieves must come from sequence structure. AUROC near 1.0 means the negative
set is separable before the model learns anything, and every downstream metric
is inflated.

Closed-form LDA rather than an iterative fit: it is the optimal linear rule
under equal covariance, so a low score is evidence about the data and not about
optimisation having failed.
"""

import csv, gzip, json, random, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
PEP = REPO/'data'/'derived'/'peptides'
FASTA = REPO/'data'/'raw'/'S5'/'UP000005640_9606.fasta.gz'
OUT = REPO/'results'/'qc'
AA = 'ACDEFGHIKLMNPQRSTVWY'
IDX = {a: i for i, a in enumerate(AA)}
SEED = 20261006
N = 60000          # per class for the diagnostic


def comp(seqs):
    X = np.zeros((len(seqs), 20), dtype=np.float32)
    for i, s in enumerate(seqs):
        for ch in s:
            j = IDX.get(ch)
            if j is not None:
                X[i, j] += 1
        X[i] /= max(len(s), 1)
    return X


def auroc(y, s):
    """Rank AUROC with MIDRANKS for ties.

    Ties are not an edge case here: the shuffled-decoy set has composition
    identical to the positives by construction, so the LDA direction is the
    zero vector and every score is equal. Without midranks that degenerate
    case returns 0.0 -- an artefact of argsort order, not a measurement -- and
    would read as perfect inverse separation rather than as no information.
    """
    s = np.asarray(s, float)
    o = np.argsort(s, kind='mergesort')
    ss = s[o]
    r = np.empty(len(s), float)
    i = 0
    while i < len(ss):
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1.0      # midrank over the tied block
        i = j + 1
    n1 = y.sum(); n0 = len(y) - n1
    return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def lda_auroc(pos, neg, rng):
    Xp, Xn = comp(pos), comp(neg)
    npos, nneg = len(Xp)//2, len(Xn)//2
    trP, teP = Xp[:npos], Xp[npos:]
    trN, teN = Xn[:nneg], Xn[nneg:]
    mu1, mu0 = trP.mean(0), trN.mean(0)
    S = np.cov(np.vstack([trP - mu1, trN - mu0]).T) + np.eye(20)*1e-6
    w = np.linalg.solve(S, mu1 - mu0)
    sc = np.concatenate([teP @ w, teN @ w])
    y = np.concatenate([np.ones(len(teP)), np.zeros(len(teN))])
    return float(auroc(y, sc))


def read_proteome():
    seqs, cur = [], []
    with gzip.open(FASTA, 'rt') as fh:
        for line in fh:
            if line.startswith('>'):
                if cur: seqs.append(''.join(cur)); cur = []
            else:
                cur.append(line.strip())
    if cur: seqs.append(''.join(cur))
    return seqs


def main():
    rng = random.Random(SEED)
    nprng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    observed, pos = set(), []
    for p in sorted(PEP.glob('*.csv.gz')):
        with gzip.open(p, 'rt', newline='') as fh:
            for r in csv.DictReader(fh):
                observed.add(r['sequence'])
    pos = rng.sample(sorted(observed), N)
    lengths = [len(s) for s in pos]
    print(f"observed universe {len(observed):,}; diagnostic sample {len(pos):,}")

    prot = read_proteome()
    print(f"proteome {len(prot):,} sequences")
    pool = [s for s in prot if len(s) >= 13]

    # ---- A: random proteome substrings, length-matched, not observed
    setA = []
    while len(setA) < N:
        s = pool[nprng.integers(len(pool))]
        L = lengths[len(setA) % len(lengths)]
        if len(s) <= L: continue
        i = int(nprng.integers(0, len(s)-L))
        cand = s[i:i+L]
        if cand not in observed and set(cand) <= set(AA):
            setA.append(cand)

    # ---- B: per-peptide shuffle of positives. Composition identical by
    #         construction, so this is the control the diagnostic is calibrated on.
    setB = []
    for s in pos:
        for _ in range(8):
            l = list(s); rng.shuffle(l); c = ''.join(l)
            if c not in observed:
                setB.append(c); break
        if len(setB) >= N: break

    # ---- C: substrings of proteins that DID yield an observed peptide, but
    #         not themselves observed. Same expression context, so a harder set.
    src = set()
    obs_sample = rng.sample(sorted(observed), 40000)
    for s in pool:
        if len(src) > 4000: break
        for o in obs_sample[:2000]:
            if o in s: src.add(s); break
    src = sorted(src) or pool[:4000]
    setC = []
    while len(setC) < N:
        s = src[nprng.integers(len(src))]
        L = lengths[len(setC) % len(lengths)]
        if len(s) <= L: continue
        i = int(nprng.integers(0, len(s)-L))
        cand = s[i:i+L]
        if cand not in observed and set(cand) <= set(AA):
            setC.append(cand)

    print(f"\ncandidate sets: A {len(setA):,}  B {len(setB):,}  C {len(setC):,}"
          f"  (source proteins for C: {len(src):,})")

    print("\n=== composition-only separability (held out) ===")
    res = {}
    for name, neg, desc in [('A', setA, 'reference-derived, length-matched'),
                            ('B', setB, 'shuffled positives'),
                            ('C', setC, 'same source proteins, unobserved')]:
        a = lda_auroc(pos, neg, nprng)
        res[name] = {'auroc_composition_only': a, 'description': desc, 'n': len(neg)}
        verdict = ('INFLATING — separable before any model' if a > 0.75 else
                   'marginal' if a > 0.60 else 'clean — composition carries no signal')
        print(f"  set {name}  AUROC {a:.4f}   {desc:<36} {verdict}")

    print("\n=== amino-acid composition, largest divergences from positives ===")
    cp = comp(pos).mean(0)
    for name, neg in [('A', setA), ('B', setB), ('C', setC)]:
        cn = comp(neg).mean(0)
        d = cn - cp
        top = np.argsort(-np.abs(d))[:4]
        print(f"  {name}: " + "  ".join(f"{AA[i]} {100*d[i]:+.2f}pp" for i in top)
              + f"   | total abs divergence {100*np.abs(d).sum():.2f}pp")
        res[name]['total_abs_divergence_pp'] = float(100*np.abs(d).sum())

    json.dump({'seed': SEED, 'n_per_class': N, 'observed_universe': len(observed),
               'proteome_sequences': len(prot), 'results': res},
              open(OUT/'negative_diagnostic.json', 'w'), indent=1)
    print(f"\nwrote {OUT/'negative_diagnostic.json'}")


if __name__ == '__main__':
    main()
