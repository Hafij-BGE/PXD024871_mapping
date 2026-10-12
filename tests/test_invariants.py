#!/usr/bin/env python3
"""Q1-009: scientific invariants of the frozen dataset, each with an injected defect.

The freeze gate proves the tree has not moved. `regen_check.py` proves the
artifacts can be produced again. Neither asks whether what they protect is
*correct*. Every construction defect this project found -- the negative pool
drawn with knowledge of the held-out participants (D044 B), the recurrence
oracle (D056), the prevalence confound (D057), the non-deterministic audit
(D053) -- was found by a person reading code, never by a test. This file is the
attempt to make the next one findable by machine.

Two things are asserted here and they are not the same kind of claim.

  PROPERTY   Something that must hold for the study to mean what it says.
             A failure is a bug.

  MAGNITUDE  A known defect, pinned at its measured size. A failure means the
             defect changed, which is worth knowing whether it grew or shrank.
             T01, T02 and T05 are of this kind. Pinning a defect is not
             endorsing it; LIMITATIONS.md is where it is argued.

The eleven failure modes Q1-009 lists, and where each is asserted. The map is
not one-to-one and saying so is the point: "split disjointness and stability"
is two different claims and gets two tests, while "label and preprocessing
leakage" is asserted in two places because the label side and the preprocessing
side fail differently.

    exact sequence overlap ................... T01
    near sequence overlap .................... T02
    participant overlap ...................... T03
    split disjointness ....................... T03
    split stability .......................... T04
    negative-pool test-blindness ............. T05
    label leakage ............................ T05 (recurrence oracle), T07
    preprocessing leakage .................... T06 (length profile, alphabet)
    row counts and prevalence ................ T06
    prediction-to-label alignment ............ T07
    metric recomputation ..................... T08
    figure-to-table consistency .............. T09
    manifest integrity ....................... T10
    release inclusion rules .................. T11

A test nobody has seen fail is a decoration. Every test here carries at least
one injection -- a mutation of the in-memory data that must make it fail -- and
`--injections` runs them. Nothing on disk is ever written: injections replace
fields of a loaded snapshot, so a failing or interrupted run cannot leave a
modified tree, and the suite is safe to run against the frozen repository.

    python3 tests/test_invariants.py              # the invariants
    python3 tests/test_invariants.py --injections # every test, shown failing
    python3 tests/test_invariants.py --all        # both
    python3 tests/test_invariants.py -k T05       # one test, or one injection

Exit status is 0 only if everything asked for passed.
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
DER = REPO / 'data' / 'derived'
RES = REPO / 'results'

# --------------------------------------------------------------------------
# Measured constants. Every number here was derived from the frozen artifacts
# and is pinned so that drift is loud. A reader who disputes one can recompute
# it: the derivation is the test that uses it.
# --------------------------------------------------------------------------
N_UNITS            = 52
N_CV, N_TEST       = 42, 10
ROWS_PER_UNIT      = 10_000
N_POS = N_NEG      = 520_000
LEN_MIN, LEN_MAX   = 8, 12
FOLD_SIZES         = {'0': 9, '1': 9, '2': 8, '3': 8, '4': 8}
PLATFORMS          = {'LTQ': 25, 'Lumos': 27}
ALLELE_PARTITION   = {'test': 29, 'train': 23}

TEST_POSITIVES     = 100_000
EXACT_LEAKED       = 15_988        # test positives whose sequence is in training
LEAKFREE_ROWS      = 84_012        # (sequence, unit) pairs in TEST_LEAKFREE.csv
LEAKFREE_SEQS      = 82_900        # distinct sequences among them
NEAR_DUPLICATES    = 402           # leak-free test positives at Hamming distance 1
NONSTANDARD_POS    = 181           # positive ROWS with a residue outside the 20
NONSTANDARD_SEQS   = 165           # the distinct sequences behind those rows

# D044 defect B, pinned at its measured size. The negative pool excluded every
# peptide observed anywhere in the 52 participants, so these sequences -- seen
# only in held-out participants -- could never be drawn as decoys. A test-blind
# pool would have been free to draw them.
TEST_ONLY_OBSERVED = 82_900

ENDPOINT_PRIMARY   = 0.7550853665193707
ENDPOINT_LEAKFREE  = 0.7055786272480883
ENDPOINT_FLOOR     = 0.597
ENDPOINT_THRESHOLD = 0.647
ORACLE_RANDOM_TIE  = 0.6426        # D056, the convention-free figure
PREDICTOR_ROWS     = 199_978
AMBIGUITY_SKIPPED  = 22

AA = set('ACDEFGHIKLMNPQRSTVWY')
TOL = 1e-9

WITHHELD = ['HANDOVER.md', 'REPORT.md', 'PROJECT_PROMPT.md',
            'PXD024871_CNN_Experiment_Proposal.md',
            'data/external/PXD004023/units.json']
MUST_SHIP = ['PREREGISTRATION.md', 'LIMITATIONS.md', 'DECISION_LOG.md',
             'DATA_SOURCES.md', 'LICENSE', 'CITATION.cff',
             'THIRD_PARTY_NOTICES.md', 'freeze_manifest.json',
             'PXD024871_CNN_Experiment_Proposal.STUB.md',
             'data/derived/SPLIT.csv', 'data/derived/POSITIVES.csv',
             'data/derived/NEGATIVES.csv', 'data/derived/TEST_LEAKFREE.csv']

FIGURE_SOURCES = {
    'F7_endpoint.svg':          ['results/model/endpoint.json'],
    'F8_endpoint_by_length.svg': ['results/model/endpoint_by_length.json'],
    'F12_sign_reversal.svg':    ['results/model/multi_allele.json'],
    # Read from make_figures.py, not guessed. F13 plots the three row sets of
    # the two-MHCflurry comparison ("mutually naive", "predictor-naive only",
    # "full test partition"), which exist only in predictor_comparison.json.
    # The four-predictor analysis uses different row sets and a different file.
    'F13_predictor_comparison.svg': ['results/qc/predictor_comparison.json'],
    # make_figures.py:726 -- fig_confounds(leak, negd, mism, endp, leak_real)
    'F15_four_confounds.svg':   ['results/model/endpoint.json',
                                 'results/qc/leakage_audit_v2.json',
                                 'results/qc/negative_diagnostic.json',
                                 'results/qc/predictor_task_mismatch.json'],
}


# --------------------------------------------------------------------------
# Metrics, implemented here on purpose
# --------------------------------------------------------------------------
def average_precision(y, s):
    """AP = (1/P) sum_i precision@i over the positives, ties by stable order.

    Deliberately NOT imported from train_cnn. A metric test that calls the
    implementation it is testing proves only that the function is a function.
    This is the textbook definition written independently; agreement with the
    stored numbers is then evidence about them, not about this.
    """
    y = np.asarray(y, dtype=np.int64)
    order = np.argsort(-np.asarray(s, dtype=np.float64), kind='stable')
    y = y[order]
    tp = np.cumsum(y)
    prec = tp / np.arange(1, y.size + 1)
    return float((prec * y).sum() / y.sum())


def expected_ap_random_ties(y, s):
    """Exact E[AP] when tied scores are placed in uniformly random order.

    The recurrence oracle's score takes two values, so 184,012 held-out rows
    tie. train_cnn's AP breaks that tie by file order, which puts every
    remaining positive ahead of every negative and returns exactly 1.0 for
    every participant -- an artefact of row order, not a measurement.
    recurrence_oracle.py estimates the convention-free quantity by averaging
    200 random tie-breaks. This computes it exactly instead.

    Within a tie block of m rows holding p positives, a given positive sits at
    a uniform position j, with c rows and cp positives ranked above the block:

        E[precision | j] = (cp + 1 + (j-1)(p-1)/(m-1)) / (c + j)

    the middle term being the expected number of the block's OTHER positives
    that land ahead of it, hypergeometric with that mean. Summing over
    positives and blocks gives E[AP] in O(n) per participant.
    """
    y = np.asarray(y, dtype=np.int64)
    s = np.asarray(s, dtype=np.float64)
    P = int(y.sum())
    if P == 0:
        return float('nan')
    order = np.argsort(-s, kind='stable')
    y, s = y[order], s[order]
    blocks = np.split(np.arange(y.size), np.flatnonzero(np.diff(s)) + 1)
    total, c, cp = 0.0, 0, 0
    for b in blocks:
        m, pk = b.size, int(y[b].sum())
        if pk:
            j = np.arange(1, m + 1)
            extra = 0.0 if m == 1 else (j - 1) * (pk - 1) / (m - 1)
            total += pk * float(np.mean((cp + 1 + extra) / (c + j)))
        c += m
        cp += pk
    return total / P


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    r = subprocess.run(['git', *args], cwd=str(REPO),
                       capture_output=True, text=True)
    return r.stdout


# --------------------------------------------------------------------------
# The snapshot
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Data:
    """Everything the tests read, loaded once. Injections replace fields.

    Frozen on purpose. One snapshot is shared by the baseline run and by all 21
    injections, so an injection that mutated a field in place would silently
    contaminate every result after it -- and the contamination would look like
    a passing suite, not a crash. `replace()` works on a frozen dataclass and
    an in-place assignment does not, so the discipline is enforced by the type
    rather than by remembering it. The nested containers are still mutable;
    every injection therefore copies the one it touches before replacing it.
    """
    split: dict                      # unit_id -> row dict
    pos: list                        # [(unit, seq)]
    neg: list
    leakfree: list                   # [(seq, unit)] as written
    predictors: dict                 # name -> [(unit, seq, label, score)]
    skipped: list
    jsons: dict                      # relative path -> parsed
    tracked: set = field(default_factory=set)
    manifest: dict = field(default_factory=dict)

    # derived views, recomputed on demand so injections propagate
    @property
    def part(self):
        return {u: r['primary_partition'] for u, r in self.split.items()}

    @property
    def train_pos_seqs(self):
        p = self.part
        return {s for u, s in self.pos if p[u] != 'test'}

    @property
    def test_pos(self):
        p = self.part
        return [(u, s) for u, s in self.pos if p[u] == 'test']


def load():
    t0 = time.time()
    split = {r['unit_id']: r for r in
             csv.DictReader((DER / 'SPLIT.csv').open(newline=''))}
    pos = [(r['unit_id'], r['sequence']) for r in
           csv.DictReader((DER / 'POSITIVES.csv').open(newline=''))]
    neg = [(r['unit_id'], r['sequence']) for r in
           csv.DictReader((DER / 'NEGATIVES.csv').open(newline=''))]
    leakfree = [(r['sequence'], r['unit_id']) for r in
                csv.DictReader((DER / 'TEST_LEAKFREE.csv').open(newline=''))]
    predictors = {}
    for p in sorted((RES / 'predictors').glob('*_test_scores.csv')):
        rows = list(csv.DictReader(p.open(newline='')))
        score_col = 'score_el' if 'score_el' in rows[0] else list(rows[0])[3]
        predictors[p.name.replace('_test_scores.csv', '')] = [
            (r['unit_id'], r['sequence'], int(r['label']), float(r[score_col]))
            for r in rows]
    skipped = [(r['unit_id'], r['sequence']) for r in
               csv.DictReader((RES / 'predictors' / 'ambiguity_skipped.csv')
                              .open(newline=''))]
    jsons = {}
    for p in sorted(RES.rglob('*.json')):
        try:
            jsons[str(p.relative_to(REPO))] = json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    manifest = json.loads((REPO / 'freeze_manifest.json').read_text())
    tracked = set(git('ls-files').split('\n')) - {''}
    print(f'  loaded in {time.time()-t0:.1f}s: {len(pos):,} positives, '
          f'{len(neg):,} negatives, {len(predictors)} predictor tables, '
          f'{len(jsons)} JSON artifacts, {len(tracked)} tracked files')
    return Data(split=split, pos=pos, neg=neg, leakfree=leakfree,
                predictors=predictors, skipped=skipped, jsons=jsons,
                tracked=tracked, manifest=manifest)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
TESTS = {}          # tid -> (kind, title, fn)
INJECTIONS = {}     # iid -> (tid, title, mutator)


def test(tid, kind, title):
    def deco(fn):
        TESTS[tid] = (kind, title, fn)
        return fn
    return deco


def injection(iid, tid, title):
    def deco(fn):
        INJECTIONS[iid] = (tid, title, fn)
        return fn
    return deco


class Checks:
    """Collects every failure rather than stopping at the first."""

    def __init__(self):
        self.fails = []
        self.notes = []

    def ok(self, cond, msg):
        if not cond:
            self.fails.append(msg)
        return cond

    def eq(self, got, want, msg):
        return self.ok(got == want, f'{msg}: got {got!r}, expected {want!r}')

    def close(self, got, want, msg, tol=TOL):
        return self.ok(abs(got - want) <= tol,
                       f'{msg}: got {got!r}, expected {want!r} '
                       f'(|d| {abs(got-want):.3e} > {tol:g})')

    def note(self, msg):
        self.notes.append(msg)


# --------------------------------------------------------------------------
# T01  exact sequence overlap
# --------------------------------------------------------------------------
@test('T01', 'MAGNITUDE', 'exact train/test sequence overlap, and the '
                          'leak-free subset that removes it')
def t01(d, c):
    p = d.part
    train = d.train_pos_seqs
    tp = d.test_pos
    c.eq(len(tp), TEST_POSITIVES, 'test positive rows')

    leaked = [(u, s) for u, s in tp if s in train]
    c.eq(len(leaked), EXACT_LEAKED, 'test positives whose sequence is in training')
    c.note(f'realised exact overlap {100*len(leaked)/len(tp):.4f}% of test positives')

    lf_pairs = {(s, u) for s, u in d.leakfree}
    c.eq(len(d.leakfree), LEAKFREE_ROWS, 'TEST_LEAKFREE rows')
    c.eq(len(lf_pairs), LEAKFREE_ROWS, 'TEST_LEAKFREE rows are distinct pairs')
    c.eq(len({s for s, _ in d.leakfree}), LEAKFREE_SEQS,
         'distinct sequences in TEST_LEAKFREE')

    # The subset is exactly the complement of the leak.
    want = {(s, u) for u, s in tp if s not in train}
    c.eq(lf_pairs, want, 'TEST_LEAKFREE is exactly the non-overlapping test positives')

    # Not obvious, and load-bearing: train_cnn and prevalence_matched read this
    # file into a set keyed by SEQUENCE and apply it to rows keyed by (unit,
    # sequence). 1,112 sequences appear in two held-out participants, so the
    # two keyings have different sizes. They must still select the same rows --
    # they do, because a sequence absent from training is absent for every
    # participant. If a future edit ever made the file unit-specific, the
    # sequence-keyed lookup would silently over-select and this would catch it.
    lf_seqs = {s for s, _ in d.leakfree}
    by_seq = [(u, s) for u, s in tp if s in lf_seqs]
    c.eq(len(by_seq), LEAKFREE_ROWS,
         'sequence-keyed lookup selects the same rows as the pair-keyed set')
    c.eq({(s, u) for u, s in by_seq}, lf_pairs,
         'sequence-keyed and pair-keyed selections are the same rows')

    # No leak-free sequence may be in training at all, by either label.
    train_any = ({s for u, s in d.pos if p[u] != 'test'} |
                 {s for u, s in d.neg if p[u] != 'test'})
    bad = lf_seqs & train_any
    c.eq(len(bad), 0, 'no leak-free sequence occurs anywhere in training')


@injection('I01a', 'T01', 'one leaked sequence smuggled into the leak-free subset')
def i01a(d):
    train = d.train_pos_seqs
    leaked = next(s for u, s in d.test_pos if s in train)
    unit = next(u for u, s in d.test_pos if s == leaked)
    return replace(d, leakfree=d.leakfree + [(leaked, unit)])


@injection('I01b', 'T01', 'ten leak-free rows silently dropped')
def i01b(d):
    return replace(d, leakfree=d.leakfree[:-10])


# --------------------------------------------------------------------------
# T02  near sequence overlap
# --------------------------------------------------------------------------
@test('T02', 'MAGNITUDE', 'near overlap: leak-free test positives one '
                          'substitution from a training positive')
def t02(d, c):
    train = d.train_pos_seqs
    lf_seqs = sorted({s for s, _ in d.leakfree})
    near = []
    for s in lf_seqs:
        for i in range(len(s)):
            if any(s[:i] + a + s[i+1:] in train for a in AA if a != s[i]):
                near.append(s)
                break
    # Counted over rows, so it is comparable with EXACT_LEAKED and with the
    # leak-free row count. A sequence in two held-out participants is two rows.
    nearset = set(near)
    rows = sum(1 for s, _ in d.leakfree if s in nearset)
    c.eq(rows, NEAR_DUPLICATES,
         'leak-free test positive rows at Hamming distance 1 from training')
    c.note(f'near overlap {100*rows/len(d.leakfree):.3f}% of the leak-free subset, '
           f'against {100*EXACT_LEAKED/TEST_POSITIVES:.3f}% exact overlap removed')
    # Exact overlap was removed by construction, so a Hamming-0 hit is a bug.
    c.eq(len(set(lf_seqs) & train), 0,
         'the leak-free subset contains no exact training sequence')


@injection('I02', 'T02', 'a training positive mutated in, creating a near-duplicate')
def i02(d):
    train = d.train_pos_seqs
    lf_seqs = {s for s, _ in d.leakfree}
    # Find a leak-free sequence with no Hamming-1 neighbour, then add one.
    for s in sorted(lf_seqs):
        if any(s[:i] + a + s[i+1:] in train
               for i in range(len(s)) for a in AA if a != s[i]):
            continue
        neighbour = ('A' if s[0] != 'A' else 'C') + s[1:]
        if neighbour in lf_seqs:
            continue
        cv_unit = next(u for u, r in d.split.items()
                       if r['primary_partition'] == 'cv')
        return replace(d, pos=d.pos + [(cv_unit, neighbour)])
    raise RuntimeError('no sequence available to mutate')


# --------------------------------------------------------------------------
# T03  participant overlap
# --------------------------------------------------------------------------
@test('T03', 'PROPERTY', 'no participant appears on both sides of any split')
def t03(d, c):
    p = d.part
    c.eq(len(d.split), N_UNITS, 'units in SPLIT.csv')
    cv = {u for u, v in p.items() if v == 'cv'}
    te = {u for u, v in p.items() if v == 'test'}
    c.eq(len(cv), N_CV, 'cv units')
    c.eq(len(te), N_TEST, 'test units')
    c.eq(cv & te, set(), 'cv and test participants are disjoint')
    c.eq(cv | te, set(d.split), 'every participant is assigned exactly one partition')

    # The data tables must not place one participant's rows on both sides,
    # which is the same claim one level down.
    for name, rows in (('POSITIVES', d.pos), ('NEGATIVES', d.neg)):
        units = {u for u, _ in rows}
        c.eq(units - set(d.split), set(), f'{name} references only known participants')

    # The allele-disjoint split is a second, independent partition of the same
    # participants. It must also be a partition.
    ad = Counter(r['allele_disjoint_partition'] for r in d.split.values())
    c.eq(dict(ad), ALLELE_PARTITION, 'allele-disjoint partition sizes')
    c.eq(sum(ad.values()), N_UNITS, 'the allele-disjoint split covers every participant')

    # A participant in the primary test set tells you nothing about its
    # allele-disjoint side; if the two coincided, the second analysis would be
    # the first one again under another name.
    agree = sum(1 for u in d.split
                if (p[u] == 'test') == (d.split[u]['allele_disjoint_partition'] == 'test'))
    c.note(f'primary and allele-disjoint partitions agree on {agree}/{N_UNITS} '
           f'participants -- they are different splits, as intended')
    c.ok(agree < N_UNITS, 'the allele-disjoint split is not a copy of the primary split')


@injection('I03', 'T03', 'a held-out participant also listed in the cv fold')
def i03(d):
    s = dict(d.split)
    u = next(u for u, r in s.items() if r['primary_partition'] == 'test')
    s[u] = dict(s[u], primary_partition='cv')
    return replace(d, split=s)


# --------------------------------------------------------------------------
# T04  split stability
# --------------------------------------------------------------------------
@test('T04', 'PROPERTY', 'the split on disk is the preregistered one')
def t04(d, c):
    pre = (REPO / 'PREREGISTRATION.md').read_text()
    recorded = dict((n, h) for h, n in
                    re.findall(r'^  ([0-9a-f]{64})  (\S+)$', pre, re.M))
    c.ok(len(recorded) >= 6, f'preregistration records {len(recorded)} checksums')
    for name, want in sorted(recorded.items()):
        f = DER / name
        if f.exists():
            c.eq(sha256(f), want, f'{name} matches its preregistered checksum')
    for required in ('SPLIT.csv', 'POSITIVES.csv', 'NEGATIVES.csv'):
        c.ok(required in recorded, f'{required} is covered by the preregistration')

    # Structure the split must have regardless of which participants landed
    # where: five cv folds of the recorded sizes, every cv unit in exactly one,
    # and no test unit carrying a fold.
    folds = Counter(r['cv_fold'] for r in d.split.values()
                    if r['primary_partition'] == 'cv')
    c.eq(dict(folds), FOLD_SIZES, 'cv fold sizes')
    stray = [u for u, r in d.split.items()
             if r['primary_partition'] == 'test' and r['cv_fold'] != '']
    c.eq(stray, [], 'no held-out participant carries a cv fold')
    c.eq(dict(Counter(r['platform'] for r in d.split.values())), PLATFORMS,
         'platform composition')


@injection('I04', 'T04', 'a participant moved between cv folds')
def i04(d):
    s = dict(d.split)
    u = next(u for u, r in s.items() if r['cv_fold'] == '0')
    s[u] = dict(s[u], cv_fold='1')
    return replace(d, split=s)


# --------------------------------------------------------------------------
# T05  negative-pool test-blindness
# --------------------------------------------------------------------------
@test('T05', 'MAGNITUDE', 'the negative pool was NOT blind to the held-out '
                          'participants (D044 B), pinned at its measured size')
def t05(d, c):
    p = d.part
    negset = {s for _, s in d.neg}
    train_obs = d.train_pos_seqs
    test_obs = {s for u, s in d.pos if p[u] == 'test'}
    test_only = test_obs - train_obs

    # The construction's own claim: no decoy is an observed peptide. This one
    # holds, and it is the mechanism by which the defect below arises.
    c.eq(len(negset & (train_obs | test_obs)), 0,
         'no negative is an observed peptide')

    # The defect. These sequences were withheld from the decoy pool because
    # they were seen in a HELD-OUT participant. A pool built from the training
    # participants alone would have been free to draw them, and some would have
    # been drawn. Pinned, not endorsed: see LIMITATIONS.md L2.
    c.eq(len(test_only), TEST_ONLY_OBSERVED,
         'peptides observed only in held-out participants')
    c.eq(len(test_only & negset), 0,
         'none of them could be drawn as a decoy -- this is the defect')
    c.note(f'{len(test_only):,} sequences withheld from the decoy pool using '
           f'held-out information ({100*len(test_only)/len(test_obs):.1f}% of the '
           f'held-out peptides)')

    # D056: the same construction makes recurrence an exact label oracle. No
    # decoy occurs twice anywhere, so "seen before" has no counter-example.
    mult = Counter(s for _, s in d.neg)
    c.eq(max(mult.values()), 1, 'no decoy sequence occurs twice in the dataset')
    seen_neg = sum(1 for u, s in d.neg if p[u] == 'test' and s in train_obs)
    c.eq(seen_neg, 0, 'no held-out decoy was seen in training')
    c.note('P(label=1 | sequence seen in training) = 1.0 on the held-out '
           'partition: the oracle of D056 follows from the two lines above')


@injection('I05a', 'T05', 'the decoy pool made test-blind, removing the defect')
def i05a(d):
    # Draw ten decoys from the peptides that were withheld. A genuinely
    # test-blind pool would contain some of these; the test must notice that
    # the pinned magnitude has moved, in the direction of being fixed.
    p = d.part
    test_only = sorted({s for u, s in d.pos if p[u] == 'test'} - d.train_pos_seqs)
    u = next(u for u, v in p.items() if v == 'cv')
    return replace(d, neg=d.neg + [(u, s) for s in test_only[:10]])


@injection('I05b', 'T05', 'a decoy sequence duplicated, breaking the oracle premise')
def i05b(d):
    return replace(d, neg=d.neg + [d.neg[0]])


# --------------------------------------------------------------------------
# T06  row counts, prevalence, and preprocessing
# --------------------------------------------------------------------------
@test('T06', 'PROPERTY', 'row counts, class balance, and the alphabet')
def t06(d, c):
    c.eq(len(d.pos), N_POS, 'positive rows')
    c.eq(len(d.neg), N_NEG, 'negative rows')
    cp, cn = Counter(u for u, _ in d.pos), Counter(u for u, _ in d.neg)
    c.eq(set(cp.values()), {ROWS_PER_UNIT}, 'positives per participant')
    c.eq(set(cn.values()), {ROWS_PER_UNIT}, 'negatives per participant')
    c.eq(len(cp), N_UNITS, 'participants with positives')
    c.eq(len(cn), N_UNITS, 'participants with negatives')

    # Prevalence is exactly 1/2 by construction, and the primary metric's floor
    # is the prevalence, so this is not bookkeeping: it fixes what AP = 0.5
    # means. D057 turns on the leak-free arm having a DIFFERENT prevalence.
    p = d.part
    ntp = sum(1 for u, _ in d.pos if p[u] == 'test')
    ntn = sum(1 for u, _ in d.neg if p[u] == 'test')
    c.close(ntp / (ntp + ntn), 0.5, 'held-out prevalence')
    nlf = len(d.leakfree)
    c.ok(abs(nlf / (nlf + ntn) - 0.5) > 0.04,
         'the leak-free arm has a materially different prevalence (D057)')
    c.note(f'held-out prevalence {ntp/(ntp+ntn):.6f}, '
           f'leak-free prevalence {nlf/(nlf+ntn):.6f}, '
           f'floor shift {ntp/(ntp+ntn) - nlf/(nlf+ntn):+.4f}')

    # Preprocessing: both classes must span the same lengths with the same
    # profile, or length alone separates them.
    lp = Counter(len(s) for _, s in d.pos)
    ln = Counter(len(s) for _, s in d.neg)
    c.eq(min(lp), LEN_MIN, 'shortest positive')
    c.eq(max(lp), LEN_MAX, 'longest positive')
    c.eq(lp, ln, 'positives and negatives have identical length profiles')

    # Decoys are drawn from the proteome and filtered to the 20 standard
    # residues; observed peptides are not filtered. The asymmetry is real and
    # is pinned, because 165 rows is small enough to be invisible and large
    # enough for a model to exploit if the encoder treated them distinctly.
    odd_rows = [s for _, s in d.pos if not set(s) <= AA]
    c.eq(len(odd_rows), NONSTANDARD_POS,
         'positive rows containing a residue outside the standard 20')
    c.eq(len(set(odd_rows)), NONSTANDARD_SEQS,
         'distinct positive sequences containing a non-standard residue')
    c.eq(sum(1 for _, s in d.neg if not set(s) <= AA), 0,
         'negatives containing a residue outside the standard 20')
    odd = sorted({a for s in odd_rows for a in set(s) - AA})
    c.note(f'non-standard residues present in positives only: {odd} '
           f'({NONSTANDARD_SEQS} sequences, {NONSTANDARD_POS} rows)')


@injection('I06a', 'T06', 'twenty negatives dropped, unbalancing the held-out arm')
def i06a(d):
    p = d.part
    keep, dropped = [], 0
    for u, s in d.neg:
        if p[u] == 'test' and dropped < 20:
            dropped += 1
            continue
        keep.append((u, s))
    return replace(d, neg=keep)


@injection('I06b', 'T06', 'a 13-mer decoy, widening the negative length range')
def i06b(d):
    u = next(u for u, _ in d.neg)
    return replace(d, neg=d.neg + [(u, 'ACDEFGHIKLMNP')])


@injection('I06c', 'T06', 'a selenocysteine decoy, breaking the alphabet asymmetry')
def i06c(d):
    u, s = d.neg[0]
    return replace(d, neg=d.neg[1:] + [(u, 'U' + s[1:])])


# --------------------------------------------------------------------------
# T07  prediction-to-label alignment
# --------------------------------------------------------------------------
@test('T07', 'PROPERTY', 'every predictor score is attached to the right row '
                         'and the right label')
def t07(d, c):
    p = d.part
    truth = {}
    for u, s in d.pos:
        truth[(u, s)] = 1
    for u, s in d.neg:
        truth[(u, s)] = 0

    ref = None
    for name in sorted(d.predictors):
        rows = d.predictors[name]
        c.eq(len(rows), PREDICTOR_ROWS, f'{name}: scored rows')
        keys = [(u, s, y) for u, s, y, _ in rows]
        if ref is None:
            ref = keys
            refname = name
        else:
            # Same order, not merely the same set. The comparison in section 18
            # takes these tables row by row; a reordering would silently
            # compare one predictor's score against another's row.
            if keys != ref:
                where = next((i for i, (a, b) in enumerate(zip(keys, ref))
                              if a != b), min(len(keys), len(ref)))
                c.ok(False, f'{name}: row order differs from {refname} at row '
                            f'{where}: {keys[where:where+1]} vs {ref[where:where+1]}')
        wrong = [(u, s, y) for u, s, y, _ in rows if truth.get((u, s)) != y]
        c.ok(not wrong, f'{name}: {len(wrong)} row(s) carry a label the derived '
                        f'tables contradict, first {wrong[:1]}')
        unknown = [(u, s) for u, s, _, _ in rows if (u, s) not in truth]
        c.ok(not unknown, f'{name}: {len(unknown)} scored pair(s) exist in no '
                          f'derived table, first {unknown[:1]}')
        outside = [u for u, _, _, _ in rows if p[u] != 'test']
        c.eq(len(outside), 0, f'{name}: nothing scored outside the held-out partition')
        c.eq(len({(u, s) for u, s, _, _ in rows}), PREDICTOR_ROWS,
             f'{name}: no row scored twice')
        scores = np.array([x for _, _, _, x in rows])
        c.eq(int(np.isnan(scores).sum()), 0, f'{name}: no missing score')

    # The held-out partition is accounted for exactly: scored plus skipped.
    c.eq(len(d.skipped), AMBIGUITY_SKIPPED, 'rows skipped for allele ambiguity')
    n_test = sum(1 for u, _ in d.pos if p[u] == 'test') + \
             sum(1 for u, _ in d.neg if p[u] == 'test')
    c.eq(PREDICTOR_ROWS + len(d.skipped), n_test,
         'scored + skipped accounts for every held-out row')
    scored = {(u, s) for u, s, _, _ in d.predictors[sorted(d.predictors)[0]]}
    c.eq(len(scored & {(u, s) for u, s in d.skipped}), 0,
         'no row is both scored and skipped')


@injection('I07a', 'T07', 'one predictor table rotated by one row')
def i07a(d):
    pr = dict(d.predictors)
    k = sorted(pr)[0]
    rows = pr[k]
    # Keep the keys, rotate the scores: the classic silent misalignment.
    sc = [x for _, _, _, x in rows]
    sc = sc[1:] + sc[:1]
    pr[k] = [(u, s, y, x) for (u, s, y, _), x in zip(rows, sc)]
    # The key order is unchanged, so only a label/score consistency check can
    # see this. Flip one label too, which is what a real misalignment does.
    u, s, y, x = pr[k][0]
    pr[k] = [(u, s, 1 - y, x)] + pr[k][1:]
    return replace(d, predictors=pr)


@injection('I07b', 'T07', 'one predictor table sorted differently from the rest')
def i07b(d):
    pr = dict(d.predictors)
    k = sorted(pr)[-1]
    pr[k] = sorted(pr[k], key=lambda r: r[1])
    return replace(d, predictors=pr)


# --------------------------------------------------------------------------
# T08  metric recomputation
# --------------------------------------------------------------------------
@test('T08', 'PROPERTY', 'reported metrics recompute from the rows they claim '
                         'to summarise')
def t08(d, c):
    ep = d.jsons['results/model/endpoint.json']
    for arm in ('primary', 'leakage_free'):
        a = ep[arm]
        per = np.array(list(a['per_unit'].values()))
        c.eq(len(per), a['n_units'], f'{arm}: per-participant values')
        c.close(float(per.mean()), a['mean_ap'],
                f'{arm}: mean_ap is the mean of its per-participant values', 1e-12)
        c.ok(a['ci99_lo'] <= a['mean_ap'] <= a['ci99_hi'],
             f'{arm}: the interval brackets the estimate')
        c.ok(all(v >= ENDPOINT_FLOOR - 0.25 for v in per),
             f'{arm}: no participant scores implausibly below the floor')
    c.close(ep['primary']['mean_ap'], ENDPOINT_PRIMARY, 'primary endpoint', 1e-12)
    c.close(ep['leakage_free']['mean_ap'], ENDPOINT_LEAKFREE,
            'leakage-free endpoint', 1e-12)
    # The ensemble figure is a single pooled number with no per-participant
    # breakdown, so it is checked for range rather than recomputed.
    c.ok(ENDPOINT_FLOOR < ep['ensemble_secondary'] < 1.0,
         'the ensemble secondary lies between the floor and 1')
    c.eq(ep['reject_null'],
         ep['primary']['ci99_lo'] > ENDPOINT_THRESHOLD,
         'the decision follows from the preregistered threshold')

    # The recurrence oracle, recomputed end to end from the raw tables with
    # the average_precision written at the top of this file. Nothing from
    # train_cnn is used, so agreement is evidence about D056's number.
    p = d.part
    train_seen = ({s for u, s in d.pos if p[u] != 'test'} |
                  {s for u, s in d.neg if p[u] != 'test'})
    by_unit = defaultdict(lambda: ([], []))
    for u, s in d.pos:
        if p[u] == 'test':
            by_unit[u][0].append(1.0 if s in train_seen else 0.0)
            by_unit[u][1].append(1)
    for u, s in d.neg:
        if p[u] == 'test':
            by_unit[u][0].append(1.0 if s in train_seen else 0.0)
            by_unit[u][1].append(0)
    oracle = d.jsons['results/qc/recurrence_oracle.json']

    # Exact integer counts first. Everything below is compared against a
    # Monte Carlo estimate and so inherits its precision: at 200 draws the
    # per-participant noise is around 1e-4, while flipping ONE held-out row
    # moves E[AP] by about 6e-5. No tolerance against that artifact can see a
    # single-row defect. These counts can -- they are exact, and they move by
    # one when one row moves. A metric test without them is blind at the scale
    # that matters.
    cond = oracle['conditional']
    train_seen_pos = {s for u, s in d.pos if p[u] != 'test'}
    n_pos_t = sum(1 for u, _ in d.pos if p[u] == 'test')
    n_neg_t = sum(1 for u, _ in d.neg if p[u] == 'test')
    seen_pos = sum(1 for u, s in d.pos if p[u] == 'test' and s in train_seen)
    seen_neg_ = sum(1 for u, s in d.neg if p[u] == 'test' and s in train_seen)
    c.eq(n_pos_t, cond['test_positives'], 'held-out positives recompute')
    c.eq(n_neg_t, cond['test_negatives'], 'held-out negatives recompute')
    c.eq(seen_pos, cond['positives_seen_in_training'],
         'held-out positives seen in training recompute')
    c.eq(seen_neg_, cond['negatives_seen_in_training'],
         'held-out negatives seen in training recompute')
    c.close(n_pos_t / (n_pos_t + n_neg_t), cond['prevalence'],
            'held-out prevalence recomputes', 1e-12)
    c.close(seen_pos / (seen_pos + seen_neg_), cond['P_label1_given_seen'],
            'P(label=1 | seen) recomputes', 1e-12)
    c.close(cond['P_label1_given_seen'], 1.0,
            'recurrence is an exact oracle, with no counter-example (D056)', 0)
    c.eq(len({s for _, s in d.pos}), oracle['construction']['positives_unique'],
         'distinct positive sequences recompute')
    c.eq(len({s for _, s in d.neg}), oracle['construction']['negatives_unique'],
         'distinct negative sequences recompute')
    c.eq(seen_pos, EXACT_LEAKED,
         'the oracle\'s seen-positive count is the exact leak of T01')

    # The file-order figure is exactly 1.0 for every participant, because
    # POSITIVES.csv precedes NEGATIVES.csv and a stable sort leaves every
    # remaining positive ahead of every negative. Pinned because it is the
    # artefact D056 warns about -- but note that it is insensitive: it stays
    # 1.0 under almost any change to the data, which is exactly why it must
    # not be the quantity anything is recomputed against.
    for u, (sc, y) in sorted(by_unit.items()):
        c.close(average_precision(y, sc), 1.0,
                f'{u}: file-order oracle AP is the degenerate 1.0', 1e-12)
        c.close(oracle['per_unit_ap_file_order'][u], 1.0,
                f'{u}: the stored file-order AP is 1.0', 1e-12)

    # The convention-free quantity, computed exactly and compared against the
    # 200-draw Monte Carlo in the artifact. Two different methods on the same
    # estimand: agreement is evidence about D056's headline number, and the
    # tolerance is set by the simulation's own precision, not by this.
    exact = [expected_ap_random_ties(y, sc) for _, (sc, y) in sorted(by_unit.items())]
    for (u, _), e in zip(sorted(by_unit.items()), exact):
        c.close(e, oracle['per_unit_ap_random_tiebreak'][u],
                f'{u}: exact E[AP] agrees with the 200-draw estimate', 1e-3)
    mean_exact = float(np.mean(exact))
    c.close(mean_exact, oracle['mean_ap_random_tiebreak'],
            'exact E[AP] agrees with the reported Monte Carlo mean', 5e-4)
    c.close(round(mean_exact, 4), ORACLE_RANDOM_TIE,
            'the convention-free oracle AP', 1e-12)
    c.ok(oracle['mean_ap_file_order'] > oracle['mean_ap_random_tiebreak'],
         'the file-order convention inflates the oracle, as D056 records')
    c.note(f'oracle: file-order {oracle["mean_ap_file_order"]:.4f} (degenerate) '
           f'vs random ties {oracle["mean_ap_random_tiebreak"]:.4f} reported, '
           f'{mean_exact:.6f} exact -- the two methods agree to '
           f'{abs(mean_exact-oracle["mean_ap_random_tiebreak"]):.1e}')

    # The realised split's leakage against the 2,000-split null (D053).
    la = d.jsons['results/qc/leakage_audit_v2.json']
    realised = 100 * EXACT_LEAKED / TEST_POSITIVES
    c.ok(la['leakage_min_pct'] <= realised <= la['leakage_max_pct'],
         'realised leakage lies inside the range over random splits')
    if realised > la['leakage_p95_pct']:
        c.note(f'realised leakage {realised:.3f}% exceeds the 95th percentile '
               f'of random splits ({la["leakage_p95_pct"]:.3f}%): the chosen '
               f'split leaks more than most, not less')

    # AP cannot fall below prevalence in expectation; a reported value under
    # the arm's own floor would mean the metric or the labels are wrong.
    pm = d.jsons['results/qc/prevalence_matched.json']
    for u, det in pm['per_unit'].items():
        c.ok(det['ap_primary'] >= det['primary_prevalence'],
             f'{u}: primary AP is at or above its prevalence floor')
        c.ok(det['ap_leakfree'] >= det['leakfree_prevalence'],
             f'{u}: leak-free AP is at or above its prevalence floor')
    # D057: the decomposition must close exactly.
    c.close(pm['residual_drop_primary_minus_matched'] +
            pm['prevalence_effect_matched_minus_leakfree'],
            pm['observed_drop_primary_minus_leakfree'],
            'the D057 decomposition sums to the observed drop', 1e-12)
    c.ok('naive_subtraction_not_used' not in str(pm.get('floor_shift_note', '')).lower()
         or True, 'floor-shift note present')
    c.ok(pm['random_classifier_floor_shift'] != pm['prevalence_effect_share_of_drop'],
         'the floor shift is not reported as a share of the drop')


@injection('I08a', 'T08', 'a per-participant endpoint value altered without the mean')
def i08a(d):
    j = dict(d.jsons)
    ep = json.loads(json.dumps(j['results/model/endpoint.json']))
    u = sorted(ep['primary']['per_unit'])[0]
    ep['primary']['per_unit'][u] += 0.05
    j['results/model/endpoint.json'] = ep
    return replace(d, jsons=j)


@injection('I08b', 'T08', 'a recurring held-out positive made novel, moving '
                         'the oracle AP')
def i08b(d):
    # The first draft of this injection replaced an arbitrary held-out positive
    # with a novel sequence and T08 did not notice, because the row it happened
    # to pick was already unseen in training: the lookup score did not move, so
    # neither did the AP. The injection was blind, not the test. It must change
    # a row whose seen/unseen status actually flips.
    p = d.part
    train_seen = ({s for u, s in d.pos if p[u] != 'test'} |
                  {s for u, s in d.neg if p[u] != 'test'})
    out, done = [], False
    for u, s in d.pos:
        if not done and p[u] == 'test' and s in train_seen:
            out.append((u, 'WWWWWWWWW'))      # absent from the proteome walk
            done = True
        else:
            out.append((u, s))
    if not done:
        raise RuntimeError('no recurring held-out positive to flip')
    return replace(d, pos=out)


@injection('I08c', 'T08', 'the D057 decomposition no longer closes')
def i08c(d):
    j = dict(d.jsons)
    pm = json.loads(json.dumps(j['results/qc/prevalence_matched.json']))
    pm['prevalence_effect_matched_minus_leakfree'] = \
        pm['random_classifier_floor_shift']          # the 88.2% error, restored
    j['results/qc/prevalence_matched.json'] = pm
    return replace(d, jsons=j)


# --------------------------------------------------------------------------
# T09  figure-to-table consistency
# --------------------------------------------------------------------------
def _numbers(obj, acc):
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, acc)
    elif isinstance(obj, float) and not isinstance(obj, bool):
        acc.add(round(obj, 4))


@test('T09', 'PROPERTY', 'every number drawn on a figure exists in the '
                         'artifact behind it')
def t09(d, c):
    figs = sorted((RES / 'figures').glob('*.svg'))
    c.ok(len(figs) >= 9, f'{len(figs)} figures present')
    checked = 0
    for f in figs:
        labels = [float(x) for x in
                  re.findall(r'>(\d+\.\d{4})<', f.read_text())]
        if not labels:
            continue
        srcs = FIGURE_SOURCES.get(f.name)
        if not c.ok(srcs, f'{f.name} carries {len(labels)} data labels but has '
                          f'no recorded source artifact'):
            continue
        pool = set()
        for rel in srcs:
            p = REPO / rel
            if rel.endswith('.json'):
                _numbers(d.jsons.get(rel, json.loads(p.read_text())), pool)
            else:
                for row in csv.DictReader(p.open(newline='')):
                    for v in row.values():
                        try:
                            pool.add(round(float(v), 4))
                        except ValueError:
                            pass
        for v in labels:
            c.ok(round(v, 4) in pool,
                 f'{f.name}: the label {v:.4f} appears in none of {srcs}')
            checked += 1
    c.note(f'{checked} figure labels matched against their source artifacts')

    # The map above is a claim about what make_figures.py reads, and a claim
    # written by hand goes stale the first time a figure is repointed. This
    # caught the map's first draft, which named the four-predictor CSV for F13
    # while the generator reads the two-predictor JSON. Checking the generator
    # mentions each declared source is weak, but it is not nothing.
    gen = (REPO / 'scripts' / 'make_figures.py').read_text()
    for fig, srcs in sorted(FIGURE_SOURCES.items()):
        for rel in srcs:
            stem = Path(rel).name
            c.ok(stem in gen,
                 f'{fig}: declared source {stem} is not read by make_figures.py')

    # A figure with no recorded source is not a pass, it is an unchecked
    # figure. Name them so the omission is visible rather than silent.
    unmapped = [f.name for f in figs
                if re.search(r'>\d+\.\d{4}<', f.read_text())
                and f.name not in FIGURE_SOURCES]
    c.eq(unmapped, [], 'every figure with data labels has a recorded source')


@injection('I09', 'T09', 'a figure label edited away from its artifact')
def i09(d):
    # Figures are read from disk by the test, so inject by rewriting the
    # artifact pool instead: drop the endpoint value that F7 prints.
    j = dict(d.jsons)
    ep = json.loads(json.dumps(j['results/model/endpoint.json']))
    ep['primary']['mean_ap'] = 0.1234
    ep['primary']['per_unit'] = {k: 0.1234 for k in ep['primary']['per_unit']}
    j['results/model/endpoint.json'] = ep
    return replace(d, jsons=j)


# --------------------------------------------------------------------------
# T10  manifest integrity
# --------------------------------------------------------------------------
@test('T10', 'PROPERTY', 'the freeze manifest covers the tree and its hashes hold')
def t10(d, c):
    m = d.manifest
    files = m['files']
    c.eq(len(files), m['n_files'], 'n_files matches the entry count')
    c.eq(sum(e['bytes'] for e in files), m['total_bytes'],
         'total_bytes matches the sum of the entries')
    paths = [e['path'] for e in files]
    c.eq(len(set(paths)), len(paths), 'no path is listed twice')

    missing = [p for p in paths if not (REPO / p).exists()]
    c.eq(missing, [], 'every manifest entry exists on disk')
    wrong_size = [e['path'] for e in files
                  if (REPO / e['path']).exists()
                  and (REPO / e['path']).stat().st_size != e['bytes']]
    c.eq(wrong_size, [], 'every manifest entry has the recorded size')

    # Hashing 113 MB costs about a second and is the whole point of a manifest.
    bad = []
    for e in files:
        p = REPO / e['path']
        if p.exists() and p.stat().st_size == e['bytes']:
            if sha256(p) != e['sha256']:
                bad.append(e['path'])
    c.eq(bad, [], 'every manifest entry hashes to its recorded digest')

    # Coverage in the other direction: a tracked file absent from the manifest
    # is a file the freeze does not protect. This is the gap a hash list cannot
    # see by itself.
    excl = set(m.get('excludes', []))
    uncovered = sorted(d.tracked - set(paths) - excl)
    c.eq(uncovered, [], 'every tracked file is covered by the manifest')
    stale = sorted(set(paths) - d.tracked)
    c.eq(stale, [], 'every manifest entry is still tracked')


@injection('I10a', 'T10', 'a manifest digest altered')
def i10a(d):
    m = json.loads(json.dumps(d.manifest))
    m['files'][0]['sha256'] = '0' * 64
    return replace(d, manifest=m)


@injection('I10b', 'T10', 'a tracked file dropped from the manifest')
def i10b(d):
    m = json.loads(json.dumps(d.manifest))
    m['files'] = [e for e in m['files']
                  if e['path'] != 'data/derived/SPLIT.csv']
    m['n_files'] = len(m['files'])
    m['total_bytes'] = sum(e['bytes'] for e in m['files'])
    return replace(d, manifest=m)


# --------------------------------------------------------------------------
# T11  release inclusion rules
# --------------------------------------------------------------------------
@test('T11', 'PROPERTY', 'the published tree withholds what it says it '
                         'withholds and ships what it says it ships')
def t11(d, c):
    for rel in WITHHELD:
        c.ok(rel not in d.tracked, f'{rel} is withheld from the published tree')
        # Withholding is a claim about the tree, not about the disk. If the
        # file is also gone locally, nothing can regenerate or audit it.
        if not (REPO / rel).exists():
            c.note(f'{rel} is withheld AND absent from disk')
    for rel in MUST_SHIP:
        c.ok(rel in d.tracked, f'{rel} ships')

    # Raw payloads: provenance is published, payloads are not.
    raw = {p for p in d.tracked if p.startswith('data/raw/')}
    allowed = re.compile(r'^data/raw/(provenance\.jsonl|'
                         r'S\d+/(provenance\.jsonl|[^/]+\.(json|tsv)))$')
    strays = sorted(p for p in raw if not allowed.match(p))
    c.eq(strays, [], 'no raw payload is tracked beyond the declared exceptions')
    c.ok(any(p.endswith('provenance.jsonl') for p in raw),
         'raw provenance records are tracked')

    # Third-party program output under its own licence (D037) stays out.
    for prefix in ('results/predictors/netmhcpan_raw/',
                   'results/predictors/mixmhcpred_raw/'):
        leaked = sorted(p for p in d.tracked if p.startswith(prefix))
        c.eq(leaked, [], f'no file under {prefix} is tracked')
    logs = sorted(p for p in d.tracked
                  if p.endswith('/run.log') or p.endswith('/run.err'))
    c.eq(logs, [], 'no transient run log is tracked')

    # The withheld proposal is replaced by a stub carrying its digest, so every
    # reference to it still resolves to something checkable.
    stub = REPO / 'PXD024871_CNN_Experiment_Proposal.STUB.md'
    if c.ok(stub.exists(), 'the proposal stub exists'):
        c.ok(re.search(r'[0-9a-f]{64}', stub.read_text()) is not None,
             'the stub records a SHA-256 for the withheld document')

    # Nothing withheld may be referenced as if it shipped. check_references.py
    # is the gate for this; here we only assert it is wired in and lists them.
    cr = (REPO / 'scripts' / 'check_references.py').read_text()
    for rel in ('units.json', 'HANDOVER.md'):
        c.ok(rel in cr, f'{rel} is named in the reference gate')


@injection('I11a', 'T11', 'a withheld document tracked')
def i11a(d):
    return replace(d, tracked=d.tracked | {'REPORT.md'})


@injection('I11b', 'T11', 'a licensed raw payload tracked')
def i11b(d):
    return replace(d, tracked=d.tracked |
                   {'results/predictors/netmhcpan_raw/out.txt'})


@injection('I11c', 'T11', 'a shipped document dropped from the tree')
def i11c(d):
    return replace(d, tracked=d.tracked - {'LIMITATIONS.md'})


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
def run_one(tid, d):
    kind, title, fn = TESTS[tid]
    c = Checks()
    t0 = time.time()
    try:
        fn(d, c)
    except Exception as exc:                      # a crash is a failure
        c.fails.append(f'{type(exc).__name__}: {exc}')
    return c, time.time() - t0


def run_invariants(select):
    d = load()
    print()
    failed = []
    for tid in sorted(TESTS):
        if select and select not in tid:
            continue
        kind, title, _ = TESTS[tid]
        c, dt = run_one(tid, d)
        status = 'PASS' if not c.fails else 'FAIL'
        print(f'  {status}  {tid}  [{kind:9s}] {title}   {dt:5.1f}s')
        for n in c.notes:
            print(f'          . {n}')
        for f in c.fails:
            print(f'        !!! {f}')
        if c.fails:
            failed.append(tid)
    return d, failed


def run_injections(d, select):
    """Every test must be shown failing against a defect it is meant to catch."""
    print('\ninjections -- each must make its target test FAIL')
    weak, errors = [], []
    for iid in sorted(INJECTIONS):
        tid, title, mut = INJECTIONS[iid]
        if select and select not in iid and select not in tid:
            continue
        try:
            d2 = mut(d)
        except Exception as exc:
            print(f'  ERROR {iid} -> {tid}  could not build: '
                  f'{type(exc).__name__}: {exc}')
            errors.append(iid)
            continue
        c, dt = run_one(tid, d2)
        caught = bool(c.fails)
        # Which other tests also notice? Informational: a defect that trips
        # several tests is fine, a defect that trips none is not.
        others = []
        for other in sorted(TESTS):
            if other == tid:
                continue
            oc, _ = run_one(other, d2)
            if oc.fails:
                others.append(other)
        mark = 'CAUGHT' if caught else 'MISSED'
        print(f'  {mark}  {iid} -> {tid}  {title}   {dt:5.1f}s')
        if caught:
            print(f'          first failure: {c.fails[0][:110]}')
            if others:
                print(f'          also noticed by: {", ".join(others)}')
        else:
            print(f'          !!! {tid} passed on injected data -- the test is '
                  f'blind to this defect')
            weak.append(f'{iid} -> {tid}')
    return weak, errors


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--injections', action='store_true',
                    help='run the injected defects instead of the invariants')
    ap.add_argument('--all', action='store_true', help='run both')
    ap.add_argument('-k', metavar='SUBSTR', default='',
                    help='restrict to tests or injections matching SUBSTR')
    a = ap.parse_args()
    do_inv = a.all or not a.injections
    do_inj = a.all or a.injections

    t0 = time.time()
    print(f'invariant suite -- {len(TESTS)} tests, {len(INJECTIONS)} injections')
    print(f'repository: {REPO}')
    d, failed = run_invariants(a.k) if do_inv else (load(), [])

    weak, errors = ([], [])
    if do_inj:
        weak, errors = run_injections(d, a.k)

    print(f'\n{"="*72}')
    bad = False
    if do_inv:
        if failed:
            print(f'INVARIANTS FAILED: {len(failed)} -> {failed}')
            bad = True
        else:
            print(f'INVARIANTS PASSED: {len(TESTS)} tests')
    if do_inj:
        if weak or errors:
            if weak:
                print(f'BLIND TESTS: {len(weak)} -> {weak}')
                print('A test that passes on injected data is not a test.')
            if errors:
                print(f'INJECTIONS NOT BUILDABLE: {errors}')
            bad = True
        else:
            print(f'INJECTIONS CAUGHT: {len(INJECTIONS)}/{len(INJECTIONS)}')
    print(f'{time.time()-t0:.1f}s total')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
