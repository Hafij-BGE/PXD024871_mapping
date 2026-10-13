#!/usr/bin/env python3
"""Check that tracked artifacts can be REGENERATED, not merely that they are unchanged.

The freeze gate hashes outputs. That proves nothing has been tampered with; it
does not prove anything could be produced again. The difference is not academic:
`leakage_audit.py` part 2 was non-deterministic from run-010 until D053 found it,
and **every one of the nine checks passed throughout**, because check 5
regenerates figures from stored JSON and check 8 compares hashes to a manifest
written from the same tree. Nothing re-ran the script that wrote the JSON. This
is the check that would have caught it.

Three classes, and the distinction is load-bearing.

  BYTES    Deterministic on tracked inputs, no model scoring. The artifact must
           regenerate byte-identically. This is where the hash-ordering defect
           class lives and where the check has teeth.

  NUMERIC  Scores the 25 frozen checkpoints. torch accumulates in a
           non-associative order, so byte-identity is not achievable: the
           endpoint reproduces to -4.2e-09 and endpoint_by_length to 2.2e-08.
           Demanding byte-identity here would produce a gate that fails for a
           reason nobody can fix, which is worse than no gate. Compared
           numerically at TOL instead.

  EXEMPT   Cannot run from tracked inputs alone, or must never run. Each carries
           its reason. An exemption is a claim, and it is listed so a reader can
           dispute it.

Every script under scripts/ that writes a tracked artifact must appear in one of
the three. An unclassified script fails the check -- the same discipline check 5
applies to figures, for the same reason: a count silently accepts a newcomer, a
named set does not.

The artifact is restored from its pre-run bytes in a `finally`, so a failing or
interrupted run cannot leave a modified tree. The scripts are deterministic when
healthy, so the restore is a no-op in the passing case.

    python3 scripts/regen_check.py           # BYTES + NUMERIC
    python3 scripts/regen_check.py --fast    # BYTES only
    python3 scripts/regen_check.py --list    # the classification, run nothing
"""

import json, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOL = 1e-6          # far above the ~1e-8 drift, far below any real change

# script -> (artifact it writes, comparison mode)
REGENERABLE = {
    'union_analysis.py':      ('results/qc/union_stats.json',          'BYTES'),
    'negative_diagnostic.py': ('results/qc/negative_diagnostic.json',  'BYTES'),
    'recurrence_oracle.py':   ('results/qc/recurrence_oracle.json',    'BYTES'),
    'leakage_audit.py':       ('results/qc/leakage_audit_v2.json',     'BYTES'),
    'tau_realised.py':        ('results/power/tau_realised.json',      'BYTES'),
    'negset_margin.py':       ('results/qc/negset_margin.json',        'BYTES'),
    'endpoint_by_length.py':  ('results/model/endpoint_by_length.json', 'NUMERIC'),
    'prevalence_matched.py':  ('results/qc/prevalence_matched.json',   'NUMERIC'),
}

EXEMPT = {
    'train_cnn.py':
        'retrains. The 25 checkpoints are hash-verified inputs, not regenerable '
        'outputs: they were trained on a Tesla T4 under torch 2.11.0+cu130 and '
        'this environment has no GPU (D052). Its selftest is check 9.',
    'build_dataset.py':
        'rebuilds the preregistered dataset. Must never run in a gate: D009 '
        'fixes those artifacts and check 2 exists to prove they have not moved.',
    'build_split.py':
        'rebuilds the preregistered split. Same reason as build_dataset.py.',
    'contamination_all.py':
        'requires sys.argv[1], the root of the predictors\' own training '
        'corpora, which are licensed third-party data and not tracked (S6).',
    'predictor_contamination.py':
        'same third-party training corpora as contamination_all.py.',
    'compare_predictors_all.py':
        'reads results/predictors/*_test_scores.csv, which are tracked, but '
        'needs ~8 minutes to score 25 checkpoints over four predictor row sets. '
        'Covered instead by check 4, which matches its headline numbers '
        'verbatim against REPORT.md.',
    'compare_predictors.py':  'superseded by compare_predictors_all.py (D036).',
    'decoy_exposure_bound.py':
        'needs data/raw/S5/UP000005640_9606.fasta.gz, 7.7 MB, retrieved on '
        'demand and not tracked. The script verifies its SHA-256 against the S5 '
        'provenance record itself and refuses if the release has rotated.',
    'replicate_px4023.py':
        'needs data/external/PXD004023/units.json, withheld pending the '
        'redistribution position for that deposit (D054 section 4).',
    'extract_px4023.py':   'needs the 1.1 GB of mzIdentML, not tracked (D054).',
    'label_px4023_runs.py':
        'needs the 161 MB of raw-file headers, not tracked (D054). It has its '
        'own --check mode that reproduces runmap.csv byte-identically.',
    'multi_allele.py':     'needs ~40 minutes of retraining across allele strata.',
    'allele_leakfree.py':  'depends on multi_allele.py outputs.',
    'subsample_curve.py':  'retrains at each subsample size.',
    'power_analysis.py':   'simulation over a grid; minutes, and its output is '
                           'a design document input, not a result.',
    'calibrate_decision_rule.py':
        'simulation that fixed the preregistered threshold before the endpoint '
        'was read. Re-running it cannot change a threshold already frozen.',
    'benchmark_compute.py': 'measures this machine, so it is expected to differ.',
    'phase_a_mapping.py':  'needs the deposited metadata containers (S1, S2).',
    'extract_peptides.py': 'needs the identification containers (S3).',
    'batch_extract.py':    'driver for extract_peptides.py; same inputs.',
    'retrieve.py':         'network retrieval of S1-S7.',
    'predict_mhcflurry.py':   'needs MHCflurry installed (S6).',
    'predict_netmhcpan.py':   'needs NetMHCpan 4.1 under its DTU licence (S6).',
    'predict_mixmhcpred.py':  'needs MixMHCpred 3.0 (S6).',
    'reconcile_provenance.py': 'reporting helper; writes no tracked artifact.',
    'make_figures.py':     'already re-run by freeze check 5.',
    'capture_environment.py': 'prints; writes nothing.',
    'check_references.py': 'is itself a gate.',
    'freeze.py':           'is itself the gate.',
    'regen_check.py':      'is this check.',
    'seeds.py':            'pure function, no outputs.',
}


