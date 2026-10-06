#!/usr/bin/env python3
"""Union, redundancy and length structure across all 52 extracted units.

Produces the eligible positive count that D007 gates on and that §14's compute
budget was sized against. Until now both rested on a Heaps' law projection
fitted to five units; this replaces the projection with the measurement and
reports how far the projection was off, because an estimate that is never
checked against the outcome teaches nothing.
"""

import csv, gzip, json, collections, math
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PEP, OUT = REPO/'data'/'derived'/'peptides', REPO/'results'/'qc'


def load(p):
    op = gzip.open if p.suffix == '.gz' else open
    with op(p, 'rt', newline='', encoding='utf-8') as fh:
        return {r['sequence']: (int(r['length']), int(r['best_confidence_level']))
                for r in csv.DictReader(fh)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    units = {}
    for p in sorted(PEP.glob('*.csv*')):
        if p.name.endswith('.meta.json'):
            continue
        units[p.name.split('.')[0]] = load(p)
    print(f"units loaded: {len(units)}")

    occur = collections.Counter()
    conf = {}
    length = {}
    for u, d in units.items():
        for s, (L, c) in d.items():
            occur[s] += 1
            length[s] = L
            conf[s] = min(conf.get(s, 9), c)

    union = len(occur)
    per_unit = {u: len(d) for u, d in units.items()}
    print(f"\nUNION: {union:,} unique 8-12mers across {len(units)} units")
    print(f"  sum of per-unit counts : {sum(per_unit.values()):,}")
    print(f"  redundancy factor      : {sum(per_unit.values())/union:.2f}x")
    print(f"  per unit: min {min(per_unit.values()):,}  median "
          f"{sorted(per_unit.values())[len(per_unit)//2]:,}  max {max(per_unit.values()):,}")

    print("\nsequences by number of units observed in:")
    dist = collections.Counter(occur.values())
    cum = 0
    for k in sorted(dist):
        cum += dist[k]
        if k <= 10 or k % 10 == 0:
            print(f"  {k:>3} unit(s): {dist[k]:>9,}  ({100*dist[k]/union:5.2f}%)"
                  f"  cumulative {100*cum/union:5.1f}%")
    private = dist[1]
    print(f"\n  seen in exactly one unit : {private:,} ({100*private/union:.1f}%)")
    print(f"  seen in >1 unit          : {union-private:,} ({100*(union-private)/union:.1f}%)")

    print("\nlength distribution of the union:")
    ld = collections.Counter(length.values())
    for L in sorted(ld):
        print(f"  {L:>2}: {ld[L]:>9,}  ({100*ld[L]/union:5.2f}%)")

    cd = collections.Counter(conf.values())
    print("\nbest confidence level across the union:")
    for c in sorted(cd):
        print(f"  level {c}: {cd[c]:>9,}  ({100*cd[c]/union:5.2f}%)")

    # how did the projection do?
    ordered = sorted(units)
    acc, curve = set(), []
    for u in ordered:
        acc |= units[u].keys()
        curve.append(len(acc))
    beta5 = math.log(curve[4]/curve[0])/math.log(5)
    proj = curve[0]*52**beta5
    print(f"\nprojection check (Heaps' law fitted on the first 5 units):")
    print(f"  beta from 5 units  : {beta5:.3f}")
    print(f"  projected at 52    : {proj:,.0f}")
    print(f"  actual at 52       : {union:,}")
    print(f"  error              : {100*(proj-union)/union:+.1f}%")
    beta52 = math.log(curve[-1]/curve[0])/math.log(52)
    print(f"  beta from 52 units : {beta52:.3f}")
    print(f"  marginal novelty of the last unit: "
          f"{(curve[-1]-curve[-2])/per_unit[ordered[-1]]:.0%}")

    json.dump({'union': union, 'units': len(units), 'per_unit': per_unit,
               'sum_per_unit': sum(per_unit.values()),
               'redundancy_factor': sum(per_unit.values())/union,
               'occurrence_distribution': {str(k): v for k, v in sorted(dist.items())},
               'private_to_one_unit': private,
               'length_distribution': {str(k): v for k, v in sorted(ld.items())},
               'confidence_distribution': {str(k): v for k, v in sorted(cd.items())},
               'accumulation_curve': curve,
               'heaps_beta_5units': beta5, 'heaps_projection_at_52': proj,
               'heaps_beta_52units': beta52,
               'projection_error_pct': 100*(proj-union)/union},
              open(REPO/'results'/'qc'/'union_stats.json', 'w'), indent=1)
    print(f"\nwrote results/qc/union_stats.json")


if __name__ == '__main__':
    main()
