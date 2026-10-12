#!/usr/bin/env python3
"""Extract accepted peptide sequences from PXD004023, aggregated donor x workflow.

Secondary analysis, external cohort. Promoted into the repository by D054; it
was previously run outside the tree, which is why the numbers D046 reports had
no tracked artifact behind them.

Input:  data/external/PXD004023/mzid/*.mzid, retrieved by
        scripts/fetch_px4023.sh mzid. NOT committed -- 1.1 GB.
Output: data/external/PXD004023/units.json   peptide sets per donor x workflow
        data/external/PXD004023/perfile.json per-container accepted counts

**units.json is not committed at present.** It holds derived peptide sequences
from a third-party deposit, and the redistribution position for PXD004023 has
not been established (D054 section 4). perfile.json carries only counts, which
is why it ships. Until units.json is either committed or declared, this script
must be run locally before scripts/replicate_px4023.py will work.

Acceptance rule, as deposited: a SpectrumIdentificationItem with
passThreshold="true", whose peptide_ref is not exclusively decoy evidence, and
whose sequence uses only the 20 standard residues. No re-searching, no
re-scoring, no FDR recomputation -- identifications are taken as the depositors
made them.

The 10 MB size floor is not arbitrary. One container in the original run matched
its declared byte count exactly and still contained
<Error><Code>ConnectionClosedException</Code>; only XML parsing caught it, and
the figures from that run were discarded (D047). A short container is refused
here rather than parsed.
"""

import glob, json, os, re, sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXT = REPO/'data'/'external'/'PXD004023'
MZID = EXT/'mzid'
NS = '{http://psidev.info/psi/pi/mzIdentML/1.1}'
AA = set('ACDEFGHIKLMNPQRSTVWY')
MIN_BYTES = 10_000_000

ELITE, QE = '2013_Elite_SCX', '2014_QEplus_unfrac'


def accepted(path):
    """Accepted, non-decoy, standard-residue peptide sequences in one container."""
    pep, ev_decoy, passed = {}, {}, set()
    for _, el in ET.iterparse(path, events=('end',)):
        t = el.tag
        if t == NS+'Peptide':
            s = el.find(NS+'PeptideSequence')
            if s is not None and s.text:
                pep[el.get('id')] = s.text.strip()
            el.clear()
        elif t == NS+'PeptideEvidence':
            ev_decoy[el.get('id')] = (el.get('isDecoy', 'false') == 'true',
                                      el.get('peptide_ref'))
            el.clear()
        elif t == NS+'SpectrumIdentificationItem':
            if el.get('passThreshold') == 'true':
                pr = el.get('peptide_ref')
                if pr:
                    passed.add(pr)
            el.clear()
    decoy_refs = {pr for d, pr in ev_decoy.values() if d}
    nondecoy_refs = {pr for d, pr in ev_decoy.values() if not d}
    out = set()
    for pr in passed:
        # A peptide_ref carrying both decoy and target evidence is kept; one
        # carrying decoy evidence alone is not.
        if pr in decoy_refs and pr not in nondecoy_refs:
            continue
        s = pep.get(pr)
        if s and set(s) <= AA:
            out.add(s)
    return out


def main():
    paths = sorted(glob.glob(str(MZID/'*.mzid')))
    if not paths:
        sys.exit(f"no containers in {MZID}\n"
                 f"retrieve them first: ./scripts/fetch_px4023.sh mzid")

    units, perfile, skipped = defaultdict(set), {}, []
    for p in paths:
        fn = os.path.basename(p)[:-5]
        if os.path.getsize(p) < MIN_BYTES:
            skipped.append(fn)
            print(f'REFUSED, under {MIN_BYTES/1e6:.0f} MB: {fn}', file=sys.stderr)
            continue
        m = re.match(r'pat_(.+?)_(\d{8})', fn) or re.match(r'(.+?)_rep\d+_(\d{6})', fn)
        if not m:
            sys.exit(f"filename does not match either naming scheme: {fn}")
        donor = m.group(1)
        era = QE if fn.startswith('pat_') else ELITE
        s = accepted(p)          # an unparseable container raises; that is intended
        perfile[fn] = dict(donor=donor, era=era, n=len(s))
        units[(donor, era)] |= s
        print(f'{fn:40s} {donor:5s} {era:22s} {len(s):7d}', flush=True)

    EXT.mkdir(parents=True, exist_ok=True)
    json.dump({f'{d}|{e}': sorted(v) for (d, e), v in units.items()},
              (EXT/'units.json').open('w'))
    json.dump(perfile, (EXT/'perfile.json').open('w'), indent=1)

    print(f'\ncontainers parsed {len(perfile)}   refused {len(skipped)}')
    if skipped:
        print('  refused:', ', '.join(skipped))
    print(f'donor x workflow units: {len(units)}')
    for (d, e), v in sorted(units.items()):
        print(f'  {d:5s} {e:22s} {len(v):7d} unique')
    both = sorted({d for d, _ in units} &
                  {d for d, e in units if e == QE} &
                  {d for d, e in units if e == ELITE})
    print(f'donors with both workflows: {len(both)}  {both}')
    print(f'\nwrote {EXT/"units.json"} and {EXT/"perfile.json"}')


if __name__ == '__main__':
    main()
