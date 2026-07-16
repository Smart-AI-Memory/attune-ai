#!/usr/bin/env bash
#
# qa_coverage_baseline.sh — authoritative coverage baseline for a QA batch.
#
# The FIRST step of any test-quality batch. Runs the full unit suite (the
# only reliable measure — a single-subdir run undercounts modules whose
# tests live elsewhere; see .claude/lessons.md "subset coverage baseline
# undercounts") scoped to one package, keyless (no API spend), and prints
# the modules under a coverage threshold, ranked by missed lines.
#
# Worktree-safe: runs from the worktree root with the MAIN checkout's venv
# python (which has all extras) + a PYTHONPATH override so the worktree's
# code is measured, and --cov-config=/dev/null to bypass the rcfile
# source-mapping that otherwise reports 0% from a worktree.
#
# --cov is given a DIRECTORY PATH, not the dotted package name. A dotted
# `--cov=attune.foo` requires coverage to `importlib.import_module` that
# exact name to find what to instrument/report -- any module loaded via
# `importlib.util.spec_from_file_location` under a different name (e.g.
# config.py's legacy-compat loader, or a hooks/scripts/*.py test loading
# its target standalone) is invisible to it and silently reports 0% even
# when thoroughly tested (verified 2026-07-15: config.py showed 0%/98%,
# worktree_path_guard.py 0%/93%, starter_reconciler.py 0%/95% dotted vs
# path-scoped). Path-based --cov tracks by executed file location, not
# import name, and gives IDENTICAL numbers to the dotted form for
# normally-imported modules -- it is a strict superset fix, not a
# tradeoff. See .claude/lessons.md "coverage baseline misreports
# spec_from_file_location-loaded modules".
#
# Usage:
#   bash scripts/qa_coverage_baseline.sh [package] [threshold] [out_file]
#
#   package    dotted package to scope coverage to   (default: attune.memory)
#   threshold  report modules strictly below this %  (default: 80)
#   out_file   where to write the full term-missing   (default: a temp file)
#
# Examples:
#   bash scripts/qa_coverage_baseline.sh
#   bash scripts/qa_coverage_baseline.sh attune.workflows 85
#
set -euo pipefail

PACKAGE="${1:-attune.memory}"
THRESHOLD="${2:-80}"

WT_ROOT="$(git rev-parse --show-toplevel)"
PACKAGE_PATH="$WT_ROOT/src/$(echo "$PACKAGE" | tr '.' '/')"

# Locate a python with all extras: prefer the MAIN checkout's venv (a
# worktree venv is usually synced with only dev/developer extras).
COMMON_DIR="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
MAIN_ROOT="$(dirname "$COMMON_DIR")"
if [ -x "$MAIN_ROOT/.venv/bin/python" ]; then
  PY="$MAIN_ROOT/.venv/bin/python"
elif [ -x "$WT_ROOT/.venv/bin/python" ]; then
  PY="$WT_ROOT/.venv/bin/python"
else
  PY="python3"
fi

OUT_FILE="${3:-$(mktemp -t qa_baseline_XXXX).txt}"

echo "package:   $PACKAGE"
echo "python:    $PY"
echo "threshold: <${THRESHOLD}%"
echo "report:    $OUT_FILE"
echo "running full unit suite (keyless, this takes ~1-2 min)…"

# ANTHROPIC_API_KEY="" => CI-keyless: integration-gated SDK tests skip and
# do NOT spend real money (an UNSET key lets dotenv inject the real one).
# --ignore=tests/integration => those add ~no unit-module coverage anyway.
set +e
ANTHROPIC_API_KEY="" PYTHONPATH="$WT_ROOT/src" "$PY" -m pytest "$WT_ROOT/tests" \
  --ignore="$WT_ROOT/tests/integration" \
  -o addopts="" \
  --cov="$PACKAGE_PATH" --cov-config=/dev/null \
  --cov-report=term-missing \
  -n auto -q -p no:cacheprovider >"$OUT_FILE" 2>&1
RC=$?
set -e

if ! grep -q "TOTAL" "$OUT_FILE"; then
  echo "ERROR: no coverage TOTAL in output — run failed. Tail:" >&2
  tail -20 "$OUT_FILE" >&2
  exit "${RC:-1}"
fi

echo
echo "=== ${PACKAGE} TOTAL ==="
grep -E "^TOTAL" "$OUT_FILE" || true

echo
echo "=== modules below ${THRESHOLD}% (ranked by missed lines, desc) ==="
# Columns: Name Stmts Miss Cover[%] [Missing…]
awk -v th="$THRESHOLD" '
  $1 ~ /\.py$/ {
    cov = $4; gsub("%", "", cov);
    if (cov + 0 < th + 0) printf "%-6s %4s missed  %5s%%  %s\n", "", $3, cov, $1;
  }
' "$OUT_FILE" | sort -k2 -nr | sed 's|src/attune/||'

echo
echo "Full term-missing report: $OUT_FILE"
echo "REMINDER: a module here is a HYPOTHESIS. Before writing tests, confirm"
echo "its real coverage with its actual test files (find tests -name '*<mod>*')."
