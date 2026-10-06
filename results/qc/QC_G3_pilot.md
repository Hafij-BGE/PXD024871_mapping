# QC_G3 addendum — S3 pilot (one container)

Pilot before committing the bulk transfer, per the staging rule: extract a
sample, measure yield, evaluate D007, then commit. Container
`UPN03_class_I.msf` (343 MiB, smallest class-I), run-004.

| Result | Check | Detail |
|---|---|---|
| PASS | Publisher checksum verified | SHA-1 matched — the first source with publisher-side integrity; the metadata file had none |
| PASS | Container readable | SQLite, 72 tables, standard Proteome Discoverer schema |
| PASS | Stream-extract-delete cycle | Downloaded, verified, extracted 49,373 sequences, container deleted; peak disk 343 MiB |
| PASS | Run count corroborates M2 | `FileInfos` holds 3 rows; `UNITS.csv` gives UPN03 3 runs |
| **FAIL** | **M5 primary join path** | Internal run references do not match deposited filenames. Zero intersection |
| PASS | Length window | All 87,026 PSMs already fall in 8–12; the deposited search was pre-restricted |

## M5 fails as specified, and why

`METHODOLOGY.md` M5 specifies the primary path as reading the container's own
record of input spectrum files and joining on normalized basename. That path
**does not work for this submission**:

| Source | Value |
|---|---|
| Deposited | `UPN03_class_I_Rep1.RAW`, `…Rep2.RAW`, `…Rep3.RAW` |
| Container-internal | `121109_DK_CLL08_W_20%_Rep#1_msms5.RAW`, `121114_DK_CLL08_W_20%_Rep#2_msms1.RAW`, `121123_DK_CLL08_W_20%_Rep#3_msms12.RAW` |
| Intersection on normalized basename | **0 of 3** |

The deposited files were **renamed** from the lab originals. Worse, the internal
names carry a **different participant identifier scheme**: this container is
`UPN03` but its internal references say `CLL08`. No cross-walk between the two
schemes exists anywhere in the retrieved metadata.

**Consequences.**

1. Run-level attribution of peptides is **not** recoverable by the specified
   method. A fallback must be used and recorded as `PARTIAL`.
2. The only container-to-unit link is the container filename stem, which is
   corroborated 1:1 against the 52 metadata-derived unit IDs (52/52, zero
   mismatches both directions). That corroboration is evidence, not inference,
   but the attribution still rests on a filename and must carry reduced status.
3. If any container were misnamed during deposition, **we could not detect it.**
   Nothing in the retrieved metadata provides an independent check.
4. Anyone linking these results back to the source publication's figures needs
   the UPN-to-CLL cross-walk, which is not in the deposit.

**This is survivable because of D011.** The unit is the participant, so the
analysis never requires run-level attribution — only unit-level, which the
corroborated container stem supplies. Had the design resampled runs, this
failure would have been blocking.

## Yield, and what it does to two earlier decisions

| Measure | Value |
|---|---|
| Unique 8–12mers, this unit | 49,373 |
| Per run | ~16,458 |
| At confidence level 1 only | 49,105 — **99.5%** |

**D007 is cleared by a wide margin.** 222 class-I runs at this rate give ~3.65M
observations before deduplication; even at 85% cross-unit redundancy the union
is ~548,000 unique sequences. The minimum-N gate passes on any assumption.

**D004's lever is nearly a no-op at the unique-sequence level.** Restricting to
the highest confidence level removes 0.5% of unique sequences. Re-filtering is
therefore not the purity control it was assumed to be, and the decision should
be re-framed around the score fields in `PeptideScores` rather than
`ConfidenceLevel`.

**run-001 assumed 40 positives per run. The real figure is ~16,458 — off by
411×.** Its dataset-size scenarios were far too small.

**The §14 compute gate is breached.** It was sized at a 100,000-positive worst
case, giving a 25-hour grid against a 48-hour cap. At a plausible 300,000–500,000
the grid is 75–125 hours. The budget needs resizing or the reduction ladder
triggers immediately — this is exactly the re-check §14's *Next Step* called for.

## Transfer cost of the full set

Measured 343 MiB in 3m48s, ~1.5 MiB/s. The class-I subset is 52 containers and
**47.85 GiB**, so roughly **9 hours** at that rate. The session container is
ephemeral, so an unattended multi-hour transfer risks losing everything not
already committed.

Note the class-I subset size, 47.85 GiB, matches the figure originally supplied
in conversation. D021 characterised that figure as wrong; it was not — it was
scoped to class-I, while the 107.53 GiB measured covers all 101 containers.
D021 is corrected accordingly.
