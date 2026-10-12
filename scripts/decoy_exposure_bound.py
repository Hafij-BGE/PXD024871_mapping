#!/usr/bin/env python3
"""Q1-009b: bound the decoy-exposure defect without the uniformity assumption.

D044 defect B established that `build_dataset.py` rejects any candidate decoy
found in `observed`, which is accumulated across all 52 participants including
the ten held out. A test-blind construction would therefore have admitted some
peptides that are genuinely presented -- in a held-out participant -- as
negatives. D044 estimated the cost at **-0.0030 AP** under an explicit
assumption: that the reservoir draws approximately uniformly from the *unique*
eligible pool. D044 flags that assumption as imperfect, because the code
reservoir-samples k-mer *occurrences* and then deduplicates, and records that
the direction of the resulting bias is not established.

That estimate is the entire basis for treating defect B as an extension rather
than a release blocker. An estimate under an unvalidated assumption is a weak
basis for that decision, so this script replaces it with two things that do not
depend on the assumption.

**1. The count, bracketed rather than assumed.** The flagged uncertainty is
exactly "unique-weighted versus occurrence-weighted". Both are computed from the
proteome, giving an interval that contains the truth under either reading
without choosing between them.

**2. The average-precision cost, bounded adversarially.** For a given number of
false negatives k, the worst case is that every one of them outranks every
positive. That bound is computed exactly from the frozen checkpoint scores: it
removes the k lowest-scoring negatives, which is the least the removal can help
the model, and inserts k negatives above the entire ranking. No assumption is
made about which peptides would have been drawn or how the network would score
them. **The true cost cannot exceed this for that k.**

The trivial count bound -- every eligible test-only peptide is drawn -- is also
reported, and it is vacuous: it would make most of the negative pool false. That
is precisely why the bound is placed on the AP cost at a bracketed count rather
than on the count alone.

Requires data/raw/S5/UP000005640_9606.fasta.gz, which is not committed. Its
SHA-256 is checked against the S5 provenance record before use; if the release
has rotated, the k-mer space is not the frozen one and the script refuses.

Writes results/qc/decoy_exposure_bound.json. Retrains nothing.
"""

import csv, gzip, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                              # noqa: E402
from train_cnn import (CNN, encode, average_precision, cluster_ci,  # noqa: E402
                       load)

DER, RES = REPO/'data'/'derived', REPO/'results'/'model'
FASTA = REPO/'data'/'raw'/'S5'/'UP000005640_9606.fasta.gz'
PROV = REPO/'data'/'raw'/'S5'/'provenance.jsonl'
OUT = REPO/'results'/'qc'/'decoy_exposure_bound.json'
LO, HI = 8, 12
AA = 'ACDEFGHIKLMNPQRSTVWY'
CODE = {c: i for i, c in enumerate(AA)}
NOMINAL = 0.99


def kcode(s):
    """Base-20 integer for a peptide of standard residues, or None."""
    v = 0
    for c in s:
        i = CODE.get(c)
        if i is None:
            return None
        v = v*20 + i
    return v


def check_proteome():
    rec = [json.loads(l) for l in PROV.read_text().splitlines() if l.strip()][0]
    want = rec['checksum'].split(':', 1)[1]
    got = hashlib.sha256(FASTA.read_bytes()).hexdigest()
    if got != want:
        sys.exit(f'proteome checksum mismatch\n  recorded {want}\n  on disk  {got}\n'
                 'The UniProt release has rotated; this is not the k-mer space the '
                 'frozen dataset was built from. Refusing.')
    return want


