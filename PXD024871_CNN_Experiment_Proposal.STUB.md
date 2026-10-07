# PXD024871 CNN Experiment Proposal — provenance stub

**The document itself is not in this repository.** It is held privately. This
stub exists so that the references to it elsewhere in this repository resolve
to something verifiable rather than to nothing.

## Why it is absent

The proposal is an internal project document (project **T-A4**) describing an
experiment that, at the time the proposal was written, was *"not yet
preregistered or executed"*. Publishing an unpreregistered internal proposal
alongside the executed, preregistered work it became invites the reading that
the two are the same artifact. They are not: `PREREGISTRATION.md` is the
binding statement, and it was committed before any model was trained (D009).

The decision to withhold it is **D037**. It was taken when this repository was
prepared for public release, by the project owner, not by the analysis.

## What it was

| | |
|---|---|
| Title | PXD024871 CNN Experiment Proposal |
| Project | T-A4 |
| Status at the time | Proposal — not yet preregistered or executed |
| Size | 15970 bytes, 1803 words |
| SHA-256 | `56b690ad9e7a05b8db0d5c641dd251e75b46af0c63028912cd6220cfee71dffe` |
| Last committed as content in | `4350e2809fb4c229134efe2dc68d2a7dc2a7fb57` |

The SHA-256 above is of the exact bytes that were tracked in this repository
up to and including commit `4350e2809fb4c229134efe2dc68d2a7dc2a7fb57`. Anyone holding a copy can confirm it is the
same document by hashing it:

```bash
sha256sum PXD024871_CNN_Experiment_Proposal.md
# 56b690ad9e7a05b8db0d5c641dd251e75b46af0c63028912cd6220cfee71dffe
```

## What it contained, in outline

Headings only, so that a reader can tell what the proposal governed without
the proposal being disclosed:

1. Purpose — define a standalone CNN experiment on PXD024871
2. Primary research question
3. Secondary research questions
4. onward — scope, dataset construction, evaluation, predictor comparison

The one constraint from it that shaped this repository's structure, and which
is reproduced in `METHODOLOGY.md` and the master prompt, is:

> The CNN must not be used to determine which raw files are HLA class-I files
> or which files belong to which donor.

That separation is why provenance and mapping (§1–§7) are closed and gated
before the CNN appears at all (§8 onward).

## What is public, and is enough to audit the work

Nothing in the proposal is load-bearing for any result. The governing and
binding documents are all here:

- `PROJECT_PROMPT.md` — the master prompt, which overrides everything
- `PREREGISTRATION.md` — the committed hypotheses, estimand and artifact hashes
- `METHODOLOGY.md` — what was actually done, stage by stage
- `DECISION_LOG.md` — every decision, including the ones that went wrong
- `REPORT.md` — the findings and their limits

If the proposal and this repository ever disagreed, the preregistration and the
master prompt would win, and did: see D015, D031 and D032 for cases where a
stated plan was changed on the record rather than quietly followed.