def numeric_close(a, b, tol=TOL, path='$'):
    """Deep compare two JSON structures, allowing tol on floats."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False, f'{path}: keys differ'
        for k in a:
            ok, why = numeric_close(a[k], b[k], tol, f'{path}.{k}')
            if not ok:
                return False, why
        return True, ''
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False, f'{path}: length {len(a)} vs {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            ok, why = numeric_close(x, y, tol, f'{path}[{i}]')
            if not ok:
                return False, why
        return True, ''
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        if abs(a-b) <= tol:
            return True, ''
        return False, f'{path}: {a!r} vs {b!r} (|d| {abs(a-b):.3e} > {tol:g})'
    if a == b:
        return True, ''
    return False, f'{path}: {a!r} vs {b!r}'


def classified_ok():
    """Every script under scripts/ must be classified. A newcomer fails."""
    on_disk = {p.name for p in (REPO/'scripts').glob('*.py')}
    known = set(REGENERABLE) | set(EXEMPT)
    return sorted(on_disk - known), sorted(known - on_disk - {'regen_check.py'})


def main():
    if '--list' in sys.argv:
        print(f'{"script":28s} {"mode":8s} artifact')
        for s, (a, m) in sorted(REGENERABLE.items()):
            print(f'  {s:26s} {m:8s} {a}')
        print(f'\n{len(EXEMPT)} exempt:')
        for s, why in sorted(EXEMPT.items()):
            print(f'  {s:26s} {why}')
        return 0

    fast = '--fast' in sys.argv
    unclassified, missing = classified_ok()
    fails = []
    print('regeneration check')
    if unclassified:
        print(f'  FAIL  unclassified script(s): {unclassified}')
        print('        Add each to REGENERABLE or EXEMPT in scripts/regen_check.py.')
        fails.append('unclassified')
    if missing:
        print(f'  note  listed but absent from scripts/: {missing}')

    for script, (rel, mode) in sorted(REGENERABLE.items()):
        if fast and mode != 'BYTES':
            print(f'  SKIP  {script:26s} {mode} (--fast)')
            continue
        art = REPO/rel
        if not art.exists():
            print(f'  FAIL  {script:26s} artifact missing: {rel}')
            fails.append(script)
            continue
        before = art.read_bytes()
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, str(REPO/'scripts'/script)],
                               capture_output=True, text=True, cwd=str(REPO))
            dt = time.time() - t0
            if r.returncode != 0:
                tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ['']
                print(f'  FAIL  {script:26s} exit {r.returncode}: {tail[0][:70]}')
                fails.append(script)
                continue
            after = art.read_bytes()
            if mode == 'BYTES':
                if after == before:
                    print(f'  PASS  {script:26s} byte-identical   {dt:5.1f}s')
                else:
                    print(f'  FAIL  {script:26s} NOT byte-identical '
                          f'({len(before)} -> {len(after)} bytes)   {dt:5.1f}s')
                    fails.append(script)
            else:
                ok, why = numeric_close(json.loads(before), json.loads(after))
                if ok:
                    print(f'  PASS  {script:26s} numeric within {TOL:g}   {dt:5.1f}s')
                else:
                    print(f'  FAIL  {script:26s} {why}   {dt:5.1f}s')
                    fails.append(script)
        finally:
            # Restore unconditionally. Deterministic scripts make this a no-op;
            # a crash or a real failure must not leave the tree modified.
            art.write_bytes(before)

    if fails:
        print(f'\nREGEN CHECK FAILED: {len(fails)} -> {fails}')
        print('An artifact that cannot be regenerated is not reproducible, '
              'whatever its hash says.')
        return 1
    print('\nREGEN CHECK PASSED: every classified artifact regenerates')
    return 0


if __name__ == '__main__':
    sys.exit(main())
