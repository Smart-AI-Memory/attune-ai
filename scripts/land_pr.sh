#!/usr/bin/env bash
# land_pr.sh — merge a PR only on full-matrix green at the chair-authorized head.
#
# Usage: scripts/land_pr.sh <pr-number> <authorized-head-sha> [--pull]
#
# Encodes the guarded-merge shape ratified from the 2026-08-12 retro
# (#2059/#2061/#2063 were merged with this logic inline):
#
#   1. Watch ALL checks to completion (full matrix — never --fail-fast,
#      so non-required OS/version lanes are blocking too).
#   2. Merge ONLY if zero checks failed AND the PR head still equals
#      the SHA the chair authorized (D10: a merge word binds to the
#      head the chair read; any later push invalidates it).
#   3. Verify the merge REMOTELY (state/mergedAt) — the local
#      --delete-branch step often errors harmlessly from a worktree.
#   4. --pull: fast-forward the main checkout afterward (autostash
#      rebase; only when that checkout is on main).
#
# The script never uses --admin and never bypasses anything: a red
# check, a moved head, or a blocked merge state all refuse loudly.
set -euo pipefail

REPO_MAIN="${LAND_PR_MAIN_CHECKOUT:-$HOME/attune-ai}"

if [ $# -lt 2 ]; then
    echo "usage: $0 <pr-number> <authorized-head-sha> [--pull]" >&2
    exit 64
fi
PR="$1"
AUTHORIZED_SHA="$2"
DO_PULL="${3:-}"

echo "[land_pr] watching PR #$PR checks (full matrix, no fail-fast)…"
# --watch exit code is unreliable (cancelled-but-fail-tagged rows);
# always re-read the buckets afterward.
gh pr checks "$PR" --watch >/dev/null 2>&1 || true

FAILS=$(gh pr checks "$PR" --json name,bucket \
    --jq '[.[] | select(.bucket == "fail")] | length')
HEAD=$(gh pr view "$PR" --json headRefOid --jq '.headRefOid')

if [ "$FAILS" != "0" ]; then
    echo "[land_pr] REFUSING: $FAILS check(s) failed:" >&2
    gh pr checks "$PR" --json name,bucket \
        --jq '.[] | select(.bucket == "fail") | "  " + .name' >&2
    exit 1
fi

case "$HEAD" in
    "$AUTHORIZED_SHA"*) ;;
    *)
        echo "[land_pr] REFUSING: head moved since authorization" >&2
        echo "  authorized: $AUTHORIZED_SHA" >&2
        echo "  current:    $HEAD" >&2
        echo "  Re-read the PR and re-authorize at the new head." >&2
        exit 1
        ;;
esac

echo "[land_pr] all checks green at authorized head — merging…"
# Local post-merge steps (branch delete, checkout refresh) often fail
# from a worktree even when the REMOTE merge succeeded; verify below.
gh pr merge "$PR" --squash --delete-branch || true

STATE=$(gh pr view "$PR" --json state --jq '.state')
if [ "$STATE" != "MERGED" ]; then
    echo "[land_pr] merge did NOT land (state: $STATE) — investigate" >&2
    exit 1
fi
gh pr view "$PR" --json state,mergedAt,mergeCommit \
    --jq '"[land_pr] #'"$PR"': \(.state) · mergedAt: \(.mergedAt) · sha: \(.mergeCommit.oid[0:9])"'

if [ "$DO_PULL" = "--pull" ]; then
    BRANCH=$(git -C "$REPO_MAIN" branch --show-current)
    if [ "$BRANCH" != "main" ]; then
        echo "[land_pr] skipping pull: $REPO_MAIN is on '$BRANCH', not main" >&2
        exit 0
    fi
    git -C "$REPO_MAIN" -c rebase.autoStash=true pull --rebase origin main
    git -C "$REPO_MAIN" log --oneline -1 | sed 's/^/[land_pr] main: /'
fi
