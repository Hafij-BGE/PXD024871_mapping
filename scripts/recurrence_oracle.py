#!/usr/bin/env python3
"""Defect D: sequence recurrence is a perfect label oracle in the frozen dataset.

Negatives were drawn without replacement across the whole 52-participant
dataset, so no decoy sequence ever occurs twice. Positives recur whenever two
participants observed the same peptide. "Have I seen this sequence before?" is
therefore not an approximate indicator that a test row is a positive -- it is an
exact one, with no counter-example in 520,000 negatives.

This script measures two things and keeps them apart:

  1. The conditional P(label = 1 | sequence appears anywhere in training).
     An exact count. No modelling, no tie convention, nothing to argue with.

  2. The average precision of a classifier that scores 1 for "seen in training"
     and 0 otherwise, using no sequence features at all. Per participant, then
     averaged, which is the project's estimand (D008).

**Quantity 2 is tie-convention dependent and both conventions are reported.**
The score takes two values, so 184,012 test rows tie at 0. `average_precision`
in train_cnn.py sorts with `kind='stable'`, which breaks that tie by file order
-- deterministic, but arbitrary. The expectation under random tie-breaking is
the convention-free quantity, and it is estimated here by Monte Carlo. If the
two disagree materially, the file-order figure is an artefact of row order and
the random-tie-break figure is the one to quote.

Writes results/qc/recurrence_oracle.json. Reads only frozen artifacts; writes
no other file; retrains nothing.
"""

import csv, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                              # noqa: E402
from train_cnn import average_precision, cluster_ci                 # noqa: E402

DER = REPO/'data'/'derived'
OUT = REPO/'results'/'qc'/'recurrence_oracle.json'
B_TIE = 200        # Monte Carlo draws for the random tie-break expectation
B_BOOT = 10000
NOMINAL = 0.99


