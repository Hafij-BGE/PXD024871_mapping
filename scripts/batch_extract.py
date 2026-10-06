#!/usr/bin/env python3
"""Download, verify, extract and delete class-I containers in batch.

Resumable by design. A Colab session is time-limited and can die mid-job, so
every unit of work is idempotent: a unit whose extract already exists is
skipped, and a container left on disk from a killed run is reconciled before
anything reads it. Re-running after a crash continues rather than restarting.

Per container: retrieve -> verify publisher checksum -> extract peptide table
-> delete the container. Peak disk is one container plus its extract, so the
47.85 GiB class-I set never needs to be resident.

Container selection uses the `*_class_I.msf` filename pattern. That is a
DOWNLOAD FILTER, not a class assignment: authoritative class comes from M3 via
the metadata, and the stems are corroborated 1:1 against the 52 metadata-derived
unit ids before any transfer starts. A mismatch aborts.
"""

import argparse, csv, json, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW_S1, RAW_S3 = REPO/'data'/'raw'/'S1', REPO/'data'/'raw'/'S3'
EXTRACTS = REPO/'data'/'derived'/'peptides'
RETRIEVE = REPO/'scripts'/'retrieve.py'
EXTRACT = REPO/'scripts'/'extract_peptides.py'
RECONCILE = REPO/'scripts'/'reconcile_provenance.py'


def manifest_class1():
    recs = []
    for p in sorted(RAW_S1.glob('files_v3_page*.json')):
        recs.extend(json.loads(p.read_text(encoding='utf-8')))
    out = []
    for r in recs:
        n = r['fileName']
        if not n.endswith('_class_I.msf'):
            continue
        url = next((l.get('value') for l in r['publicFileLocations']
                    if str(l.get('value', '')).startswith('ftp')), None)
        if not url:
            sys.exit(f'no ftp location for {n}')
        out.append({'name': n, 'unit': n[:-len('_class_I.msf')],
                    'size': r['fileSizeBytes'], 'sha1': r['checksum'],
                    'url': url.replace('ftp://', 'https://')})
    return sorted(out, key=lambda r: r['size'])


def known_units():
    f = REPO/'data'/'derived'/'UNITS.csv'
    if not f.exists():
        sys.exit('UNITS.csv missing: run scripts/phase_a_mapping.py first')
    return {r['unit_id'] for r in csv.DictReader(f.open(newline='', encoding='utf-8'))}


def done_units():
    if not EXTRACTS.exists():
        return set()
    return {p.name.split('.')[0] for p in EXTRACTS.glob('*.csv*')}


def run(cmd):
    return subprocess.run([sys.executable, '-I'] + cmd, cwd=REPO,
                          capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='stop after N containers (0 = all)')
    ap.add_argument('--keep', action='store_true', help='do not delete containers after extraction')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    RAW_S3.mkdir(parents=True, exist_ok=True)
    (RAW_S3/'provenance.jsonl').touch()

    containers = manifest_class1()
    units, stems = known_units(), {c['unit'] for c in containers}
    if stems != units:
        sys.exit(f'ABORT: container stems do not match UNITS.csv. '
                 f'only-in-containers={sorted(stems-units)} only-in-units={sorted(units-stems)}')
    print(f'{len(containers)} class-I containers; stems match all {len(units)} metadata units')

    # reconcile anything a previous killed run left behind
    r = run([str(RECONCILE), '--source-id', 'S3', '--write'])
    for line in r.stdout.splitlines():
        if 'NO record' in line or 'PROBLEM' in line or 'wrote' in line:
            print(f'  reconcile: {line.strip()}')

    done = done_units()
    todo = [c for c in containers if c['unit'] not in done]
    print(f'already extracted: {len(done)}  remaining: {len(todo)}  '
          f'({sum(c["size"] for c in todo)/2**30:.2f} GiB to transfer)')
    if a.limit:
        todo = todo[:a.limit]
        print(f'  limited to {len(todo)} this run')
    if a.dry_run:
        for c in todo:
            print(f'  would fetch {c["name"]} ({c["size"]/2**20:,.0f} MiB)')
        return

    ok = fail = 0
    for i, c in enumerate(todo, 1):
        t0 = time.time()
        print(f'[{i}/{len(todo)}] {c["name"]} ({c["size"]/2**20:,.0f} MiB)', flush=True)
        dest = RAW_S3/c['name']
        if not dest.exists():
            r = run([str(RETRIEVE), '--source-id', 'S3', '--url', c['url'],
                     '--filename', c['name'], '--origin', 'PRIDE Archive, EMBL-EBI',
                     '--published-checksum', f'sha1:{c["sha1"]}'])
            if r.returncode != 0:
                print(f'  RETRIEVE FAILED: {(r.stdout or r.stderr).strip()[:200]}')
                dest.unlink(missing_ok=True)
                fail += 1
                continue
        cmd = [str(EXTRACT), c['name']] + ([] if a.keep else ['--delete'])
        r = run(cmd)
        if r.returncode != 0:
            print(f'  EXTRACT FAILED: {(r.stdout or r.stderr).strip()[:200]}')
            fail += 1
            continue
        print(f'  {r.stdout.strip()}  [{time.time()-t0:.0f}s]', flush=True)
        ok += 1

    print(f'\ndone: {ok} extracted, {fail} failed, {len(done_units())} units total')
    if fail:
        print('re-run to retry the failures; completed units are skipped')
        sys.exit(1)


if __name__ == '__main__':
    main()
