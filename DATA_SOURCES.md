# DATA_SOURCES

Provenance registry for every input to the PXD024871 mapping project.

**Status:** OPEN — registry schema defined, **no source retrieved**. Every
provenance field below is `PENDING`. This file is the acquisition plan and
becomes the record as each source is retrieved.

> **BLOCKED 2026-10-06 — outbound network policy.** Retrieval of S1 was
> attempted twice (two API versions, 00:32 and 00:59 UTC) and denied both
> times; `ftp.pride.ebi.ac.uk` was also probed and denied. The execution environment's network policy refuses
> `www.ebi.ac.uk:443`; the gateway answers 403 to CONNECT, which surfaces to
> `curl` as HTTP 403. The denial was confirmed independently of the retrieval
> attempt, so it is the policy and not a malformed request or a wrong endpoint.
> The attempt is recorded in `data/raw/S1/provenance.jsonl` with `outcome:
> FAILED`. No retrieval is possible until the policy allows the host; see
> **Blocked retrievals** below.

**Raw data is never modified.** Retrieved files are written once to
`data/raw/<source_id>/`, checksummed, and treated as read-only thereafter.

**The small authoritative inputs are committed; the large payloads are not.**
S1 (manifest, ~690 KB) and S2 (metadata, 318 KB) are in the repository, because
every pipeline stage reads them and excluding them made a fresh clone unable to
run at all. The identification containers are not, because they are 107 GiB and
the repository is not their archive — their provenance records stand in for
them. Committed copies are checksum-verified against their provenance records.
All derived files go to `data/derived/`. No process writes to `data/raw/`
after its initial retrieval and verification.

---

## Required fields

Per master prompt §2, every source records all twelve:

| Field | Definition |
|---|---|
| `source_id` | Internal identifier, stable across the project |
| `origin` | Publishing organisation or repository |
| `accession_or_url` | Accession, or the retrieval URL |
| `version` | Release, revision, or submission version |
| `retrieval_date` | UTC date of retrieval |
| `original_filename` | Filename exactly as published |
| `local_path` | Path under `data/raw/` |
| `checksum` | Our SHA-256, computed on retrieval |
| `file_size` | Bytes, as stored locally |
| `license` | Terms governing reuse |
| `reference` | Citation for the source |
| `acquisition_method` | Exact command or tool used |
| `processing_history` | Ordered list of operations applied, or `NONE` |

---

## Checksum policy

1. **We compute our own SHA-256 for every retrieved file**, regardless of
   whether the publisher provides a hash. The publisher's hash, where present,
   is recorded separately in `published_checksum` with its algorithm.
2. Where both exist, they are **verified against each other** at G1, and both
   are recorded. A mismatch is a G1 FAIL and the file is re-retrieved, not
   accepted.
3. Where the publisher provides no hash, or provides an empty value, this is
   recorded as `published_checksum: ABSENT`. Our own hash still establishes
   internal reproducibility — it proves the file did not change after we
   retrieved it — but it **cannot** establish that we retrieved the file the
   publisher intended. That distinction is recorded per source and carried into
   the limitations section.
4. **Confirmed 2026-10-06.** 503 of 504 deposited files carry a published
   checksum. The one that does not is the metadata file itself — the single
   evidence source for M2, M3 and M4. Its integrity rests on our own SHA-256
   plus one independent agreement: the manifest declares 317,806 bytes and the
   retrieved file is exactly that size. That is weaker than a hash and is
   carried as a limitation (`QC_G1.md`).
5. Algorithm choice: SHA-256 for everything we compute. Published hashes are
   recorded in whatever algorithm the publisher used, with the algorithm named;
   they are not re-expressed or converted.

---

## Source registry

### S1 — File manifest

| Field | Value |
|---|---|
| `source_id` | S1 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING |
| `local_path` | `data/raw/S1/` |
| `checksum` | PENDING |
| `published_checksum` | n/a — API response, not a published file |
| `file_size` | PENDING |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | PENDING — exact command recorded on retrieval |
| `processing_history` | `NONE` |

**Role:** authoritative list of deposited files with their published hashes and
sizes. Left side of M1. Retrieved and stored verbatim, including the raw API
response body, so the manifest itself is auditable rather than only our parse
of it.

**Used by:** M1, M5. **Gate:** G1.

---

### S2 — Sample metadata

| Field | Value |
|---|---|
| `source_id` | S2 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING — community-annotated files are revised; the exact revision retrieved is recorded |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING |
| `local_path` | `data/raw/S2/` |
| `checksum` | PENDING |
| `published_checksum` | PENDING — expected `ABSENT`, see policy item 4 |
| `file_size` | PENDING |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | PENDING |
| `processing_history` | `NONE` |

**Role:** the single most important input. Supplies the right side of M1 and the
entire evidence base for M2, M3, and M4 — unit assignment, class assignment,
and genotype all derive from this one file.

