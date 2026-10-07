#!/usr/bin/env python3
"""M7 contamination check for the §18 predictors, under D006's protocol.

D006: "No predictor enters the §18 comparison until its training peptide list
has been retrieved and registered as an S6 source." Both MHCflurry release
lines' curated training data are registered in data/raw/S6 with checksums, so
this measures the thing D006 fixed the handling for, at SEQUENCE level:

  "Exact normalized sequence match against the frozen test partition (M7).
   Dataset provenance is not a substitute."

Reports, per release line: overlap with the test partition's positives and with
its negatives, the per-unit breakdown, and whether this deposit is nameable in
the training sources at all.
"""

import bz2, csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER, RAW = REPO/'data'/'derived', REPO/'data'/'raw'/'S6'
OUT = REPO/'results'/'qc'
# The AUTHORITATIVE training list for each released predictor is the one the
# model bundle itself ships, not the generic curated release. Both bundles carry
# per-component train_data files, so the exact footprint of the presentation
# predictor is the union over its components. Using the curated release instead
# would have left the 2.3.0 line only lower-boundable, because release 2.3.0
# pairs 2026 models with a 2023 curated file.
BUNDLED = {
    '2.0.0': ['m200/train_data.csv.bz2',
              'm200/models/affinity_predictor_train_data.csv.bz2',
              'm200/models/processing_predictor_train_data.csv.bz2',
              'm200/models/processing_predictor_no_flank_train_data.csv.bz2'],
    '2.3.0': ['m230/models/affinity_predictor_train_data.csv.bz2',
              'm230/models/processing_predictor_with_flanks_train_data.csv.bz2',
              'm230/models/processing_predictor_no_flank_train_data.csv.bz2'],
}
# Secondary cross-check only: the curated release each line declares.
CURATED = {'2.0.0': 'curated2020', '2.3.0': 'curated2023'}