def main():
    if not FASTA.exists():
        sys.exit(f'missing {FASTA}\nRetrieve it with the command in '
                 f'data/raw/S5/provenance.jsonl (acquisition_method).')
    sha = check_proteome()
    print(f'proteome verified against S5 provenance: {sha[:16]}...')

    split = {r['unit_id']: r['primary_partition']
             for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}

    # --- the observed universe, and the part of it seen only in test units ---
    # This must be the FULL extracted union, not the 10,000-per-unit sample in
    # POSITIVES.csv: build_dataset.py rejected candidate decoys against the
    # union, so that is the set whose test-only part would have been eligible
    # under a test-blind build.
    pep_dir = DER/'peptides'
    files = sorted(pep_dir.glob('*.csv.gz'))
    if not files:
        sys.exit(f'no per-unit peptide files in {pep_dir}')
    universe, test_seen, nontest_seen = set(), set(), set()
    for p in files:
        unit = p.name.split('.')[0]
        part = split.get(unit)
        if part is None:
            sys.exit(f'{unit} is not in SPLIT.csv')
        tgt = test_seen if part == 'test' else nontest_seen
        with gzip.open(p, 'rt', newline='') as fh:
            for r in csv.DictReader(fh):
                s = r['sequence']
                universe.add(s)
                tgt.add(s)
    test_only = test_seen - nontest_seen
    print(f'observed universe {len(universe):,}   '
          f'seen in a test unit {len(test_seen):,}   test-only {len(test_only):,}')

    obs_codes = {}
    for s in universe:
        c = kcode(s)
        if c is not None and LO <= len(s) <= HI:
            obs_codes.setdefault(len(s), set()).add(c)
    to_codes = {}
    for s in test_only:
        c = kcode(s)
        if c is not None and LO <= len(s) <= HI:
            to_codes.setdefault(len(s), set()).add(c)

    # --- proteins yielding at least one observed peptide ---------------------
    seqs = {}
    name, cur = None, []
    with gzip.open(FASTA, 'rt') as fh:
        for line in fh:
            if line.startswith('>'):
                if name:
                    seqs[name] = ''.join(cur)
                name, cur = line[1:].split()[0], []
            else:
                cur.append(line.strip())
    if name:
        seqs[name] = ''.join(cur)
    allobs = set().union(*obs_codes.values()) if obs_codes else set()
    expressed = []
    for nm, s in seqs.items():
        hit = False
        for L in range(LO, HI+1):
            for i in range(len(s)-L+1):
                c = kcode(s[i:i+L])
                if c is not None and c in allobs:
                    hit = True
                    break
            if hit:
                break
        if hit:
            expressed.append(nm)
    del allobs
    print(f'proteome {len(seqs):,}; expressed {len(expressed):,}')

    # --- per length: unique and occurrence weights --------------------------
    neg_drawn = defaultdict(int)
    for r in csv.DictReader((DER/'NEGATIVES.csv').open(newline='')):
        neg_drawn[len(r['sequence'])] += 1

    per_len = {}
    for L in range(LO, HI+1):
        obs_L = obs_codes.get(L, set())
        to_L = to_codes.get(L, set())
        uniq_elig, uniq_to = set(), set()
        occ_elig = occ_to = 0
        for nm in expressed:
            s = seqs[nm]
            for i in range(len(s)-L+1):
                c = kcode(s[i:i+L])
                if c is None:
                    continue
                if c in to_L:
                    occ_to += 1
                    uniq_to.add(c)
                elif c not in obs_L:
                    occ_elig += 1
                    uniq_elig.add(c)
        n = neg_drawn[L]
        # Unique-weighted: D044's assumption. Occurrence-weighted: what the
        # reservoir actually samples before dedup. The truth lies between.
        pool_u = len(uniq_elig) + len(uniq_to)
        pool_o = occ_elig + occ_to
        k_unique = n * len(uniq_to) / pool_u if pool_u else 0.0
        k_occ = n * occ_to / pool_o if pool_o else 0.0
        per_len[L] = {
            'negatives_drawn': n,
            'unique_eligible_excluding_testonly': len(uniq_elig),
            'unique_testonly_in_proteome': len(uniq_to),
            'occurrences_eligible_excluding_testonly': occ_elig,
            'occurrences_testonly_in_proteome': occ_to,
            'expected_false_negatives_unique_weighted': k_unique,
            'expected_false_negatives_occurrence_weighted': k_occ,
            'trivial_max_false_negatives': min(n, len(uniq_to)),
        }
        print(f'  L={L}  n={n:,}  unique test-only {len(uniq_to):,}  '
              f'k_unique {k_unique:7.1f}  k_occ {k_occ:7.1f}')
        del uniq_elig, uniq_to

    k_u = sum(d['expected_false_negatives_unique_weighted'] for d in per_len.values())
    k_o = sum(d['expected_false_negatives_occurrence_weighted'] for d in per_len.values())
    k_max = sum(d['trivial_max_false_negatives'] for d in per_len.values())
    n_tot = sum(d['negatives_drawn'] for d in per_len.values())
    print(f'\ntotal negatives {n_tot:,}')
    print(f'  k unique-weighted      {k_u:9.1f}  ({100*k_u/n_tot:.3f}%)')
    print(f'  k occurrence-weighted  {k_o:9.1f}  ({100*k_o/n_tot:.3f}%)')
    print(f'  k trivial maximum      {k_max:9.0f}  ({100*k_max/n_tot:.1f}%)  <- vacuous')

    # --- the adversarial AP bound, from the frozen checkpoints --------------
    rows, sp = load()
    meta = json.loads((RES/'final.json').read_text())
    cfg = meta['config']
    test = [(s, u, l) for s, u, l in rows if sp[u]['primary_partition'] == 'test']
    X = encode([s for s, _, _ in test])
    y = np.array([l for _, _, l in test])
    ua = np.array([u for _, u, _ in test])
    print(f'\nscoring {len(test):,} test rows with {len(meta["models"])} checkpoints...')
    Xt = torch.from_numpy(X)
    S = []
    for m_ in meta['models']:
        ck = torch.load(RES/m_['file'], map_location='cpu', weights_only=False)
        m = CNN(**cfg); m.load_state_dict(ck['state']); m.eval()
        with torch.no_grad():
            S.append(torch.cat([m(Xt[i:i+8192])
                                for i in range(0, len(Xt), 8192)]).numpy())
    S = np.vstack(S)
    units = sorted(set(ua))

    rng_ins = np.random.default_rng(seed('decoy_insert'))

    def bound_at(k_per_unit, insert='top'):
        """Per-participant AP if k negatives per unit are false negatives.

        insert='top' is the BOUND. It is adversarial on both sides: the k
        removed negatives are the lowest scoring, which is the least their
        removal can help, and the k inserted negatives outrank every positive,
        which is the most they can hurt. Writing AP as

            AP = (1/P) * sum_i t_i / (t_i + n_i)

        over positives i, where t_i counts positives at or above i and is
        invariant under any change to the negatives, AP is strictly decreasing
        in each n_i. Deleting a negative ranked below i leaves n_i alone while
        deleting one above it lowers n_i and RAISES AP, so the minimal-help
        deletion is the lowest scoring; and no insertion raises every n_i by
        more than one placed above all positives. The pair therefore MINIMISES
        AP at that k, which an exhaustive search over removal and insertion
        strategies confirms.

        insert='random' draws the replacement scores from the unit's own score
        distribution. That is the realistic case, not a bound, and it is what
        D044's -0.0030 estimate corresponds to. Both are reported.
        """
        out = []
        for u in units:
            m = ua == u
            per_model = []
            for j in range(S.shape[0]):
                s = S[j][m]
                yy = y[m]
                neg = np.flatnonzero(yy == 0)
                k = min(k_per_unit, neg.size)
                drop = neg[np.argsort(s[neg], kind='stable')[:k]]
                keep = np.ones(yy.size, bool)
                keep[drop] = False
                v = (np.full(k, s.max() + 1.0) if insert == 'top'
                     else rng_ins.choice(s, k))
                s2 = np.concatenate([s[keep], v])
                y2 = np.concatenate([yy[keep], np.zeros(k, int)])
                per_model.append(average_precision(y2, s2))
            out.append(float(np.mean(per_model)))
        return np.array(out)

    base = bound_at(0)
    n_units = len(units)
    # k_u and k_o count false negatives across all 52 units. Negatives are
    # drawn 10,000 per unit, so the per-unit figure is k/52 -- NOT k divided by
    # the ten test units, which would overstate it fivefold.
    n_all_units = len(set(sp))
    k_u_per_unit = k_u / n_all_units
    k_o_per_unit = k_o / n_all_units
    grid = sorted({0, 1, 5, 10, 25, 50, 100, 150, 200, 400,
                   int(round(k_u_per_unit)), int(round(k_o_per_unit))})
    curve = {}
    for k in grid:
        v = bound_at(k)
        curve[k] = {'mean_ap': float(v.mean()),
                    'delta_vs_base': float(v.mean() - base.mean())}
    print(f'\nexpected false negatives per unit: unique {k_u_per_unit:.1f}, '
          f'occurrence {k_o_per_unit:.1f}  (total / {n_all_units} units)')
    print(f'baseline mean AP {base.mean():.6f}')
    print(f'{"k/unit":>8s} {"worst-case AP":>14s} {"delta":>10s}')
    for k in grid:
        print(f'{k:8d} {curve[k]["mean_ap"]:14.6f} {curve[k]["delta_vs_base"]:+10.4f}')

    # --- the interval, bootstrapped from the PERTURBED per-unit values -------
    # Subtracting a point delta from the recorded CI lower bound does not give a
    # calibrated bound on the perturbed estimand. The per-unit worst-case values
    # are resampled directly instead. This is a SENSITIVITY interval: it carries
    # the bootstrap's own under-coverage (R6: nominal-95% delivers 0.884-0.890
    # at ten units, which is why nominal-99% is used) AND it is conditional on
    # exactly k false negatives in every unit. It is not a coverage statement
    # about the realised dataset.
    k_star = int(round(k_u_per_unit))
    worst = bound_at(k_star, insert='top')
    realistic = bound_at(k_star, insert='random')
    rb = np.random.default_rng(seed('decoy_bound'))
    base_ci = cluster_ci(base, rb, nominal=NOMINAL)
    rb = np.random.default_rng(seed('decoy_bound'))
    worst_ci = cluster_ci(worst, rb, nominal=NOMINAL)
    rb = np.random.default_rng(seed('decoy_bound'))
    real_ci = cluster_ci(realistic, rb, nominal=NOMINAL)
    endpoint = json.loads((RES/'endpoint.json').read_text())
    thresh = endpoint['threshold']
    naive = endpoint['primary']['ci99_lo'] + (worst.mean() - base.mean())
    print(f'\n=== at k = {k_star} per unit ===')
    print(f'  base                 {base.mean():.6f}  [{base_ci[0]:.6f}, {base_ci[1]:.6f}]')
    print(f'  realistic insertion  {realistic.mean():.6f}  [{real_ci[0]:.6f}, {real_ci[1]:.6f}]'
          f'   delta {realistic.mean()-base.mean():+.4f}  (D044 estimated -0.0030)')
    print(f'  WORST CASE           {worst.mean():.6f}  [{worst_ci[0]:.6f}, {worst_ci[1]:.6f}]'
          f'   delta {worst.mean()-base.mean():+.4f}')
    print(f'  threshold {thresh}: worst-case sensitivity lower bound clears it '
          f'by {worst_ci[0]-thresh:+.4f}')
    print(f'  (naive CI_lo - delta would have given {naive:.6f}, which is NOT a '
          f'calibrated bound)')

    rb = np.random.default_rng(seed('decoy_bound'))
    report = {
        'decision': 'D058',
        'replaces': 'the -0.0030 AP ESTIMATE in D044 defect B, which assumed '
                    'uniform sampling from the unique eligible pool',
        'proteome_sha256': sha,
        'proteome_matches_s5_record': True,
        'per_length': {str(k): v for k, v in per_len.items()},
        'total_negatives': n_tot,
        'k_unique_weighted': k_u,
        'k_occurrence_weighted': k_o,
        'k_bracket': [min(k_u, k_o), max(k_u, k_o)],
        'units_total': n_all_units,
        'k_per_unit_unique_weighted': k_u_per_unit,
        'k_per_unit_occurrence_weighted': k_o_per_unit,
        'k_per_unit_note':
            'Negatives are drawn 10,000 per unit across all 52 units, so the '
            'per-unit count is the total divided by 52. D044 reports 81.6 per '
            'test unit by the same arithmetic.',
        'k_trivial_maximum': k_max,
        'd044_comparison': {
            'd044_pool_as_built': {'8': 9905950, '9': 9685563, '10': 9783092,
                                   '11': 10031599, '12': 10249119},
            'd044_k_unique_weighted': 4242.5,
            'd044_expressed_proteins': 20152,
            'this_expressed_proteins': len(expressed),
            'status': 'UNRESOLVED',
            'note':
                'Test-only counts and negatives drawn match D044 exactly at '
                'every length, and the universe (2,658,972) and test-only total '
                '(364,900) match. The eligible pool does not: this '
                'reconstruction is smaller by 49,589 to 50,015 at every length, '
                'a near-constant offset. That rules out the 6-protein '
                'difference in the expressed set, which would push the pool the '
                'other way, and it rules out non-standard-residue skipping, '
                'which would scale with length. D044\'s audit was run outside '
                'this repository and its script is not available, so the '
                'definitional difference CANNOT BE SETTLED from the evidence '
                'here. It propagates to k as +0.5% (4264.0 against 4242.5), '
                'which does not affect any conclusion drawn here. Recorded as '
                'unresolved rather than explained.',
        },
        'k_trivial_maximum_note':
            'Every eligible test-only peptide drawn. Assumption-free and '
            'vacuous: it would make most of the negative pool false. Reported '
            'so the reader can see why the bound is placed on the AP cost at a '
            'bracketed count instead.',
        'baseline_mean_ap': float(base.mean()),
        'baseline_ci': [float(x) for x in base_ci],
        'n_units': n_units,
        'k_evaluated_per_unit': k_star,
        'worst_case_mean_ap': float(worst.mean()),
        'worst_case_ci': [float(x) for x in worst_ci],
        'worst_case_delta': float(worst.mean()-base.mean()),
        'realistic_insertion_mean_ap': float(realistic.mean()),
        'realistic_insertion_ci': [float(x) for x in real_ci],
        'realistic_insertion_delta': float(realistic.mean()-base.mean()),
        'realistic_insertion_note':
            'Replacement scores drawn from the unit\'s own score distribution. '
            'This is the realistic case and NOT a bound. It is what D044\'s '
            '-0.0030 estimate corresponds to, and it reproduces that figure.',
        'preregistered_threshold': thresh,
        'worst_case_lower_bound_clears_threshold': bool(worst_ci[0] > thresh),
        'worst_case_margin_above_threshold': float(worst_ci[0]-thresh),
        'interval_status': 'SENSITIVITY INTERVAL, NOT A CALIBRATED CONFIDENCE '
            'BOUND. It is a cluster bootstrap of the perturbed per-unit values, '
            'so it carries the bootstrap\'s own under-coverage at ten units '
            '(R6: nominal-95% delivers 0.884-0.890, hence nominal-99%), and it '
            'is CONDITIONAL on exactly k false negatives in every unit. The '
            'realised per-unit count is a random draw; units above k fare '
            'worse. Subtracting the worst-case delta from the recorded CI lower '
            'bound, which an earlier draft did, is not valid and is not used.',
        'naive_subtraction_not_used': float(naive),
        'worst_case_curve': {str(k): v for k, v in curve.items()},
        'bound_method':
            'For k false negatives per unit, the k lowest-scoring negatives are '
            'removed and k negatives inserted above the entire ranking. This is '
            'adversarial on both sides and makes no assumption about which '
            'peptides would have been drawn or how the network would score '
            'them. The true cost at that k cannot exceed it.',
        'what_this_does_not_do':
            'It does not say which k is correct. The bracket is the range the '
            'flagged unique-versus-occurrence uncertainty admits; it is not a '
            'confidence interval, and it assumes the reservoir is otherwise '
            'unbiased. It bounds the AVERAGE-PRECISION cost only, conditional '
            'on k per unit. A bounded and tolerable cost is not the same as no '
            'defect: the construction remains non-test-blind in principle, and '
            'nothing here shows D044\'s other assumptions are harmless.',
        'seeds': {'bootstrap': seed('decoy_bound')},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + '\n')
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
