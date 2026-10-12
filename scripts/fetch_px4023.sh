#!/bin/bash
# Retrieve PXD004023 inputs from the PRIDE archive. Nothing here is committed:
# the identification containers are 1.1 GB and the acquisition-file headers are
# 161 MB, against a tracked payload of 110 MB. This repository records their
# provenance instead -- data/external/PXD004023/header_checksums.txt and the two
# manifests -- so that an absent payload stays verifiable (D054, and the same
# rule DATA_SOURCES.md applies to S3 and S4).
#
#   ./scripts/fetch_px4023.sh headers   # 160 x 1 MiB range requests, ~161 MB
#   ./scripts/fetch_px4023.sh mzid      # 37 identification containers, ~1.1 GB
#   ./scripts/fetch_px4023.sh verify    # re-hash local headers against the record
#
# Downloads land in data/external/PXD004023/{hdr,mzid}/, which .gitignore
# excludes. Both modes resume: an existing non-empty target is left alone.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
D="$REPO/data/external/PXD004023"
BASE=https://ftp.pride.ebi.ac.uk/pride/data/archive/2016/12/PXD004023
MODE="${1:-}"

case "$MODE" in
headers)
  mkdir -p "$D/hdr"
  n=0
  while read -r f; do
    [ -z "$f" ] && continue
    out="$D/hdr/$f.head"
    [ -s "$out" ] && continue
    # Only the first 1 MiB: the instrument model string lives in the header.
    curl -s --max-time 120 -r 0-1048576 "$BASE/$f" -o "$out" || rm -f "$out"
    n=$((n+1))
  done < "$D/raw_manifest.txt"
  echo "fetched $n header(s) into $D/hdr"
  ;;
mzid)
  mkdir -p "$D/mzid"
  n=0
  while read -r f; do
    [ -z "$f" ] && continue
    out="$D/mzid/$f"
    [ -s "$out" ] && continue
    curl -s --max-time 900 "$BASE/$f" -o "$out" || rm -f "$out"
    n=$((n+1))
  done < "$D/mzid_manifest.txt"
  echo "fetched $n container(s) into $D/mzid"
  echo "NOTE: a truncated download can match a declared byte count and still be"
  echo "an error page. extract_px4023.py refuses any container under 10 MB and"
  echo "fails loudly on unparseable XML; that is deliberate (D047)."
  ;;
verify)
  if [ ! -d "$D/hdr" ]; then echo "no local headers; run: $0 headers" >&2; exit 1; fi
  cd "$D/hdr" || exit 1
  grep -v '^#' "$D/header_checksums.txt" | sha256sum -c --quiet \
    && echo "all local headers match data/external/PXD004023/header_checksums.txt"
  ;;
*)
  echo "usage: $0 {headers|mzid|verify}" >&2; exit 2 ;;
esac
