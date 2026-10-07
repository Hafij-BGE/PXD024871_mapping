#!/usr/bin/env python3
"""Stage 1 of §18: score the frozen test partition with MHCflurry.

Run with the MHCflurry virtualenv's python. Writes one CSV of scores per
release line; the comparison itself is stage 2 (`compare_predictors.py`), which
needs torch for the CNN and is kept separate so neither environment has to
carry the other's dependencies.

Rows whose sequence carries an ambiguity code are skipped and counted. The
frozen positives contain 181 such rows (0.035%) using X, B (Asx) and Z (Glx);
MHCflurry refuses them outright, and the CNN's encoder silently maps an unknown
character to the pad token, so those peptides were encoded with internal pads.
Both are recorded; excluding them keeps the two systems on identical rows.

Each peptide is scored against ITS OWN participant's recorded alleles, which is
how a presentation predictor is meant to be used: the quantity is "would this
peptide be presented by this donor", and `presentation_score` already takes the
best allele. Partially typed units are scored on the alleles actually recorded
(D012: none are imputed), which can only understate the predictor.
"""

import argparse, csv, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER = REPO/'data'/'derived'
OUT = REPO/'results'/'predictors'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--models', required=True, help="extracted models dir")
    ap.add_argument('--line', required=True, help="release line label, e.g. 2.3.0")
    a = ap.parse_args()
    from mhcflurry import Class1PresentationPredictor

    split = {r['unit_id']: r for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    geno = {r['unit_id']: [x for x in r['hla_genotype'].split(';') if x]
            for r in csv.DictReader((DER/'UNIT_GENOTYPE.csv').open(newline=''))}
    AA = set('ACDEFGHIKLMNPQRSTVWY')
    rows, skipped = defaultdict(list), []
    for fn, lab in (('POSITIVES.csv', 1), ('NEGATIVES.csv', 0)):
        for r in csv.DictReader((DER/fn).open(newline='')):
            if split[r['unit_id']]['primary_partition'] != 'test':
                continue
            if set(r['sequence']) - AA:
                skipped.append((r['unit_id'], r['sequence'], lab))
                continue
            rows[r['unit_id']].append((r['sequence'], lab))
    units = sorted(rows)
    print(f"skipped {len(skipped)} rows with ambiguity codes "
          f"({[s for _, s, _ in skipped][:3]}...)")


    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'ambiguity_skipped.csv').open('w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['unit_id', 'sequence', 'label'])
        w.writerows(skipped)

    P = Class1PresentationPredictor.load(a.models)
    supported = set(P.supported_alleles)
    out = OUT/f"mhcflurry_{a.line.replace('.', '_')}_test_scores.csv"
    n = 0
    with out.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['unit_id', 'sequence', 'label', 'presentation_score',
                    'presentation_percentile', 'affinity', 'best_allele'])
        for u in units:
            alleles = [x for x in geno[u] if x in supported]
            dropped = [x for x in geno[u] if x not in supported]
            peps = [s for s, _ in rows[u]]
            labs = [l for _, l in rows[u]]
            print(f"  {u}: {len(peps):,} peptides x {len(alleles)} alleles"
                  + (f"   DROPPED unsupported: {dropped}" if dropped else ""), flush=True)
            df = P.predict(peptides=peps, alleles={u: alleles}, verbose=0)
            assert len(df) == len(peps), f"{u}: {len(df)} scores for {len(peps)} peptides"
            # predict() preserves input order and returns one row per peptide
            for (s, l), (_, r) in zip(rows[u], df.iterrows()):
                assert r['peptide'] == s, f"order mismatch at {s}"
                w.writerow([u, s, l, r['presentation_score'],
                            r['presentation_percentile'], r['affinity'],
                            r['best_allele']])
                n += 1
    print(f"\nwrote {out}  ({n:,} rows)")


if __name__ == '__main__':
    sys.exit(main())
