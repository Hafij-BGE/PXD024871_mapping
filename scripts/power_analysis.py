#!/usr/bin/env python3
"""Resolution and power analysis for the PXD024871 CNN experiment.

Question this answers
---------------------
Proposal section 16 makes the participant the resampling unit and section 25
claims generalization to unseen participants. Uncertainty on such a claim is
bounded by the number of held-out participants and by how much performance
varies between them -- not by the number of peptides and not by B. This script
quantifies that bound by simulation, so that the decision rule in D008 and the
minimum-N gate in D007 can be set against a number rather than a hope.

Model
-----
Binormal score model, the standard generative model for ROC analysis.
For participant i, a latent discrimination d_i ~ Normal(d_bar, tau^2).
Positive peptides score ~ Normal(d_i, 1); negatives score ~ Normal(0, 1).
Per-participant AUROC is Phi(d_i / sqrt(2)).

tau is the between-participant SD of discrimination. It is the parameter that
governs resolution and it is UNKNOWN until data exist, so it is swept rather
than assumed. Peptide counts per participant are unbalanced, reconstructed to
match the described acquisition-count marginals (see RUNS_PER_PARTICIPANT).

Estimator
---------
Primary estimand is the mean per-participant average precision -- the
participant-level quantity section 17 asks for. Uncertainty by cluster
bootstrap resampling participants with replacement.

Everything here is a simulation under an assumed model. It bounds what the
design can resolve; it says nothing about what the CNN will actually achieve.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "power"

SEED = 20261006

# Reconstruction consistent with the described marginals: 52 participants,
# 222 acquisitions, per-participant range 3-15, 29 participants at exactly 3.
# This is a RECONSTRUCTION, not the observed distribution. It is replaced by
# the real counts once S1/S2 are retrieved.
RUNS_PER_PARTICIPANT = np.array(
    [3] * 29 + [4] * 8 + [5] * 6 + [6] * 4 + [8] * 2 + [9] * 2 + [15] * 1
)

POS_PER_RUN = 40          # positives yielded per acquisition; swept in scenario B
N_SIM = 250               # simulated studies per grid cell
B_BOOT = 2000             # bootstrap replicates
ALPHA = 0.05


def average_precision(y, s):
    """Empirical average precision; equals sklearn's average_precision_score."""
    order = np.argsort(-s, kind="stable")
    y = y[order]
    tp = np.cumsum(y)
    k = np.arange(1, y.size + 1)
    precision = tp / k
    npos = tp[-1]
    if npos == 0:
        return np.nan
    return float(np.sum(precision * y) / npos)


_T = np.linspace(-12.0, 12.0, 8001)
_SF_T = norm.sf(_T)                     # survival at threshold, independent of d
_PHI_CACHE = {}


