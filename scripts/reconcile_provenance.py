#!/usr/bin/env python3
"""Reconcile a raw directory against its provenance log and the S1 manifest.

Provenance must not depend on the download process surviving to write its own
record. A container can finish transferring and the writer can still die before
logging it, leaving a file on disk that nothing accounts for. This recovers
that state from the file itself: hash what is present, verify against the
publisher's checksum from the manifest, and write any missing record.

Reports in both directions. A file with no record is recoverable. A record with
no file is either a streamed-and-deleted container, which is expected, or a
loss, which is not, and the two are distinguished by the recorded outcome.
"""

import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / 'data' / 'raw'


def digest(path, algo):
    h = hashlib.new(algo)
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest_index():
    idx = {}
    for p in sorted((RAW / 'S1').glob('files_v3_page*.json')):
        for r in json.loads(p.read_text(encoding='utf-8')):
            idx[r['fileName']] = r
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-id', required=True)
    ap.add_argument('--write', action='store_true', help='write missing records')
    a = ap.parse_args()

    d = RAW / a.source_id
    log = d / 'provenance.jsonl'
    recorded = {}
    if log.exists():
        for line in log.read_text(encoding='utf-8').splitlines():
            if line.strip():
                r = json.loads(line)
                recorded.setdefault(r['original_filename'], []).append(r)

    on_disk = {p.name for p in d.iterdir() if p.is_file() and p.name != 'provenance.jsonl'}
    idx = manifest_index()

    unrecorded = sorted(on_disk - set(recorded))
    missing_file = sorted(n for n, rs in recorded.items()
                          if n not in on_disk and any(r['outcome'] == 'RETRIEVED' for r in rs))

    print(f"source {a.source_id}: {len(on_disk)} files on disk, {len(recorded)} filenames in log")
    print(f"  on disk with NO record     : {len(unrecorded)} {unrecorded}")
    print(f"  recorded RETRIEVED, absent : {len(missing_file)} {missing_file}")
    print("  (the second set is expected for streamed-and-deleted containers)")

    added = 0
    for name in unrecorded:
        p = d / name
        m = idx.get(name, {})
        pub = (m.get('checksum') or '').strip()
        rec = {
            'source_id': a.source_id,
            'origin': 'PRIDE Archive, EMBL-EBI',
            'accession_or_url': next((l.get('value') for l in m.get('publicFileLocations', [])
                                      if str(l.get('value', '')).startswith('ftp')), 'UNKNOWN'),
            'version': 'as published',
            'retrieval_date': datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
            'original_filename': name,
            'local_path': str(p.relative_to(REPO)),
            'license': 'PENDING',
            'reference': 'PENDING',
            'acquisition_method': 'scripts/retrieve.py (record reconstructed by '
                                  'scripts/reconcile_provenance.py; the downloader did not '
                                  'survive to log it)',
            'processing_history': 'NONE',
            'published_checksum': f'sha1:{pub}' if pub else 'ABSENT',
            'outcome': 'RETRIEVED',
            'checksum': f'sha256:{digest(p, "sha256")}',
            'file_size': p.stat().st_size,
            'reconciled': True,
        }
        if pub:
            got = digest(p, 'sha1')
            rec['published_checksum_verified'] = (got.lower() == pub.lower())
            if not rec['published_checksum_verified']:
                rec['outcome'] = 'CHECKSUM_MISMATCH'
                rec['error'] = f'published {pub}, computed {got}'
        size_ok = m.get('fileSizeBytes') == rec['file_size']
        rec['manifest_size_agrees'] = size_ok
        flag = 'OK' if rec['outcome'] == 'RETRIEVED' and rec.get('published_checksum_verified') else 'PROBLEM'
        print(f"  {name}: sha1 verified={rec.get('published_checksum_verified')} "
              f"size agrees={size_ok} -> {flag}")
        if a.write:
            with log.open('a') as fh:
                fh.write(json.dumps(rec) + '\n')
            added += 1

    if a.write:
        print(f"  wrote {added} reconstructed record(s)")
    elif unrecorded:
        print("  dry run; pass --write to record these")


if __name__ == '__main__':
    main()
