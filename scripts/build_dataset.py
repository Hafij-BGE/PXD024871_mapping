#!/usr/bin/env python3
"""Build and freeze the analysis dataset (G4).

Applies the preregistered decisions exactly:
  D024  10,000 positives per unit, stratified by length, seed 20261006
  D002  negatives are set C -- length-matched peptides from proteins that
        yielded at least one observed peptide, excluding everything observed
  D002  class ratio 1:1

Negatives are drawn by reservoir sampling over a streamed enumeration of the
proteome rather than by materialising every candidate: the full 8-12mer space of
20,652 proteins is tens of millions of strings, and holding it would cost
gigabytes to then discard almost all of it. Reservoir sampling gives the same
uniform draw in bounded memory.

Freezing writes FREEZE.json: counts, checksums, parameters and the commit the
build ran from. Nothing downstream may read a dataset whose checksum does not
match that record.
"""

import csv, gzip, hashlib, json, random, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PEP = REPO/'data'/'derived'/'peptides'
FASTA = REPO/'data'/'raw'/'S5'/'UP000005640_9606.fasta.gz'
OUT = REPO/'data'/'derived'
AA = set('ACDEFGHIKLMNPQRSTVWY')
SEED = 20261006
CAP = 10_000
RATIO = 1
LO, HI = 8, 12


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    rng = random.Random(SEED)

    # ---- positives, per unit, stratified by length -------------------------
    units, observed = {}, set()
    for p in sorted(PEP.glob('*.csv.gz')):
        u = p.name.split('.')[0]
        by_len = defaultdict(list)
        with gzip.open(p, 'rt', newline='') as fh:
            for r in csv.DictReader(fh):
                s = r['sequence']
                observed.add(s)
                by_len[int(r['length'])].append(s)
        units[u] = by_len
    print(f"units {len(units)}  observed universe {len(observed):,}")

    positives = {}
    for u, by_len in sorted(units.items()):
        total = sum(len(v) for v in by_len.values())
        take = min(CAP, total)
        # proportional allocation, largest-remainder so the quota is exact
        exact = {L: take * len(v) / total for L, v in by_len.items()}
        alloc = {L: int(e) for L, e in exact.items()}
        short = take - sum(alloc.values())
        for L in sorted(exact, key=lambda L: -(exact[L] - alloc[L]))[:short]:
            alloc[L] += 1
        picked = []
        for L, n in alloc.items():
            picked += rng.sample(by_len[L], n) if n < len(by_len[L]) else list(by_len[L])
        positives[u] = picked
    npos = sum(len(v) for v in positives.values())
    want_len = Counter(len(s) for v in positives.values() for s in v)
    print(f"positives {npos:,} over {len(positives)} units "
          f"(per unit {min(map(len, positives.values()))}-{max(map(len, positives.values()))})")

    # ---- expressed proteins, then reservoir-sample unobserved k-mers -------
    seqs, name, cur = {}, None, []
    with gzip.open(FASTA, 'rt') as fh:
        for line in fh:
            if line.startswith('>'):
                if name: seqs[name] = ''.join(cur)
                name, cur = line[1:].split()[0], []
            else:
                cur.append(line.strip())
    if name: seqs[name] = ''.join(cur)

    expressed = []
    for n, s in seqs.items():
        hit = False
        for L in range(LO, HI + 1):
            for i in range(len(s) - L + 1):
                if s[i:i+L] in observed:
                    hit = True; break
            if hit: break
        if hit: expressed.append(n)
    print(f"proteome {len(seqs):,}; proteins yielding >=1 observed peptide: "
          f"{len(expressed):,} ({100*len(expressed)/len(seqs):.1f}%)")

    need = {L: want_len[L] * RATIO for L in want_len}
    # Oversample: the same k-mer occurs in several proteins, so the reservoir
    # yields duplicates that dedup removes. Without headroom the quota comes up
    # short -- the first build missed by 1,911.
    draw = {L: int(n * 1.15) + 1000 for L, n in need.items()}
    res = {L: [] for L in need}
    seen = {L: 0 for L in need}
    for n in expressed:
        s = seqs[n]
        for L in need:
            for i in range(len(s) - L + 1):
                c = s[i:i+L]
                if c in observed or not set(c) <= AA:
                    continue
                seen[L] += 1
                if len(res[L]) < draw[L]:
                    res[L].append(c)
                else:
                    j = rng.randrange(seen[L])
                    if j < draw[L]:
                        res[L][j] = c
    # global uniqueness: a sequence may occur in several proteins
    for L in res:
        uniq = list(dict.fromkeys(res[L]))
        if len(uniq) < need[L]:
            sys.exit(f"ABORT: length {L} yielded {len(uniq):,} unique negatives, "
                     f"{need[L]:,} required; raise the oversampling factor")
        rng.shuffle(uniq)
        res[L] = uniq[:need[L]]
    print("negative pool per length: " + "  ".join(f"{L}:{len(res[L]):,}" for L in sorted(res)))

    # ---- assign negatives to units, matching each unit's length profile ----
    cursor = {L: 0 for L in res}
    negatives = {}
    for u, picked in sorted(positives.items()):
        prof = Counter(len(s) for s in picked)
        out = []
        for L, n in prof.items():
            out += res[L][cursor[L]:cursor[L]+n*RATIO]
            cursor[L] += n * RATIO
        negatives[u] = out
    nneg = sum(len(v) for v in negatives.values())
    print(f"negatives {nneg:,}")

    # ---- integrity checks before anything is written ----------------------
    allpos = {s for v in positives.values() for s in v}
    allneg = {s for v in negatives.values() for s in v}
    pos_len = Counter(len(s) for v in positives.values() for s in v)
    neg_len = Counter(len(s) for v in negatives.values() for s in v)
    shared = npos - len(allpos)
    checks = [
        ("positives are observed", allpos <= observed),
        ("no negative is observed", not (allneg & observed)),
        ("positive/negative disjoint", not (allpos & allneg)),
        ("negatives globally unique", len(allneg) == nneg),
        ("class ratio 1:%d" % RATIO, nneg == npos * RATIO),
        ("length profiles match", all(neg_len[L] == pos_len[L]*RATIO for L in pos_len)),
    ]
    # A sequence may legitimately be positive in more than one unit -- run-006
    # measured 20.1% of the universe in >1 unit, and that is precisely what the
    # split rule (D003) has to handle. It is reported, never silently removed:
    # deduplicating here would hide the leakage exposure rather than address it.
    print(f"\ncross-unit positive duplication: {shared:,} of {npos:,} rows "
          f"({100*shared/npos:.2f}%) are sequences also positive in another unit")
    print(f"  distinct positive sequences: {len(allpos):,}")
    print("\nintegrity:")
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not all(ok for _, ok in checks):
        sys.exit("ABORT: integrity check failed; nothing written")

    # ---- write -------------------------------------------------------------
    for fn, data, label in (('POSITIVES.csv', positives, 1), ('NEGATIVES.csv', negatives, 0)):
        with (OUT/fn).open('w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['sequence', 'length', 'unit_id', 'label'])
            for u, seqs_ in sorted(data.items()):
                for s in sorted(seqs_):
                    w.writerow([s, len(s), u, label])
        print(f"wrote {fn}")

    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    freeze = {
        'frozen_utc': __import__('datetime').datetime.now(
            __import__('datetime').timezone.utc).isoformat(),
        'commit': commit,
        'decisions_applied': {
            'D024': f'cap {CAP} per unit, length-stratified, seed {SEED}',
            'D002': f'negatives = set C (expressed-protein, unobserved); ratio 1:{RATIO}',
            'D004': 'no confidence filter: 99.29% of the union is level 1, so it is a no-op',
            'D011': 'unit = participant',
        },
        'seed': SEED, 'cap_per_unit': CAP, 'ratio': RATIO, 'length_window': [LO, HI],
        'n_units': len(positives), 'n_positives': npos, 'n_negatives': nneg,
        'distinct_positive_sequences': len(allpos),
        'cross_unit_duplicate_rows': shared,
        'cross_unit_duplicate_pct': round(100*shared/npos, 3),
        'note_on_duplicates': 'Sequences positive in more than one unit are '
                              'retained, not deduplicated. They are the exposure '
                              'D003 governs and the split rule must handle them.',
        'observed_universe': len(observed),
        'expressed_proteins': len(expressed), 'proteome_sequences': len(seqs),
        'length_distribution': {str(k): v for k, v in sorted(want_len.items())},
        'composition_floor_ap': 0.597,
        'composition_floor_source': 'results/qc/negative_diagnostic.json (set C)',
        'files': {fn: {'sha256': sha256(OUT/fn), 'bytes': (OUT/fn).stat().st_size}
                  for fn in ('POSITIVES.csv', 'NEGATIVES.csv')},
        'integrity_checks': {label: ok for label, ok in checks},
    }
    (OUT/'FREEZE.json').write_text(json.dumps(freeze, indent=1))
    print(f"\nFROZEN at commit {commit[:12]}")
    for fn, m in freeze['files'].items():
        print(f"  {fn:<16} {m['bytes']:>12,} bytes  sha256 {m['sha256'][:16]}")


if __name__ == '__main__':
    main()
