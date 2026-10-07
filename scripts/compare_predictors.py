#!/usr/bin/env python3
"""Stage 2 of §18: CNN against MHCflurry on identical rows (D006, D033).

Three row sets, per D033. The primary is naive to BOTH systems, because
removing only the predictor's overlap would hand the CNN a selectively easier
dataset and §18 forbids that in those words:

  mutually naive        neither system trained on any sequence scored  [PRIMARY]
  predictor-naive only  D006 as literally written
  full partition        D006's secondary; both memorisation advantages left in

The CNN's score is the mean per-unit AP across the frozen 25 models (D027),
exactly as the endpoint was computed. Intervals are nominal-99% cluster
bootstraps over participants (D008). Nothing is retrained.
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

LINES = ['2.0.0', '2.3.0']


def main():
    rows, split = load()
    # what the CNN trained on: every sequence in the cv partition, either label.
    # Taken as the union over the 25 models (each saw 4 of 5 folds), which is
    # the conservative direction -- it can only shrink the naive subset.
    cnn_seen = {s for s, u, _ in rows if split[u]['primary_partition'] == 'cv'}

    scores, pred_seen = {}, {}
    for line in LINES:
        f = PRED/f"mhcflurry_{line.replace('.', '_')}_test_scores.csv"
        d = {}
        for r in csv.DictReader(f.open(newline='')):
            d[(r['unit_id'], r['sequence'])] = float(r['presentation_score'])
        scores[line] = d
        ov = PRED.parent.parent/'data'/'derived'/f"TEST_PREDICTOR_OVERLAP_{line.replace('.', '_')}.csv"
        pred_seen[line] = {r['sequence'] for r in csv.DictReader(ov.open(newline=''))}
        print(f"MHCflurry {line}: {len(d):,} scored rows, "
              f"{len(pred_seen[line]):,} overlapping sequences")

    # the evaluated rows are exactly those MHCflurry could score (ambiguity
    # codes excluded for both systems, so the rows are identical)
    keep = [(s, u, l) for s, u, l in rows
            if split[u]['primary_partition'] == 'test'
            and (u, s) in scores[LINES[0]] and (u, s) in scores[LINES[1]]]
    print(f"\nidentical rows for every system: {len(keep):,}")

    X = encode([s for s, _, _ in keep])
    y = np.array([l for _, _, l in keep])
    uarr = np.array([u for _, u, _ in keep])
    sarr = np.array([s for s, _, _ in keep], dtype=object)
    units = sorted(set(uarr))

    meta = json.loads((RES/'final.json').read_text())
    cfg = meta['config']
    S = []
    Xt = torch.from_numpy(X)
    for m_ in meta['models']:
        ck = torch.load(RES/m_['file'], map_location='cpu', weights_only=False)
        m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval()
        with torch.no_grad():
            S.append(torch.cat([m(Xt[i:i+8192])
                                for i in range(0, len(Xt), 8192)]).numpy())
    S = np.vstack(S)
    P = {line: np.array([scores[line][(u, s)] for s, u, _ in keep]) for line in LINES}

    masks = {
        'mutually naive (PRIMARY)': np.array(
            [(s not in cnn_seen) and all(s not in pred_seen[l] for l in LINES)
             for s in sarr]),
        'predictor-naive only': np.array(
            [all(s not in pred_seen[l] for l in LINES) for s in sarr]),
        'full test partition': np.ones(len(y), bool),
    }

    rng = np.random.default_rng(seed('predictor_bootstrap'))
    report = {'n_rows_identical': len(keep), 'row_sets': {},
              'cnn_config': cfg, 'n_cnn_models': S.shape[0]}

    def per_unit_cnn(mask):
        out = {}
        for u in units:
            k = (uarr == u) & mask
            if y[k].sum() in (0, k.sum()):
                continue
            out[u] = float(np.mean([average_precision(y[k], S[j][k])
                                    for j in range(S.shape[0])]))
        return out

    def per_unit_pred(mask, v):
        out = {}
        for u in units:
            k = (uarr == u) & mask
            if y[k].sum() in (0, k.sum()):
                continue
            out[u] = average_precision(y[k], v[k])
        return out

    for name, mask in masks.items():
        print(f"\n=== {name} ===")
        print(f"  rows {int(mask.sum()):,}  positives {int(y[mask].sum()):,}  "
              f"prevalence {y[mask].mean():.3f}")
        pu = {'CNN': per_unit_cnn(mask)}
        for line in LINES:
            pu[f'MHCflurry {line}'] = per_unit_pred(mask, P[line])
        rec = {'n_rows': int(mask.sum()), 'n_positives': int(y[mask].sum()),
               'prevalence': float(y[mask].mean()), 'systems': {}, 'contrasts': []}
        for k, d in pu.items():
            us = sorted(d)
            v = np.array([d[u] for u in us])
            lo, hi = cluster_ci(v, rng)
            print(f"  {k:<20} units {v.size:>2}  AP {v.mean():.4f}  "
                  f"CI99 [{lo:.4f}, {hi:.4f}]  range {v.min():.4f}-{v.max():.4f}")
            rec['systems'][k] = {'n_units': int(v.size), 'mean_ap': float(v.mean()),
                                 'ci99': [lo, hi], 'min': float(v.min()),
                                 'max': float(v.max()), 'per_unit': d}
        for line in LINES:
            a, b = pu['CNN'], pu[f'MHCflurry {line}']
            us = sorted(set(a) & set(b))
            d = np.array([a[u] - b[u] for u in us])
            lo, hi = paired_ci(d, rng)
            print(f"  -> CNN - MHCflurry {line}: {d.mean():+.4f}  "
                  f"CI99 [{lo:+.4f}, {hi:+.4f}]  ({int((d>0).sum())}/{len(us)} units)")
            rec['contrasts'].append(
                {'vs': f'MHCflurry {line}', 'difference': float(d.mean()),
                 'ci99': [lo, hi], 'n_units': len(us),
                 'n_cnn_better': int((d > 0).sum())})
        report['row_sets'][name] = rec

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT/'predictor_comparison.json', 'w'), indent=1)
    # the §18 deliverable named in SECTIONS.md
    with (REPO/'results'/'predictors'/'comparison_with_predictors.csv').open(
            'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['row_set', 'system', 'n_units', 'mean_per_unit_ap',
                    'ci99_lo', 'ci99_hi', 'n_rows', 'prevalence'])
        for name, rec in report['row_sets'].items():
            for k, s in rec['systems'].items():
                w.writerow([name, k, s['n_units'], f"{s['mean_ap']:.6f}",
                            f"{s['ci99'][0]:.6f}", f"{s['ci99'][1]:.6f}",
                            rec['n_rows'], f"{rec['prevalence']:.6f}"])
    print(f"\nwrote {OUT/'predictor_comparison.json'} and "
          f"results/predictors/comparison_with_predictors.csv")


if __name__ == '__main__':
    main()
