#!/usr/bin/env bash
# pr_rollup_gate.sh — wait until a PR's FULL status rollup settles green.
#
# The two failure modes this replaces (both hit on 2026-08-16):
#   * `gh pr checks --watch` exits green while a late matrix leg is
#     still QUEUED (the windows-3.13 near-merge on attune-ai #2073).
#   * an empty rollup counts zero "bad" checks and reads as green
#     before any check has been reported (attune-forms #31).
#
# Green means: zero completed-non-green AND zero pending AND at least
# MIN_CHECKS reported. Exit 0 = green, 1 = a check failed, 2 = usage.
#
# Usage: scripts/pr_rollup_gate.sh <pr-number> [min-checks] [interval-s]
#   Run from the repo the PR belongs to (gh resolves by cwd).
set -euo pipefail

PR="${1:?usage: pr_rollup_gate.sh <pr-number> [min-checks] [interval-s]}"
MIN_CHECKS="${2:-7}"
INTERVAL="${3:-30}"

while :; do
  bad=$(gh pr view "$PR" --json statusCheckRollup -q \
    '[.statusCheckRollup[] | select(.status == "COMPLETED"
      and .conclusion != "SUCCESS" and .conclusion != "SKIPPED"
      and .conclusion != "NEUTRAL")] | length')
  pending=$(gh pr view "$PR" --json statusCheckRollup -q \
    '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')
  total=$(gh pr view "$PR" --json statusCheckRollup -q \
    '.statusCheckRollup | length')
  echo "pr=$PR bad=$bad pending=$pending total=$total"
  if [ "$bad" != "0" ]; then
    gh pr view "$PR" --json statusCheckRollup -q \
      '.statusCheckRollup[] | select(.status == "COMPLETED"
        and .conclusion != "SUCCESS" and .conclusion != "SKIPPED"
        and .conclusion != "NEUTRAL") | "RED: " + .name' | sort -u
    exit 1
  fi
  if [ "$pending" = "0" ] && [ "$total" -ge "$MIN_CHECKS" ]; then
    echo "GREEN ($total checks)"
    exit 0
  fi
  sleep "$INTERVAL"
done
