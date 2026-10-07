#!/usr/bin/env python3
"""Correct the D029 contrasts for memorisation. No model is retrained.

WHY THIS EXISTS. D029's allele-enriched stratum was defined as "observed in >=2
of the 15 C_pool units and in none of the 15 N_pool units". C_pool is M_AM's
training pool and N_pool is M_AD's. So the definition guaranteed that M_AM had
seen the stratum sequences in training and that M_AD provably had not:
measured, 97.93% of the stratum's rows in the held-out carriers are sequences
M_AM trained on, against 0.00% for M_AD. The +0.0660 that definition produced
is therefore a memorisation measurement wearing an allele label, and it is the
same failure as the first TEST_LEAKFREE mask, which selected a set with no
negatives and returned a perfect 1.0000. A subset must not be defined by a
property that fixes the answer.

WHAT THIS DOES INSTEAD. Every row set below excludes any positive either
matched arm saw in training, so the two models are equally naive to every
sequence scored. Carrier-linkage is then expressed the only way that survives:
recurrence among HELD-OUT carriers plus absence from every non-carrier.

A recurrence-matched control is scored alongside it -- equally recurrent,
equally unseen, but NOT exclusive to one allele class. If the contrast tracks
alleles it should be larger on the exclusive stratum than on the control; if it
tracks recurrence it should be the same on both.
"""

import csv, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                                # noqa: E402
from train_cnn import (CNN, encode, composition, lda_scores,          # noqa: E402
                       average_precision, cluster_ci, paired_ci, load)

RES = REPO/'results'/'model'


