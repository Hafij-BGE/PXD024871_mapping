#!/usr/bin/env python3
"""M7 contamination for every §18 predictor, one method, one table (D036).

`predictor_contamination.py` covered the two MHCflurry lines only and is kept
as it was when QC_G11 was written. This supersedes it for the four-predictor
comparison, deriving every figure the same way so the columns are comparable:
exact normalized sequence match against the frozen test partition (D016 --
nothing fuzzy), counted separately for peptides the predictor saw as POSITIVE
and as NEGATIVE.

That split matters and the earlier script did not make it. D006's argument that
contamination can only flatter a predictor holds when the overlap is lopsided
toward positives. A predictor that has also seen our negatives, labelled as
non-ligands, may reject them correctly for a reason that is memory rather than
modelling -- which cuts the other way.

Usage: contamination_all.py <extract-root>
"""

import bz2, csv, gzip, json, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER, OUT = REPO/'data'/'derived', REPO/'results'/'qc'


def test_partition():
    split = {r['unit_id']: r for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    pos, neg = defaultdict(set), defaultdict(set)
    for fn, b in (('POSITIVES.csv', pos), ('NEGATIVES.csv', neg)):
        for r in csv.DictReader((DER/fn).open(newline='')):
            if split[r['unit_id']]['primary_partition'] == 'test':
                b[r['unit_id']].add(r['sequence'])
    return pos, neg


def _norm(p):
    return p.strip().upper()


def mhcflurry(root, files):
    """Union over the released model's own bundled component training sets.
    These carry no usable positive/negative label for our purpose: the affinity
    table is measurements, the processing table is 1:1 hit/decoy."""
    pos, neg = set(), set()
    for rel in files:
        with bz2.open(Path(root)/rel, 'rt') as fh:
            for r in csv.DictReader(fh):
                p = r.get('peptide')
                if not p:
                    continue
                hit = r.get('hit')
                (neg if hit == '0' else pos).add(_norm(p))
    return pos, neg


def netmhcpan(train_dir):
    """c00?_{ba,el[,iedb,cedar]}: peptide, target, allele[, context].
    EL/epitope targets are 1 for ligands and 0 for decoys; BA rows are
    normalized affinities, treated as 'seen' without a class."""
    pos, neg = set(), set()
    for f in sorted(Path(train_dir).glob('c00?_*')):
        kind = f.name.rsplit('_', 1)[1]
        with f.open() as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 2:
                    continue
                p, tgt = _norm(parts[0]), parts[1]
                if kind == 'ba':
                    pos.add(p)                      # a measured peptide, class n/a
                else:
                    (pos if tgt == '1' else neg).add(p)
    return pos, neg


def mixmhcpred(path):
    """Allele / peptite / Target  (the header's spelling is theirs)."""
    pos, neg = set(), set()
    with Path(path).open() as fh:
        head = fh.readline().lower().split()
        ip = 1 if 'pept' in head[1] else 0
        it = 2 if len(head) > 2 else 1
        for line in fh:
            parts = line.split()
            if len(parts) <= max(ip, it):
                continue
            (pos if parts[it] == '1' else neg).add(_norm(parts[ip]))
    return pos, neg


def main():
    root = Path(sys.argv[1])
    pos, neg = test_partition()
    tp = set().union(*pos.values())
    tn = set().union(*neg.values())
    units = sorted(pos)
    print(f"frozen test partition: {len(units)} units, {len(tp):,} distinct "
          f"positives, {len(tn):,} distinct negatives\n")

    preds = {
        'MHCflurry 2.0.0': lambda: mhcflurry(root, [
            'm200/train_data.csv.bz2',
            'm200/models/affinity_predictor_train_data.csv.bz2',
            'm200/models/processing_predictor_train_data.csv.bz2',
            'm200/models/processing_predictor_no_flank_train_data.csv.bz2']),
        'MHCflurry 2.3.0': lambda: mhcflurry(root, [
            'm230/models/affinity_predictor_train_data.csv.bz2',
            'm230/models/processing_predictor_with_flanks_train_data.csv.bz2',
            'm230/models/processing_predictor_no_flank_train_data.csv.bz2']),
        'NetMHCpan 4.1': lambda: netmhcpan(root/'netmhc_train'/'NetMHCpan_train'),
        'NetMHCpan 4.2': lambda: netmhcpan(root/'nm42'/'NetMHCpan_train'),
        'MixMHCpred 3.0': lambda: mixmhcpred(
            REPO/'data'/'raw'/'S6'/'MixMHCpred3.0_training_data_MOESM2.txt'),
    }

    rep = {'test_partition': {'n_units': len(units), 'positives': len(tp),
                              'negatives': len(tn)}, 'predictors': {}}
    print(f"{'predictor':<18}{'train pos':>12}{'train neg':>12}"
          f"{'our pos seen':>14}{'our neg seen':>14}{'bias':>8}  verdict")
    for name, fn in preds.items():
        trp, trn = fn()
        seen = trp | trn
        op, on = tp & seen, tn & seen
        fp, fn_ = len(op)/len(tp), len(on)/len(tn)
        bias = fp/fn_ if fn_ else float('inf')
        print(f"{name:<18}{len(trp):>12,}{len(trn):>12,}"
              f"{100*fp:>13.2f}%{100*fn_:>13.2f}%{bias:>7.1f}:1  "
              f"{'CLEAN' if not op else 'OVERLAPPING'}")
        per = {u: len(pos[u] & seen)/len(pos[u]) for u in units}
        rep['predictors'][name] = {
            'train_positive': len(trp), 'train_negative': len(trn),
            'train_union': len(seen),
            'overlap_positives': len(op), 'overlap_negatives': len(on),
            'overlap_positives_frac': fp, 'overlap_negatives_frac': fn_,
            'bias_pos_over_neg': bias,
            'per_unit_positive_overlap': per,
            'm7_verdict': 'CLEAN' if not op else 'OVERLAPPING'}
        with (DER/f"TEST_PREDICTOR_OVERLAP_{name.replace(' ', '_').replace('.', '_')}.csv"
              ).open('w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['sequence'])
            for s in sorted(op | on):
                w.writerow([s])

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(OUT/'contamination_all.json', 'w'), indent=1)
    print(f"\nwrote {OUT/'contamination_all.json'} and per-predictor overlap lists")


if __name__ == '__main__':
    main()
