#!/usr/bin/env python3
"""The multi-allele test (D031). Two parts.

PART A -- replication. For each of the five most frequent class-I alleles, train
one arm on carriers and one on locus-certain non-carriers, equal size, and score
both on the held-out carriers' allele-exclusive stratum.

PART B -- the decisive, SYMMETRIC test. A*02:01 and C*07:02 are the only pair
whose mutually exclusive groups are both large enough. Both arms are
carrier-trained, each for its own allele, so neither group is the "defined by an
absence" group that made D029's contrast II uninformative. A SIGN REVERSAL
between the two exclusive strata is the signature of an allele effect.

Every row set excludes positives either compared arm saw in training, and every
evaluation prints the seen-fraction per arm -- the standing check from D030,
added after the first stratum turned out to be 97.93% memorised by one arm and
0.00% by the other.
"""

import csv, json, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                                 # noqa: E402
from train_cnn import (CNN, encode, composition, lda_scores, fit,      # noqa: E402
                       average_precision, cluster_ci, paired_ci, load, MAX_EPOCHS)

RES = REPO/'results'/'model'
DER = REPO/'data'/'derived'
ALLELES = ['HLA-A*02:01', 'HLA-C*07:02', 'HLA-A*01:01', 'HLA-A*24:02', 'HLA-B*07:02']
PAIR = ('HLA-A*02:01', 'HLA-C*07:02')


def locus(a):
    return a.split('*')[0]