def main():
    A = json.loads((RES/'allele.json').read_text())
    arms = {a['id']: a for a in A['arms']}
    P = A['pools']
    Cp, Ct, Np, Nt = (set(P[k]) for k in ('C_pool', 'C_test', 'N_pool', 'N_test'))
    car, non = Cp | Ct, Np | Nt
    cfg = A['config']

    rows, split = load()
    seqs = [s for s, _, _ in rows]
    X, y = encode(seqs), np.array([l for _, _, l in rows])
    uarr = np.array([u for _, u, _ in rows])
    sarr = np.array(seqs, dtype=object)
    where = defaultdict(list)
    for i, u in enumerate(uarr):
        where[u].append(i)
    where = {u: np.array(v) for u, v in where.items()}
    C = composition(seqs)

    obs = defaultdict(set)
    for s, u, l in rows:
        if l == 1:
            obs[s].add(u)

    # leakage is defined on the ACTUAL training units, not the pools
    tr = {k: set(arms[k]['train_units']) for k in arms}
    seen = {k: {s for s, us in obs.items() if us & tr[k]} for k in tr}
    naive = {s for s in obs if s not in seen['M_AM'] and s not in seen['M_AD']}
    print(f"sequences neither matched arm trained on: {len(naive):,} of {len(obs):,}\n")

    # exclusive strata: recurrent among held-out units of one class, absent from
    # every unit of the other class, and unseen by both training sets
    excl = {'carrier':    {s for s, u in obs.items()
                           if len(u & Ct) >= 2 and not (u & non) and s in naive},
            'noncarrier': {s for s, u in obs.items()
                           if len(u & Nt) >= 2 and not (u & car) and s in naive}}
    # recurrence-matched controls: same recurrence, same naivety, NOT exclusive
    ctrl = {'carrier':    {s for s, u in obs.items()
                           if len(u & Ct) >= 2 and (u & non) and s in naive},
            'noncarrier': {s for s, u in obs.items()
                           if len(u & Nt) >= 2 and (u & car) and s in naive}}
    for k in excl:
        print(f"{k:<11} exclusive {len(excl[k]):>6,} seqs   "
              f"recurrence-matched control {len(ctrl[k]):>6,} seqs")
    print()

    rng_n = np.random.default_rng(seed('allele_leakfree_negatives'))

    def build(units, which, kind):
        """kind: 'all' = every leak-free positive + all negatives;
        'excl'/'ctrl' = that stratum's positives + 1:1 negatives per unit."""
        out = []
        for u in sorted(units):
            idx = where[u]
            pos_mask = y[idx] == 1
            if kind == 'all':
                keep = np.array([s in naive for s in sarr[idx]])
                pos = idx[pos_mask & keep]
                out.append(pos); out.append(idx[y[idx] == 0])
            else:
                S = (excl if kind == 'excl' else ctrl)[which]
                pos = idx[pos_mask & np.array([s in S for s in sarr[idx]])]
                if len(pos) < 8:
                    continue
                neg = idx[y[idx] == 0]
                out.append(pos)
                out.append(rng_n.choice(neg, size=len(pos), replace=False))
        return np.concatenate(out) if out else np.array([], dtype=int)

    models = {}
    for aid in ('M_AM', 'M_AD', 'P_AD'):
        ms = []
        for f in arms[aid]['fits']:
            ck = torch.load(RES/f['file'], map_location='cpu', weights_only=False)
            m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval(); ms.append(m)
        models[aid] = ms

    rng = np.random.default_rng(seed('allele_leakfree_bootstrap'))
    cache, report = {}, {'note': __doc__.strip().splitlines()[0],
                         'leakage_rule': 'positives seen by either matched arm '
                                         'in training are excluded from every row set',
                         'strata_sizes': {k: {'exclusive': len(excl[k]),
                                              'control': len(ctrl[k])} for k in excl},
                         'evals': [], 'contrasts': []}

    def score(aid, tei, train_idx):
        key = (aid, tei.tobytes())
        if key in cache:
            return cache[key]
        Xt = torch.from_numpy(X[tei])
        S = []
        for m in models[aid]:
            with torch.no_grad():
                S.append(torch.cat([m(Xt[i:i+8192])
                                    for i in range(0, len(Xt), 8192)]).numpy())
        S = np.vstack(S)
        fl = lda_scores(C[train_idx], y[train_idx], C[tei])
        yte, ute = y[tei], uarr[tei]
        pu, puf = {}, {}
        for u in sorted(set(ute)):
            k = ute == u
            if yte[k].sum() in (0, k.sum()):
                continue
            pu[u] = float(np.mean([average_precision(yte[k], S[j][k])
                                   for j in range(S.shape[0])]))
            puf[u] = average_precision(yte[k], fl[k])
        cache[key] = (pu, puf)
        return pu, puf

    def emit(name, aid, pu, puf, nrows):
        us = sorted(pu)
        v = np.array([pu[u] for u in us]); vf = np.array([puf[u] for u in us])
        lo, hi = cluster_ci(v, rng); dlo, dhi = paired_ci(v - vf, rng)
        print(f"  {name}")
        print(f"    units {v.size}  rows {nrows:,}  mean AP {v.mean():.4f}  "
              f"CI99 [{lo:.4f}, {hi:.4f}]   floor {vf.mean():.4f}  "
              f"lift {v.mean()-vf.mean():+.4f} CI99 [{dlo:+.4f}, {dhi:+.4f}]", flush=True)
        report['evals'].append({'arm': aid, 'set': name, 'n_units': int(v.size),
                                'n_rows': int(nrows), 'mean_ap': float(v.mean()),
                                'ci99': [lo, hi], 'floor_mean_ap': float(vf.mean()),
                                'lift_over_floor': float(v.mean()-vf.mean()),
                                'lift_ci99': [dlo, dhi],
                                'per_unit': {u: pu[u] for u in us}})

    tri = {k: np.concatenate([where[u] for u in sorted(tr[k])]) for k in tr}

    specs = [('I', 'C_test (14 carriers)', Ct, 'carrier', 'M_AM', 'M_AD'),
             ('II', 'N_test (8 non-carriers)', Nt, 'noncarrier', 'M_AD', 'M_AM')]
    pus = {}
    for cname, tlabel, units, which, m_arm, x_arm in specs:
        for kind, klabel in (('all', 'leak-free, all rows'),
                             ('excl', f'leak-free {which}-EXCLUSIVE stratum'),
                             ('ctrl', f'leak-free recurrence-matched CONTROL')):
            tei = build(units, which, kind)
            if tei.size == 0:
                print(f"  {tlabel} / {klabel}: EMPTY, skipped"); continue
            print(f"{tlabel}  —  {klabel}")
            for aid in (m_arm, x_arm):
                pu, puf = score(aid, tei, tri[aid])
                tagn = 'matched' if aid == m_arm else 'mismatched'
                emit(f"{tagn} ({aid})", aid, pu, puf, tei.size)
                pus[(cname, kind, tagn)] = pu
            print()

    print("="*74)
    for cname, tlabel, units, which, m_arm, x_arm in specs:
        for kind, klabel in (('all', 'leak-free, all rows'),
                             ('excl', f'{which}-exclusive stratum'),
                             ('ctrl', 'recurrence-matched control')):
            a = pus.get((cname, kind, 'matched')); b = pus.get((cname, kind, 'mismatched'))
            if not (a and b):
                continue
            us = sorted(set(a) & set(b))
            d = np.array([a[u] - b[u] for u in us])
            lo, hi = paired_ci(d, rng)
            print(f"  Contrast {cname} — {tlabel} — {klabel}")
            print(f"    matched {np.mean([a[u] for u in us]):.4f}   "
                  f"mismatched {np.mean([b[u] for u in us]):.4f}   "
                  f"paired {d.mean():+.4f}  CI99 [{lo:+.4f}, {hi:+.4f}]  "
                  f"({int((d>0).sum())}/{len(us)} units positive)")
            report['contrasts'].append(
                {'contrast': cname, 'test_set': tlabel, 'scope': klabel,
                 'matched_arm': m_arm, 'mismatched_arm': x_arm, 'n_units': len(us),
                 'matched_mean': float(np.mean([a[u] for u in us])),
                 'mismatched_mean': float(np.mean([b[u] for u in us])),
                 'difference': float(d.mean()), 'ci99': [lo, hi],
                 'n_units_positive': int((d > 0).sum())})
    print("="*74)

    # P_AD's preregistered headline, leakage-free against its own training units
    print("\nP_AD (preregistered D001) — leakage-free against its own 18 training units")
    pad_naive = {s for s in obs if s not in seen['P_AD']}
    out = []
    for u in sorted(Cp | Ct):
        idx = where[u]
        keep = np.array([s in pad_naive for s in sarr[idx]])
        out.append(idx[(y[idx] == 1) & keep]); out.append(idx[y[idx] == 0])
    tei = np.concatenate(out)
    pu, puf = score('P_AD', tei, tri['P_AD'])
    emit('all 29 carriers, leakage-free', 'P_AD', pu, puf, tei.size)

    json.dump(report, open(RES/'allele_leakfree.json', 'w'), indent=1)
    print(f"\nwrote {RES/'allele_leakfree.json'}")


if __name__ == '__main__':
    main()
