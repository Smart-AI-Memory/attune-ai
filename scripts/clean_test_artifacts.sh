#!/usr/bin/env bash
# Clean up test/coverage artifacts that accumulate across runs.
#
# Run this when:
# - Coverage runs error with "Data file ... doesn't seem to be a coverage data file"
# - Stale pytest processes are eating RAM (each can hold ~5GB)
# - You want a clean slate before a fresh full run
#
# Safe to run anytime — only touches artifacts excluded by .gitignore.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "Cleaning test artifacts in $repo_root"

# Remove coverage data files (current + parallel-run shards)
removed=0
shopt -s nullglob
for f in .coverage .coverage.* coverage.xml coverage.json; do
  if [ -e "$f" ]; then
    rm -f "$f"
    removed=$((removed + 1))
  fi
done
echo "  removed $removed coverage files"

# Remove pytest cache
if [ -d .pytest_cache ]; then
  rm -rf .pytest_cache
  echo "  removed .pytest_cache/"
fi

# Kill stale pytest processes (only ours — match by user)
stale=$(pgrep -u "$(id -u)" -f "python -m pytest" 2>/dev/null | wc -l | tr -d ' ')
if [ "$stale" -gt 0 ]; then
  pgrep -u "$(id -u)" -f "python -m pytest" | xargs -r kill -9 2>/dev/null || true
  echo "  killed $stale stale pytest process(es)"
fi

echo "Done."
