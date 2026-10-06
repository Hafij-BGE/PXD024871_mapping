#!/usr/bin/env python3
"""Extract the unique peptide table from one identification container.

Refuses to extract a container whose provenance record does not show a verified
publisher checksum. A truncated transfer can leave a file that opens and
under-reports, so the integrity check is the checksum, never the reader's
willingness to open the database.
"""
import argparse, csv, hashlib, json, ntpath, sqlite3, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW, DER = REPO/'data'/'raw'/'S3', REPO/'data'/'derived'/'peptides'
LO, HI = 8, 12


def provenance_ok(name):
    log = RAW/'provenance.jsonl'
    best = None
    for line in log.read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            if r['original_filename'] == name:
                best = r
    if best is None:
        return False, 'no provenance record'
    if best['outcome'] != 'RETRIEVED':
        return False, f"outcome {best['outcome']}"
    if best.get('published_checksum_verified') is not True:
        return False, 'publisher checksum not verified'
    return True, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('container')
    ap.add_argument('--delete', action='store_true', help='delete the container after extraction')
    a = ap.parse_args()
    name = Path(a.container).name
    src = RAW/name
    ok, why = provenance_ok(name)
    if not ok:
        sys.exit(f'REFUSING to extract {name}: {why}')
    if not src.exists():
        sys.exit(f'{src} not present')

    unit = name.replace('_class_I.msf', '').replace('_class_II.msf', '')
    DER.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    runs = [ntpath.basename(f) for (f,) in con.execute('SELECT FileName FROM FileInfos')]
    rows = con.execute(
        'SELECT Sequence, LENGTH(Sequence), MIN(ConfidenceLevel), COUNT(*) FROM Peptides '
        'WHERE LENGTH(Sequence) BETWEEN ? AND ? GROUP BY Sequence ORDER BY Sequence',
        (LO, HI)).fetchall()
    n_all = con.execute('SELECT COUNT(*) FROM Peptides').fetchone()[0]
    con.close()

    out = DER/f'{unit}.csv'
    with out.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['sequence', 'length', 'best_confidence_level', 'n_psms', 'unit_id', 'container'])
        for seq, L, cl, n in rows:
            w.writerow([seq, L, cl, n, unit, name])

    meta = {'container': name, 'unit_id': unit, 'internal_run_refs': runs,
            'n_internal_runs': len(runs), 'psms_total': n_all,
            'unique_sequences': len(rows),
            'extract_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
            'length_window': [LO, HI]}
    (DER/f'{unit}.meta.json').write_text(json.dumps(meta, indent=1))
    print(f'{unit}: {len(rows):,} unique / {n_all:,} PSMs over {len(runs)} internal runs')
    if a.delete:
        src.unlink()
        print(f'  deleted {name}')


if __name__ == '__main__':
    main()
