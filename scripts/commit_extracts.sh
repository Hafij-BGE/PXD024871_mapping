#!/usr/bin/env bash
# Gzip and commit completed peptide extracts, then push.
#
# Only touches units that have a .meta.json: extract_peptides.py writes that
# after the CSV, so its presence means the CSV is complete. A CSV being written
# right now has no meta yet and is left alone.
#
# Safe to run while batch_extract.py is still going, and safe to re-run.
set -uo pipefail
cd "$(dirname "$0")/.."
D=data/derived/peptides
n=0
for meta in "$D"/*.meta.json; do
  [ -e "$meta" ] || continue
  unit=$(basename "$meta" .meta.json)
  if [ -f "$D/$unit.csv" ] && [ ! -f "$D/$unit.csv.gz" ]; then
    gzip -6 -n "$D/$unit.csv" && n=$((n+1))
  fi
done
echo "gzipped $n newly-completed extract(s)"
done_n=$(ls "$D"/*.csv.gz 2>/dev/null | wc -l | tr -d ' ')
git add "$D" data/raw/S3/provenance.jsonl 2>/dev/null
if git diff --cached --quiet; then echo "nothing new to commit ($done_n/52 units)"; exit 0; fi
git commit -q -m "$(cat <<MSG
Extract peptide tables: ${done_n}/52 class-I units complete

Streamed by scripts/batch_extract.py. Each container was verified
against the publisher's SHA-1 before extraction and deleted afterwards,
so the extracts are the retained form of data no longer held locally.
Committed incrementally because this session's container is ephemeral
and the extracts cannot be regenerated without re-transferring.

Stored gzipped: peptide sequences compress about sixfold, which keeps
the full set near 16 MiB rather than 98.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01WB9rZBEvRjGfNdk5pHev3V
MSG
)"
for i in 1 2 3 4; do
  git push -q origin claude/mapping-research-project-prompt-glsess && { echo "pushed ($done_n/52)"; exit 0; }
  echo "push failed, retry $i"; sleep $((2**i))
done
echo "PUSH FAILED after retries — commit is local, extracts still at risk"; exit 1
