#!/usr/bin/env python3
"""Per-length decomposition of the already-read primary endpoint (§20 robustness).

NOT a second reading of the endpoint. The primary value is read, reported and
closed: 0.7551, CI99 [0.7368, 0.7721], null rejected (R9, QC_G10). This
re-scores the same rows with the same 25 models and splits the result by peptide
length, because §20's methodology requires robustness across peptide lengths and
nothing had reported it. Every length is reported; no length is selected; the
primary decision is untouched and cannot change.
"""

import csv, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                              # noqa: E402
from train_cnn import (CNN, encode, average_precision, cluster_ci,  # noqa: E402
                       paired_ci, load)

RES, DER = REPO/'results'/'model', REPO/'data'/'derived'

meta = json.loads((RES/'final.json').read_text())
cfg = meta['config']
rows, split = load()
test = [(s, u, l) for s, u, l in rows if split[u]['primary_partition'] == 'test']
X = encode([s for s, _, _ in test])
y = np.array([l for _, _, l in test])
uarr = np.array([u for _, u, _ in test])
lens = np.array([len(s) for s, _, _ in test])
print(f"same {len(test):,} rows and {len(meta['models'])} models as QC_G10\n")

S = []
for m_ in meta['models']:
    ck = torch.load(RES/m_['file'], map_location='cpu', weights_only=False)
    m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval()
    Xt = torch.from_numpy(X)
    with torch.no_grad():
        S.append(torch.cat([m(Xt[i:i+8192])
                            for i in range(0, len(Xt), 8192)]).numpy())
S = np.vstack(S)

rng = np.random.default_rng(seed('endpoint_by_length'))
units = sorted(set(uarr))
out = {'note': __doc__.strip().splitlines()[0],
       'primary_as_read': 0.7551, 'by_length': []}


def report(name, mask):
    pu = {}
    for u in units:
        k = (uarr == u) & mask
        if k.sum() == 0 or y[k].sum() in (0, k.sum()):
            continue
        pu[u] = float(np.mean([average_precision(y[k], S[j][k])
                               for j in range(S.shape[0])]))
    us = sorted(pu)
    v = np.array([pu[u] for u in us])
    lo, hi = cluster_ci(v, rng)
    print(f"  {name:<14} rows {int(mask.sum()):>7,}  units {v.size:>2}  "
          f"AP {v.mean():.4f}  CI99 [{lo:.4f}, {hi:.4f}]  "
          f"range {v.min():.4f}-{v.max():.4f}")
    return {'stratum': name, 'n_rows': int(mask.sum()), 'n_units': int(v.size),
            'mean_ap': float(v.mean()), 'ci99': [lo, hi],
            'min': float(v.min()), 'max': float(v.max()),
            'per_unit': {u: pu[u] for u in us}}


print("all lengths (reproduces the read value):")
allr = report('all', np.ones(len(y), bool))
out['all'] = allr
print("\nby peptide length:")
for L in range(8, 13):
    out['by_length'].append(report(f'{L}-mer', lens == L))
vals = [r['mean_ap'] for r in out['by_length']]
out['spread_across_lengths'] = float(max(vals) - min(vals))
print(f"\n  spread across lengths: {max(vals)-min(vals):.4f} "
      f"(min {min(vals):.4f} at {out['by_length'][int(np.argmin(vals))]['stratum']}, "
      f"max {max(vals):.4f} at {out['by_length'][int(np.argmax(vals))]['stratum']})")
# is any length below the D008 threshold?
below = [r['stratum'] for r in out['by_length'] if r['ci99'][0] <= 0.647]
out['lengths_not_clearing_threshold'] = below
print(f"  lengths whose CI99 lower bound does NOT clear 0.647: "
      f"{below if below else 'none'}")
json.dump(out, open(RES/'endpoint_by_length.json', 'w'), indent=1)
print(f"\nwrote {RES/'endpoint_by_length.json'}")
