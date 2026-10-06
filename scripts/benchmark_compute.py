#!/usr/bin/env python3
"""Measure this machine's throughput on the proposal's CNN architecture.

Purpose: set the section 14 compute gate against a measurement rather than an
assumption. Implements the forward pass of the section 11 architecture with
im2col convolutions over BLAS, times it at several batch sizes, and derives
per-epoch and grid-level wall clock.

Conservative by construction. This is numpy over BLAS, not an optimised deep
learning framework, so it measures the same GEMMs and the same memory movement
with none of a framework's kernel fusion. A real framework should be faster, so
a budget set from these numbers has headroom rather than a shortfall. Treated
as an upper bound on time, not a forecast.

Training cost is taken as 3x the forward pass, the standard approximation for
forward plus backward.
"""

import json, platform, time
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "results" / "compute"
SEED = 20261006

L, E, C1, C2, D, K = 12, 32, 64, 64, 64, 3   # length, embed, conv1, conv2, dense, kernel
ALPHABET = 21                                 # 20 residues + pad
BATCHES = (256, 1024, 4096)
REPS = 20


def build(rng):
    return {
        "emb": rng.standard_normal((ALPHABET, E)).astype(np.float32),
        "w1": rng.standard_normal((K * E, C1)).astype(np.float32) * 0.1,
        "w2": rng.standard_normal((K * C1, C2)).astype(np.float32) * 0.1,
        "w3": rng.standard_normal((C2, D)).astype(np.float32) * 0.1,
        "w4": rng.standard_normal((D, 1)).astype(np.float32) * 0.1,
    }


def im2col(x, k):
    b, lx, c = x.shape
    lout = lx - k + 1
    s0, s1, s2 = x.strides
    view = np.lib.stride_tricks.as_strided(x, (b, lout, k, c), (s0, s1, s1, s2))
    return np.ascontiguousarray(view).reshape(b * lout, k * c), lout


def forward(idx, p):
    b = idx.shape[0]
    h = p["emb"][idx]
    col, lo = im2col(h, K)
    h = (col @ p["w1"]).reshape(b, lo, C1)
    np.maximum(h, 0, out=h)
    h = h[:, : lo // 2 * 2, :].reshape(b, lo // 2, 2, C1).max(axis=2)
    col, lo2 = im2col(h, K)
    h = (col @ p["w2"]).reshape(b, lo2, C2)
    np.maximum(h, 0, out=h)
    h = h.max(axis=1) @ p["w3"]
    np.maximum(h, 0, out=h)
    z = h @ p["w4"]
    return np.where(z >= 0, 1 / (1 + np.exp(-np.abs(z))), np.exp(-np.abs(z)) / (1 + np.exp(-np.abs(z))))


def main():
    rng = np.random.default_rng(SEED)
    p = build(rng)
    OUT.mkdir(parents=True, exist_ok=True)

    per_batch = {}
    for b in BATCHES:
        idx = rng.integers(0, ALPHABET, size=(b, L)).astype(np.int32)
        forward(idx, p)
        t0 = time.perf_counter()
        for _ in range(REPS):
            forward(idx, p)
        dt = (time.perf_counter() - t0) / REPS
        per_batch[b] = {"ms_per_batch": dt * 1e3, "peptides_per_sec": b / dt}
        print(f"  batch {b:>5}: {dt*1e3:>8.2f} ms  {b/dt:>12,.0f} peptides/s")

    fwd = max(v["peptides_per_sec"] for v in per_batch.values())
    train = fwd / 3.0
    print(f"\n  forward  {fwd:,.0f} peptides/s")
    print(f"  training {train:,.0f} peptides/s (fwd+bwd, 3x)")

    scenarios = {}
    for npos in (10_000, 50_000, 100_000):
        for ratio in (1, 10):
            rows = npos * (1 + ratio)
            spe = rows / train
            scenarios[f"{npos}_1to{ratio}"] = {
                "positives": npos, "neg_per_pos": ratio, "rows": rows,
                "sec_per_epoch": spe,
                "min_per_100ep_run": spe * 100 / 60,
                "hours_20cfg_5fold": spe * 100 * 20 * 5 / 3600,
            }

    rec = {
        "seed": SEED,
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown",
            "cores": __import__("os").cpu_count(),
            "gpu": None,
        },
        "architecture": {"length": L, "embed": E, "conv1": C1, "conv2": C2,
                         "dense": D, "kernel": K, "alphabet": ALPHABET},
        "numpy": np.__version__,
        "per_batch": {str(k): v for k, v in per_batch.items()},
        "forward_peptides_per_sec": fwd,
        "training_peptides_per_sec": train,
        "scenarios": scenarios,
        "method": "numpy/BLAS im2col forward pass; training = 3x forward",
        "caveat": "conservative: no framework kernel fusion, so a real "
                  "framework should be faster. Upper bound on time.",
    }
    (OUT / "benchmark.json").write_text(json.dumps(rec, indent=2))
    print(f"\nwrote {OUT/'benchmark.json'}")


if __name__ == "__main__":
    main()
