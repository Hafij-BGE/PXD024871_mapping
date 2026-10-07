#!/usr/bin/env python3
"""Train the preregistered CNN (§§11-13).

Implements the frozen specification exactly. Nothing here is a free parameter:
topology from §11, encoding from §12, optimiser/grid/selection from §13, seeds
derived per D010.

  --mode selftest   correctness checks only; touches no real data
  --mode cv         grid search over the 5 folds; never reads the test partition
  --mode final      fit the selected config, 5 folds x 5 seeds
  --mode test       read the held-out partition ONCE and compute the endpoint
  --mode transfer   cross-platform transfer (D025) with the matched control (D028)
  --mode allele     dominant-allele-held-out transfer (D001) with its control (D029)

The test partition is guarded: --mode test refuses to run unless a completed
selection record exists naming the configuration, so the endpoint cannot be
computed before selection is finished.
"""

import argparse, csv, gzip, hashlib, json, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

REPO = Path(__file__).resolve().parent.parent
DER, RES = REPO/'data'/'derived', REPO/'results'/'model'
sys.path.insert(0, str(REPO/'scripts'))
from seeds import seed                                    # noqa: E402

AA = 'ACDEFGHIKLMNPQRSTVWY'
IDX = {a: i+1 for i, a in enumerate(AA)}                  # 0 = pad
L = 12
GRID = [{'E': e, 'C': c, 'k': k, 'p': p}
        for e in (16, 32) for c in (32, 64) for k in (3, 5) for p in (0.0, 0.3)]
MAX_EPOCHS, PATIENCE, BATCH, LR = 100, 10, 512, 1e-3


def encode(seqs):
    """§12: integers 1-20, 0 = pad, CENTRE-padded so both termini align.

    LOSSLESS. The first ceil(n/2) residues go at the head, the remaining
    floor(n/2) at the tail, and the L-n pad tokens sit between them. An earlier
    version fixed the head and tail at 4 residues each, which silently discarded
    the middle of every peptide longer than 8 -- 72.9% of the dataset, including
    1 residue from every 9-mer. The selftest now asserts conservation, which is
    the check that would have caught it.
    """
    X = np.zeros((len(seqs), L), dtype=np.int64)
    for i, s in enumerate(seqs):
        n = len(s)
        if n >= L:
            for j, ch in enumerate(s[:L]):
                X[i, j] = IDX.get(ch, 0)
        else:
            h = (n + 1) // 2                      # head keeps the extra residue when n is odd
            for j in range(h):
                X[i, j] = IDX.get(s[j], 0)
            for j in range(h, n):
                X[i, L - (n - j)] = IDX.get(s[j], 0)
    return X


def decode(row):
    """Inverse of encode, used only to assert that encoding loses nothing."""
    inv = {v: k for k, v in IDX.items()}
    return ''.join(inv[v] for v in row if v != 0)


class CNN(nn.Module):
    """§11: embed -> conv -> pool -> conv -> global max -> dropout -> dense -> 1."""
    def __init__(self, E, C, k, p):
        super().__init__()
        self.emb = nn.Embedding(21, E, padding_idx=0)
        pad = k // 2
        self.c1 = nn.Conv1d(E, C, k, padding=pad)
        self.c2 = nn.Conv1d(C, C, k, padding=pad)
        self.pool = nn.MaxPool1d(2)
        self.drop = nn.Dropout(p)
        self.fc1, self.fc2 = nn.Linear(C, 64), nn.Linear(64, 1)
        self.act = nn.ReLU()

    def forward(self, x):
        h = self.emb(x).transpose(1, 2)
        h = self.pool(self.act(self.c1(h)))
        h = self.act(self.c2(h))
        h = h.max(dim=2).values
        return self.fc2(self.act(self.fc1(self.drop(h)))).squeeze(1)


def average_precision(y, s):
    o = np.argsort(-s, kind='stable'); y = y[o]
    tp = np.cumsum(y); k = np.arange(1, y.size+1)
    npos = tp[-1]
    return float(np.sum((tp/k) * y) / npos) if npos else float('nan')


def load():
    rows = []
    for fn, lab in (('POSITIVES.csv', 1), ('NEGATIVES.csv', 0)):
        with (DER/fn).open(newline='') as fh:
            for r in csv.DictReader(fh):
                rows.append((r['sequence'], r['unit_id'], lab))
    split = {r['unit_id']: r for r in csv.DictReader((DER/'SPLIT.csv').open(newline=''))}
    return rows, split


