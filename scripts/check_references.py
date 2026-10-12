#!/usr/bin/env python3
"""Gate: every file a shipped document points at must itself be shipped.

WHY THIS EXISTS. The published repository cited nine documents it did not ship.
A reader following `README.md` was told to consult `REPORT.md` for the study's
limits -- the one file stating what the numbers may not support -- and it was
not there. That is worse than a broken link: it is an instruction to rely on
evidence the repository withholds.

WHAT "SHIPPED" MEANS. Tracked by git. A file present in the working tree but
untracked is NOT shipped: it is on the author's disk and in nobody else's
clone. That distinction is the whole point of this check, so it is `git
ls-files` that defines the universe here, never `os.path.exists`.

WHAT IT SCANS. Every tracked .md, .cff and .ipynb. From each it extracts
Markdown links, HTML src/href attributes, and backticked repository paths,
resolves them relative to the citing file, and asserts each resolves to a
tracked file. URLs, mail addresses, pure anchors and prose in backticks are
not references and are skipped.

  python3 scripts/check_references.py             # gate: exit 1 on any dangle
  python3 scripts/check_references.py --selftest  # prove the gate can fail
"""

import json, posixpath, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A backticked token counts as a path only if it looks like one: a known
# extension, or a slash with a known directory root. Without this, prose like
# `--mode selftest` and `Score_EL` would be reported as missing files.
EXT = r'(?:md|cff|py|sh|ipynb|json|jsonl|csv|tsv|svg|txt|yml|yaml|pt|gz)'
RE_BACKTICK = re.compile(r'`([A-Za-z0-9_./-]+\.' + EXT + r')`')
RE_MDLINK = re.compile(r'\[[^\]]*\]\(\s*<?([^)\s>]+)>?\s*(?:"[^"]*")?\s*\)')
RE_HTMLATTR = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']')
SKIP = re.compile(r'^(?:https?:|mailto:|ftp:|#|data:)', re.I)


# ---------------------------------------------------------------------------
# Declared absences
# ---------------------------------------------------------------------------
# A reference to something deliberately not shipped is not a defect, but it is
# not nothing either: it must be DECLARED, with a reason, not silently passed.
# The gate prints these every run so they stay visible and so an entry that
# stops being true gets noticed. Anything NOT in this map still fails the gate.
#
# Adding an entry here is a decision. Record it in DECISION_LOG.md.
_PX4023_UNITS = ('derived peptide sequences from PXD004023, withheld pending the '
                 'redistribution position for that deposit (D054 section 4). It '
                 'exists locally and is rebuilt by scripts/extract_px4023.py; '
                 'the retrieval is scripts/fetch_px4023.sh mzid')

DECLARED_ABSENT = {
    # Withheld on purpose
    # Referenced both bare and by full path, so both forms are declared: the
    # gate matches the literal reference text or the resolved path, not the
    # basename of a declared key.
    'units.json': _PX4023_UNITS,
    'data/external/PXD004023/units.json': _PX4023_UNITS,
    'data/external/PXD004023/mzid':
        'identification containers, 1.1 GB, retrieved on demand and not '
        'archived here (D054). Manifest and acceptance rule are committed',
    'data/external/PXD004023/hdr':
        'acquisition-file headers, 161 MB, retrieved on demand and not archived '
        "here (D054). Their SHA-256 are in the same directory's "
        'header_checksums.txt',
    'HANDOVER.md':
        'withheld under D039: cloud spend and a credential-scope instruction, '
        'no scientific content',
    'REPORT.md':
        "withheld under D041 at the owner's instruction, pending submission. "
        'LIMITATIONS.md carries the limitations ledger separately, and every '
        'number the report states is in README.md and under results/',
    'PROJECT_PROMPT.md':
        "withheld under D041 at the owner's instruction: the internal brief "
        'the project was run from. PREREGISTRATION.md and METHODOLOGY.md are '
        'the public record of what was specified and what was done',
    'PXD024871_CNN_Experiment_Proposal.md':
        'withheld under D037: internal, unpreregistered; the STUB records its '
        'title, size and SHA-256',
    'data/derived/TEST_PREDICTOR_OVERLAP_2_0_0.csv':
        'untracked under D037: byte-identical duplicate of '
        'TEST_PREDICTOR_OVERLAP_MHCflurry_2_0_0.csv',

    # Third-party material that is not ours to redistribute
    'NetMHCpan_train.tar.gz':
        "NetMHCpan 4.2 training data: DTU's, not redistributable (D037)",
    'netMHCpan-4.1_license.txt':
        'the DTU licence text, which ships inside their package; quoted in '
        'THIRD_PARTY_NOTICES.md, not copied here',

    # Planned in the specification, never produced. Annotated in place in
    # METHODOLOGY.md and SECTIONS.md rather than deleted: the gap between a
    # plan and what was built is evidence about the project, not clutter.
    'CONTAINER_RUN_MAP.csv':  "planned; M5's join path failed (QC_G3_pilot.md)",
    'PEPTIDE_OBSERVATIONS.parquet':
        'planned; data/derived/peptides/ serves this role',
    'TRAIN.csv':       'planned; build_split.py writes SPLIT.csv instead',
    'VALIDATION.csv':  'planned; build_split.py writes SPLIT.csv instead',
    'TEST.csv':        'planned; build_split.py writes SPLIT.csv instead',
    'CNN_PREREGISTRATION.md':
        'planned; written directly as PREREGISTRATION.md, not emitted',
    'cnn_config.json':
        'planned; the chosen configuration is results/model/selection.json and '
        'endpoint.json["config"], the grid is cv_results.json',
    'training_log.csv':
        'planned; per-run records live in results/model/*.json and RUN_LOG.md',

    # Intermediates and prose notation
    'multi_allele.PARTIAL.json': 'in-flight run file, not retained',
    'transfer.PARTIAL.json':     'in-flight run file, not retained',
    '.meta.json':                'a filename suffix in prose, not a path',
    'data/raw/S1/files_v3_page0..5.json':
        'a range written in prose; the six files are shipped individually',
}


