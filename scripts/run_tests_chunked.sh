#!/usr/bin/env bash
# Run the test suite in directory chunks, each in its own pytest process.
#
# Why: pytest.ini forces `-n 0` (sequential) due to known import-timing
# issues in the workflows package. Sequential + ~5000 tests means the
# single pytest process accumulates memory across all imports and OOMs
# on most dev machines. CI works because each matrix job runs on a fresh
# VM. Locally, run chunks instead.
#
# Each chunk is its own pytest invocation, so memory is reclaimed
# between chunks. Failures in one chunk don't stop the rest.
#
# Usage:
#   ./scripts/run_tests_chunked.sh           # run all chunks
#   ./scripts/run_tests_chunked.sh --failfast # stop at first chunk failure

set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

failfast=false
if [ "${1:-}" = "--failfast" ]; then
  failfast=true
fi

# Ordered to put fast chunks first so failures surface early
chunks=(
  "tests/unit/hooks"
  "tests/unit/help"
  "tests/unit/patterns"
  "tests/unit/routing"
  "tests/unit/orchestration"
  "tests/unit/socratic"
  "tests/unit/meta_workflows"
  "tests/unit/agent_factory"
  "tests/unit/cli_commands"
  "tests/unit/resilience"
  "tests/unit/security"
  "tests/unit/verification"
  "tests/unit/models"
  "tests/unit/telemetry"
  "tests/unit/wizards"
  "tests/unit/workflows"
  "tests/unit/memory"
)

total_passed=0
total_failed=0
failed_chunks=()

for chunk in "${chunks[@]}"; do
  if [ ! -d "$chunk" ]; then
    echo "[skip] $chunk (not found)"
    continue
  fi
  echo
  echo "=== $chunk ==="
  start=$(date +%s)
  out=$(python -m pytest "$chunk" -q --tb=line --timeout=120 -p no:cacheprovider 2>&1)
  rc=$?
  elapsed=$(($(date +%s) - start))
  summary=$(echo "$out" | tail -1 | tr -d '\r')
  passed=$(echo "$summary" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" || echo 0)
  failed=$(echo "$summary" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" || echo 0)
  total_passed=$((total_passed + passed))
  total_failed=$((total_failed + failed))
  if [ $rc -eq 0 ]; then
    echo "[${elapsed}s] OK :: $summary"
  else
    echo "[${elapsed}s] FAIL :: $summary"
    echo "$out" | grep -E "^FAILED|^ERROR" | head -5
    failed_chunks+=("$chunk")
    if [ "$failfast" = true ]; then
      break
    fi
  fi
done

echo
echo "===== chunked run complete ====="
echo "passed: $total_passed"
echo "failed: $total_failed"
if [ ${#failed_chunks[@]} -gt 0 ]; then
  echo "failed chunks:"
  for c in "${failed_chunks[@]}"; do echo "  - $c"; done
  exit 1
fi
