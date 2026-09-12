#!/usr/bin/env bash
# land_pr.sh — merge a PR only on full-matrix green at the chair-authorized head.
#
# Usage: scripts/land_pr.sh <pr-number> <authorized-head-sha> [--pull]
#
# Encodes the guarded-merge shape ratified from the 2026-08-12 retro
# (#2059/#2061/#2063 were merged with this logic inline):
#
#   0. Probe mergeability FIRST. A PR that is CONFLICTING against main
#      (or still a DRAFT) cannot merge no matter what the checks say, so
#      it is refused with the rebase instruction BEFORE the long watch —
#      #2513 (2026-09-11) watched a full matrix only to fail at merge time.
#   1. Watch ALL checks to completion (full matrix — never --fail-fast,
#      so non-required OS/version lanes are blocking too).
#   2. Merge ONLY if zero checks failed AND the PR head still equals
#      the SHA the chair authorized (D10: a merge word binds to the
#      head the chair read; any later push invalidates it).
#   3. Verify the merge REMOTELY (state/mergedAt) — the local
#      --delete-branch step often errors harmlessly from a worktree.
#      The remote state IS the exit status: anything but MERGED exits
#      non-zero, so a background task's "exit 0" means the PR landed.
#   4. --pull: fast-forward the main checkout afterward (autostash
#      rebase; only when that checkout is on main).
#
# Exit status:   0  merged (remote state MERGED)
#                1  refused — a red check, a moved head, or the merge
#                   did not land
#                2  refused — CONFLICTING (rebase first) or DRAFT
#               64  usage
#
# Run it directly. Through `… | tee log` the shell reports tee's exit
# status, not this script's — use `set -o pipefail` or read
# `${PIPESTATUS[0]}`; that is how #2513's refusal surfaced as "exit 0".
#
# The script never uses --admin and never bypasses anything: a red
# check, a moved head, a conflicting base, or a blocked merge state all
# refuse loudly.
set -euo pipefail

REPO_MAIN="${LAND_PR_MAIN_CHECKOUT:-$HOME/attune-ai}"

if [ $# -lt 2 ]; then
    echo "usage: $0 <pr-number> <authorized-head-sha> [--pull]" >&2
    exit 64
fi
PR="$1"
AUTHORIZED_SHA="$2"
DO_PULL="${3:-}"

# Refuse (exit 2) when the PR cannot merge no matter what the checks
# say — CONFLICTING against main, or still a DRAFT — and say what to do
# instead. GitHub computes mergeability lazily, so right after a push
# it reads UNKNOWN for a few seconds: re-probe before trusting that.
# $1 names the moment for the message ("before watching"/"before merging").
gate_mergeability() {
    local probe tries=0
    while :; do
        probe=$(gh pr view "$PR" --json mergeable,mergeStateStatus \
            --jq '"\(.mergeable) \(.mergeStateStatus)"')
        tries=$((tries + 1))
        if [ "${probe%% *}" != "UNKNOWN" ] || [ "$tries" -ge 3 ]; then
            break
        fi
        sleep "${LAND_PR_PROBE_DELAY:-5}"
    done
    case "$probe" in
        CONFLICTING*)
            echo "[land_pr] REFUSING ($1): PR #$PR is CONFLICTING against main (mergeStateStatus: ${probe#* })" >&2
            echo "  Rebase, then re-authorize at the NEW head (the merge word binds to the head the chair read):" >&2
            echo "    git fetch origin main && git rebase -S origin/main" >&2
            echo "    git log --format='%G? %h %s' origin/main..HEAD   # every row G — a rebase can replay unsigned" >&2
            echo "    git push --force-with-lease" >&2
            exit 2
            ;;
        *" DRAFT")
            echo "[land_pr] REFUSING ($1): PR #$PR is a DRAFT — mark it ready first: gh pr ready $PR" >&2
            exit 2
            ;;
        UNKNOWN*)
            echo "[land_pr] note ($1): GitHub has not computed mergeability yet ($probe) — continuing"
            ;;
    esac
}

gate_mergeability "before watching"

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

# CLAIM FRESHNESS. The head-SHA gate above answers "did the content
# change since the chair read it". It cannot answer "is what this
# content ASSERTS still true" — a sibling PR touching no file in common
# can invalidate a claim, and the merge order is decided after both were
# written. D18 landed 19 minutes after #2476 falsified a version bound it
# stated in present tense; nothing conflicted, rebased or went red.
if git rev-parse --verify --quiet "$AUTHORIZED_SHA^{commit}" >/dev/null; then
    git fetch origin main --quiet 2>/dev/null || true
    MB=$(git merge-base "$AUTHORIZED_SHA" origin/main 2>/dev/null || true)
    if [ -n "$MB" ]; then
        LANDED=$(git log --oneline "$MB..origin/main" 2>/dev/null)
        if [ -n "$LANDED" ]; then
            echo "[land_pr] landed on main since this branch forked:"
            printf '%s\n' "$LANDED" | sed 's/^/    /'
            echo "[land_pr] ^ did any of these change a fact this PR ASSERTS"
            echo "          (a version bound, a count, a status, \"X is not implemented\")?"
            echo "          Ctrl-C now if so; the head-SHA gate does not cover it."
        fi
    fi
else
    echo "[land_pr] note: $AUTHORIZED_SHA not resolvable locally —" >&2
    echo "          claim-freshness window skipped, verify by hand." >&2
fi

# Main may have moved during the watch: re-probe so a conflict that
# appeared mid-watch is reported as a rebase instruction, not as gh's
# generic "the merge commit cannot be cleanly created".
gate_mergeability "before merging"

echo "[land_pr] all checks green at authorized head — merging…"
# Local post-merge steps (branch delete, checkout refresh) often fail
# from a worktree even when the REMOTE merge succeeded; the known
# worktree case is reported calmly, anything else is surfaced. The
# merge command's own exit status is deliberately NOT the verdict —
# the remote state re-read below is.
MERGE_ERR=$(gh pr merge "$PR" --squash --delete-branch 2>&1 >/dev/null) || true
if [ -n "$MERGE_ERR" ]; then
    case "$MERGE_ERR" in
        *"already used by worktree"*|*"failed to run git"*)
            echo "[land_pr] local branch cleanup skipped (running from a worktree); remote merge unaffected" ;;
        *)
            printf '%s\n' "$MERGE_ERR" >&2 ;;
    esac
fi

# THE REMOTE STATE IS THE EXIT STATUS. Nothing after this check may
# soften it: a caller judging by exit code (a background task, a CI
# step, an && chain) must only ever see 0 when the PR is MERGED.
STATE=$(gh pr view "$PR" --json state --jq '.state')
if [ "$STATE" != "MERGED" ]; then
    echo "[land_pr] merge did NOT land (state: $STATE) — exit 1" >&2
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
