#!/usr/bin/env bash
# Q1-009 runner. Read-only: it hashes, counts and recomputes, and writes nothing.
#
# This is NOT the freeze gate. `scripts/freeze.py --verify` re-runs the figure
# generators and the regeneration check, so it writes to the tree and takes
# minutes; it is run deliberately, by a person, at a freeze. This runs on every
# push and asks a different question -- not "has the tree moved" but "does the
# tree still mean what the manuscript says it means".
#
#   tests/run.sh            invariants, then every injected defect   ~3m10s
#   tests/run.sh --fast     invariants only                          ~10s
#
# PYTHON=... overrides the interpreter; the project's own venv is the default
# when present, because numpy must be importable.
set -uo pipefail
cd "$(dirname "$0")/.."

if [ -z "${PYTHON:-}" ]; then
    if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
fi
echo "interpreter: $PYTHON  ($($PYTHON --version 2>&1))"

rc=0
run () {
    echo
    echo "=============================================================="
    echo "$1"
    echo "=============================================================="
    shift
    "$@" || rc=1
}

if [ "${1:-}" = "--fast" ]; then
    run "invariants (injections skipped)" "$PYTHON" tests/test_invariants.py
else
    run "invariants, and every test shown failing against a defect" \
        "$PYTHON" tests/test_invariants.py --all
fi

# The reference gate is read-only too, and a broken reference is the same class
# of problem: something the prose claims that the tree does not support.
if [ -f scripts/check_references.py ]; then
    run "references resolve" "$PYTHON" scripts/check_references.py
fi

echo
if [ $rc -eq 0 ]; then echo "ALL GATES PASSED"; else echo "GATES FAILED"; fi
exit $rc
