#!/usr/bin/env python3
"""Deterministic per-purpose seeds derived from one project base seed.

Using one seed everywhere is reproducible but couples unrelated draws: the
per-unit subsample and the split would share a stream, so a change to one
silently reshuffles the other, and any accidental alignment between them is
undetectable. Deriving a seed per purpose keeps every draw reproducible and
independent.

    seed('split')  ->  stable integer, unchanged across runs and machines

BASE is the date the preregistration was first drafted, per D010. It is never
changed. A sensitivity analysis over seeds uses seed(purpose, replicate=n) and
reports every replicate -- selecting the best is seed shopping, which D010
prohibits.
"""

import hashlib

BASE = 20261006


def seed(purpose: str, replicate: int = 0) -> int:
    """Stable 32-bit seed for a named purpose. Pure function of its arguments."""
    key = f"{BASE}:{purpose}:{replicate}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:4], "big")


if __name__ == "__main__":
    for p in ("subsample", "split", "bootstrap", "model_init", "negative_sampling"):
        print(f"  {p:<18} {seed(p)}")
    print(f"\n  split replicate 1  {seed('split', 1)}")
    print(f"  split replicate 2  {seed('split', 2)}")
