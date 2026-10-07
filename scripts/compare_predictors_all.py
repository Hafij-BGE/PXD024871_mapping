#!/usr/bin/env python3
"""§18 across every admitted predictor, on the two row sets D036 fixed.

`compare_predictors.py` covered the CNN and the two MHCflurry lines and is kept
as QC_G11 used it. This supersedes it.

D033 fixed the primary as rows naive to both compared systems. With four
predictors the naive extension -- rows naive to all of them -- would let the
most contaminated predictor shrink every other contrast, so D036 fixed two:

  PAIRWISE   each CNN-vs-X contrast on rows naive to the CNN and X ALONE.
             Largest valid row set per contrast; predictors are NOT mutually
             comparable across these sets, and the output says so.
  COMMON     all systems on rows naive to every system. Directly comparable,
             smaller. The price of comparability.

The full partition is also reported, as D006's secondary, with both
memorisation advantages left in.

The CNN score is the mean per-unit AP across the frozen 25 models (D027).
Intervals are nominal-99% cluster bootstraps over participants (D008). Nothing
is retrained.
"""

import csv, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
DER, RES = REPO/'data'/'derived', REPO/'results'/'model'
PRED, OUT = REPO/'results'/'predictors', REPO/'results'/'qc'
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                              # noqa: E402
from train_cnn import (CNN, encode, average_precision, cluster_ci,  # noqa: E402
                       paired_ci, load)

# name -> (scores csv, score column, overlap-list slug)
PREDICTORS = [
    ('MHCflurry 2.0.0', 'mhcflurry_2_0_0_test_scores.csv', 'presentation_score',
     'MHCflurry_2_0_0'),
    ('MHCflurry 2.3.0', 'mhcflurry_2_3_0_test_scores.csv', 'presentation_score',
     'MHCflurry_2_3_0'),
    ('NetMHCpan 4.1', 'netmhcpan_4_1_test_scores.csv', 'score_el', 'NetMHCpan_4_1'),
    ('MixMHCpred 3.0', 'mixmhcpred_3_0_test_scores.csv', 'score_best',
     'MixMHCpred_3_0'),
]


