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

import argparse, csv, json, shutil, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    ap.add_argument('--parallel', type=int, default=1,
                    help='concurrent downloads. EBI rate-limits per connection, so '
                         'this is usually near-linear. Bounded by free disk.')
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

    # Disk guard. Parallel downloads multiply peak usage, and the largest
    # container is 9.25 GiB, so N workers can need N x that before any is
    # deleted. Refuse rather than fill the disk mid-run.
    workers = max(1, a.parallel)
    if workers > 1:
        free = shutil.disk_usage(REPO).free
        biggest = max(c['size'] for c in todo)
        need = workers * biggest * 1.2          # container + its extract, with slack
        if need > free * 0.8:
            safe = max(1, int(free * 0.8 / (biggest * 1.2)))
            print(f'  disk guard: {workers} workers would need {need/2**30:.1f} GiB of '
                  f'{free/2**30:.1f} GiB free; reducing to {safe}')
            workers = safe
        print(f'  downloading {workers} containers concurrently')

    lock = threading.Lock()
    counter = {'n': 0, 'ok': 0, 'fail': 0}

    def process(c):
        t0 = time.time()
        dest = RAW_S3/c['name']
        complete = dest.exists() and dest.stat().st_size == c['size']
        if not complete:
            # A partial from a previous attempt is resumed, not discarded. The
            # checksum afterwards is what makes that safe.
            extra = ['--resume'] if dest.exists() else []
            r = run([str(RETRIEVE), '--source-id', 'S3', '--url', c['url'],
                     '--filename', c['name'], '--origin', 'PRIDE Archive, EMBL-EBI',
                     '--published-checksum', f'sha1:{c["sha1"]}'] + extra)
            if r.returncode != 0:
                # Keep the partial so the next run resumes; delete only if the
                # bytes are known bad.
                if 'CHECKSUM_MISMATCH' in (r.stdout or ''):
                    dest.unlink(missing_ok=True)
                return c, False, (r.stdout or r.stderr).strip()[:160], time.time()-t0
        r = run([str(EXTRACT), c['name']] + ([] if a.keep else ['--delete']))
        if r.returncode != 0:
            return c, False, (r.stdout or r.stderr).strip()[:160], time.time()-t0
        return c, True, r.stdout.strip(), time.time()-t0

    started = time.time()
    bytes_done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(process, c): c for c in todo}
        for fut in as_completed(futs):
            c, good, msg, dt = fut.result()
            with lock:
                counter['n'] += 1
                counter['ok' if good else 'fail'] += 1
                if good:
                    bytes_done += c['size']
                elapsed = time.time() - started
                rate = bytes_done / elapsed / 2**20 if elapsed > 0 else 0
                tag = 'ok  ' if good else 'FAIL'
                print(f'[{counter["n"]}/{len(todo)}] {tag} {c["name"]:<24} '
                      f'{c["size"]/2**20:>6,.0f} MiB  {dt:>5.0f}s  '
                      f'| aggregate {rate:.1f} MiB/s  | {msg[:60]}', flush=True)

    ok, fail = counter['ok'], counter['fail']
    elapsed = time.time() - started
    print(f'\ndone: {ok} extracted, {fail} failed, {len(done_units())} units total')
    if elapsed > 0 and bytes_done:
        print(f'aggregate throughput: {bytes_done/elapsed/2**20:.2f} MiB/s '
              f'over {elapsed/60:.1f} min with {workers} worker(s)')
    if fail:
        print('re-run to retry the failures; completed units are skipped')
        sys.exit(1)


if __name__ == '__main__':
    main()