def tracked():
    out = subprocess.run(['git', '-C', str(REPO), 'ls-files'],
                         capture_output=True, text=True).stdout
    return {l for l in out.splitlines() if l}


def text_of(path):
    """Markdown and CFF read as-is; a notebook reads as its concatenated cells."""
    raw = (REPO / path).read_text(encoding='utf-8', errors='replace')
    if path.endswith('.ipynb'):
        try:
            nb = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        out = []
        for cell in nb.get('cells', []):
            src = cell.get('source', '')
            out.append(''.join(src) if isinstance(src, list) else str(src))
        return '\n'.join(out)
    return raw


def refs_in(path, body):
    """Candidate references in one file, as (raw, kind, resolved-candidates).

    Two kinds, deliberately resolved differently, because conflating them is
    what made the first version of this gate report 120 findings of which most
    were noise:

      LINK  -- a Markdown link or HTML src/href. Navigable: GitHub resolves it
               relative to the citing file. A link that does not resolve is
               broken for a reader who clicks it.
      NAME  -- a backticked token in prose. A MENTION, not a link. Written
               repo-relative when it has a slash (`results/qc/QC_G10.md`) and
               as a bare basename otherwise (`REPORT.md`, `seeds.py`). A bare
               basename is satisfied by a tracked file of that name ANYWHERE:
               `QC_G1.md` means results/qc/QC_G1.md and is not a dangle.
    """
    base = Path(path).parent.as_posix()
    out = set()

    def rel_to_citing(raw):
        return posixpath.normpath(posixpath.join(base, raw)) if base != '.' \
            else posixpath.normpath(raw)

    for rx in (RE_MDLINK, RE_HTMLATTR):
        for m in rx.finditer(body):
            raw = m.group(1).strip().split('#', 1)[0].strip()
            if not raw or SKIP.match(raw) or '...' in raw:
                continue
            r = rel_to_citing(raw.rstrip('/'))
            if r.startswith('..'):
                continue                       # escapes the repository
            out.add((raw, 'LINK', (r,)))

    for m in RE_BACKTICK.finditer(body):
        raw = m.group(1).strip()
        if '...' in raw or SKIP.match(raw):
            continue                           # `...STUB.md` is an abbreviation
        if '/' in raw:
            cands = (posixpath.normpath(raw), rel_to_citing(raw))
            out.add((raw, 'NAME', tuple(c for c in cands if not c.startswith('..'))))
        else:
            out.add((raw, 'NAME', (raw,)))     # matched by basename below
    return out


def resolves(kind, cands, ship, dirs, basenames, suffixes):
    for c in cands:
        if c in ship or c in dirs:
            return True
    if kind != 'NAME':
        return False
    tok = cands[0]
    if '/' not in tok:
        return tok in basenames                # `REPORT.md` -> any tracked REPORT.md
    # Prose often writes a path fragment relative to a directory under
    # discussion: `model/endpoint.json` inside a passage about results/. A
    # fragment that suffixes a tracked path on a component boundary is a real
    # reference, and treating it as a dangle was this gate's second round of
    # false positives.
    return tok in suffixes


