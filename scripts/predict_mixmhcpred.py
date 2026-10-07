#!/usr/bin/env python3
"""Score the frozen test partition with MixMHCpred 3.0 (§18 fourth arm, D036).

Same protocol as the MHCflurry and NetMHCpan arms: each peptide is scored
against ITS OWN participant's recorded alleles, and the per-peptide value is the
best allele's. MixMHCpred reports `Score_bestAllele` directly, so the
best-of-own-alleles step is the tool's own rather than ours.

Allele names convert HLA-A*02:01 -> A0201.

ONE ALLELE IS DROPPED. HLA-B*27:02 is not in MixMHCpred's 144 known-ligand
alleles, and passing it to -a raises a KeyError: the pan-allele path for an
unlisted allele needs the MHC sequence and a MAFFT alignment, not just a name.
It appears in exactly one test unit, UPN27, which is therefore scored on five of
its six alleles. A missing allele can only lose the predictor a true positive,
so this understates MixMHCpred -- the same direction as the partial-typing
caveat, and recorded for the same reason.

Rows carrying an ambiguity code are skipped, as for the other arms, so all
systems score identical rows. Raw output is retained per unit (D035's lesson:
re-parsing is free, re-scoring is not).
"""

import argparse, csv, gzip, subprocess, sys, tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DER, OUT = REPO/'data'/'derived', REPO/'results'/'predictors'
AA = set('ACDEFGHIKLMNPQRSTVWY')


def conv(a):
    return a.replace('HLA-', '').replace('*', '').replace(':', '')


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
    exe, root, pybin, unit, peptides, alleles, supported = args
    use = [conv(a) for a in alleles if conv(a) in supported]
    dropped = [a for a in alleles if conv(a) not in supported]
    with tempfile.TemporaryDirectory() as td:
        pep, out = Path(td)/'in.pep', Path(td)/'out.txt'
        pep.write_text('\n'.join(peptides) + '\n')
        env = {'PATH': f"{pybin}:/usr/bin:/bin", 'HOME': td}
        p = subprocess.run([exe, '-i', str(pep), '-o', str(out),
                            '-a', ','.join(use)],
                           capture_output=True, text=True, cwd=root, env=env)
        if not out.exists():
            return unit, None, dropped, (p.stderr or p.stdout)[-600:]
        raw = OUT/'mixmhcpred_raw'
        raw.mkdir(parents=True, exist_ok=True)
        text = out.read_text()
        with gzip.open(raw/f'{unit}.out.gz', 'wt') as fh:
            fh.write(text)
        best = {}
        hdr = None
        for line in text.splitlines():
            if line.startswith('#') or not line.strip():
                continue
            if hdr is None:
                hdr = line.split('\t')
                ip, isc, ib = (hdr.index('Peptide'), hdr.index('Score_bestAllele'),
                               hdr.index('BestAllele'))
                ir = hdr.index('%Rank_bestAllele')
                continue
            f = line.split('\t')
            if len(f) <= max(ip, isc, ib, ir):
                continue
            try:
                best[f[ip]] = (float(f[isc]), float(f[ir]), f[ib])
            except ValueError:
                continue
        return unit, best, dropped, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True, help='MixMHCpred checkout')
    ap.add_argument('--python-bin', required=True, help='dir holding the venv python')
    ap.add_argument('--jobs', type=int, default=2)
    a = ap.parse_args()
    root = Path(a.repo)
    supported = {l.split()[0] for l in (root/'lib'/'alleles_list.txt').open()
                 if l.strip() and not l.startswith('Allele')}
    rows, geno = load()
    units = sorted(rows)
    print(f"{sum(len(v) for v in rows.values()):,} rows over {len(units)} units; "
          f"{a.jobs} jobs; {len(supported):,} supported alleles", flush=True)

    work = [(str(root/'MixMHCpred'), str(root), a.python_bin, u,
             [s for s, _ in rows[u]], geno[u], supported) for u in units]
    res, drops = {}, {}
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for unit, best, dropped, err in ex.map(score_unit, work):
            if err:
                sys.exit(f"{unit} FAILED: {err}")
            res[unit], drops[unit] = best, dropped
            want = len({s for s, _ in rows[unit]})
            flag = '' if len(best) == want else f'   <-- EXPECTED {want:,}'
            d = f"   dropped allele(s): {dropped}" if dropped else ''
            print(f"  {unit}: {len(best):,} peptides scored{flag}{d}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT/'mixmhcpred_3_0_test_scores.csv'
    n, miss = 0, 0
    with out.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['unit_id', 'sequence', 'label', 'score_best', 'rank_best',
                    'best_allele', 'alleles_dropped'])
        for u in units:
            dd = ';'.join(drops[u])
            for s, l in rows[u]:
                b = res[u].get(s)
                if b is None:
                    miss += 1
                    continue
                w.writerow([u, s, l, b[0], b[1], b[2], dd]); n += 1
    print(f"\nwrote {out}  ({n:,} rows"
          + (f"; {miss} peptides absent from the output)" if miss else ")"))


if __name__ == '__main__':
    main()