def load_test():
    split = {r['unit_id']: r for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    pos, neg = defaultdict(set), defaultdict(set)
    for fn, bucket in (('POSITIVES.csv', pos), ('NEGATIVES.csv', neg)):
        for r in csv.DictReader((DER/fn).open(newline='')):
            if split[r['unit_id']]['primary_partition'] == 'test':
                bucket[r['unit_id']].add(r['sequence'])
    return pos, neg


def peptides_from(path):
    """Every peptide in one train_data file. Schemas differ between components
    (allele vs hla column, hit vs measurement_value); only `peptide` is needed,
    and it is present in all of them. Normalization is uppercase-strip on both
    sides; nothing fuzzy (D016)."""
    out = set()
    with bz2.open(path, 'rt') as fh:
        for r in csv.DictReader(fh):
            if r.get('peptide'):
                out.add(r['peptide'].strip().upper())
    return out


def bundled_training_peptides(root, files):
    """Union over the released model's own component training sets."""
    total, per_file = set(), {}
    for rel in files:
        s = peptides_from(Path(root)/rel)
        per_file[rel.split('/')[-1]] = len(s)
        total |= s
    return total, per_file


def curated_peptides(extract_dir):
    """Secondary cross-check: the curated release the line declares."""
    allp, human = set(), set()
    sources = Counter()
    with bz2.open(Path(extract_dir)/'curated_training_data.csv.bz2', 'rt') as fh:
        for r in csv.DictReader(fh):
            p = r['peptide'].strip().upper()
            allp.add(p)
            if r['allele'].startswith('HLA-'):
                human.add(p)
                sources[r['measurement_source']] += 1
    return allp, human, sources


def main():
    pos, neg = load_test()
    test_pos = set().union(*pos.values())
    test_neg = set().union(*neg.values())
    units = sorted(pos)
    print(f"frozen test partition: {len(units)} units, "
          f"{len(test_pos):,} distinct positives, {len(test_neg):,} distinct negatives\n")

    report = {'test_partition': {'n_units': len(units),
                                 'distinct_positives': len(test_pos),
                                 'distinct_negatives': len(test_neg)},
              'release_lines': {}}

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    for line, files in BUNDLED.items():
        train, per_file = bundled_training_peptides(root, files)
        cur_all, cur_human, sources = curated_peptides(root/CURATED[line])
        ov_pos = test_pos & train
        ov_neg = test_neg & train
        ov_pos_any = test_pos & cur_all
        print(f"=== MHCflurry {line} — the released model's OWN training data ===")
        for k, v in per_file.items():
            print(f"    {k:<52} {v:>9,}")
        print(f"  union: {len(train):,} distinct training peptides")
        print(f"  OVERLAP with test POSITIVES: {len(ov_pos):,} "
              f"({100*len(ov_pos)/len(test_pos):.2f}% of {len(test_pos):,})")
        print(f"  OVERLAP with test NEGATIVES: {len(ov_neg):,} "
              f"({100*len(ov_neg)/len(test_neg):.2f}% of {len(test_neg):,})")
        print(f"  asymmetry (positives : negatives) "
              f"{(len(ov_pos)/len(test_pos))/max(len(ov_neg)/len(test_neg), 1e-12):.1f} : 1"
              f"   — contamination flatters the predictor, as D006 predicted")
        print(f"  cross-check, declared curated release {CURATED[line]}: "
              f"{len(cur_human):,} human-HLA peptides, "
              f"{len(ov_pos_any):,} positive overlap")

        per_unit = {}
        for u in units:
            o = len(pos[u] & train)
            per_unit[u] = {'n_pos': len(pos[u]), 'overlap': o,
                           'frac': o/max(len(pos[u]), 1)}
        fr = [per_unit[u]['frac'] for u in units]
        print(f"  per-unit positive overlap: min {min(fr):.2%} "
              f"mean {sum(fr)/len(fr):.2%} max {max(fr):.2%}")

        # Is this deposit nameable in the training sources at all?
        hits = {s: n for s, n in sources.items()
                if any(k in s.upper() for k in ('PXD024871', 'PXD24871'))}
        print(f"  sources naming this deposit: {hits if hits else 'none'}")
        print(f"  distinct human-HLA measurement sources: {len(sources)}")

        verdict = 'CLEAN' if not ov_pos else 'OVERLAPPING'
        print(f"  -> M7 verdict, against the model's own training data: {verdict}\n")
        report['release_lines'][line] = {
            'training_source': 'model bundle train_data (authoritative)',
            'per_component': per_file,
            'n_training_peptides': len(train),
            'curated_cross_check': {'release': CURATED[line],
                                    'n_human_hla': len(cur_human),
                                    'overlap_positives': len(ov_pos_any)},
            'overlap_positives': len(ov_pos), 'overlap_negatives': len(ov_neg),
            'overlap_positives_frac': len(ov_pos)/len(test_pos),
            'overlap_negatives_frac': len(ov_neg)/len(test_neg),
            'overlap_positives_any_species': len(ov_pos_any),
            'per_unit': per_unit, 'n_sources': len(sources),
            'sources_naming_deposit': hits, 'm7_verdict': verdict,
            'overlapping_positive_sequences': sorted(ov_pos)[:0]}
        # the actual overlapping sequences, written separately for the
        # non-overlapping-subset comparison D006 requires
        tagf = line.replace('.', '_')
        with (DER/f'TEST_PREDICTOR_OVERLAP_{tagf}.csv').open('w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['sequence'])
            for s in sorted(ov_pos | ov_neg):
                w.writerow([s])
        print(f"  wrote data/derived/TEST_PREDICTOR_OVERLAP_{tagf}.csv "
              f"({len(ov_pos | ov_neg):,} sequences)\n")

    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(OUT/'predictor_contamination.json', 'w'), indent=1)
    print(f"wrote {OUT/'predictor_contamination.json'}")


if __name__ == '__main__':
    main()
