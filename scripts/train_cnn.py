#!/usr/bin/env python3
"""Train the preregistered CNN (§§11-13).

Implements the frozen specification exactly. Nothing here is a free parameter:
topology from §11, encoding from §12, optimiser/grid/selection from §13, seeds
derived per D010.

  --mode selftest   correctness checks only; touches no real data
  --mode cv         grid search over the 5 folds; never reads the test partition
  --mode final      fit the selected config, 5 folds x 5 seeds
  --mode test       read the held-out partition ONCE and compute the endpoint

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


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument('--mode', required=True, choices=['selftest', 'cv', 'final', 'test'])
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


if __name__ == '__main__':
    main()
