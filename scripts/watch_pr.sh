#!/bin/sh
# watch_pr.sh — terminal-state PR watcher that cannot false-alarm on
# stale check rows.
#
# Born from the 2026-08-24 retro: five hand-rolled watcher loops in one
# session produced three bugs — `gh pr checks` fail-rows from a
# SUPERSEDED run firing after a fix was already pushed (twice), and a
# watcher keyed to the wrong head SHA that could never complete. The
# durable shape, encoded here: judge only the latest workflow RUN for
# the branch, only when it is COMPLETED, and only when its headSha
# matches the head you meant to watch.
#
# Usage: scripts/watch_pr.sh <pr-number> [workflow] [interval-seconds]
#   workflow defaults to tests.yml; interval defaults to 120.
#
# Prints exactly ONE line and exits:
#   MERGED <pr> <mergedAt>          exit 0
#   CLOSED <pr>                     exit 2
#   RED <pr> <conclusion> <sha>     exit 1   (latest run on the CURRENT
#                                             head completed non-success)
#
# The head SHA is re-read each pass, so pushing a fix retargets the
# watch automatically instead of leaving it keyed to a dead SHA.
set -u

PR="${1:?usage: watch_pr.sh <pr-number> [workflow] [interval]}"
WORKFLOW="${2:-tests.yml}"
INTERVAL="${3:-120}"

while :; do
    info=$(gh pr view "$PR" --json state,mergedAt,headRefOid,headRefName 2>/dev/null) || {
        sleep "$INTERVAL"
        continue
    }
    pr_state=$(printf '%s' "$info" | jq -r .state)
    case "$pr_state" in
    MERGED)
        printf 'MERGED %s %s\n' "$PR" "$(printf '%s' "$info" | jq -r .mergedAt)"
        exit 0
        ;;
    CLOSED)
        printf 'CLOSED %s\n' "$PR"
        exit 2
        ;;
    esac

    head=$(printf '%s' "$info" | jq -r .headRefOid)
    branch=$(printf '%s' "$info" | jq -r .headRefName)
    run=$(gh run list --workflow "$WORKFLOW" --branch "$branch" --limit 1 \
        --json status,conclusion,headSha 2>/dev/null |
        jq -r '.[0] | "\(.status)|\(.conclusion)|\(.headSha)"')
    run_status=${run%%|*}
    rest=${run#*|}
    conclusion=${rest%%|*}
    run_sha=${rest#*|}

    # Judge only a COMPLETED run on the PR's CURRENT head — anything
    # else (queued, in-flight, or a superseded SHA) is not evidence.
    if [ "$run_status" = "completed" ] && [ "$run_sha" = "$head" ] &&
        [ "$conclusion" != "success" ] && [ "$conclusion" != "" ] &&
        [ "$conclusion" != "null" ]; then
        printf 'RED %s %s %s\n' "$PR" "$conclusion" "$run_sha"
        exit 1
    fi
    sleep "$INTERVAL"
done
