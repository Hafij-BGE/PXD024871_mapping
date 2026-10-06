# HANDOVER — extraction moves to Colab

**Date:** 2026-10-06 · **Reason:** cloud-session credit, not a technical blocker.

## State

| | |
|---|---|
| Units extracted | **7 of 52** (committed, gzipped) |
| Remaining | 45 containers, ~45 GiB |
| Containers on local disk | none — all streamed and deleted |
| Partial transfers | none — the in-flight container was removed, not kept |
| Gates passed | G1, G2, G3 (except M5, see `QC_G3_pilot.md`) |

## Why it moved

This session consumed **$50.05** of a $100 cloud-session allowance in ~11 hours.
The cost is per-turn and scales with context, which reached 451k tokens — roughly
$0.70 per turn. An 8-hour supervised transfer would have spent most of the
remaining $49 watching a progress bar, with the stages that actually need a
capable model (G4 onward) still ahead.

The transfer itself is free; supervising it is not. Colab costs no Claude credit
and its bandwidth to EBI is likely well above the 1.6 MiB/s measured here.

## Resume

Open `notebooks/colab_runner.ipynb` in Colab on a **CPU runtime**. Add a GitHub
token with `repo` scope to Colab Secrets as `GH_TOKEN`. Run the cells.

`scripts/batch_extract.py` resumes automatically: it skips the 7 completed units,
reconciles any half-transferred container, and verifies every publisher checksum
before extraction. Re-running after a dropped session is safe and expected.

## After extraction

G4 is the next gate and needs two decisions closed first: **D002** (negative
strategy and class ratio) and **D004** (confidence threshold, which run-004
showed is nearly a no-op at the unique-sequence level and should be re-framed
around the score table). Both are preregistration-gated and should not be run
from a notebook cell.

**Training wants the T4**, as a separate `env_id`, after re-running
`scripts/benchmark_compute.py` on that hardware — §14's limits came from CPU
throughput and do not port.

## Known open issues

- **M5's specified join path fails** (`results/qc/QC_G3_pilot.md`). Survivable
  only because the unit is the participant; attribution rests on the container
  filename, corroborated 1:1 against the 52 metadata unit ids.
- **Instrument is completely confounded with unit** (D005), accepted as a
  limitation. No split over units can separate the two.
- **run-001 needs re-running** on the observed run distribution.
- **§14 is arithmetically consistent but was not executable on CPU here** (D022).
