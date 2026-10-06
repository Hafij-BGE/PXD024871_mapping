#!/usr/bin/env python3
"""Build and freeze the split (G6).

Applies the preregistered decisions:
  D011  unit = participant; partitions are participant-disjoint
  D025  every partition platform-stratified; cross-platform transfer preregistered
  D003  shared sequences kept; the leakage-free test subset defined here
  D010  seed('split'), derived per purpose
  D001  allele-disjoint secondary split
  §10   the test partition is untouched during model selection
  §14   5 folds

Primary: 10 units held out as TEST, never seen until the endpoint is computed;
the remaining 42 are split into 5 grouped folds for model selection.

Secondaries, both fixed now rather than after seeing a result:
  allele-disjoint   hold out every unit carrying the most common allele
  cross-platform    train on one instrument, test on the other, and the reverse
"""

import csv, gzip, hashlib, json, random, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER = REPO/'data'/'derived'
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed, BASE                      # noqa: E402

N_TEST, N_FOLDS = 10, 5


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def stratified(units, platform, k, rng):
    """Draw k units keeping platform proportions as close as the counts allow."""
    by = defaultdict(list)
    for u in units:
        by[platform[u]].append(u)
    for v in by.values():
        rng.shuffle(v)
    want = {p: round(k * len(v) / len(units)) for p, v in by.items()}
    while sum(want.values()) != k:          # repair rounding
        p = max(by, key=lambda p: len(by[p]) / max(want[p], 1)) if sum(want.values()) < k \
            else max(want, key=want.get)
        want[p] += 1 if sum(want.values()) < k else -1
    return [u for p in by for u in by[p][:want[p]]]


def main():
    rng = random.Random(seed('split'))

    units_meta = {r['unit_id']: r for r in csv.DictReader((DER/'UNITS.csv').open(newline=''))}
    units = sorted(units_meta)
    platform = {u: ('LTQ' if 'LTQ' in units_meta[u]['instruments'] else 'Lumos') for u in units}
    geno = {u: set(units_meta[u]['hla_genotype'].split(';')) for u in units}
    print(f"units {len(units)}  platforms {Counter(platform.values())}")

    # ---- primary: held-out test, then grouped folds over the remainder ----
    test = sorted(stratified(units, platform, N_TEST, rng))
    rest = [u for u in units if u not in test]
    folds = {}
    for i, u in enumerate(stratified(rest, platform, len(rest), rng)):
        folds[u] = i % N_FOLDS                 # stratified order -> balanced folds
    print(f"\nTEST  {len(test)} units  {Counter(platform[u] for u in test)}")
    print(f"CV    {len(rest)} units over {N_FOLDS} folds")
    for f in range(N_FOLDS):
        fu = [u for u in rest if folds[u] == f]
        print(f"  fold {f}: {len(fu)} units  {dict(Counter(platform[u] for u in fu))}")

    # ---- secondary: allele-disjoint ---------------------------------------
    af = Counter(a for u in units for a in geno[u])
    top, n_top = af.most_common(1)[0]
    allele_test = sorted(u for u in units if top in geno[u])
    print(f"\nALLELE-DISJOINT secondary: hold out {top} carriers -> "
          f"{len(allele_test)} test / {len(units)-len(allele_test)} train")

    # ---- leakage for the ACTUAL primary split, not a random one ------------
    by_unit = defaultdict(set)
    with (DER/'POSITIVES.csv').open(newline='') as fh:
        for r in csv.DictReader(fh):
            by_unit[r['unit_id']].add(r['sequence'])
    tr = set().union(*(by_unit[u] for u in rest))
    te_rows, te_clean = 0, 0
    leak = set()
    for u in test:
        for s in by_unit[u]:
            te_rows += 1
            if s in tr:
                leak.add(s)
            else:
                te_clean += 1
    print(f"\nleakage on the chosen split: {te_rows-te_clean:,} of {te_rows:,} "
          f"test positives also in training ({100*(te_rows-te_clean)/te_rows:.2f}%)")
    print(f"  leakage-free test subset: {te_clean:,} rows "
          f"({100*te_clean/te_rows:.2f}%) -- the D003 sensitivity analysis")

    # ---- write -------------------------------------------------------------
    with (DER/'SPLIT.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['unit_id', 'platform', 'n_alleles', 'primary_partition',
                    'cv_fold', 'allele_disjoint_partition', 'carries_top_allele'])
        for u in units:
            w.writerow([u, platform[u], units_meta[u]['n_alleles'],
                        'test' if u in test else 'cv',
                        '' if u in test else folds[u],
                        'test' if u in allele_test else 'train',
                        'yes' if top in geno[u] else 'no'])
    with (DER/'TEST_LEAKFREE.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['sequence', 'unit_id'])
        for u in test:
            for s in sorted(by_unit[u] - tr):
                w.writerow([s, u])

    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    rec = {
        'frozen_utc': __import__('datetime').datetime.now(
            __import__('datetime').timezone.utc).isoformat(),
        'commit': commit, 'base_seed': BASE, 'split_seed': seed('split'),
        'decisions_applied': {
            'D011': 'unit = participant; partitions participant-disjoint',
            'D025': 'every partition platform-stratified; cross-platform transfer preregistered',
            'D003': 'shared sequences kept; leakage-free test subset written out',
            'D010': "seed('split') derived from the base seed",
            'D001': 'allele-disjoint secondary split constructed',
        },
        'primary': {'test_units': test, 'n_test': len(test), 'n_cv': len(rest),
                    'n_folds': N_FOLDS,
                    'test_platforms': dict(Counter(platform[u] for u in test)),
                    'folds': {str(f): sorted(u for u in rest if folds[u] == f)
                              for f in range(N_FOLDS)}},
        'secondary_allele_disjoint': {'allele': top, 'n_test_units': len(allele_test),
                                      'n_train_units': len(units)-len(allele_test),
                                      'test_units': allele_test},
        'secondary_cross_platform': {
            'LTQ_units': sorted(u for u in units if platform[u] == 'LTQ'),
            'Lumos_units': sorted(u for u in units if platform[u] == 'Lumos'),
            'protocol': 'train on one instrument, evaluate on the other, and the reverse'},
        'leakage_on_chosen_split': {
            'test_positive_rows': te_rows, 'leaked_rows': te_rows-te_clean,
            'leaked_pct': round(100*(te_rows-te_clean)/te_rows, 3),
            'leakfree_rows': te_clean},
        'files': {f: {'sha256': sha256(DER/f), 'bytes': (DER/f).stat().st_size}
                  for f in ('SPLIT.csv', 'TEST_LEAKFREE.csv')},
        'dataset_freeze': json.loads((DER/'FREEZE.json').read_text())['files'],
    }
    (DER/'SPLIT_FREEZE.json').write_text(json.dumps(rec, indent=1))
    print(f"\nFROZEN at {commit[:12]}")
    for f, m in rec['files'].items():
        print(f"  {f:<20} {m['bytes']:>10,} bytes  sha256 {m['sha256'][:16]}")


if __name__ == '__main__':
    main()
