#!/usr/bin/env python3
"""Estimate tau from the realised endpoint, and recompute power against it (D063).

POWER_ANALYSIS.md calls tau -- the between-participant SD of latent
discrimination -- "unknown and unmeasurable before data exist", and sweeps it at
0.10 / 0.25 / 0.50. D008 adopted 0.25, and every power figure in the record is
conditional on that choice.

It is measurable now. Inverting the binormal model on the ten realised
per-participant average precisions in results/model/endpoint.json gives a
per-participant discrimination d for each, and their SD is tau.

This script recomputes power against the PREREGISTERED threshold of 0.647 at
both the assumed and the realised tau, so the planning value and the measured
one can be read side by side. It does not revise the threshold, the endpoint, or
any preregistered decision: D008's rule and its 0.42/0.978 figures stand as the
record, and these are reported beside them as a sensitivity.

Two caveats travel with the estimate and are written into the artifact:
tau is estimated from ten participants and carries its own uncertainty, and the
inversion inherits the binormal model that POWER_ANALYSIS.md already flags as a
convenience rather than a prediction.

Deterministic: fixed seed, tracked inputs only. Classified BYTES in
scripts/regen_check.py.
"""

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

REPO = Path(__file__).resolve().parent.parent
OUT = REPO/'results'/'power'/'tau_realised.json'
ENDPOINT = REPO/'results'/'model'/'endpoint.json'

SEED = 20261013
K, NPOS, NSIM, B = 10, 10_000, 250, 2000
NOMINAL = 0.99
PREREG_THRESH = 0.647            # D008, floor 0.597 + lift 0.05
TAU_ASSUMED = 0.25               # the value D008 adopted
AUROCS = (0.70, 0.75)            # the two the record quotes


def average_precision(y, s):
    o = np.argsort(-s, kind='stable'); y = y[o]
    tp = np.cumsum(y); k = np.arange(1, y.size+1)
    return float(np.sum((tp/k) * y) / tp[-1])


def true_ap(d, pi, m=12001):
    """Asymptotic AP under the binormal model at prevalence pi."""
    t = np.linspace(-12.0, 12.0 + d, m)
    tpr = 1.0 - norm.cdf(t - d)
    fpr = 1.0 - norm.cdf(t)
    prec = np.divide(pi*tpr, pi*tpr + (1.0-pi)*fpr,
                     out=np.zeros_like(tpr), where=(pi*tpr + (1.0-pi)*fpr) > 0)
    return float(-np.trapezoid(prec, tpr))


def estimand(d_bar, tau, pi, m=4001):
    if tau <= 0:
        return true_ap(d_bar, pi)
    q = (np.arange(m) + 0.5) / m
    return float(np.mean([true_ap(x, pi) for x in d_bar + tau*norm.ppf(q)]))


def power_cell(d_bar, tau, rng):
    a = (1.0 - NOMINAL) / 2 * 100
    rej, half = 0, []
    for _ in range(NSIM):
        d = d_bar + tau*rng.standard_normal(K)
        aps = np.empty(K)
        for i in range(K):
            s = np.concatenate([d[i] + rng.standard_normal(NPOS),
                                rng.standard_normal(NPOS)])
            y = np.concatenate([np.ones(NPOS), np.zeros(NPOS)])
            aps[i] = average_precision(y, s)
        reps = aps[rng.integers(0, K, size=(B, K))].mean(axis=1)
        lo, hi = np.percentile(reps, [a, 100-a])
        half.append((hi-lo)/2.0)
        if lo > PREREG_THRESH:
            rej += 1
    return {'power_vs_prereg_threshold': rej/NSIM,
            'mean_ci_halfwidth': float(np.mean(half))}


def main():
    ep = json.loads(ENDPOINT.read_text())
    per = ep['primary']['per_unit']
    units = sorted(per)
    aps = np.array([per[u] for u in units])
    d = np.array([brentq(lambda x: true_ap(x, 0.5) - a, 0.01, 8.0) for a in aps])
    tau_hat = float(d.std(ddof=1))

    rng = np.random.default_rng(SEED)
    cells = []
    for tau, tag in ((tau_hat, 'realised'), (TAU_ASSUMED, 'assumed')):
        for auroc in AUROCS:
            d_bar = float(np.sqrt(2)*norm.ppf(auroc))
            c = power_cell(d_bar, tau, rng)
            c.update({'tau': tau, 'tau_source': tag, 'auroc': auroc,
                      'estimand_ap': estimand(d_bar, tau, 0.5)})
            cells.append(c)

    rec = {
        'decision': 'D063',
        'what_this_is': ('tau estimated from the realised per-participant average '
                         'precisions, with power against the preregistered '
                         'threshold recomputed at both the assumed and the '
                         'realised value. Reported beside D008, not instead of it.'),
        'threshold': PREREG_THRESH,
        'threshold_source': 'D008, composition floor 0.597 plus a lift of 0.05',
        'nominal': NOMINAL,
        'tau_assumed_by_D008': TAU_ASSUMED,
        'tau_realised': tau_hat,
        'per_unit': {u: {'ap': float(a), 'implied_d': float(x)}
                     for u, a, x in zip(units, aps, d)},
        'realised_mean_ap': float(aps.mean()),
        'realised_sd_ap': float(aps.std(ddof=1)),
        'implied_d_mean': float(d.mean()),
        'cells': cells,
        'config': {'K': K, 'n_pos_per_participant': NPOS, 'ratio': 1,
                   'prevalence': 0.5, 'n_sim': NSIM, 'B': B, 'seed': SEED},
        'caveat_sample_size': ('tau is estimated from ten held-out participants '
                               'and carries its own uncertainty. It is an '
                               'estimate, not a constant.'),
        'caveat_model': ('The inversion assumes the binormal model, which '
                         'POWER_ANALYSIS.md flags as a convenience rather than '
                         'a prediction. These figures inherit that caveat.'),
        'what_this_does_not_do': ('Revise the preregistered threshold, the '
                                  'endpoint, or D008. The 0.647 rule and its '
                                  'recorded power stand.'),
    }
    OUT.write_text(json.dumps(rec, indent=1) + '\n')
    print(f'tau assumed {TAU_ASSUMED}  realised {tau_hat:.4f}')
    for c in cells:
        print(f"  tau={c['tau']:.4f} ({c['tau_source']:<8}) auroc={c['auroc']:.2f} "
              f"AP={c['estimand_ap']:.4f} power={c['power_vs_prereg_threshold']:.3f} "
              f"half={c['mean_ci_halfwidth']:.4f}")
    print(f'wrote {OUT.relative_to(REPO)}')


if __name__ == '__main__':
    main()
