#!/usr/bin/env python3
"""Label each PXD004023 acquisition run with its instrument, from the raw header.

Writes data/external/PXD004023/runmap.csv, the table that establishes this
cohort's confound structure: instrument, acquisition year and SCX fractionation
partition the 160 runs identically, 95 against 65, with no run breaking the
pattern. That table is the central caveat on the whole replication, so it needs
a generator rather than being data of unknown provenance.

**Why this exists (D054).** runmap.csv was first built ad hoc in the session
that ran the replication; the labelling step was never written to a file. The
committed table therefore asserted `confidence=verified` and
`evidence=raw header bytes 0-1048576` while nothing in the tree could reproduce
it. That is the same defect Stage 3 was opened to fix -- a cited artifact with
no tracked generator -- so it is fixed here rather than deferred.

Input:  data/external/PXD004023/hdr/<name>.head  -- the first 1,048,576 bytes of
        each acquisition file, retrieved by `scripts/fetch_px4023.sh headers`.
        NOT committed, 161 MB; their SHA-256 are in header_checksums.txt and
        `fetch_px4023.sh verify` checks them.
Output: data/external/PXD004023/runmap.csv

The file list comes from raw_manifest.txt, **not** from globbing the directory.
A stray or renamed file in hdr/ therefore cannot add a row, and a missing one is
reported rather than silently skipped.

Thermo .raw headers store the instrument model as UTF-16LE text. `Orbitrap
Elite` appears inside `LTQ Orbitrap Elite`, and `Exactive` inside `Q Exactive
Plus`, so the models are matched longest-first and the canonical name recorded
is the one runmap.csv already used.

**What `confidence` means, exactly.** `verified` records that **exactly one**
recognised instrument model string was found in the retrieved header, at either
byte alignment. It means nothing more than that:

  * it is **not** verification by the depositor, and not agreement with any
    record PRIDE publishes. PRIDE's per-file checksums were never collected for
    this deposit (`DATA_SOURCES.md` S8, `published_checksum: Not retrieved`);
  * the SHA-256 in `header_checksums.txt` are **this project's own**, computed
    from the bytes we retrieved. They detect local corruption or substitution
    after retrieval. They cannot establish that the bytes we received are the
    bytes the depositor uploaded;
  * it says nothing about the acquisition itself, only about a string in a file
    header.

`ambiguous` means more than one model was found, `none` that no model was. Both
refuse to write.

Run with --check to compare against the committed table without writing.
"""

import csv, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXT = REPO/'data'/'external'/'PXD004023'
HDR = EXT/'hdr'
OUT = EXT/'runmap.csv'
MANIFEST = EXT/'raw_manifest.txt'
EVIDENCE = 'raw header bytes 0-1048576'
HEADER = ['file', 'donor', 'date', 'era', 'fraction', 'instrument',
          'confidence', 'evidence', 'all_strings']

# Longest first: 'LTQ Orbitrap Elite' contains 'Orbitrap Elite', and
# 'Q Exactive Plus' contains 'Exactive'. The second element is the canonical
# name written to runmap.csv.
MODELS = [
    ('LTQ Orbitrap Elite', 'Orbitrap Elite'),
    ('Orbitrap Elite',     'Orbitrap Elite'),
    ('Q Exactive Plus',    'Q Exactive Plus'),
]

# 2014 arm: pat_<donor>_<ddmmyyyy>_rep<n>[...]   -- one file carries a trailing
#           _2 after the replicate number, so this is not anchored at the end.
# 2013 arm: <donor>_rep<n>_<ddmmyy>[_Fx<n>mM]
RE_2014 = re.compile(r'^pat_(.+?)_(\d{8})_rep\d+')
RE_2013 = re.compile(r'^(.+?)_rep\d+_(\d{6})(?:_Fx(\d+mM))?$')


