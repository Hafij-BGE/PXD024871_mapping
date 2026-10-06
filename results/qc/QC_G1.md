# QC_G1 — Retrieval and inventory

| Result | Check | Detail |
|---|---|---|
| PASS | Manifest complete | 504 file records across 6 pages |
| PASS | No duplicate accessions | 504 unique |
| PASS | Categories enumerated | 402 RAW, 101 SEARCH, 1 EXPERIMENTAL DESIGN |
| PASS | M1 both directions | 402 matched; 0 manifest-only; 0 metadata-only |
| PASS | M1 rejects empty | 0 rejects |
| PASS | Out-of-scope enumerated | 102 non-acquisition files: msf, tsv |
| PASS | Published checksums | 503/504 present; 1 absent (the metadata file itself) |
| PASS | Our own checksums | recorded for every retrieved file in data/raw/*/provenance.jsonl |
| PASS | Declared vs actual size | metadata file 317,806 bytes on disk matches manifest fileSizeBytes |

**Note on the API.** `pageSize=1000` is silently capped at 100 and returns a
bare list with no total count, so a single naive request looks complete and is
not. Six explicit page requests were required. Recorded because it is a trap
for anyone reproducing this.

**Absent checksum.** The metadata file is the one input with no publisher hash,
and it is the sole evidence source for M2, M3 and M4. Its integrity rests on our
own SHA-256 plus the size agreement above. Carried as a limitation.
