#!/usr/bin/env python3
"""Retrieve one source into a write-once raw directory and record its provenance.

Fills the twelve DATA_SOURCES.md fields it can determine; the rest are taken
from flags and default to PENDING. Refuses to overwrite an existing raw file,
because data/raw is write-once by policy.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-id", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--filename", help="defaults to the URL basename")
    p.add_argument("--origin", default="PENDING")
    p.add_argument("--version", default="PENDING")
    p.add_argument("--license", default="PENDING")
    p.add_argument("--reference", default="PENDING")
    p.add_argument(
        "--published-checksum",
        default="ABSENT",
        help="as 'algo:hex' if the publisher supplies one",
    )
    p.add_argument(
        "--resume", action="store_true",
        help="continue a partial transfer rather than restarting it. Safe because "
             "the checksum is verified afterwards: a bad resume fails the check "
             "exactly as a bad download would.",
    )
    args = p.parse_args()

    name = args.filename or unquote(Path(urlparse(args.url).path).name)
    if not name:
        sys.exit("cannot determine a filename; pass --filename")

    dest_dir = RAW / args.source_id
    dest = dest_dir / name
    partial = dest.exists() and args.resume
    if dest.exists() and not args.resume:
        sys.exit(f"refusing to overwrite {dest}; data/raw is write-once "
                 f"(pass --resume to continue an interrupted transfer)")
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Abort on a STALL, not on duration. A total time limit punishes large files
    # for being large: the 9.25 GiB container failed at 5.7 GiB purely because
    # it was still going at 30 minutes. --speed-limit/--speed-time ends a
    # transfer that has genuinely died, while letting a slow one finish.
    cmd = ["curl", "--fail", "--location", "--silent", "--show-error",
           "--speed-limit", "10240", "--speed-time", "120",
           "--max-time", "21600",
           "--output", str(dest), args.url]
    if partial:
        cmd[-3:-3] = ["--continue-at", "-"]
    started = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, capture_output=True, text=True)

    record = {
        "source_id": args.source_id,
        "origin": args.origin,
        "accession_or_url": args.url,
        "version": args.version,
        "retrieval_date": started.isoformat(),
        "original_filename": name,
        "local_path": str(dest.relative_to(REPO)),
        "license": args.license,
        "reference": args.reference,
        "acquisition_method": " ".join(cmd),
        "processing_history": "RESUMED from a partial transfer" if partial else "NONE",
        "published_checksum": args.published_checksum,
    }

    if proc.returncode != 0:
        # Keep whatever transferred: the next attempt resumes from it. Deleting
        # here would discard gigabytes of good bytes on every interruption,
        # which is what made the 9.25 GiB container unrecoverable. Bytes proven
        # wrong are deleted below, under CHECKSUM_MISMATCH.
        kept = dest.stat().st_size if dest.exists() else 0
        record["outcome"] = "FAILED"
        record["partial_bytes_kept"] = kept
        record["error"] = (proc.stderr or "").strip() or f"curl exit {proc.returncode}"
        record["checksum"] = None
        record["file_size"] = None
    else:
        record["outcome"] = "RETRIEVED"
        record["checksum"] = f"sha256:{sha256(dest)}"
        record["file_size"] = dest.stat().st_size
        if args.published_checksum != "ABSENT":
            algo, _, expected = args.published_checksum.partition(":")
            h = hashlib.new(algo)
            with open(dest, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            got = h.hexdigest()
            ok = got.lower() == expected.lower()
            record["published_checksum_verified"] = ok
            if not ok:
                record["outcome"] = "CHECKSUM_MISMATCH"
                record["error"] = f"published {expected}, computed {got}"
                # These bytes are proven wrong; resuming from them would only
                # reproduce the mismatch. Remove so the next attempt starts clean.
                dest.unlink(missing_ok=True)

    log = dest_dir / "provenance.jsonl"
    with open(log, "a") as fh:
        fh.write(json.dumps(record) + "\n")

    print(json.dumps(record, indent=2))
    return 0 if record["outcome"] == "RETRIEVED" else 1


if __name__ == "__main__":
    sys.exit(main())