def models_in(path):
    """Canonical instrument names present in one header, longest match first.

    Both byte alignments are scanned. UTF-16LE text decoded from offset 0 only
    would miss any string starting at an odd offset -- and these headers are
    1,048,577 bytes, an odd length, so appended or shifted content lands at the
    wrong parity. A second model string hidden at an odd offset would then be
    invisible and the run would be labelled `verified` on the one model the
    decoder happened to see. Scanning offsets 0 and 1 removes that blind spot.

    MODELS order is preserved so that `all_strings` is stable regardless of
    which alignment a string was found at.
    """
    raw = path.read_bytes()
    texts = (raw.decode('utf-16-le', errors='ignore'),
             raw[1:].decode('utf-16-le', errors='ignore'))
    found, seen = [], set()
    for needle, canonical in MODELS:
        if canonical in seen:
            continue
        if any(needle in text for text in texts):
            seen.add(canonical)
            found.append(canonical)
    return found


def parse_name(stem):
    """(donor, date, era, fraction) from an acquisition filename stem."""
    m = RE_2014.match(stem)
    if m:
        return m.group(1), m.group(2), '2014', 'none'
    m = RE_2013.match(stem)
    if m:
        return m.group(1), m.group(2), '2013', m.group(3) or 'none'
    return None


def build():
    if not MANIFEST.exists():
        sys.exit(f"missing {MANIFEST}")
    names = [l.strip() for l in MANIFEST.read_text().splitlines() if l.strip()]
    if not HDR.is_dir():
        sys.exit(f"no headers in {HDR}\n"
                 f"retrieve them first: ./scripts/fetch_px4023.sh headers")

    rows, missing, unparsed, ambiguous = [], [], [], []
    for name in names:                     # manifest order, not directory order
        h = HDR/f'{name}.head'
        if not h.exists():
            missing.append(name)
            continue
        parsed = parse_name(name[:-4] if name.endswith('.raw') else name)
        if parsed is None:
            unparsed.append(name)
            continue
        donor, date, era, fraction = parsed
        found = models_in(h)
        if len(found) == 1:
            instrument, confidence = found[0], 'verified'
        elif not found:
            instrument, confidence = '', 'none'
            ambiguous.append(name)
        else:
            instrument, confidence = found[0], 'ambiguous'
            ambiguous.append(name)
        rows.append([name, donor, date, era, fraction, instrument,
                     confidence, EVIDENCE, ';'.join(found)])

    for label, lst in (('missing header', missing),
                       ('filename not parsed', unparsed),
                       ('instrument not uniquely identified', ambiguous)):
        if lst:
            print(f'{label}: {len(lst)}  {lst[:5]}', file=sys.stderr)
    if missing or unparsed or ambiguous:
        sys.exit('refusing to write an incomplete or unverified run map')
    return rows


def render(rows):
    """CSV text exactly as runmap.csv stores it: CRLF, no quoting."""
    import io
    buf = io.StringIO()
    w = csv.writer(buf)                    # csv default lineterminator is \r\n
    w.writerow(HEADER)
    w.writerows(rows)
    return buf.getvalue()


def main():
    rows = build()
    text = render(rows)

    if '--check' in sys.argv:
        if not OUT.exists():
            sys.exit(f'{OUT} does not exist; nothing to check against')
        current = OUT.read_text(newline='')
        if current == text:
            print(f'{OUT} reproduces byte-identically from {len(rows)} headers')
            return
        print(f'MISMATCH against {OUT}', file=sys.stderr)
        a, b = current.splitlines(), text.splitlines()
        print(f'  committed {len(a)} lines, regenerated {len(b)}', file=sys.stderr)
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                print(f'  first difference, line {i+1}:\n    committed  {x}\n'
                      f'    regenerated {y}', file=sys.stderr)
                break
        sys.exit(1)

    OUT.write_text(text, newline='')
    print(f'wrote {OUT}: {len(rows)} runs')
    by = {}
    for r in rows:
        by.setdefault((r[3], r[5], 'fractionated' if r[4] != 'none' else 'none'), 0)
        by[(r[3], r[5], 'fractionated' if r[4] != 'none' else 'none')] += 1
    for k, n in sorted(by.items()):
        print(f'  year {k[0]}  {k[1]:16s}  fractionation {k[2]:12s}  {n:3d} runs')
    print('Instrument, year and fractionation are perfectly confounded in this '
          'cohort; no run breaks the pattern. See ANALYSIS_PLAN.md.')


if __name__ == '__main__':
    main()