def audit(ship, declared_absent=None):
    """Return {citing file: [(raw, kind, first-candidate), ...]} for dangles.

    `declared_absent` defaults to the module-level map. The selftest passes an
    empty one: its fixture cites names that are real entries in that map, and a
    gate whose selftest silently stops exercising a case the moment a document
    is withheld is a gate that tests less than it appears to (D041).
    """
    DECLARED_ABSENT = (declared_absent if declared_absent is not None
                       else globals()['DECLARED_ABSENT'])
    dirs = {d for f in ship for d in _parents(f)}
    basenames = {f.rsplit('/', 1)[-1] for f in ship}
    suffixes = {'/'.join(f.split('/')[i:]) for f in ship
                for i in range(1, len(f.split('/')))}
    bad, declared = {}, {}
    for f in sorted(ship):
        if not f.endswith(('.md', '.cff', '.ipynb')):
            continue
        for raw, kind, cands in sorted(refs_in(f, text_of(f))):
            if not cands:
                continue
            if resolves(kind, cands, ship, dirs, basenames, suffixes):
                continue
            if raw in DECLARED_ABSENT or cands[0] in DECLARED_ABSENT:
                declared.setdefault(raw if raw in DECLARED_ABSENT else cands[0],
                                    set()).add(f)
                continue
            bad.setdefault(f, []).append((raw, kind, cands[0]))
    return bad, declared


def _parents(f):
    parts = f.split('/')[:-1]
    return ['/'.join(parts[:i + 1]) for i in range(len(parts))]


def selftest():
    """A gate only ever observed to pass is untested. Make it fail on purpose."""
    import tempfile, os
    ok = True
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / 'docs').mkdir()
        (d / 'real.md').write_text('see [here](docs/present.md) and `shipped.py`\n')
        (d / 'docs' / 'present.md').write_text('up: [x](../real.md)\n')
        (d / 'shipped.py').write_text('')
        (d / 'bad.md').write_text(
            'read [the report](REPORT.md), also `METHODOLOGY.md`\n'
            'and <img src="results/fig.svg">\n')
        global REPO
        keep = REPO
        try:
            REPO = d
            ship = {'real.md', 'docs/present.md', 'shipped.py', 'bad.md'}

            clean, _ = audit(ship - {'bad.md'}, declared_absent={})
            ok &= _assert(not clean, 'a consistent tree reports nothing', clean)

            dirty, _ = audit(ship, declared_absent={})
            got = {p for v in dirty.values() for _, _, p in v}
            ok &= _assert('bad.md' in dirty, 'the dangling file is named')
            ok &= _assert(got == {'REPORT.md', 'METHODOLOGY.md', 'results/fig.svg'},
                          'all three dangling forms are caught '
                          '(md link, backtick, html src)', got)
            ok &= _assert('real.md' not in dirty,
                          'resolving references are not reported')
        finally:
            REPO = keep
    print('\nSELFTEST PASSED' if ok else '\nSELFTEST FAILED')
    return 0 if ok else 1


def _assert(cond, label, detail=''):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f'  -> {detail}' if detail and not cond else ''))
    return bool(cond)


def main():
    if '--selftest' in sys.argv:
        return selftest()
    ship = tracked()
    bad, declared = audit(ship)
    scanned = sum(1 for f in ship if f.endswith(('.md', '.cff', '.ipynb')))
    if declared:
        print(f"Declared absent ({len(declared)}), cited but deliberately not "
              f"shipped:\n")
        for tgt in sorted(declared):
            print(f"  {tgt}\n      {DECLARED_ABSENT[tgt]}")
            print(f"      cited by: {', '.join(sorted(declared[tgt]))}")
        print()
    if not bad:
        print(f"PASS: {scanned} shipped documents scanned; every file "
              f"reference either resolves to a tracked file or is declared "
              f"absent with a reason.")
        return 0
    n = sum(len(v) for v in bad.values())
    print(f"FAIL: {n} dangling reference(s) in {len(bad)} of {scanned} "
          f"shipped documents.\n")
    for f, items in bad.items():
        print(f"  {f}")
        for raw, kind, p in items:
            exists = (REPO / p).exists()
            why = 'untracked: on disk, not shipped' if exists else 'does not exist'
            print(f"      [{kind}] {raw:<42} [{why}]")
    print("\nEvery reference in a shipped document must resolve to a shipped "
          "file.\nEither ship the target, or rewrite the reference.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