def fit(cfg, tr, va, sd, device, max_epochs=MAX_EPOCHS, log=None):
    torch.manual_seed(sd); np.random.seed(sd % (2**32))
    Xtr, ytr = tr; Xva, yva = va
    m = CNN(**cfg).to(device)
    opt = torch.optim.Adam(m.parameters(), lr=LR)
    lossf = nn.BCEWithLogitsLoss()
    Xtr_t = torch.from_numpy(Xtr).to(device); ytr_t = torch.from_numpy(ytr).float().to(device)
    Xva_t = torch.from_numpy(Xva).to(device)
    best, best_ep, bad, best_state = -1.0, 0, 0, None
    for ep in range(1, max_epochs+1):
        m.train()
        perm = torch.randperm(len(Xtr_t), device=device)
        for i in range(0, len(perm), BATCH):
            b = perm[i:i+BATCH]
            opt.zero_grad()
            lossf(m(Xtr_t[b]), ytr_t[b]).backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            sc = torch.cat([m(Xva_t[i:i+8192]) for i in range(0, len(Xva_t), 8192)]).cpu().numpy()
        ap = average_precision(yva, sc)
        if log is not None: log.append({'epoch': ep, 'val_ap': ap})
        if ap > best:
            best, best_ep, bad = ap, ep, 0
            best_state = {k: v.detach().clone() for k, v in m.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE: break
    m.load_state_dict(best_state)
    return m, best, best_ep


def selftest(device):
    """Correctness only. No project data is read."""
    print("=== §12 encoding ===")
    for s in ('ACDEFGHI', 'ACDEFGHIKLMN', 'ACDEFGHIK'):
        e = encode([s])[0]
        print(f"  {s:<13} -> {e.tolist()}")
    # Conservation first: this is the check whose absence hid a bug that
    # silently deleted residues from 72.9% of the dataset.
    import random as _r
    _rng = _r.Random(0)
    for _ in range(2000):
        n = _rng.randint(8, 12)
        s = ''.join(_rng.choice(AA) for _ in range(n))
        row = encode([s])[0]
        assert decode(row) == s, f"encoding is lossy for {s!r}: got {decode(row)!r}"
        assert int((row != 0).sum()) == n, f"wrong residue count for {s!r}"
    print("  PASS  lossless: 2000 random peptides round-trip exactly, all lengths")

    e8, e12 = encode(['ACDEFGHI'])[0], encode(['ACDEFGHIKLMN'])[0]
    assert e8[0] == e12[0] == IDX['A'], "N-terminus must sit at index 0"
    assert e8[-1] == IDX['I'] and e12[-1] == IDX['N'], "C-terminus must sit at the last index"
    assert 0 in list(e8) and 0 not in list(e12), "padding present only when n < 12"
    mid = encode(['ACDEFGHIK'])[0]
    assert list(mid).count(0) == 3, "an n-mer must carry exactly 12-n pads"
    print("  PASS  both termini align across lengths; padding is central")

    print("\n=== average precision ===")
    y = np.r_[np.ones(100), np.zeros(100)].astype(np.int64)
    assert abs(average_precision(y, np.r_[np.ones(100), np.zeros(100)]) - 1.0) < 1e-9
    rnd = np.mean([average_precision(y, np.random.randn(200)) for _ in range(300)])
    print(f"  perfect 1.0; random {rnd:.3f} (expect ~0.5)  PASS")

    print("\n=== gradient check (torch autograd vs finite differences) ===")
    torch.manual_seed(0)
    m = CNN(E=8, C=8, k=3, p=0.0).double().to(device)
    x = torch.randint(0, 21, (16, L), device=device)
    yt = torch.randint(0, 2, (16,), device=device).double()
    lf = nn.BCEWithLogitsLoss()
    lf(m(x), yt).backward()
    w = m.c1.weight
    g_auto = w.grad.flatten()[:5].clone()
    g_num = []
    for i in range(5):
        eps, flat = 1e-6, w.data.flatten()
        orig = flat[i].item()
        flat[i] = orig + eps; lp = lf(m(x), yt).item()
        flat[i] = orig - eps; lm = lf(m(x), yt).item()
        flat[i] = orig
        g_num.append((lp - lm) / (2*eps))
    g_num = torch.tensor(g_num, dtype=torch.float64, device=device)
    rel = (g_auto - g_num).abs().max() / max(g_num.abs().max().item(), 1e-12)
    print(f"  max relative error {rel:.2e}  {'PASS' if rel < 1e-5 else 'FAIL'}")
    assert rel < 1e-5

    print("\n=== can it overfit 256 separable examples? ===")
    rng = np.random.default_rng(0)
    Xp = rng.integers(1, 21, (128, L)); Xp[:, 1] = IDX['L']; Xp[:, -1] = IDX['V']
    Xn = rng.integers(1, 21, (128, L))
    X = np.vstack([Xp, Xn]); y = np.r_[np.ones(128), np.zeros(128)].astype(np.int64)
    m, ap, ep = fit({'E': 16, 'C': 32, 'k': 3, 'p': 0.0}, (X, y), (X, y),
                    seed('model_init'), device, max_epochs=60)
    print(f"  train-set AP {ap:.4f} after {ep} epochs  "
          f"{'PASS' if ap > 0.95 else 'FAIL — cannot fit a signal it should find'}")
    assert ap > 0.95
    print("\nALL SELFTESTS PASS")



# ----------------------------------------------------------------- D025 / D028

def composition(seqs):
    """20-dim amino-acid frequency, as scripts/negative_diagnostic.py computes it."""
    C = np.zeros((len(seqs), 20), dtype=np.float64)
    for i, s in enumerate(seqs):
        for ch in s:
            j = IDX.get(ch)
            if j is not None:
                C[i, j-1] += 1.0
        C[i] /= max(len(s), 1)
    return C


def lda_scores(Ctr, ytr, Cte):
    """Closed-form LDA direction, as D002's diagnostic used. Optimal linear rule
    under equal covariance, so a low score is evidence about the data rather
    than about an optimiser having failed."""
    m1, m0 = Ctr[ytr == 1].mean(0), Ctr[ytr == 0].mean(0)
    S = np.cov(Ctr.T) + 1e-8*np.eye(20)
    w = np.linalg.solve(S, m1 - m0)
    return Cte @ w


def cluster_ci(vals, rng, B=10000, nominal=0.99):
    """Nominal-99% cluster bootstrap over units (D008). Units are the clusters."""
    v = np.asarray(vals, float)
    reps = v[rng.integers(0, v.size, size=(B, v.size))].mean(axis=1)
    a = (1.0 - nominal) / 2 * 100
    lo, hi = np.percentile(reps, [a, 100-a])
    return float(lo), float(hi)


def paired_ci(d, rng, B=10000, nominal=0.99):
    """Paired cluster bootstrap on per-unit differences (contrast B, D028)."""
    d = np.asarray(d, float)
    reps = d[rng.integers(0, d.size, size=(B, d.size))].mean(axis=1)
    a = (1.0 - nominal) / 2 * 100
    lo, hi = np.percentile(reps, [a, 100-a])
    return float(lo), float(hi)


def transfer(rows, split, device, max_epochs, want_arms, replicates):
    """D025 as preregistered, plus the D028 matched control.

    Nothing here is chosen after a number is seen: halves, validation holdouts
    and weights all come from derived seeds, and the arm list is fixed below.
    """
    import random
    by_plat = {}
    for u, r in sorted(split.items()):
        by_plat.setdefault(r['platform'], []).append(u)
    assert set(by_plat) == {'LTQ', 'Lumos'}, by_plat

    rng_h = random.Random(seed('transfer_halves'))
    half = {}
    for p in ('LTQ', 'Lumos'):
        us = list(by_plat[p]); rng_h.shuffle(us)
        h = (len(us) + 1) // 2
        half[p] = (sorted(us[:h]), sorted(us[h:]))        # (A = train pool, B = test half)

    rng_v = random.Random(seed('transfer_valsplit'))

    def hold_out(pool, n_train):
        """n_train units train; the rest of the pool is the early-stopping set.
        Unit-disjoint, so the stopping epoch is never chosen on rows that share
        a participant with the training rows."""
        us = list(pool); rng_v.shuffle(us)
        return sorted(us[:n_train]), sorted(us[n_train:])

    LTQ, LUM = by_plat['LTQ'], by_plat['Lumos']
    LA, LB = half['LTQ']
    MA, MB = half['Lumos']

    arms = []
    # --- preregistered (D025), verbatim: train one platform, test the other ---
    for src, tgt, sname, tname in (('LTQ', 'Lumos', 'LTQ', 'Lumos'),
                                   ('Lumos', 'LTQ', 'Lumos', 'LTQ')):
        pool = by_plat[src]
        n_val = max(3, round(0.2*len(pool)))
        tr, va = hold_out(pool, len(pool) - n_val)
        arms.append({'id': f'P_{sname}_to_{tname}', 'kind': 'preregistered-D025',
                     'train_platform': src, 'train_units': tr, 'val_units': va,
                     'evals': [{'label': f'across: all {len(by_plat[tgt])} {tgt} units',
                                'rel': 'across', 'platform': tgt,
                                'units': by_plat[tgt]}]})
    # --- matched control (D028): 10 training units each, both B halves scored ---
    for src, pool, own_B, other_B, other in (('LTQ', LA, LB, MB, 'Lumos'),
                                             ('Lumos', MA, MB, LB, 'LTQ')):
        tr, va = hold_out(pool, 10)
        arms.append({'id': f'M_{src}', 'kind': 'matched-D028',
                     'train_platform': src, 'train_units': tr, 'val_units': va,
                     'evals': [{'label': f'within: {src} held-out half',
                                'rel': 'within', 'platform': src, 'units': own_B},
                               {'label': f'across: {other} held-out half',
                                'rel': 'across', 'platform': other, 'units': other_B}]})

    if want_arms:
        keep = set(want_arms.split(','))
        arms = [a for a in arms if a['id'] in keep]

    cfg = json.loads((RES/'selection.json').read_text())['selected']['config']
    print(f"config {cfg} (frozen by selection; not re-tuned here)")
    print(f"halves: LTQ A={len(LA)} B={len(LB)}   Lumos A={len(MA)} B={len(MB)}")
    for a in arms:
        print(f"  {a['id']:<16} train {len(a['train_units'])} {a['train_platform']} units, "
              f"val {len(a['val_units'])}, evals " +
              "; ".join(f"{e['label']} ({len(e['units'])})" for e in a['evals']))
    print()

    seqs = [s for s, _, _ in rows]
    X = encode(seqs)
    y = np.array([l for _, _, l in rows])
    uarr = np.array([u for _, u, _ in rows])
    where = {}
    for i, u in enumerate(uarr):
        where.setdefault(u, []).append(i)
    where = {u: np.array(v) for u, v in where.items()}
    def rowsof(units):
        return np.concatenate([where[u] for u in units])

    C = composition(seqs)                     # for the arm-specific floors

    if max_epochs != MAX_EPOCHS or replicates != 5:
        print(f"*** SHORTENED RUN (max_epochs={max_epochs}, replicates={replicates}). "
              f"Results go to transfer.PARTIAL.json and are not a result. ***\n")
    full = (max_epochs == MAX_EPOCHS and replicates == 5)
    outfile = RES/('transfer.json' if full else 'transfer.PARTIAL.json')
    # Shortened runs keep their own checkpoint namespace, so a plumbing test can
    # never be silently picked up as a cached model by the real run.
    tag = '' if full else f'.e{max_epochs}r{replicates}'
    out = {'config': cfg, 'replicates': replicates, 'max_epochs': max_epochs,
           'halves': {'LTQ': {'A': LA, 'B': LB}, 'Lumos': {'A': MA, 'B': MB}},
           'seeds': {'halves': seed('transfer_halves'),
                     'valsplit': seed('transfer_valsplit'),
                     'bootstrap': seed('transfer_bootstrap')},
           'arms': []}
    prev = outfile
    if prev.exists():
        old = json.loads(prev.read_text())
        out['arms'] = [a for a in old.get('arms', [])
                       if a['id'] not in {x['id'] for x in arms}]

    rng = np.random.default_rng(seed('transfer_bootstrap'))
    per_unit_by_arm = {}

    for ai, arm in enumerate(arms):
        tri, vai = rowsof(arm['train_units']), rowsof(arm['val_units'])
        print(f"=== {arm['id']} ({arm['kind']}) ===", flush=True)
        print(f"  train rows {len(tri):,}  val rows {len(vai):,}", flush=True)
        models, fitlog = [], []
        for r_ in range(replicates):
            sd = seed('transfer_init', ai*10 + r_)
            path = RES/f"transfer_{arm['id']}_s{r_}{tag}.pt"
            if path.exists():
                ck = torch.load(path, map_location='cpu', weights_only=False)
                # A checkpoint fitted under a SHORTENED budget must never be
                # reused by a full run: it is a plumbing test, not a result.
                # Mixing the two is how a partial run gets reported as complete.
                if ck.get('max_epochs') != max_epochs or ck.get('cfg') != cfg:
                    sys.exit(f"REFUSING to reuse {path.name}: it was fitted at "
                             f"max_epochs={ck.get('max_epochs')} cfg={ck.get('cfg')}, "
                             f"this run is max_epochs={max_epochs} cfg={cfg}. "
                             f"Delete it or match the budget.")
                m = CNN(**cfg).to(device); m.load_state_dict(ck['state']); m.eval()
                models.append(m)
                fitlog.append({'replicate': r_, 'seed': sd, 'val_ap': ck['val_ap'],
                               'epochs': ck['epochs'], 'file': path.name, 'cached': True})
                print(f"  seed {r_}: cached (val AP {ck['val_ap']:.4f})", flush=True)
                continue
            t0 = time.time()
            m, vap, ep = fit(cfg, (X[tri], y[tri]), (X[vai], y[vai]), sd, device, max_epochs)
            torch.save({'state': m.state_dict(), 'cfg': cfg, 'seed': sd,
                        'arm': arm['id'], 'replicate': r_, 'val_ap': vap, 'epochs': ep,
                        'max_epochs': max_epochs,
                        'train_units': arm['train_units'], 'val_units': arm['val_units']},
                       path)
            m.eval(); models.append(m)
            fitlog.append({'replicate': r_, 'seed': sd, 'val_ap': vap, 'epochs': ep,
                           'file': path.name, 'cached': False})
            print(f"  seed {r_}: val AP {vap:.4f} ({ep} epochs, {time.time()-t0:.0f}s)",
                  flush=True)

        rec = {'id': arm['id'], 'kind': arm['kind'],
               'train_platform': arm['train_platform'],
               'train_units': arm['train_units'], 'val_units': arm['val_units'],
               'n_train_units': len(arm['train_units']), 'fits': fitlog, 'evals': []}

        for ev in arm['evals']:
            tei = rowsof(ev['units'])
            Xte = torch.from_numpy(X[tei]).to(device)
            S = []
            for m in models:
                with torch.no_grad():
                    S.append(torch.cat([m(Xte[i:i+8192])
                                        for i in range(0, len(Xte), 8192)]).cpu().numpy())
            S = np.vstack(S)
            yte, ute = y[tei], uarr[tei]
            # arm-specific floor: composition-only LDA, same train and test rows
            fl = lda_scores(C[tri], y[tri], C[tei])
            pu, puf = {}, {}
            for u in ev['units']:
                k = ute == u
                if k.sum() == 0 or yte[k].sum() == 0:
                    continue
                pu[u] = float(np.mean([average_precision(yte[k], S[j][k])
                                       for j in range(S.shape[0])]))   # D027
                puf[u] = average_precision(yte[k], fl[k])
            us = sorted(pu)
            v = np.array([pu[u] for u in us])
            vf = np.array([puf[u] for u in us])
            lo, hi = cluster_ci(v, rng)
            flo, fhi = cluster_ci(vf, rng)
            dlo, dhi = paired_ci(v - vf, rng)
            print(f"  {ev['label']}")
            print(f"    units {v.size}  mean per-unit AP {v.mean():.4f}  "
                  f"CI99 [{lo:.4f}, {hi:.4f}]  range {v.min():.4f}-{v.max():.4f}")
            print(f"    arm floor (composition-only LDA) {vf.mean():.4f}  "
                  f"CI99 [{flo:.4f}, {fhi:.4f}]")
            print(f"    lift over own floor {v.mean()-vf.mean():+.4f}  "
                  f"CI99 [{dlo:+.4f}, {dhi:+.4f}]", flush=True)
            rec['evals'].append({
                'label': ev['label'], 'rel': ev['rel'], 'platform': ev['platform'],
                'n_units': int(v.size), 'mean_ap': float(v.mean()),
                'ci99': [lo, hi], 'min': float(v.min()), 'max': float(v.max()),
                'floor_mean_ap': float(vf.mean()), 'floor_ci99': [flo, fhi],
                'lift_over_floor': float(v.mean()-vf.mean()), 'lift_ci99': [dlo, dhi],
                'per_unit': {u: pu[u] for u in us},
                'per_unit_floor': {u: puf[u] for u in us}})
            per_unit_by_arm[(arm['id'], ev['rel'])] = {u: pu[u] for u in us}
        out['arms'].append(rec)
        print()
        out['arms'].sort(key=lambda a: a['id'])
        json.dump(out, open(outfile, 'w'), indent=1)

    # ---- contrasts (D028). Only computable when both matched arms are present.
    out['contrasts'] = []
    idx = {a['id']: a for a in out['arms']}

    def ev_of(arm_id, rel):
        a = idx.get(arm_id)
        if not a:
            return None
        for e in a['evals']:
            if e['rel'] == rel:
                return e
        return None

    # Contrast A: one model, own-platform held-out units vs other-platform units.
    for arm_id in ('M_LTQ', 'M_Lumos'):
        w, ac = ev_of(arm_id, 'within'), ev_of(arm_id, 'across')
        if not (w and ac):
            continue
        vw = np.array([w['per_unit'][u] for u in sorted(w['per_unit'])])
        va = np.array([ac['per_unit'][u] for u in sorted(ac['per_unit'])])
        B = 10000
        rw = vw[rng.integers(0, vw.size, (B, vw.size))].mean(1)
        ra = va[rng.integers(0, va.size, (B, va.size))].mean(1)
        lo, hi = np.percentile(rw - ra, [0.5, 99.5])
        out['contrasts'].append({
            'contrast': 'A — same model, test platform moves', 'arm': arm_id,
            'within_mean': float(vw.mean()), 'across_mean': float(va.mean()),
            'difference': float(vw.mean() - va.mean()),
            'ci99': [float(lo), float(hi)], 'paired': False,
            'note': 'unpaired: the two test sets are different units'})

    # Contrast B: one test half, own-platform model vs other-platform model.
    for half_name, own_arm, other_arm in (('LTQ held-out half', 'M_LTQ', 'M_Lumos'),
                                          ('Lumos held-out half', 'M_Lumos', 'M_LTQ')):
        a_own, a_oth = ev_of(own_arm, 'within'), ev_of(other_arm, 'across')
        if not (a_own and a_oth):
            continue
        us = sorted(set(a_own['per_unit']) & set(a_oth['per_unit']))
        if not us:
            continue
        d = np.array([a_own['per_unit'][u] - a_oth['per_unit'][u] for u in us])
        lo, hi = paired_ci(d, rng)
        out['contrasts'].append({
            'contrast': 'B — same test units, training platform moves',
            'test_set': half_name, 'n_units': len(us),
            'own_platform_model_mean': float(np.mean([a_own['per_unit'][u] for u in us])),
            'other_platform_model_mean': float(np.mean([a_oth['per_unit'][u] for u in us])),
            'difference': float(d.mean()), 'ci99': [lo, hi], 'paired': True,
            'n_units_degraded': int((d > 0).sum())})

    if out['contrasts']:
        print("="*68)
        for c in out['contrasts']:
            print(f"  {c['contrast']}" + (f"  [{c.get('arm') or c.get('test_set')}]"))
            if c['paired']:
                print(f"    own-platform model {c['own_platform_model_mean']:.4f}   "
                      f"other-platform model {c['other_platform_model_mean']:.4f}")
                print(f"    paired difference {c['difference']:+.4f}  "
                      f"CI99 [{c['ci99'][0]:+.4f}, {c['ci99'][1]:+.4f}]  "
                      f"({c['n_units_degraded']}/{c['n_units']} units degraded)")
            else:
                print(f"    within {c['within_mean']:.4f}   across {c['across_mean']:.4f}")
                print(f"    difference {c['difference']:+.4f}  "
                      f"CI99 [{c['ci99'][0]:+.4f}, {c['ci99'][1]:+.4f}] (unpaired)")
        print("="*68)
        print("  A collapse is attributable to platform only when BOTH contrasts")
        print("  agree: A controls for the model, B controls for the test set.")
        print("="*68)

    json.dump(out, open(outfile, 'w'), indent=1)
    print(f"\nwrote {outfile}")



# ------------------------------------------------------------------ D001 / D029

def allele(rows, split, device, max_epochs, want_arms, replicates):
    """D001's split run verbatim, plus the D029 matched pair and stratum.

    The split holds out ONE allele, not a disjoint allele set: 21.7% of a test
    unit's repertoire is unseen, so a real effect arrives attenuated. The
    matched pair tells an allele effect apart from one training set simply
    being better; a single arm cannot.
    """
    import random
    from collections import defaultdict

    car = sorted(u for u, r in split.items() if r['carries_top_allele'] == 'yes')
    non = sorted(u for u, r in split.items() if r['carries_top_allele'] == 'no')
    ad_tr = sorted(u for u, r in split.items() if r['allele_disjoint_partition'] == 'train')
    ad_te = sorted(u for u, r in split.items() if r['allele_disjoint_partition'] == 'test')
    assert set(ad_tr) == set(non) and set(ad_te) == set(car), \
        "the frozen split's allele partition must be exactly carrier vs non-carrier"

    rng_s = random.Random(seed('allele_split'))

    def strat(units, n_first):
        """Platform-stratified draw. D025 made stratification mandatory: at
        0.6451 composition-only separability, an unstratified draw can quietly
        become a platform split and be read as an allele effect."""
        byp = defaultdict(list)
        for u in units:
            byp[split[u]['platform']].append(u)
        first = []
        for pl in sorted(byp):
            lst = sorted(byp[pl]); rng_s.shuffle(lst)
            first += lst[:round(n_first*len(lst)/len(units))]
        rest = [u for u in units if u not in set(first)]; rng_s.shuffle(rest)
        while len(first) < n_first:
            first.append(rest.pop())
        return sorted(first), sorted(u for u in units if u not in set(first))

    C_pool, C_test = strat(car, 15)
    N_pool, N_test = strat(non, 15)

    rng_v = random.Random(seed('allele_valsplit'))
    def hold_out(pool, n_train):
        us = list(pool); rng_v.shuffle(us)
        return sorted(us[:n_train]), sorted(us[n_train:])

    # --- the two strata, defined on the POOLED units only, never the held-out ones
    obs = defaultdict(set)
    for s, u, l in rows:
        if l == 1:
            obs[s].add(u)
    Cp, Np = set(C_pool), set(N_pool)
    cres = {s for s, us in obs.items() if len(us & Cp) >= 2 and not (us & Np)}
    nres = {s for s, us in obs.items() if len(us & Np) >= 2 and not (us & Cp)}
    print(f"strata (defined on the 15+15 pooled units only): "
          f"carrier-restricted {len(cres):,}, non-carrier-restricted {len(nres):,}")

    arms = []
    tr, va = hold_out(ad_tr, len(ad_tr) - 5)
    arms.append({'id': 'P_AD', 'kind': 'preregistered-D001',
                 'train_class': 'non-carrier', 'train_units': tr, 'val_units': va,
                 'evals': [{'label': 'dominant allele unseen: all 29 carriers',
                            'rel': 'mismatched', 'units': ad_te, 'stratum': 'carrier'}]})
    tr, va = hold_out(N_pool, 12)
    arms.append({'id': 'M_AD', 'kind': 'matched-D029', 'train_class': 'non-carrier',
                 'train_units': tr, 'val_units': va,
                 'evals': [{'label': 'mismatched: 14 held-out carriers',
                            'rel': 'mismatched', 'units': C_test, 'stratum': 'carrier'},
                           {'label': 'matched: 8 held-out non-carriers',
                            'rel': 'matched', 'units': N_test, 'stratum': 'noncarrier'}]})
    tr, va = hold_out(C_pool, 12)
    arms.append({'id': 'M_AM', 'kind': 'matched-D029', 'train_class': 'carrier',
                 'train_units': tr, 'val_units': va,
                 'evals': [{'label': 'matched: 14 held-out carriers',
                            'rel': 'matched', 'units': C_test, 'stratum': 'carrier'},
                           {'label': 'mismatched: 8 held-out non-carriers',
                            'rel': 'mismatched', 'units': N_test, 'stratum': 'noncarrier'}]})
    if want_arms:
        keep = set(want_arms.split(','))
        arms = [a for a in arms if a['id'] in keep]

    cfg = json.loads((RES/'selection.json').read_text())['selected']['config']
    print(f"config {cfg} (frozen by selection; not re-tuned here)")
    print(f"C_pool {len(C_pool)}  C_test {len(C_test)}  "
          f"N_pool {len(N_pool)}  N_test {len(N_test)}")
    for a in arms:
        print(f"  {a['id']:<6} train {len(a['train_units'])} {a['train_class']} units, "
              f"val {len(a['val_units'])}, evals " +
              "; ".join(f"{e['label']} [{e['rel']}]" for e in a['evals']))
    print()

    seqs = [s for s, _, _ in rows]
    X, y = encode(seqs), np.array([l for _, _, l in rows])
    uarr = np.array([u for _, u, _ in rows])
    sarr = np.array(seqs, dtype=object)
    where = defaultdict(list)
    for i, u in enumerate(uarr):
        where[u].append(i)
    where = {u: np.array(v) for u, v in where.items()}
    def rowsof(units):
        return np.concatenate([where[u] for u in units])
    C = composition(seqs)

    rng_n = np.random.default_rng(seed('allele_stratum_negatives'))
    def stratum_rows(units, which):
        """Stratum positives plus 1:1 negatives drawn per unit, so average
        precision stays on the primary's scale instead of dropping with
        prevalence. Identical rows for every arm, so pairing holds."""
        S = cres if which == 'carrier' else nres
        out = []
        for u in sorted(units):
            idx = where[u]
            pos = idx[(y[idx] == 1) & np.array([s in S for s in sarr[idx]])]
            neg = idx[y[idx] == 0]
            if len(pos) < 10:
                continue
            out.append(pos)
            out.append(rng_n.choice(neg, size=len(pos), replace=False))
        return np.concatenate(out) if out else np.array([], dtype=int)

    full = (max_epochs == MAX_EPOCHS and replicates == 5)
    outfile = RES/('allele.json' if full else 'allele.PARTIAL.json')
    tag = '' if full else f'.e{max_epochs}r{replicates}'
    if not full:
        print(f"*** SHORTENED RUN (max_epochs={max_epochs}, replicates={replicates}). "
              f"Not a result. ***\n")

    out = {'config': cfg, 'replicates': replicates, 'max_epochs': max_epochs,
           'pools': {'C_pool': C_pool, 'C_test': C_test,
                     'N_pool': N_pool, 'N_test': N_test},
           'strata_sizes': {'carrier_restricted': len(cres),
                            'noncarrier_restricted': len(nres)},
           'seeds': {k: seed(f'allele_{k}') for k in
                     ('split', 'valsplit', 'bootstrap', 'stratum_negatives')},
           'arms': []}
    if outfile.exists():
        old = json.loads(outfile.read_text())
        out['arms'] = [a for a in old.get('arms', [])
                       if a['id'] not in {x['id'] for x in arms}]

    rng = np.random.default_rng(seed('allele_bootstrap'))

    for ai, arm in enumerate(arms):
        tri, vai = rowsof(arm['train_units']), rowsof(arm['val_units'])
        print(f"=== {arm['id']} ({arm['kind']}) ===", flush=True)
        print(f"  train rows {len(tri):,}  val rows {len(vai):,}", flush=True)
        models, fitlog = [], []
        for r_ in range(replicates):
            sd = seed('allele_init', ai*10 + r_)
            path = RES/f"allele_{arm['id']}_s{r_}{tag}.pt"
            if path.exists():
                ck = torch.load(path, map_location='cpu', weights_only=False)
                if ck.get('max_epochs') != max_epochs or ck.get('cfg') != cfg:
                    sys.exit(f"REFUSING to reuse {path.name}: fitted at "
                             f"max_epochs={ck.get('max_epochs')}, this run is "
                             f"{max_epochs}. Delete it or match the budget.")
                m = CNN(**cfg).to(device); m.load_state_dict(ck['state']); m.eval()
                models.append(m)
                fitlog.append({'replicate': r_, 'seed': sd, 'val_ap': ck['val_ap'],
                               'epochs': ck['epochs'], 'file': path.name, 'cached': True})
                print(f"  seed {r_}: cached (val AP {ck['val_ap']:.4f})", flush=True)
                continue
            t0 = time.time()
            m, vap, ep = fit(cfg, (X[tri], y[tri]), (X[vai], y[vai]), sd, device, max_epochs)
            torch.save({'state': m.state_dict(), 'cfg': cfg, 'seed': sd,
                        'arm': arm['id'], 'replicate': r_, 'val_ap': vap,
                        'epochs': ep, 'max_epochs': max_epochs,
                        'train_units': arm['train_units'], 'val_units': arm['val_units']},
                       path)
            m.eval(); models.append(m)
            fitlog.append({'replicate': r_, 'seed': sd, 'val_ap': vap, 'epochs': ep,
                           'file': path.name, 'cached': False})
            print(f"  seed {r_}: val AP {vap:.4f} ({ep} epochs, {time.time()-t0:.0f}s)",
                  flush=True)

        rec = {'id': arm['id'], 'kind': arm['kind'], 'train_class': arm['train_class'],
               'train_units': arm['train_units'], 'val_units': arm['val_units'],
               'n_train_units': len(arm['train_units']), 'fits': fitlog, 'evals': []}

        for ev in arm['evals']:
            for scope, tei in (('all rows', rowsof(ev['units'])),
                               (f"{ev['stratum']}-restricted stratum",
                                stratum_rows(ev['units'], ev['stratum']))):
                if tei.size == 0:
                    print(f"  {ev['label']} / {scope}: EMPTY, skipped")
                    continue
                Xte = torch.from_numpy(X[tei]).to(device)
                S = []
                for m in models:
                    with torch.no_grad():
                        S.append(torch.cat([m(Xte[i:i+8192]) for i in
                                            range(0, len(Xte), 8192)]).cpu().numpy())
                S = np.vstack(S)
                yte, ute = y[tei], uarr[tei]
                fl = lda_scores(C[tri], y[tri], C[tei])
                pu, puf = {}, {}
                for u in sorted(set(ute)):
                    k = ute == u
                    if yte[k].sum() == 0 or yte[k].sum() == k.sum():
                        continue
                    pu[u] = float(np.mean([average_precision(yte[k], S[j][k])
                                           for j in range(S.shape[0])]))
                    puf[u] = average_precision(yte[k], fl[k])
                us = sorted(pu)
                v = np.array([pu[u] for u in us]); vf = np.array([puf[u] for u in us])
                lo, hi = cluster_ci(v, rng)
                flo, fhi = cluster_ci(vf, rng)
                dlo, dhi = paired_ci(v - vf, rng)
                print(f"  {ev['label']}  /  {scope}")
                print(f"    units {v.size}  rows {tei.size:,}  mean per-unit AP "
                      f"{v.mean():.4f}  CI99 [{lo:.4f}, {hi:.4f}]")
                print(f"    arm floor {vf.mean():.4f}   lift {v.mean()-vf.mean():+.4f}  "
                      f"CI99 [{dlo:+.4f}, {dhi:+.4f}]", flush=True)
                rec['evals'].append({
                    'label': ev['label'], 'rel': ev['rel'], 'scope': scope,
                    'units': ev['units'], 'n_units': int(v.size), 'n_rows': int(tei.size),
                    'mean_ap': float(v.mean()), 'ci99': [lo, hi],
                    'min': float(v.min()), 'max': float(v.max()),
                    'floor_mean_ap': float(vf.mean()), 'floor_ci99': [flo, fhi],
                    'lift_over_floor': float(v.mean()-vf.mean()), 'lift_ci99': [dlo, dhi],
                    'per_unit': {u: pu[u] for u in us},
                    'per_unit_floor': {u: puf[u] for u in us}})
        out['arms'].append(rec)
        out['arms'].sort(key=lambda a: a['id'])
        json.dump(out, open(outfile, 'w'), indent=1)
        print()

    # ---- the two paired contrasts (D029). Their SIGNS are what identifies the cause.
    out['contrasts'] = []
    idx = {a['id']: a for a in out['arms']}
    def ev_of(arm_id, rel, scope):
        a = idx.get(arm_id)
        if not a:
            return None
        for e in a['evals']:
            if e['rel'] == rel and e['scope'] == scope:
                return e
        return None

    for cname, test_set, m_arm, x_arm, strat_scope in (
            ('I', 'C_test (14 carriers)', 'M_AM', 'M_AD', 'carrier-restricted stratum'),
            ('II', 'N_test (8 non-carriers)', 'M_AD', 'M_AM', 'noncarrier-restricted stratum')):
        for scope in ('all rows', strat_scope):
            a, b = ev_of(m_arm, 'matched', scope), ev_of(x_arm, 'mismatched', scope)
            if not (a and b):
                continue
            us = sorted(set(a['per_unit']) & set(b['per_unit']))
            if not us:
                continue
            d = np.array([a['per_unit'][u] - b['per_unit'][u] for u in us])
            lo, hi = paired_ci(d, rng)
            out['contrasts'].append({
                'contrast': cname, 'test_set': test_set, 'scope': scope,
                'matched_arm': m_arm, 'mismatched_arm': x_arm, 'n_units': len(us),
                'matched_mean': float(np.mean([a['per_unit'][u] for u in us])),
                'mismatched_mean': float(np.mean([b['per_unit'][u] for u in us])),
                'difference': float(d.mean()), 'ci99': [lo, hi],
                'n_units_positive': int((d > 0).sum())})

    if out['contrasts']:
        print("="*72)
        for c in out['contrasts']:
            print(f"  Contrast {c['contrast']} — {c['test_set']} — {c['scope']}")
            print(f"    matched ({c['matched_arm']}) {c['matched_mean']:.4f}   "
                  f"mismatched ({c['mismatched_arm']}) {c['mismatched_mean']:.4f}")
            print(f"    paired difference {c['difference']:+.4f}  "
                  f"CI99 [{c['ci99'][0]:+.4f}, {c['ci99'][1]:+.4f}]  "
                  f"({c['n_units_positive']}/{c['n_units']} units positive)")
        print("="*72)
        print("  D029 fixed the reading in advance: BOTH contrasts positive is an")
        print("  allele effect; OPPOSITE SIGNS mean one training set is simply")
        print("  better and contrast I alone would have been misread.")
        print("="*72)

    json.dump(out, open(outfile, 'w'), indent=1)
    print(f"\nwrote {outfile}")


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument('--mode', required=True,
                     choices=['selftest', 'cv', 'final', 'test', 'transfer', 'allele'])
    ap_.add_argument('--arms', default='', help='comma-separated arm ids; default all')
    ap_.add_argument('--replicates', type=int, default=5)
    ap_.add_argument('--limit-configs', type=int, default=0)
    ap_.add_argument('--max-epochs', type=int, default=MAX_EPOCHS)
    a = ap_.parse_args()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"torch {torch.__version__}  device {device}  threads {torch.get_num_threads()}")
    RES.mkdir(parents=True, exist_ok=True)

    if a.mode == 'selftest':
        selftest(device); return

    rows, split = load()
    if a.mode == 'test':
        sel = RES/'selection.json'
        if not sel.exists():
            sys.exit("REFUSING: --mode test requires results/model/selection.json. "
                     "The endpoint cannot be computed before model selection is complete.")
    cv = [(s, u, l) for s, u, l in rows if split[u]['primary_partition'] == 'cv']
    print(f"cv rows {len(cv):,}; test rows {len(rows)-len(cv):,} (untouched in this mode)")

    if a.mode == 'cv':
        grid = GRID[:a.limit_configs] if a.limit_configs else GRID
        # Resume: a Colab session can drop mid-grid, and completed configs are
        # deterministic given their seed, so re-running them would only burn
        # time. Partial files from a truncated run are not resumed from -- they
        # carry a different epoch budget and must not be mixed in.
        out, done = [], set()
        prev = RES/'cv_results.json'
        if prev.exists() and a.max_epochs == MAX_EPOCHS and not a.limit_configs:
            out = json.loads(prev.read_text())
            done = {r['config_index'] for r in out}
            print(f"resuming: {len(done)} of {len(grid)} configs already complete")
        for ci, cfg in enumerate(grid):
            if ci in done:
                continue
            aps = []
            for f in range(5):
                tr = [(s, u, l) for s, u, l in cv if int(split[u]['cv_fold']) != f]
                va = [(s, u, l) for s, u, l in cv if int(split[u]['cv_fold']) == f]
                Xtr, ytr = encode([s for s, _, _ in tr]), np.array([l for _, _, l in tr])
                Xva, yva = encode([s for s, _, _ in va]), np.array([l for _, _, l in va])
                t0 = time.time()
                _, ap, ep = fit(cfg, (Xtr, ytr), (Xva, yva), seed('model_init', ci),
                                device, a.max_epochs)
                aps.append(ap)
                print(f"  cfg {ci} {cfg} fold {f}: val AP {ap:.4f} "
                      f"({ep} epochs, {time.time()-t0:.0f}s)", flush=True)
            out.append({'config_index': ci, 'config': cfg, 'fold_val_ap': aps,
                        'mean_val_ap': float(np.mean(aps)),
                        'device': device, 'torch': torch.__version__})
            out.sort(key=lambda r: r['config_index'])
            json.dump(out, open(RES/'cv_results.json', 'w'), indent=1)
        best = max(out, key=lambda r: r['mean_val_ap'])
        # selection.json is what unlocks --mode test, so it is written ONLY by a
        # complete grid at the preregistered epoch budget. A truncated or
        # shortened run is a timing or debugging exercise and must not be able
        # to unlock the held-out partition.
        complete = (len(out) == len(GRID)) and (a.max_epochs == MAX_EPOCHS) and not a.limit_configs
        if complete:
            json.dump({'selected': best, 'grid_size': len(grid),
                       'criterion': 'mean validation average precision across 5 folds',
                       'max_epochs': a.max_epochs},
                      open(RES/'selection.json', 'w'), indent=1)
            print(f"\nselected cfg {best['config_index']} {best['config']} "
                  f"mean val AP {best['mean_val_ap']:.4f}")
        else:
            (RES/'cv_results.json').rename(RES/'cv_results.PARTIAL.json')
            print(f"\nPARTIAL RUN ({len(grid)}/{len(GRID)} configs, "
                  f"{a.max_epochs}/{MAX_EPOCHS} epochs): selection.json NOT written, "
                  f"results renamed to cv_results.PARTIAL.json. The held-out "
                  f"partition stays locked.")


    if a.mode == 'final':
        sel = json.loads((RES/'selection.json').read_text())
        cfg = sel['selected']['config']
        print(f"final fit: {cfg}  (selected on mean validation AP)")
        models = []
        for f in range(5):
            tr = [(s, u, l) for s, u, l in cv if int(split[u]['cv_fold']) != f]
            va = [(s, u, l) for s, u, l in cv if int(split[u]['cv_fold']) == f]
            Xtr, ytr = encode([s for s, _, _ in tr]), np.array([l for _, _, l in tr])
            Xva, yva = encode([s for s, _, _ in va]), np.array([l for _, _, l in va])
            for r_ in range(5):
                sd = seed('model_init', f*5 + r_)
                path = RES/f'final_f{f}_s{r_}.pt'
                if path.exists():
                    # Resumable: each model is deterministic given its seed, so a
                    # completed one is never refit. A dropped session costs at
                    # most the model in flight.
                    ck = torch.load(path, map_location='cpu', weights_only=False)
                    models.append({'fold': f, 'replicate': r_, 'seed': sd,
                                   'val_ap': ck['val_ap'], 'epochs': ck['epochs'],
                                   'file': path.name})
                    print(f"  fold {f} seed {r_}: cached (val AP {ck['val_ap']:.4f})", flush=True)
                    continue
                m, ap, ep = fit(cfg, (Xtr, ytr), (Xva, yva), sd, device, a.max_epochs)
                torch.save({'state': m.state_dict(), 'cfg': cfg, 'seed': sd,
                            'fold': f, 'replicate': r_, 'val_ap': ap, 'epochs': ep}, path)
                models.append({'fold': f, 'replicate': r_, 'seed': sd,
                               'val_ap': ap, 'epochs': ep, 'file': path.name})
                print(f"  fold {f} seed {r_}: val AP {ap:.4f} ({ep} epochs)", flush=True)
        json.dump({'config': cfg, 'models': models,
                   'n_models': len(models)}, open(RES/'final.json', 'w'), indent=1)
        print(f"\nwrote {len(models)} models; none has seen the test partition")

    if a.mode == 'test':
        fin = RES/'final.json'
        if not fin.exists():
            sys.exit("REFUSING: --mode test requires results/model/final.json")
        meta = json.loads(fin.read_text())
        cfg = meta['config']
        test_rows = [(s, u, l) for s, u, l in rows if split[u]['primary_partition'] == 'test']
        units = sorted({u for _, u, _ in test_rows})
        leakfree = {r['sequence'] for r in csv.DictReader((DER/'TEST_LEAKFREE.csv').open(newline=''))}
        print(f"READING THE HELD-OUT PARTITION. {len(test_rows):,} rows, {len(units)} units.")
        print("This is the single preregistered reading of the endpoint.\n")

        X = encode([s for s, _, _ in test_rows])
        y = np.array([l for _, _, l in test_rows])
        unit_of = np.array([u for _, u, _ in test_rows])
        # The leakage-free subset is leakage-free POSITIVES plus ALL test
        # negatives. TEST_LEAKFREE.csv lists only positives by construction, so
        # masking on membership alone selects a set containing no negatives, and
        # average precision on an all-positive set is 1.0 trivially. That is an
        # artefact, not a clean result, and it is exactly what the first run
        # produced before this was corrected.
        clean = np.array([(l == 0) or (s in leakfree) for s, _, l in test_rows])
        Xt = torch.from_numpy(X).to(device)

        scores = []
        for mrec in meta['models']:
            ck = torch.load(RES/mrec['file'], map_location=device, weights_only=False)
            m = CNN(**cfg).to(device); m.load_state_dict(ck['state']); m.eval()
            with torch.no_grad():
                sc = torch.cat([m(Xt[i:i+8192]) for i in range(0, len(Xt), 8192)]).cpu().numpy()
            scores.append(sc)
        S = np.vstack(scores)                       # (25, n)

        def per_unit(mask):
            """mean-across-models per-unit AP (D027), over rows selected by mask"""
            out = {}
            for u in units:
                sel_ = (unit_of == u) & mask
                if sel_.sum() == 0 or y[sel_].sum() == 0:
                    continue
                out[u] = float(np.mean([average_precision(y[sel_], S[k][sel_])
                                        for k in range(S.shape[0])]))
            return out

        rng = np.random.default_rng(seed('bootstrap'))
        def report(name, mask):
            pu = per_unit(mask)
            v = np.array([pu[u] for u in sorted(pu)])
            idx = rng.integers(0, v.size, size=(10000, v.size))
            reps = v[idx].mean(axis=1)
            lo, hi = np.percentile(reps, [0.5, 99.5])      # nominal 99% (D008)
            print(f"  {name}")
            print(f"    units {v.size}   mean per-unit AP {v.mean():.4f}")
            print(f"    nominal-99% CI  [{lo:.4f}, {hi:.4f}]")
            print(f"    per-unit range  {v.min():.4f} - {v.max():.4f}")
            return {'name': name, 'n_units': int(v.size), 'mean_ap': float(v.mean()),
                    'ci99_lo': float(lo), 'ci99_hi': float(hi),
                    'per_unit': {u: pu[u] for u in sorted(pu)}}

        FLOOR, THRESH = 0.597, 0.647
        print(f"floor {FLOOR}  threshold {THRESH} (D008)\n")
        full = report('PRIMARY — full test partition', np.ones(len(y), bool))
        print()
        lf = report('SENSITIVITY — leakage-free subset (D003)', clean)
        ens = float(np.mean([average_precision(y[unit_of == u], S.mean(axis=0)[unit_of == u])
                             for u in units]))
        print(f"\n  SECONDARY — score-ensembled (D027, flattering framing): {ens:.4f}")

        decision = full['ci99_lo'] > THRESH
        print(f"\n{'='*64}")
        print(f"  DECISION (D008): lower bound {full['ci99_lo']:.4f} vs threshold {THRESH}")
        print(f"  -> {'REJECT the null' if decision else 'DO NOT REJECT'}")
        if not decision:
            print("  Not evidence of absent signal: power is 0.42 at AUROC 0.70.")
        print(f"  Inflation from leakage: {full['mean_ap'] - lf['mean_ap']:+.4f}")
        print('='*64)

        json.dump({'floor': FLOOR, 'threshold': THRESH, 'reject_null': bool(decision),
                   'primary': full, 'leakage_free': lf, 'ensemble_secondary': ens,
                   'n_models': S.shape[0], 'config': cfg,
                   'bootstrap': {'B': 10000, 'nominal': 0.99, 'unit': 'participant'}},
                  open(RES/'endpoint.json', 'w'), indent=1)
        print(f"\nwrote {RES/'endpoint.json'}")

    if a.mode == 'transfer':
        if not (RES/'selection.json').exists():
            sys.exit("REFUSING: --mode transfer needs the frozen configuration from "
                     "results/model/selection.json; it does not tune its own.")
        if not (RES/'endpoint.json').exists():
            sys.exit("REFUSING: --mode transfer trains on units that fall inside the "
                     "primary test partition. It must not run before the single "
                     "preregistered endpoint read (results/model/endpoint.json).")
        transfer(rows, split, device, a.max_epochs, a.arms, a.replicates)

    if a.mode == 'allele':
        if not (RES/'selection.json').exists():
            sys.exit("REFUSING: --mode allele needs the frozen configuration from "
                     "results/model/selection.json; it does not tune its own.")
        if not (RES/'endpoint.json').exists():
            sys.exit("REFUSING: --mode allele trains on units inside the primary "
                     "test partition. It must follow the single preregistered read.")
        allele(rows, split, device, a.max_epochs, a.arms, a.replicates)


if __name__ == '__main__':
    main()
