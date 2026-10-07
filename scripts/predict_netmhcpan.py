#!/usr/bin/env python3
"""Score the frozen test partition with NetMHCpan 4.1 (§18 third arm, D035).

Same protocol as `predict_mhcflurry.py`: each peptide is scored against ITS OWN
participant's recorded alleles, and the per-peptide value is the best allele's,
because the quantity is "would this peptide be presented by this donor".

NetMHCpan reports `Score_EL`, the eluted-ligand likelihood, which is the
quantity comparable to MHCflurry's presentation score; `%Rank_EL` is kept too.
Best allele = highest Score_EL, equivalently lowest %Rank_EL.

Rows whose sequence carries an ambiguity code (X, B, Z) are skipped, exactly as
for MHCflurry, so all three systems score identical rows.

Runs one unit per process, --jobs at a time: NetMHCpan is single-threaded and
the container has four cores.
"""

import argparse, csv, re, subprocess, sys, tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER, OUT = REPO/'data'/'derived', REPO/'results'/'predictors'
AA = set('ACDEFGHIKLMNPQRSTVWY')
ROW = re.compile(r'^\s*\d+\s+(\S+)\s+(\S+)\s+.*?\s+(\S+)\s+PEPLIST\s+([\d.eE+-]+)\s+([\d.eE+-]+)')


def load():
    split = {r['unit_id']: r for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    geno = {r['unit_id']: [a for a in r['hla_genotype'].split(';') if a]
            for r in csv.DictReader((DER/'UNIT_GENOTYPE.csv').open(newline=''))}
    rows = defaultdict(list)
    for fn, lab in (('POSITIVES.csv', 1), ('NEGATIVES.csv', 0)):
        for r in csv.DictReader((DER/fn).open(newline='')):
            if split[r['unit_id']]['primary_partition'] == 'test' \
                    and not (set(r['sequence']) - AA):
                rows[r['unit_id']].append((r['sequence'], lab))
    return rows, geno


def score_unit(args):
    """One unit, one NetMHCpan invocation per unit over all its alleles."""
    exe, unit, peptides, alleles = args
    # NetMHCpan wants HLA-A02:01, the SDRF gives HLA-A*02:01
    al = ','.join(a.replace('*', '') for a in alleles)
    with tempfile.TemporaryDirectory() as td:
        pep = Path(td)/'in.pep'
        pep.write_text('\n'.join(peptides) + '\n')
        p = subprocess.run([exe, '-p', str(pep), '-a', al],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return unit, None, p.stderr[-500:]
        best = {}
        for line in p.stdout.splitlines():
            m = ROW.match(line)
            if not m:
                continue
            _mhc, _core, icore, el, rank = m.groups()
            el, rank = float(el), float(rank)
            cur = best.get(icore)
            if cur is None or el > cur[0]:
                best[icore] = (el, rank, _mhc)
        return unit, best, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True, help='path to the netMHCpan wrapper')
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()

    rows, geno = load()
    units = sorted(rows)
    total = sum(len(v) for v in rows.values())
    print(f"{total:,} rows over {len(units)} units; {a.jobs} parallel jobs", flush=True)

    work = [(a.exe, u, [s for s, _ in rows[u]], geno[u]) for u in units]
    results = {}
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for unit, best, err in ex.map(score_unit, work):
            if err:
                sys.exit(f"{unit} FAILED: {err}")
            results[unit] = best
            print(f"  {unit}: {len(best):,} peptides scored", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT/'netmhcpan_4_1_test_scores.csv'
    n, miss = 0, 0
    with out.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['unit_id', 'sequence', 'label', 'score_el', 'rank_el', 'best_allele'])
        for u in units:
            for s, l in rows[u]:
                b = results[u].get(s)
                if b is None:
                    miss += 1
                    continue
                w.writerow([u, s, l, b[0], b[1], b[2]])
                n += 1
    print(f"\nwrote {out}  ({n:,} rows"
          + (f"; {miss} peptides absent from the output)" if miss else ")"))
    if miss:
        print("  NOTE: absent peptides are reported, not silently dropped.")


if __name__ == '__main__':
    main()