**Risk concentration:** four of the seven mappings depend on this file alone,
and it **does** lack a published checksum (confirmed). It is also
community-annotated rather than depositor-authored, meaning its annotations are
a third-party interpretation of the submission. Both facts are recorded as
limitations. The independent cross-check in `METHODOLOGY.md`, *Independent verification*, exists
specifically because of this concentration.

**Version sensitivity:** because the file may be revised after our retrieval,
the recorded version and our own checksum are what define the analysis. A later
revision does not retroactively change results; it would be a new source entry
and a logged decision.

**Used by:** M1, M2, M3, M4. **Gate:** G1, G2, G3.

---

### S3 — Identification containers

| Field | Value |
|---|---|
| `source_id` | S3 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING — one entry per container retrieved |
| `local_path` | `data/raw/S3/` — transient, see retrieval strategy |
| `checksum` | PENDING — recorded per container **before** extraction |
| `published_checksum` | PENDING |
| `file_size` | PENDING |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | PENDING |
| `processing_history` | Read-only extraction of the identification table; container never modified |

**Role:** source of peptide identifications. Right side of M5, input to M6.

**Retrieval strategy — streaming.** **Verified:** the container set totals
107.53 GiB over 101 files, against a 30 GB working allowance. Per
container: retrieve → verify checksum → extract the identification table to
Parquet → record both checksums in the registry → delete the container.

Peak storage is one container plus its extract, rather than the whole set.

**Not a choice — a constraint.** 30 GB of writable disk (run-002) against a
container set **verified at 107.53 GiB over 101 files**. The full set cannot be
held at once, so streaming is the only feasible route rather than the tidier of
two options. This paragraph originally presented it as a trade; it is not one.

The margin is also thinner than first stated. The largest single container is
**9.25 GiB**, so peak working space is ~12 GiB rather than the ~2 GB claimed
before anything had been measured. Still comfortable against 30 GB, but the
earlier figure was a guess presented as a budget.

**Consequence for reproducibility, stated plainly:** the containers are not
retained. Reproduction re-retrieves them from the publisher and verifies
against the checksums recorded here. This makes our extraction verifiable but
makes the pipeline dependent on the publisher's continued availability. The
recorded checksums are what make the dependency auditable — a future retrieval
that hashes differently is detectable. This is a constraint we are under rather than a trade we made (run-002), and it
is a limitation, not a solved problem.

**Extraction is read-only.** The container is opened for reading; no write
path exists to `data/raw/`.

**Used by:** M5, M6. **Gate:** G3, G4.

---

### S4 — Acquisition files

| Field | Value |
|---|---|
| `source_id` | S4 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING |
| `retrieval_date` | **NOT PLANNED** |
| `local_path` | n/a |
| `checksum` | Published hashes recorded from S1 without retrieval |
| `file_size` | **Verified** 247.31 GiB over 402 files |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | **NOT PLANNED** |
| `processing_history` | n/a |

**Decision: not retrieved.** The identifications in S3 are the required input;
re-deriving them from the acquisition files would be a reprocessing project
with its own search parameters, error model, and decisions — a different study
from the one proposed.

**Consequence:** we inherit the depositor's identification pipeline, including
its search parameters and error-rate control, and cannot audit it. This caps
positive-set purity at whatever that pipeline achieved. It is the reason D004
exists — our only remaining lever is how strictly we re-filter the scores the
containers already contain. Recorded as a limitation.

These files are still registered here, with their published hashes from S1, so
the registry describes the complete submission rather than only the part we
touched.

**Used by:** nothing directly; referenced by M1 and M5 as the entities that
acquisitions and containers refer to.

---

### S5 — Reference background

| Field | Value |
|---|---|
| `source_id` | S5 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING — a dated release, pinned exactly |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING |
| `local_path` | `data/raw/S5/` |
| `checksum` | PENDING |
| `published_checksum` | PENDING |
| `file_size` | PENDING |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | PENDING |
| `processing_history` | `NONE` |

**Conditional on D002.** Required only if the negative construction draws on a
reference background. If D002 selects a construction that does not, this source
is not retrieved and the entry is marked `NOT REQUIRED` with D002 cited.

**Version pinning is mandatory.** Reference releases change between versions,
and a negative set built on an unpinned reference is not reproducible. The exact
release identifier is recorded, not "current" or "latest".

**Used by:** negative construction at S9. **Gate:** G4.

---

### S6 — Comparison predictors

| Field | Value |
|---|---|
| `source_id` | S6 |
| `origin` | PENDING |
| `accession_or_url` | PENDING |
| `version` | PENDING — predictor version affects outputs and is recorded |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING |
| `local_path` | `data/raw/S6/` |
| `checksum` | PENDING |
| `published_checksum` | PENDING |
| `file_size` | PENDING |
| `license` | PENDING — redistribution terms checked before any output is committed |
| `reference` | PENDING |
| `acquisition_method` | PENDING |
| `processing_history` | Applied to the frozen analysis table only |

**Role:** the §18 comparison. Two distinct things are needed and they have
different availability:

