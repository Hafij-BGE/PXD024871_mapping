#!/usr/bin/env python3
"""Q1-005: separate the leakage effect from the prevalence change it is confounded with.

The study reports a primary endpoint of 0.7551 on the full held-out partition
and 0.7056 on the leakage-free subset, a drop of 0.0495, and `train_cnn.py`
printed that difference as "Inflation from leakage".

**That attribution is not supported by the comparison that produces it.** The
leakage-free subset is built by dropping the 15,988 test positives whose
sequence occurs verbatim in training. It drops positives only, so prevalence
falls from 0.500000 to 0.456321. Average precision has the prevalence as its
own floor -- a random classifier scores AP equal to the positive fraction -- so
the comparison's floor moves on its own. Two things change at once and the
difference cannot be read as either one.

**The floor shift is not a share of the drop.** How far the random-classifier
floor moves (0.0437) and how far THIS MODEL's AP moves when prevalence is
restored (0.0330) are different quantities, and only the second decomposes:
(P - L) = (P - M) + (M - L). The CNN is not a random classifier and its AP does
not track the floor one-for-one. An earlier draft divided the floor shift by the
drop and reported 88.2%; that was wrong -- adding it to the residual overshoots
the drop by 0.0107. The measured prevalence effect is 66.6%.

This script holds prevalence fixed and re-measures. For each held-out
participant it subsamples the negatives so that the leakage-free arm has the
same positive fraction as the primary arm, rescores from the 25 frozen
checkpoints, and reports the decomposition.

**What this can show:** whether a gap survives when both arms have the same
positive fraction. **What it cannot show:** that any surviving gap is caused by
leakage. The leakage-free subset is also a different, plausibly harder set of
peptides -- peptides unique to one participant -- so prevalence matching removes
one confound of several, not all of them.

Nothing is retrained. The checkpoints are read, not written. Writes
results/qc/prevalence_matched.json and no other file.
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
                       load)

DER = REPO/'data'/'derived'
RES = REPO/'results'/'model'
OUT = REPO/'results'/'qc'/'prevalence_matched.json'
B_SUB = 50          # independent negative subsamples per participant
B_BOOT = 10000
NOMINAL = 0.99


def main():
    rows, split = load()
    meta = json.loads((RES/'final.json').read_text())
    cfg = meta['config']
    leakfree = {r['sequence'] for r in
                csv.DictReader((DER/'TEST_LEAKFREE.csv').open(newline=''))}

    test = [(s, u, l) for s, u, l in rows if split[u]['primary_partition'] == 'test']
    X = encode([s for s, _, _ in test])
    y = np.array([l for _, _, l in test])
    ua = np.array([u for _, u, _ in test])
    clean = np.array([(l == 0) or (s in leakfree) for s, _, l in test])

    print(f'scoring {len(test):,} rows with {len(meta["models"])} checkpoints...')
    Xt = torch.from_numpy(X)
    S = []
    for m_ in meta['models']:
        ck = torch.load(RES/m_['file'], map_location='cpu', weights_only=False)
        m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval()
        with torch.no_grad():
            S.append(torch.cat([m(Xt[i:i+8192])
                                for i in range(0, len(Xt), 8192)]).numpy())
    S = np.vstack(S)

    units = sorted(set(ua))
    rng = np.random.default_rng(seed('prevalence_match'))

    def mean_ap(mask):
        """Mean across the 25 checkpoints, for one row mask, one unit."""
        return float(np.mean([average_precision(y[mask], S[j][mask])
                              for j in range(S.shape[0])]))

    primary, leakfree_ap, matched, detail = [], [], [], {}
    for u in units:
        inu = ua == u
        prim = inu
        lf = inu & clean
        n_pos_lf = int(y[lf].sum())
        n_neg_lf = int((~y[lf].astype(bool)).sum())
        # prevalence of the primary arm for this unit
        p_prim = y[prim].mean()
        # negatives to keep so that n_pos_lf / (n_pos_lf + k) == p_prim
        keep = int(round(n_pos_lf * (1 - p_prim) / p_prim))
        neg_idx = np.flatnonzero(lf & (y == 0))
        pos_idx = np.flatnonzero(lf & (y == 1))

        draws = []
        for _ in range(B_SUB):
            sel = rng.choice(neg_idx, size=min(keep, neg_idx.size), replace=False)
            mask = np.zeros(len(y), bool)
            mask[pos_idx] = True
            mask[sel] = True
            draws.append(mean_ap(mask))
        primary.append(mean_ap(prim))
        leakfree_ap.append(mean_ap(lf))
        matched.append(float(np.mean(draws)))
        detail[u] = {
            'primary_rows': int(prim.sum()), 'primary_prevalence': float(p_prim),
            'leakfree_rows': int(lf.sum()),
            'leakfree_prevalence': float(y[lf].mean()),
            'leakfree_positives': n_pos_lf, 'leakfree_negatives': n_neg_lf,
            'matched_negatives_kept': int(min(keep, neg_idx.size)),
            'matched_prevalence': float(n_pos_lf/(n_pos_lf+min(keep, neg_idx.size))),
            'ap_primary': primary[-1], 'ap_leakfree': leakfree_ap[-1],
            'ap_matched': matched[-1],
            'ap_matched_sd_over_draws': float(np.std(draws, ddof=1)),
        }
        print(f'  {u}  primary {primary[-1]:.4f}  leak-free {leakfree_ap[-1]:.4f}  '
              f'matched {matched[-1]:.4f}  (prev {detail[u]["matched_prevalence"]:.4f})')

    pr, lf_, mt = np.array(primary), np.array(leakfree_ap), np.array(matched)
    rb = np.random.default_rng(seed('prevalence_bootstrap'))
    out = {
        'decision': 'D057',
        'n_units': len(units),
        'primary_mean_ap': float(pr.mean()),
        'primary_ci': [float(x) for x in cluster_ci(pr, rb, B=B_BOOT, nominal=NOMINAL)],
        'leakfree_mean_ap': float(lf_.mean()),
        'leakfree_ci': [float(x) for x in cluster_ci(lf_, rb, B=B_BOOT, nominal=NOMINAL)],
        'matched_mean_ap': float(mt.mean()),
        'matched_ci': [float(x) for x in cluster_ci(mt, rb, B=B_BOOT, nominal=NOMINAL)],
        # The only additive decomposition of the observed drop:
        #     (P - L) = (P - M) + (M - L)
        # (M - L) is the measured prevalence effect ON THIS CLASSIFIER. It is
        # NOT the shift in the random-classifier floor, reported separately
        # below, which must not be divided by the drop.
        'observed_drop_primary_minus_leakfree': float(pr.mean()-lf_.mean()),
        'residual_drop_primary_minus_matched': float(pr.mean()-mt.mean()),
        'prevalence_effect_matched_minus_leakfree': float(mt.mean()-lf_.mean()),
        'prevalence_effect_share_of_drop': float((mt.mean()-lf_.mean())
                                                 / (pr.mean()-lf_.mean())),
        'random_classifier_floor_shift': None,   # filled below; NOT a share
        'floor_shift_note':
            'random_classifier_floor_shift is prevalence_primary minus '
            'prevalence_leakfree: how far the AP floor moves, because a random '
            'classifier scores AP equal to the positive fraction. It explains '
            'WHY the two arms are not comparable. It is NOT the measured effect '
            'on this model and is NOT a share of the observed drop -- adding it '
            'to the residual overshoots the drop by 0.0107.',
        'subsamples_per_unit': B_SUB,
        'per_unit': detail,
        'what_this_shows':
            'Whether an AP gap survives when both arms carry the same positive '
            'fraction. The residual is the part of the drop not explained by '
            'the prevalence baseline moving.',
        'what_this_does_not_show':
            'That the residual is caused by leakage. The leakage-free subset is '
            'also a different and plausibly harder set of peptides -- those '
            'unique to one participant -- so matching prevalence removes one '
            'confound, not all of them. No causal attribution is made here.',
        'seeds': {'match': seed('prevalence_match'),
                  'bootstrap': seed('prevalence_bootstrap')},
    }
    pool_prim = float(np.mean([d['primary_prevalence'] for d in detail.values()]))
    pool_lf = float(np.mean([d['leakfree_prevalence'] for d in detail.values()]))
    out['prevalence_primary'] = pool_prim
    out['prevalence_leakfree'] = pool_lf
    out['random_classifier_floor_shift'] = pool_prim - pool_lf

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + '\n')

    drop = pr.mean()-lf_.mean(); resid = pr.mean()-mt.mean(); pref = mt.mean()-lf_.mean()
    print('\n=== decomposition ===')
    print(f'  primary                          {pr.mean():.4f}  prevalence {pool_prim:.6f}')
    print(f'  leakage-free, as reported        {lf_.mean():.4f}  prevalence {pool_lf:.6f}')
    print(f'  leakage-free, prevalence-matched {mt.mean():.4f}  prevalence {pool_prim:.6f}')
    print(f'\n  observed drop   (P-L)            {drop:+.4f}')
    print(f'    prevalence effect   (M-L)      {pref:+.4f}   {100*pref/drop:.1f}% of the drop')
    print(f'    residual            (P-M)      {resid:+.4f}   {100*resid/drop:.1f}% of the drop')
    print(f'    sum to the drop                {abs(pref+resid-drop)<1e-12}')
    print(f'\n  random-classifier floor shift    {pool_prim-pool_lf:+.4f}')
    print('    How far the AP FLOOR moves, not the effect on this model.')
    print(f'    NOT a share of the drop: floor shift + residual overshoots by '
          f'{pool_prim-pool_lf+resid-drop:+.4f}.')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
