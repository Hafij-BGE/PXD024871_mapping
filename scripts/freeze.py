#!/usr/bin/env python3
"""Verify the repository, then freeze it.

A checksum manifest of an unverified tree records only that a mess was
reproducible. So `--verify` runs first and `--write` refuses unless it passes.

Checks:
  1  working tree clean, nothing untracked
  2  the preregistration checksums still hold -- the frozen dataset and split
     have not moved since commit f7550f54 (D009)
  3  every artifact and script REPORT.md names exists
  4  every headline number in REPORT.md matches the artifact it came from
  5  the figures regenerate byte-identically from those artifacts
  6  every gate in SECTIONS.md is PASSED or carries a recorded unavailability
  7  every decision D001..Dnnn has an entry and a resolved status
  8  the trainer's own selftest passes
"""

import hashlib, json, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R = lambda p: (REPO/p).read_text()
FAIL = []


def ok(cond, label, detail=''):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  {detail}" if detail else ''))
    if not cond:
        FAIL.append(label)
    return cond


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def git(*a):
    return subprocess.run(['git', '-C', str(REPO)] + list(a),
                          capture_output=True, text=True).stdout.strip()


def verify():
    print("1. working tree")
    ok(git('status', '--porcelain') == '', 'clean, nothing untracked')

    print("\n2. preregistration checksums still hold (D009)")
    pre = R('PREREGISTRATION.md')
    n = 0
    for m in re.finditer(r'^  ([0-9a-f]{64})  (\S+)$', pre, re.M):
        want, name = m.groups()
        f = REPO/'data'/'derived'/name
        if f.exists():
            n += 1
            ok(sha(f) == want, f'{name} unchanged since the freeze')
    ok(n >= 6, f'{n} preregistered artifacts checked')

    print("\n3. everything REPORT.md names exists")
    rep = R('REPORT.md')
    missing = []
    for m in re.finditer(r'`((?:results|data|scripts)/[\w./-]+)`', rep):
        if not (REPO/m.group(1)).exists():
            missing.append(m.group(1))
    for m in re.finditer(r'\]\((results/figures/[\w.-]+)\)', rep):
        if not (REPO/m.group(1)).exists():
            missing.append(m.group(1))
    for m in re.finditer(r'`(\w+\.py)`', rep):
        if not (REPO/'scripts'/m.group(1)).exists():
            missing.append('scripts/' + m.group(1))
    ok(not missing, 'all referenced paths resolve',
       '' if not missing else f'missing: {sorted(set(missing))}')

    print("\n4. headline numbers match their artifacts")
    J = lambda p: json.loads(R(f'results/{p}'))
    e, L = J('model/endpoint.json'), J('model/endpoint_by_length.json')
    T, D = J('model/transfer.json'), J('model/multi_allele_dod.json')
    C, K = J('qc/predictor_comparison.json'), J('qc/predictor_contamination.json')
    checks = [('endpoint', e['primary']['mean_ap'], '{:.4f}'),
              ('endpoint CI lo', e['primary']['ci99_lo'], '{:.4f}'),
              ('endpoint CI hi', e['primary']['ci99_hi'], '{:.4f}'),
              ('leakage-free', e['leakage_free']['mean_ap'], '{:.4f}'),
              ('inflation', e['primary']['mean_ap'] - e['leakage_free']['mean_ap'], '{:.4f}')]
    for a in T['arms']:
        if a['kind'].startswith('preregistered'):
            checks.append((a['id'], a['evals'][0]['mean_ap'], '{:.4f}'))
    pb = {r['stratum']: r for r in D['part_B']}
    checks += [('part B adjusted', pb['HLA-A*02:01']['adjusted'], '{:.4f}'),
               ('part B CI lo', pb['HLA-A*02:01']['ci99'][0], '{:.4f}'),
               ('part B CI hi', pb['HLA-A*02:01']['ci99'][1], '{:.4f}')]
    for r in D['part_A']:
        checks.append((f"{r['allele']} adjusted", r['excl_minus_neutral'], '{:.4f}'))
    prim = C['row_sets']['mutually naive (PRIMARY)']
    checks.append(('CNN primary', prim['systems']['CNN']['mean_ap'], '{:.4f}'))
    for c in prim['contrasts']:
        checks.append((f"CNN - {c['vs']}", c['difference'], '{:.4f}'))
    for line, d in K['release_lines'].items():
        checks.append((f'overlap {line}', 100 * d['overlap_positives_frac'], '{:.2f}'))
    for r in L['by_length']:
        checks.append((r['stratum'], r['mean_ap'], '{:.4f}'))
    bad = [n for n, v, f in checks if f.format(v) not in rep]
    ok(not bad, f'{len(checks)} numbers found verbatim in REPORT.md',
       '' if not bad else f'absent: {bad}')

    print("\n5. figures regenerate byte-identically")
    before = {p.name: sha(p) for p in sorted((REPO/'results'/'figures').glob('*.svg'))}
    subprocess.run([sys.executable, str(REPO/'scripts'/'make_figures.py')],
                   capture_output=True)
    after = {p.name: sha(p) for p in sorted((REPO/'results'/'figures').glob('*.svg'))}
    ok(before == after and len(before) == 7,
       f'{len(before)} figures reproduce from the artifacts',
       '' if before == after else 'DRIFT: ' + str([k for k in before if before[k] != after.get(k)]))

    print("\n6. gates")
    sec = R('SECTIONS.md')
    for g in ('G10', 'G11', 'G12', 'G13'):
        line = next((l for l in sec.splitlines() if l.startswith(g + ' ')), '')
        ok('PASSED' in line, f'{g} passed', line.strip()[-28:])
    ok('All gates are now closed' in sec, 'gate summary records closure')

    print("\n7. decision log")
    dl = R('DECISION_LOG.md')
    ids = sorted({int(m) for m in re.findall(r'\bD(\d{3})\b', dl)})
    gaps = [i for i in range(1, max(ids) + 1) if i not in ids]
    ok(not gaps, f'D001..D{max(ids):03d} all present', '' if not gaps else f'gaps {gaps}')
    # The status lives in the entry BODY as often as in its heading, so scan
    # the opening lines of each entry rather than the heading alone. An earlier
    # version of this check read only headings and reported six resolved
    # entries as open.
    parts = re.split(r'^## (D\d{3}) — ', dl, flags=re.M)
    entries = list(zip(parts[1::2], parts[2::2]))
    unres = []
    for did, body in entries:
        headroom = '\n'.join(body.splitlines()[:8])
        if not re.search(r'RESOLVED|ACCEPTED|RATIFIED|PERMANENT|CONFIRMED',
                         headroom, re.I):
            unres.append(did)
    ok(not unres, f'{len(entries)} written-up entries, all resolved',
       '' if not unres else f'open: {unres}')
    openq = [d for d, b in entries if re.search(r'\bStatus: OPEN\b|· OPEN\b',
                                                '\n'.join(b.splitlines()[:8]))]
    ok(not openq, 'no decision left OPEN', '' if not openq else f'OPEN: {openq}')

    man = REPO/'freeze_manifest.json'
    if man.exists():
        print("\n8. existing manifest agrees with the tree")
        mj = json.loads(man.read_text())
        drift = [f['path'] for f in mj['files']
                 if (REPO/f['path']).exists() and sha(REPO/f['path']) != f['sha256']]
        gone = [f['path'] for f in mj['files'] if not (REPO/f['path']).exists()]
        ok(not drift and not gone, f"{len(mj['files'])} manifest entries match",
           '' if not (drift or gone) else f'drift {drift} missing {gone}')
        ok(mj.get('excludes') == [MANIFEST],
           'manifest excludes itself, the one file it cannot hash')

    print("\n9. trainer selftest")
    r = subprocess.run([sys.executable, str(REPO/'scripts'/'train_cnn.py'),
                        '--mode', 'selftest'], capture_output=True, text=True)
    ok('ALL SELFTESTS PASS' in r.stdout, 'encoder, AP, gradients, overfit')

    print()
    if FAIL:
        print(f"VERIFY FAILED: {len(FAIL)} check(s) -> {FAIL}")
        return False
    print("VERIFY PASSED: every check clean")
    return True


