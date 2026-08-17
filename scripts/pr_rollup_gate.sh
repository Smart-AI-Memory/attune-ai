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
  # The rollup is a UNION: CheckRun (name/status/conclusion) and
  # StatusContext (context/state — legacy commit statuses, e.g. Vercel
  # deploys, codecov). Reading StatusContexts through CheckRun fields
  # makes them nameless never-completing phantoms — the gate spun
  # forever on a fully-green docs PR (hit live 2026-08-17, #2083; same
  # cause stalled the #2076 poll a day earlier). Normalize both arms
  # to {key, done, ok}, then dedupe per key keeping the LATEST run —
  # a re-run leaves the old failed check-run beside its replacement
  # (CodeQL, #2082) and GitHub's merge box evaluates latest-per-name.
  normalized=$(jq '[.statusCheckRollup[]
      | if .__typename == "StatusContext" then
          {key: ("ctx:" + .context),
           done: (.state != "PENDING" and .state != "EXPECTED"),
           ok: (.state == "SUCCESS"),
           started: (.startedAt // .createdAt // "")}
        else
          {key: ("run:" + (.name // "?")),
           done: (.status == "COMPLETED"),
           ok: (.conclusion == "SUCCESS" or .conclusion == "SKIPPED"
                or .conclusion == "NEUTRAL"),
           started: (.startedAt // .completedAt // "")}
        end]
      | [group_by(.key)[] | max_by(.started)]' <<<"$rollup")
  bad=$(jq -r '[.[] | select(.done and (.ok | not))] | length' <<<"$normalized")
  pending=$(jq -r '[.[] | select(.done | not)] | length' <<<"$normalized")
  total=$(jq -r 'length' <<<"$normalized")
  echo "pr=$PR bad=$bad pending=$pending total=$total"
  if [ "$bad" != "0" ]; then
    jq -r '.[] | select(.done and (.ok | not)) | "RED: " + .key' <<<"$normalized" | sort -u
    exit 1
  fi
  if [ "$pending" = "0" ] && [ "$total" -ge "$MIN_CHECKS" ]; then
    echo "GREEN ($total checks)"
    exit 0
  fi
  sleep "$INTERVAL"
done