1. **Predictor outputs** — obtainable by running each predictor on our frozen
   table.
2. **Predictor training sets** — needed for the M7 contamination check, and
   **not reliably obtainable**. Where a training set cannot be inspected,
   M7 returns `UNVERIFIABLE` and the comparison carries that caveat.

Both are registered separately per predictor, because the first being available
does not imply the second is.

**License check precedes commit.** Some predictor distributions restrict
redistribution of outputs. Checked per predictor before any output file enters
the repository.

**Used by:** M7, §18 comparison. **Gate:** G11.

---

### S7 — Dataset publication

| Field | Value |
|---|---|
| `source_id` | S7 |
| `origin` | PENDING |
| `accession_or_url` | PENDING — DOI |
| `version` | Version of record |
| `retrieval_date` | PENDING |
| `original_filename` | PENDING |
| `local_path` | `data/raw/S7/` |
| `checksum` | PENDING |
| `published_checksum` | n/a |
| `file_size` | PENDING |
| `license` | PENDING |
| `reference` | PENDING |
| `acquisition_method` | PENDING |
| `processing_history` | `NONE` |

**Role:** the independent cross-check for M3 class assignment and the
description of the depositor's identification pipeline that S4's non-retrieval
makes us dependent on. Not a data source for the analysis table; an evidence
source for validating the metadata and for the methods description.

A disagreement between this source and S2 is `CONFLICT` under
`METHODOLOGY.md` M3, *Confidence/status categories* — recorded, not resolved
by preferring either.

**Used by:** G2 independent verification; methods and limitations text.

---

## Blocked retrievals

### Hosts the network policy must allow

| Host | Needed for | Note |
|---|---|---|
| `www.ebi.ac.uk` | S1, S2, S3 | API and file distribution. Confirmed denied 2026-10-06 |
| `ftp.pride.ebi.ac.uk` | S2, S3 | Bulk file distribution; may be the actual transfer host once the manifest is readable. Not yet probed |

Adding `www.ebi.ac.uk` alone may be sufficient for S1 and therefore for
settling the counts. Whether file payloads transfer from that host or from the
FTP host is not knowable until the manifest can be read, so the second host may
also be required for S3.

### S2 is additionally blocked behind S1

Independently of the policy, S2's retrieval URL is **not yet known**. Two
candidate routes exist and they are not equivalent:

1. **From the submission** — if the metadata file is deposited alongside the
   data, its URL comes from the S1 manifest. This route makes S2 part of the
   submission, with whatever checksum the submission carries.
2. **From the community annotation project** — community-annotated metadata is
   maintained in a separate public repository, in which case S2 is a different
   artifact with a different version history, different authorship, and no
   submission checksum at all.

These produce **different provenance records and possibly different file
contents**, so the route is a recorded decision rather than a convenience. It
cannot be settled by guessing a path; it is settled by reading the S1 manifest
and checking whether the file is present in the submission. Guessing a
distribution path would also violate the no-approximate-matching rule in
`METHODOLOGY.md` M1, *Approximate/fuzzy matching rules*, applied to provenance: a file retrieved from an assumed
location has unestablished identity.

Recorded as pending decision **D013**.

### What is not blocked

The retrieval mechanism itself is written and tested on its failure path:
`scripts/retrieve.py` writes to a write-once raw directory, computes our own
SHA-256, verifies a published checksum when one is supplied, and appends a
provenance record for every attempt including failures. Once the policy allows
the host, S1 is a single invocation.

---

## Summary

| ID | Source | Retrieved? | Gates | Blocked by |
|---|---|---|---|---|
| S1 | File manifest | **BLOCKED** | G1 | network policy |
| S2 | Sample metadata | **BLOCKED** | G1–G3 | network policy, then D013 |
| S3 | Identification containers | BLOCKED, streamed when open | G3–G4 | network policy |
| S4 | Acquisition files | **Not planned** | — | decision recorded above |
| S5 | Reference background | Conditional | G4 | D002 |
| S6 | Comparison predictors | PENDING | G11 | D006 |
| S7 | Dataset publication | PENDING | G2 | — |

Nothing in this registry can be retrieved under the current network policy.
**Superseded 2026-10-06:** the policy was opened and S1 and S2 were retrieved.
G1, G2 and G3 have been run (`results/qc/`). The remaining blocked source is
S3, the identification containers.

---

## Processing-history convention

Each derived file records an ordered chain back to its sources:

```
<derived_file>
  ← <stage_id> @ <script>@<commit>  params:<hash>  env:<env_id>
  ← <input_file> [sha256:<...>]
  ← <source_id>  [sha256:<...>]
```

Written to `RUN_LOG.md` at each stage and embedded in the Parquet metadata
where the format permits. The chain, not a narrative description, is what
makes a derived file reproducible.

---

## See also

- `METHODOLOGY.md` — mappings these sources feed
- `DECISION_LOG.md` — D002 gates S5; D006 gates S6
- `SECTIONS.md` — per-section status
- `FLOWCHART.md` — source-to-output dataflow