MANIFEST = 'freeze_manifest.json'


def write_manifest():
    # The manifest cannot carry its own hash: hashing it and then overwriting it
    # stores the PREVIOUS version's digest, which makes the file disagree with
    # itself. The first run of this script did exactly that, and the documented
    # verification command reported freeze_manifest.json as changed. It is the
    # one file the manifest cannot cover, so it is excluded and said so.
    files = [f for f in git('ls-files').splitlines() if f and f != MANIFEST]
    rows, total = [], 0
    for f in sorted(files):
        p = REPO/f
        if not p.exists():
            continue
        sz = p.stat().st_size
        total += sz
        rows.append({'path': f, 'bytes': sz, 'sha256': sha(p)})
    man = {'frozen_utc': subprocess.run(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'],
                                        capture_output=True, text=True).stdout.strip(),
           'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
           'parent_commit': git('rev-parse', 'HEAD'),
           'n_files': len(rows), 'total_bytes': total,
           'excludes': [MANIFEST],
           'note': 'parent_commit is the commit BEFORE this manifest was committed. '
                   'The anchor is the commit that ADDS this file; a manifest cannot '
                   'contain the hash of the commit that carries it, nor its own '
                   'digest, so freeze_manifest.json is the one file excluded.',
           'files': rows}
    (REPO/'freeze_manifest.json').write_text(json.dumps(man, indent=1))
    print(f"wrote freeze_manifest.json: {len(rows)} files, {total/1e6:.1f} MB")
    return man


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else '--verify'
    good = verify()
    if mode == '--write':
        if not good:
            sys.exit("\nREFUSING to freeze: verification failed. A checksum manifest "
                     "of an unverified tree records only that a mess was reproducible.")
        write_manifest()
    sys.exit(0 if good else 1)