def main():
    rows, split = load()
    cnn_seen = {s for s, u, _ in rows if split[u]['primary_partition'] == 'cv'}

    scores, seen = {}, {}
    for name, fn, col, slug in PREDICTORS:
        f = PRED/fn
        if not f.exists():
            sys.exit(f"missing {f}")
        scores[name] = {(r['unit_id'], r['sequence']): float(r[col])
                        for r in csv.DictReader(f.open(newline=''))}
        ov = DER/f'TEST_PREDICTOR_OVERLAP_{slug}.csv'
        seen[name] = {r['sequence'] for r in csv.DictReader(ov.open(newline=''))}
        print(f"{name:<18}{len(scores[name]):>9,} scored rows   "
              f"{len(seen[name]):>7,} overlapping sequences")

    names = [n for n, *_ in PREDICTORS]
    keep = [(s, u, l) for s, u, l in rows
            if split[u]['primary_partition'] == 'test'
            and all((u, s) in scores[n] for n in names)]
    print(f"\nrows every system scored: {len(keep):,}\n")

    X = encode([s for s, _, _ in keep])
    y = np.array([l for _, _, l in keep])
    uarr = np.array([u for _, u, _ in keep])
    sarr = np.array([s for s, _, _ in keep], dtype=object)
    units = sorted(set(uarr))

    meta = json.loads((RES/'final.json').read_text())
    cfg = meta['config']
    S, Xt = [], torch.from_numpy(X)
    for m_ in meta['models']:
        ck = torch.load(RES/m_['file'], map_location='cpu', weights_only=False)
        m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval()
        with torch.no_grad():
            S.append(torch.cat([m(Xt[i:i+8192])
                                for i in range(0, len(Xt), 8192)]).numpy())
    S = np.vstack(S)
    P = {n: np.array([scores[n][(u, s)] for s, u, _ in keep]) for n in names}

    rng = np.random.default_rng(seed('predictor_bootstrap'))

    def per_unit_cnn(mask):
        out = {}
        for u in units:
            k = (uarr == u) & mask
            if y[k].sum() in (0, k.sum()):
                continue
            out[u] = float(np.mean([average_precision(y[k], S[j][k])
                                    for j in range(S.shape[0])]))
        return out

    def per_unit(mask, v):
        out = {}
        for u in units:
            k = (uarr == u) & mask
            if y[k].sum() in (0, k.sum()):
                continue
            out[u] = average_precision(y[k], v[k])
        return out

    def mask_naive(exclude):
        bad = set(cnn_seen)
        for n in exclude:
            bad |= seen[n]
        return np.array([s not in bad for s in sarr])

    def summarise(label, mask, systems):
        print(f"=== {label} ===")
        print(f"  rows {int(mask.sum()):,}   positives {int(y[mask].sum()):,}   "
              f"prevalence {y[mask].mean():.3f}")
        pu = {'CNN': per_unit_cnn(mask)}
        for n in systems:
            pu[n] = per_unit(mask, P[n])
        rec = {'label': label, 'n_rows': int(mask.sum()),
               'prevalence': float(y[mask].mean()), 'systems': {}, 'contrasts': []}
        for k, d in pu.items():
            us = sorted(d)
            v = np.array([d[u] for u in us])
            lo, hi = cluster_ci(v, rng)
            print(f"  {k:<18} units {v.size:>2}  AP {v.mean():.4f}  "
                  f"CI99 [{lo:.4f}, {hi:.4f}]")
            rec['systems'][k] = {'n_units': int(v.size), 'mean_ap': float(v.mean()),
                                 'ci99': [lo, hi], 'per_unit': d}
        for n in systems:
            a, b = pu['CNN'], pu[n]
            us = sorted(set(a) & set(b))
            d = np.array([a[u] - b[u] for u in us])
            lo, hi = paired_ci(d, rng)
            print(f"  -> CNN - {n}: {d.mean():+.4f}  CI99 [{lo:+.4f}, {hi:+.4f}]  "
                  f"({int((d > 0).sum())}/{len(us)} units)")
            rec['contrasts'].append({'vs': n, 'difference': float(d.mean()),
                                     'ci99': [lo, hi], 'n_units': len(us),
                                     'n_cnn_better': int((d > 0).sum())})
        print()
        return rec

    report = {'n_rows_all_scored': len(keep), 'cnn_config': cfg,
              'n_cnn_models': int(S.shape[0]), 'pairwise': [], 'common': None,
              'full': None,
              'note': 'Pairwise row sets differ between contrasts, so the '
                      'predictors are NOT comparable to each other there. Use '
                      'the common row set for predictor-vs-predictor.'}

    print("PAIRWISE  — each contrast on the largest row set valid for it\n")
    for n in names:
        report['pairwise'].append(summarise(f'naive to CNN + {n}',
                                            mask_naive([n]), [n]))

    print("COMMON  — every system on rows naive to all of them\n")
    report['common'] = summarise('naive to CNN + all four predictors',
                                 mask_naive(names), names)

    print("FULL PARTITION  — D006's secondary; both advantages left in\n")
    report['full'] = summarise('full test partition',
                               np.ones(len(y), bool), names)

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT/'predictor_comparison_all.json', 'w'), indent=1)
    with (PRED/'comparison_with_predictors_all.csv').open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['row_set', 'system', 'n_units', 'mean_per_unit_ap',
                    'ci99_lo', 'ci99_hi', 'n_rows', 'prevalence'])
        for rec in report['pairwise'] + [report['common'], report['full']]:
            for k, s in rec['systems'].items():
                w.writerow([rec['label'], k, s['n_units'], f"{s['mean_ap']:.6f}",
                            f"{s['ci99'][0]:.6f}", f"{s['ci99'][1]:.6f}",
                            rec['n_rows'], f"{rec['prevalence']:.6f}"])
    print(f"wrote {OUT/'predictor_comparison_all.json'} and "
          f"results/predictors/comparison_with_predictors_all.csv")


if __name__ == '__main__':
    main()
