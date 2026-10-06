# Mapping Research — Master Project Prompt

**This is the governing document for the project.** Everything else in this
repository is subordinate to it. Where another file conflicts with this one,
this one wins.

> **Transcription note (added by Claude, not part of the original).**
> Transcribed verbatim from the project brief as supplied at the start of the
> working session on 2026-10-06. Section numbering and line breaks are
> reproduced **as given**, including irregularities: the Mapping Methodology
> and Validation & QC Gates sections carry no number in the original (they sit
> where 3 and 5 would be), and three lines — "Maintain:", "Each gate is:" and
> "Keep progress updates concise:" — introduce content that did not survive
> into the text supplied. These look like artifacts of pasting rather than
> intent, but they have **not** been corrected, because silently repairing a
> source document is exactly what §2 and the Mapping Methodology section
> forbid. Please confirm or replace; see D015.
>
> References elsewhere in this repository of the form "master prompt §N" point
> at the numbered sections below.

---

## 1. Research Structure

Divide the study into logical numbered sections.
For every section record:

Purpose / research question
Why the method is needed
Input and source data
Methodology
Metrics and statistical basis
Expected outcome and interpretation
Limitations
Status: OPEN / RESOLVED / PERMANENT
Next step

Do not proceed to the next major stage until the current stage has passed its QC gate.

## 2. Data & Provenance

Never modify raw data.
For every source record:

source/origin
URL or accession
version/release
retrieval date
original filename
local path
checksum
file size
license
reference
acquisition method
processing history

Maintain:

## Mapping Methodology

Clearly define:
what is being mapped;
source entity;
target entity;
matching criteria;
normalization rules;
exact-match rules;
approximate/fuzzy matching rules;
ambiguity handling;
unmatched records;
duplicate handling;
confidence/status categories.

Never silently force an ambiguous match.
Every mapping decision must be traceable to its evidence.

## 4. Analysis Records

For every meaningful run maintain:

Computational record
Automatically record:

timestamp
code/script/notebook
inputs
outputs
parameters
software versions
random seed
CPU/RAM/GPU
runtime
errors/warnings
metrics

Research record
Record:

purpose
reasoning
interpretation
alternatives considered
limitations
decision
next step

## Validation & QC Gates

Every major mapping stage must have a QC gate.
Check:
input/output counts
missing values
duplicates
unmatched records
unexpected matches
mapping consistency
identifier validity
preprocessing correctness
statistical validity where applicable
reproducibility
expected ranges

Each gate is:

A FAIL blocks progression until corrected or formally accepted as a limitation.
Where possible, validate using an independent source, method, implementation, or reference.

## 6. Results

Generate appropriate:

mapping tables
summary statistics
QC reports
figures
unmatched/ambiguous lists
validation reports

Every output must have:

unique ID
source
method
caption/description
generation code
relevant statistics

Never delete failed or rejected analyses. Record why they were rejected.

## 7. Reproducibility

Maintain a continuously updated:
MANUSCRIPT.md or REPORT.md
with:

Introduction
Methods
Results
Discussion
Limitations
Conclusion
References
Tables/Figures

Every important claim must link to the analysis, data, table, figure, and evidence supporting it.

At completion:

run the full workflow in a clean environment;
verify inputs and checksums;
reproduce key outputs;
compare results;
perform a final data, mapping, statistical, and documentation audit.

## 8. Method Traceability

For every analysis document:
What was done → Why → Method/technique → Code → Environment → Input → Parameters → Output → QC → Interpretation

The complete mapping pathway must be reproducible from the documented files alone.

## 9. Communication

Keep progress updates concise:

Do not proceed blindly. If a mapping strategy, validation method, or project structure can be scientifically improved, explain why, propose the improvement, and record the decision before changing it.