def genotypes():
    g, two = {}, {}
    for r in csv.DictReader((DER/'UNIT_GENOTYPE.csv').open()):
        al = [a for a in r['hla_genotype'].split(';') if a]
        g[r['unit_id']] = set(al)
        c = Counter(locus(a) for a in al)
        two[r['unit_id']] = {L for L, n in c.items() if n == 2}
    return g, two


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', default='AB', choices=['A', 'B', 'AB'])
    ap.add_argument('--replicates', type=int, default=5)
    ap.add_argument('--max-epochs', type=int, default=MAX_EPOCHS)
    a_ = ap.parse_args()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    full = (a_.max_epochs == MAX_EPOCHS and a_.replicates == 5)
    tag = '' if full else f'.e{a_.max_epochs}r{a_.replicates}'
    outfile = RES/('multi_allele.json' if full else 'multi_allele.PARTIAL.json')
    if not full:
        print(f"*** SHORTENED RUN (max_epochs={a_.max_epochs}, "
              f"replicates={a_.replicates}). Not a result. ***\n")

    cfg = json.loads((RES/'selection.json').read_text())['selected']['config']
    g, two = genotypes()
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
    print(f"torch {torch.__version__}  device {device}  config {cfg}\n")

    def strat(units, n, rng):
        """platform-stratified draw (D025)"""
        byp = defaultdict(list)
        for u in units:
            byp[split[u]['platform']].append(u)
        first = []
        for pl in sorted(byp):
            lst = sorted(byp[pl]); rng.shuffle(lst)
            first += lst[:round(n*len(lst)/len(units))]
        rest = [u for u in units if u not in set(first)]; rng.shuffle(rest)
        while len(first) < n:
            first.append(rest.pop())
        return sorted(first), sorted(u for u in units if u not in set(first))

    def carriers(al):
        return sorted(u for u in g if al in g[u])

    def certain_non(al):
        """two alleles reported at the locus, neither of them al"""
        L = locus(al)
        return sorted(u for u in g if al not in g[u] and L in two[u])

    models_cache = {}

    def train_arm(arm_id, units_train, units_val):
        key = arm_id
        if key in models_cache:
            return models_cache[key]
        tri = np.concatenate([where[u] for u in units_train])
        vai = np.concatenate([where[u] for u in units_val])
        ms, logs = [], []
        print(f"  [{arm_id}] train {len(units_train)} units / {len(tri):,} rows, "
              f"val {len(units_val)} units", flush=True)
        for r_ in range(a_.replicates):
            # NOT hash(arm_id): Python randomises string hashing per process, so
            # that would give a different seed on every run. seeds.seed() hashes
            # the purpose string with SHA-256, which is stable across processes.
            sd = seed(f'multi_init:{arm_id}', r_)
            path = RES/f'multi_{arm_id}_s{r_}{tag}.pt'
            if path.exists():
                ck = torch.load(path, map_location='cpu', weights_only=False)
                if ck.get('max_epochs') != a_.max_epochs or ck.get('cfg') != cfg:
                    sys.exit(f"REFUSING to reuse {path.name}: budget/config mismatch")
                m = CNN(**cfg).to(device); m.load_state_dict(ck['state']); m.eval()
                ms.append(m); logs.append({'replicate': r_, 'val_ap': ck['val_ap'],
                                           'epochs': ck['epochs'], 'cached': True})
                print(f"    seed {r_}: cached ({ck['val_ap']:.4f})", flush=True)
                continue
            t0 = time.time()
            m, vap, ep = fit(cfg, (X[tri], y[tri]), (X[vai], y[vai]), sd,
                             device, a_.max_epochs)
            torch.save({'state': m.state_dict(), 'cfg': cfg, 'seed': sd,
                        'arm': arm_id, 'replicate': r_, 'val_ap': vap, 'epochs': ep,
                        'max_epochs': a_.max_epochs, 'train_units': units_train,
                        'val_units': units_val}, path)
            m.eval(); ms.append(m)
            logs.append({'replicate': r_, 'val_ap': vap, 'epochs': ep, 'cached': False})
            print(f"    seed {r_}: val AP {vap:.4f} ({ep} ep, {time.time()-t0:.0f}s)",
                  flush=True)
        models_cache[key] = (ms, logs, tri, set(units_train))
        return models_cache[key]

    rng_neg = np.random.default_rng(seed('multi_negatives'))
    rng = np.random.default_rng(seed('multi_bootstrap'))

    def seen_set(units_train):
        return {s for s, us in obs.items() if us & units_train}

    def build(test_units, member, naive, ratio1to1=True):
        """positives in `member` and in `naive`, plus negatives (1:1 per unit)"""
        out = []
        for u in sorted(test_units):
            idx = where[u]
            pos = idx[(y[idx] == 1) &
                      np.array([(s in member) and (s in naive) for s in sarr[idx]])]
            if len(pos) < 8:
                continue
            neg = idx[y[idx] == 0]
            out.append(pos)
            out.append(rng_neg.choice(neg, size=len(pos), replace=False)
                       if ratio1to1 else neg)
        return np.concatenate(out) if out else np.array([], dtype=int)

    def per_unit(ms, tei, tri):
        Xt = torch.from_numpy(X[tei]).to(device)
        S = []
        for m in ms:
            with torch.no_grad():
                S.append(torch.cat([m(Xt[i:i+8192])
                                    for i in range(0, len(Xt), 8192)]).cpu().numpy())
        S = np.vstack(S)
        fl = lda_scores(C[tri], y[tri], C[tei])
        yte, ute = y[tei], uarr[tei]
        pu, puf = {}, {}
        for u in sorted(set(ute)):
            k = ute == u
            if yte[k].sum() in (0, k.sum()):
                continue
            pu[u] = float(np.mean([average_precision(yte[k], S[j][k])
                                   for j in range(S.shape[0])]))
            puf[u] = average_precision(yte[k], fl[k])
        return pu, puf

    report = {'config': cfg, 'replicates': a_.replicates,
              'max_epochs': a_.max_epochs, 'part_A': [], 'part_B': {}}
    if outfile.exists():
        old = json.loads(outfile.read_text())
        report['part_A'] = old.get('part_A', [])
        report['part_B'] = old.get('part_B', {})

    def compare(label, tei, arms, nrows_note=''):
        """arms: list of (name, ms, tri, train_units). Prints each arm's
        seen-fraction on this row set -- the D030 standing check."""
        res = {}
        pos = tei[y[tei] == 1]
        for name, ms, tri, tu in arms:
            sseen = seen_set(tu)
            frac = float(np.mean([s in sseen for s in sarr[pos]])) if pos.size else 0.0
            pu, puf = per_unit(ms, tei, tri)
            us = sorted(pu)
            v = np.array([pu[u] for u in us]); vf = np.array([puf[u] for u in us])
            lo, hi = cluster_ci(v, rng)
            res[name] = {'per_unit': pu, 'floor_per_unit': puf,
                         'mean_ap': float(v.mean()), 'ci99': [lo, hi],
                         'floor_mean_ap': float(vf.mean()),
                         'seen_fraction': frac, 'n_units': int(v.size)}
            print(f"      {name:<22} units {v.size:>2}  AP {v.mean():.4f} "
                  f"CI99 [{lo:.4f}, {hi:.4f}]  floor {vf.mean():.4f}  "
                  f"SEEN {frac:.2%}", flush=True)
        if len(arms) == 2:
            n1, n2 = arms[0][0], arms[1][0]
            us = sorted(set(res[n1]['per_unit']) & set(res[n2]['per_unit']))
            d = np.array([res[n1]['per_unit'][u] - res[n2]['per_unit'][u] for u in us])
            lo, hi = paired_ci(d, rng)
            res['contrast'] = {'a': n1, 'b': n2, 'n_units': len(us),
                               'difference': float(d.mean()), 'ci99': [lo, hi],
                               'n_positive': int((d > 0).sum())}
            print(f"      -> paired {n1} - {n2}: {d.mean():+.4f}  "
                  f"CI99 [{lo:+.4f}, {hi:+.4f}]  ({int((d>0).sum())}/{len(us)})",
                  flush=True)
        res['n_rows'] = int(tei.size)
        res['label'] = label
        return res

    # ------------------------------------------------------------------ PART A
    if 'A' in a_.part:
        print("="*78); print("PART A — replication across five alleles"); print("="*78)
        done = {r['allele'] for r in report['part_A']}
        for ai, al in enumerate(ALLELES):
            if al in done:
                print(f"\n--- {al}: cached ---"); continue
            carr, non = carriers(al), certain_non(al)
            r1 = random.Random(seed('multi_split', ai))
            r2 = random.Random(seed('multi_valsplit', ai))
            cp, ctest = strat(carr, 10, r1)
            npool, _ = strat(non, 10, r1)
            ctr, cva = strat(cp, 8, r2)
            ntr, nva = strat(npool, 8, r2)
            print(f"\n--- {al}: {len(carr)} carriers, {len(non)} certain non-carriers, "
                  f"{len(ctest)} carrier test units ---")
            A_c = train_arm(f"A{ai}_{al.split('*')[1].replace(':','')}_carr", ctr, cva)
            A_n = train_arm(f"A{ai}_{al.split('*')[1].replace(':','')}_non", ntr, nva)
            # Both hoisted out of the comprehensions. seen_set() builds a
            # 467k-element set; calling it per sequence made this O(n^2), about
            # 2e11 operations, and the first run sat in it for ten minutes.
            seen_either = seen_set(A_c[3] | A_n[3])
            ct_set = set(ctest)
            naive = {s for s in obs if s not in seen_either}
            excl = {s for s, us in obs.items()
                    if len(us & ct_set) >= 2 and not any(al not in g[u] for u in us)}
            ctrl = {s for s, us in obs.items()
                    if len(us & ct_set) >= 2 and any(al not in g[u] for u in us)}
            shared = {s for s, us in obs.items()
                      if any(al in g[u] for u in us) and any(al not in g[u] for u in us)}
            print(f"    {al}-exclusive {len(excl):,} seqs   "
                  f"recurrence control {len(ctrl):,}   class-shared {len(shared):,}")
            arms = [(f'{al} carrier-trained', A_c[0], A_c[2], A_c[3]),
                    ('non-carrier-trained', A_n[0], A_n[2], A_n[3])]
            rec = {'allele': al, 'n_carriers': len(carr), 'n_certain_non': len(non),
                   'carrier_test_units': ctest,
                   'train_units': {'carrier': ctr, 'non': ntr},
                   'val_units': {'carrier': cva, 'non': nva},
                   'strata_sizes': {'exclusive': len(excl), 'control': len(ctrl),
                                    'shared': len(shared)},
                   'fits': {'carrier': A_c[1], 'non': A_n[1]}, 'comparisons': []}
            for nm, member in ((f'{al}-EXCLUSIVE stratum', excl),
                               ('recurrence-matched control', ctrl),
                               ('class-shared (neutral delta)', shared)):
                tei = build(ctest, member, naive)
                if tei.size == 0:
                    print(f"    {nm}: EMPTY, skipped"); continue
                print(f"    {nm}  ({tei.size:,} rows)")
                rec['comparisons'].append(compare(nm, tei, arms))
            report['part_A'].append(rec)
            json.dump(report, open(outfile, 'w'), indent=1)

    # ------------------------------------------------------------------ PART B
    if 'B' in a_.part:
        print("\n" + "="*78)
        print("PART B — symmetric pair: both arms carrier-trained, sign reversal expected")
        print("="*78)
        A, B = PAIR
        gA = sorted(u for u in g if A in g[u] and B not in g[u] and locus(B) in two[u])
        gB = sorted(u for u in g if B in g[u] and A not in g[u] and locus(A) in two[u])
        rA = random.Random(seed('multi_split', 100))
        rV = random.Random(seed('multi_valsplit', 100))
        pA, tA = strat(gA, 8, rA); pB, tB = strat(gB, 8, rA)
        trA, vaA = strat(pA, 6, rV); trB, vaB = strat(pB, 6, rV)
        print(f"  {A} not {B}: {len(gA)} units -> train {len(trA)}, test {len(tA)}")
        print(f"  {B} not {A}: {len(gB)} units -> train {len(trB)}, test {len(tB)}")
        MA = train_arm('B_A0201', trA, vaA)
        MB = train_arm('B_C0702', trB, vaB)
        seen_either = seen_set(MA[3] | MB[3])        # hoisted, as in Part A
        naive = {s for s in obs if s not in seen_either}
        arms = [(f'{A}-trained', MA[0], MA[2], MA[3]),
                (f'{B}-trained', MB[0], MB[2], MB[3])]
        report['part_B'] = {'pair': [A, B], 'groups': {'A_not_B': gA, 'B_not_A': gB},
                            'train_units': {'A': trA, 'B': trB},
                            'val_units': {'A': vaA, 'B': vaB},
                            'test_units': {'A': tA, 'B': tB},
                            'fits': {'A': MA[1], 'B': MB[1]}, 'comparisons': []}
        for al, test_units in ((A, tA), (B, tB)):
            tu_set = set(test_units)
            excl = {s for s, us in obs.items()
                    if len(us & tu_set) >= 2
                    and not any(al not in g[u] for u in us)}
            ctrl = {s for s, us in obs.items()
                    if len(us & tu_set) >= 2 and any(al not in g[u] for u in us)}
            shared = {s for s, us in obs.items()
                      if any(al in g[u] for u in us) and any(al not in g[u] for u in us)}
            print(f"\n  {al}-exclusive {len(excl):,} seqs  control {len(ctrl):,}  "
                  f"shared {len(shared):,}")
            for nm, member in ((f'{al}-EXCLUSIVE stratum', excl),
                               (f'{al} recurrence-matched control', ctrl),
                               (f'{al} class-shared (neutral delta)', shared)):
                tei = build(test_units, member, naive)
                if tei.size == 0:
                    print(f"    {nm}: EMPTY, skipped"); continue
                print(f"    {nm}  ({tei.size:,} rows)")
                report['part_B']['comparisons'].append(compare(nm, tei, arms))
        json.dump(report, open(outfile, 'w'), indent=1)

    json.dump(report, open(outfile, 'w'), indent=1)
    print(f"\nwrote {outfile}")


if __name__ == '__main__':
    main()