def main():
    split = {r['unit_id']: r['primary_partition']
             for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    pos = list(csv.DictReader((DER/'POSITIVES.csv').open(newline='')))
    neg = list(csv.DictReader((DER/'NEGATIVES.csv').open(newline='')))

    # ---- 1. the construction that creates the oracle -----------------------
    pos_seqs = [r['sequence'] for r in pos]
    neg_seqs = [r['sequence'] for r in neg]
    pos_mult = defaultdict(int)
    for s in pos_seqs:
        pos_mult[s] += 1
    neg_mult = defaultdict(int)
    for s in neg_seqs:
        neg_mult[s] += 1
    construction = {
        'positives_rows': len(pos_seqs),
        'positives_unique': len(pos_mult),
        'positives_max_multiplicity': max(pos_mult.values()),
        'negatives_rows': len(neg_seqs),
        'negatives_unique': len(neg_mult),
        'negatives_max_multiplicity': max(neg_mult.values()),
        'positive_negative_sequence_overlap': len(set(pos_mult) & set(neg_mult)),
    }

    # ---- 2. the oracle on the held-out partition ---------------------------
    train_seen = ({r['sequence'] for r in pos if split[r['unit_id']] != 'test'} |
                  {r['sequence'] for r in neg if split[r['unit_id']] != 'test'})
    test_rows = ([(r['unit_id'], r['sequence'], 1) for r in pos
                  if split[r['unit_id']] == 'test'] +
                 [(r['unit_id'], r['sequence'], 0) for r in neg
                  if split[r['unit_id']] == 'test'])

    seen_pos = sum(1 for u, s, y in test_rows if y == 1 and s in train_seen)
    seen_neg = sum(1 for u, s, y in test_rows if y == 0 and s in train_seen)
    n_pos = sum(1 for _, _, y in test_rows if y == 1)
    n_neg = len(test_rows) - n_pos
    conditional = {
        'test_positives': n_pos,
        'test_negatives': n_neg,
        'positives_seen_in_training': seen_pos,
        'negatives_seen_in_training': seen_neg,
        'P_label1_given_seen': (seen_pos/(seen_pos+seen_neg)
                                if seen_pos+seen_neg else None),
        'P_label1_given_unseen': (n_pos-seen_pos)/((n_pos-seen_pos)+(n_neg-seen_neg)),
        'prevalence': n_pos/len(test_rows),
    }

    # ---- 3. the lookup classifier, per participant -------------------------
    by_unit = defaultdict(list)
    for u, s, y in test_rows:
        by_unit[u].append((1.0 if s in train_seen else 0.0, y))
    units = sorted(by_unit)

    rng = np.random.default_rng(seed('recurrence_tiebreak'))
    file_order, random_tie = [], []
    for u in units:
        sc = np.array([a for a, _ in by_unit[u]])
        y = np.array([b for _, b in by_unit[u]])
        file_order.append(average_precision(y, sc))
        # Random tie-breaking: jitter inside each tie block by an amount far
        # smaller than the gap between the two score levels.
        draws = [average_precision(y, sc + rng.random(sc.size)*1e-6)
                 for _ in range(B_TIE)]
        random_tie.append(float(np.mean(draws)))

    fo = np.array(file_order)
    rt = np.array(random_tie)
    rng_b = np.random.default_rng(seed('recurrence_bootstrap'))
    fo_ci = cluster_ci(fo, rng_b, B=B_BOOT, nominal=NOMINAL)
    rt_ci = cluster_ci(rt, rng_b, B=B_BOOT, nominal=NOMINAL)

    report = {
        'decision': 'D056',
        'what_this_is': 'A lookup classifier scoring 1 for "sequence seen '
                        'anywhere in training" and 0 otherwise, using no '
                        'sequence features. It measures what the dataset '
                        'construction gives away, not what the network learns.',
        'construction': construction,
        'conditional': conditional,
        'n_units': len(units),
        'per_unit_ap_file_order': {u: float(v) for u, v in zip(units, fo)},
        'per_unit_ap_random_tiebreak': {u: float(v) for u, v in zip(units, rt)},
        'mean_ap_file_order': float(fo.mean()),
        'mean_ap_file_order_ci': [float(x) for x in fo_ci],
        'mean_ap_random_tiebreak': float(rt.mean()),
        'mean_ap_random_tiebreak_ci': [float(x) for x in rt_ci],
        'tiebreak_draws': B_TIE,
        'tie_convention_note':
            'The score takes two values, so most test rows tie. '
            'train_cnn.average_precision sorts with kind="stable", breaking '
            'that tie by file order: deterministic but arbitrary. The '
            'random-tiebreak figure is the convention-free quantity. Quote '
            'that one.',
        'interval_note':
            'Nominal-99% cluster bootstrap over the 10 held-out participants '
            '(D008). R6 measured nominal-95% delivering 0.884-0.890 actual '
            'coverage at this unit count, which is why nominal-99% is used '
            'and why no 99% confidence is claimed.',
        'what_this_does_not_show':
            'That the network exploits this shortcut. The oracle shows the '
            'shortcut exists and is exploitable; attributing any part of the '
            'endpoint to it would need an experiment this is not.',
        'seeds': {'tiebreak': seed('recurrence_tiebreak'),
                  'bootstrap': seed('recurrence_bootstrap')},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + '\n')

    print('=== construction ===')
    for k, v in construction.items():
        print(f'  {k:38s} {v:,}' if isinstance(v, int) else f'  {k:38s} {v}')
    print('\n=== the conditional, on the held-out partition ===')
    print(f'  test positives seen in training   {seen_pos:,} of {n_pos:,}')
    print(f'  test negatives seen in training   {seen_neg:,} of {n_neg:,}')
    print(f'  P(label=1 | seen)                 {conditional["P_label1_given_seen"]:.6f}')
    print(f'  P(label=1 | unseen)               {conditional["P_label1_given_unseen"]:.6f}')
    print(f'  prevalence                        {conditional["prevalence"]:.6f}')
    print('\n=== lookup classifier, mean per-participant AP ===')
    print(f'  file-order ties     {fo.mean():.4f}  [{fo_ci[0]:.4f}, {fo_ci[1]:.4f}]')
    print(f'  random ties         {rt.mean():.4f}  [{rt_ci[0]:.4f}, {rt_ci[1]:.4f}]'
          f'   <- quote this one')
    print(f'  difference          {fo.mean()-rt.mean():+.4f}')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