def _ap_many(ds, pi):
    """Asymptotic AP under the binormal model for an array of d, at prevalence pi.

    AP = integral precision(t) dTPR, dTPR = phi(t - d) dt. Vectorised over d in
    chunks so the (len(ds), len(_T)) intermediate stays small.
    """
    ds = np.atleast_1d(np.asarray(ds, dtype=float))
    out = np.empty(ds.size)
    chunk = max(1, int(4_000_000 // _T.size))
    for a in range(0, ds.size, chunk):
        d = ds[a:a + chunk][:, None]
        shifted = _T[None, :] - d
        tpr = norm.sf(shifted)
        num = pi * tpr
        den = num + (1.0 - pi) * _SF_T[None, :]
        prec = np.where(den > 1e-300, num / np.maximum(den, 1e-300), 1.0)
        out[a:a + chunk] = np.trapezoid(prec * norm.pdf(shifted), _T, axis=1)
    return out


def true_ap(d, pi):
    """Asymptotic average precision at discrimination d and prevalence pi."""
    return float(_ap_many([d], pi)[0])


def estimand(d_bar, tau, pi, m=1200):
    """Population mean per-participant AP: E_d[true_ap(d, pi)], d ~ N(d_bar, tau^2).

    Cached: depends only on (d_bar, tau, pi), so the grid recomputes it once
    per distinct combination rather than once per cell.
    """
    key = (round(float(d_bar), 10), round(float(tau), 10), round(float(pi), 12), m)
    if key in _PHI_CACHE:
        return _PHI_CACHE[key]
    if tau <= 0:
        val = true_ap(d_bar, pi)
    else:
        q = (np.arange(m) + 0.5) / m
        val = float(np.mean(_ap_many(d_bar + tau * norm.ppf(q), pi)))
    _PHI_CACHE[key] = val
    return val


def simulate_study(K, d_bar, tau, ratio, pos_per_run, rng):
    """Return per-participant AP for one simulated held-out set of K participants."""
    runs = rng.choice(RUNS_PER_PARTICIPANT, size=K, replace=False) \
        if K <= RUNS_PER_PARTICIPANT.size else \
        rng.choice(RUNS_PER_PARTICIPANT, size=K, replace=True)
    d = d_bar + tau * rng.standard_normal(K)
    aps = np.empty(K)
    for i in range(K):
        npos = max(int(runs[i] * pos_per_run), 10)
        nneg = max(int(npos * ratio), 10)
        s = np.concatenate([
            d[i] + rng.standard_normal(npos),
            rng.standard_normal(nneg),
        ])
        y = np.concatenate([np.ones(npos), np.zeros(nneg)])
        aps[i] = average_precision(y, s)
    return aps


def cluster_bootstrap(aps, B, rng):
    """Percentile CI on the mean per-participant AP, resampling participants."""
    K = aps.size
    idx = rng.integers(0, K, size=(B, K))
    reps = aps[idx].mean(axis=1)
    lo, hi = np.percentile(reps, [100 * ALPHA / 2, 100 * (1 - ALPHA / 2)])
    return float(lo), float(hi)


def run_cell(K, tau, ratio, d_bar, pos_per_run, rng, n_sim=N_SIM, B=B_BOOT):
    pi = 1.0 / (1.0 + ratio)
    target = estimand(d_bar, tau, pi)
    half, covered, rejected, point = [], 0, 0, []
    for _ in range(n_sim):
        aps = simulate_study(K, d_bar, tau, ratio, pos_per_run, rng)
        lo, hi = cluster_bootstrap(aps, B, rng)
        half.append((hi - lo) / 2.0)
        point.append(aps.mean())
        if lo <= target <= hi:
            covered += 1
        if lo > pi:                      # reject "no better than prevalence"
            rejected += 1
    return {
        "K": K, "tau": tau, "neg_per_pos": ratio, "prevalence": pi,
        "d_bar": d_bar, "auroc_mean": float(norm.cdf(d_bar / np.sqrt(2))),
        "pos_per_run": pos_per_run,
        "estimand_ap": target,
        "ap_lift_over_prevalence": target - pi,
        "mean_point_estimate": float(np.mean(point)),
        "mean_ci_halfwidth": float(np.mean(half)),
        "halfwidth_as_frac_of_lift": float(np.mean(half) / max(target - pi, 1e-12)),
        "coverage_nominal_95": covered / n_sim,
        "power_vs_prevalence": rejected / n_sim,
        "n_sim": n_sim, "B": B,
    }


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []

    # ---- Grid 1: resolution vs held-out participant count ------------------
    d_bar = float(np.sqrt(2) * norm.ppf(0.80))        # mean per-participant AUROC 0.80
    Ks = [5, 8, 10, 13, 16, 26]
    taus = [0.10, 0.25, 0.50]
    ratios = [1, 10, 100]
    total = len(Ks) * len(taus) * len(ratios)
    n = 0
    for ratio in ratios:
        for tau in taus:
            for K in Ks:
                n += 1
                r = run_cell(K, tau, ratio, d_bar, POS_PER_RUN, rng)
                r["grid"] = "main"
                rows.append(r)
                print(f"[{n}/{total}] ratio=1:{ratio} tau={tau} K={K} "
                      f"half={r['mean_ci_halfwidth']:.4f} "
                      f"cov={r['coverage_nominal_95']:.2f} "
                      f"pow={r['power_vs_prevalence']:.2f}", file=sys.stderr, flush=True)

    # ---- Grid 2: effect size sweep at a realistic held-out count -----------
    for auroc in [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]:
        db = float(np.sqrt(2) * norm.ppf(auroc))
        for tau in [0.25]:
            for ratio in [10]:
                r = run_cell(10, tau, ratio, db, POS_PER_RUN, rng)
                r["grid"] = "effect_sweep_K10"
                rows.append(r)
                print(f"[effect] auroc={auroc} pow={r['power_vs_prevalence']:.2f} "
                      f"half={r['mean_ci_halfwidth']:.4f}", file=sys.stderr, flush=True)

    # ---- Grid 3: does B matter? -------------------------------------------
    bdemo = []
    for K in [10, 26]:
        for B in [200, 1000, 2000, 10000, 50000]:
            r = run_cell(K, 0.25, 10, d_bar, POS_PER_RUN, rng, n_sim=120, B=B)
            r["grid"] = "B_demo"
            bdemo.append(r)
            print(f"[B] K={K} B={B} half={r['mean_ci_halfwidth']:.4f}",
                  file=sys.stderr, flush=True)
    rows.extend(bdemo)

    # ---- Grid 4: paired comparison MDE (section 18) ------------------------
    # Two predictors scored on the SAME peptides, sharing the participant
    # effect u_i (a participant easy for one is easy for the other) with
    # independent score noise. Paired bootstrap on the per-participant
    # difference in AP. Shared u_i is an assumption, stated not derived.
    paired = []
    for K in [5, 10, 16, 26]:
        for delta_d in [0.05, 0.10, 0.20, 0.35, 0.55]:
            tau, ratio, pi = 0.25, 10, 1.0 / 11.0
            rej, diffs, n_paired = 0, [], 150
            for _ in range(n_paired):
                runs = rng.choice(RUNS_PER_PARTICIPANT, size=K, replace=K > 52)
                u = tau * rng.standard_normal(K)
                dd = np.empty(K)
                for i in range(K):
                    npos = max(int(runs[i] * POS_PER_RUN), 10)
                    nneg = max(int(npos * ratio), 10)
                    y = np.concatenate([np.ones(npos), np.zeros(nneg)])
                    dA = d_bar + u[i]
                    dB = d_bar + u[i] + delta_d
                    sA = np.concatenate([dA + rng.standard_normal(npos),
                                         rng.standard_normal(nneg)])
                    sB = np.concatenate([dB + rng.standard_normal(npos),
                                         rng.standard_normal(nneg)])
                    dd[i] = average_precision(y, sB) - average_precision(y, sA)
                idx = rng.integers(0, K, size=(B_BOOT, K))
                reps = dd[idx].mean(axis=1)
                lo = np.percentile(reps, 100 * ALPHA / 2)
                diffs.append(dd.mean())
                if lo > 0:
                    rej += 1
            row = {"grid": "paired_mde", "K": K, "tau": tau, "neg_per_pos": ratio,
                   "prevalence": pi, "delta_d": delta_d,
                   "mean_ap_difference": float(np.mean(diffs)),
                   "power_paired": rej / n_paired, "n_sim": n_paired, "B": B_BOOT}
            paired.append(row)
            print(f"[paired] K={K} dd={delta_d} dAP={row['mean_ap_difference']:.4f} "
                  f"pow={row['power_paired']:.2f}", file=sys.stderr, flush=True)
    rows.extend(paired)

    # ---- write ------------------------------------------------------------
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "power_grid.csv", "w") as fh:
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join("" if r.get(k) is None else str(r.get(k, "")) for k in keys) + "\n")

    with open(OUT / "power_params.json", "w") as fh:
        json.dump({
            "seed": SEED, "n_sim": N_SIM, "B_boot": B_BOOT, "alpha": ALPHA,
            "pos_per_run": POS_PER_RUN,
            "runs_per_participant_reconstruction": RUNS_PER_PARTICIPANT.tolist(),
            "runs_total": int(RUNS_PER_PARTICIPANT.sum()),
            "participants_total": int(RUNS_PER_PARTICIPANT.size),
            "model": "binormal; d_i ~ N(d_bar, tau^2); pos ~ N(d_i,1); neg ~ N(0,1)",
            "estimand": "mean per-participant average precision",
            "uncertainty": "cluster bootstrap resampling participants, percentile CI",
            "numpy": np.__version__,
            "note": "runs_per_participant is a RECONSTRUCTION of described "
                    "marginals, not observed data; replace after S1/S2 retrieval",
        }, fh, indent=2)

    print(f"\nwrote {OUT/'power_grid.csv'} ({len(rows)} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
