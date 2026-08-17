#!/usr/bin/env bash
# pr_rollup_gate.sh — wait until a PR's FULL status rollup settles green.
#
# The failure modes this replaces (all hit live on 2026-08-16/17):
#   * `gh pr checks --watch` exits green while a late matrix leg is
#     still QUEUED (the windows-3.13 near-merge on attune-ai #2073).
#   * an empty rollup counts zero "bad" checks and reads as green
#     before any check has been reported (attune-forms #31).
#   * a transient GitHub 503 killed the first version mid-poll under
#     `set -e`, and a caller piping through `tail` discarded the exit
#     code — the #2080 merge ran with 2 (non-required) checks pending.
#     API failures now tolerate-and-retry with a consecutive-failure
#     cap, and callers MUST NOT pipe this script (its exit code is the
#     contract): run it bare, or with `set -o pipefail` if you must.
#
# Green means: zero completed-non-green AND zero pending AND at least
# MIN_CHECKS reported. Exit 0 = green, 1 = a check failed,
# 2 = usage/API unreachable.
#
# Usage: scripts/pr_rollup_gate.sh <pr-number> [min-checks] [interval-s]
#   Run from the repo the PR belongs to (gh resolves by cwd).
set -uo pipefail

PR="${1:?usage: pr_rollup_gate.sh <pr-number> [min-checks] [interval-s]}"
MIN_CHECKS="${2:-7}"
INTERVAL="${3:-30}"
MAX_API_FAILURES=10

fails=0
while :; do
  if ! rollup=$(gh pr view "$PR" --json statusCheckRollup 2>/dev/null); then
    fails=$((fails + 1))
    echo "pr=$PR api-failure $fails/$MAX_API_FAILURES (retrying in ${INTERVAL}s)" >&2
    if [ "$fails" -ge "$MAX_API_FAILURES" ]; then
      echo "UNREACHABLE: $MAX_API_FAILURES consecutive API failures" >&2
      exit 2
    fi
    sleep "$INTERVAL"
    continue
  fi
  fails=0
  bad=$(jq -r '[.statusCheckRollup[] | select(.status == "COMPLETED"
      and .conclusion != "SUCCESS" and .conclusion != "SKIPPED"
      and .conclusion != "NEUTRAL")] | length' <<<"$rollup")
  pending=$(jq -r '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length' <<<"$rollup")
  total=$(jq -r '.statusCheckRollup | length' <<<"$rollup")
  echo "pr=$PR bad=$bad pending=$pending total=$total"
  if [ "$bad" != "0" ]; then
    jq -r '.statusCheckRollup[] | select(.status == "COMPLETED"
        and .conclusion != "SUCCESS" and .conclusion != "SKIPPED"
        and .conclusion != "NEUTRAL") | "RED: " + .name' <<<"$rollup" | sort -u
    exit 1
  fi
  if [ "$pending" = "0" ] && [ "$total" -ge "$MIN_CHECKS" ]; then
    echo "GREEN ($total checks)"
    exit 0
  fi
  sleep "$INTERVAL"
done
