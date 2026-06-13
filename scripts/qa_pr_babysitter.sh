#!/usr/bin/env bash
#
# qa_pr_babysitter.sh — merge your own green QA PRs as their CI passes.
#
# A standing poller for a QA batch: every interval it lists YOUR open PRs
# whose head branch matches a prefix, and squash-merges any whose REQUIRED
# checks are all green. Exits when no matching PRs remain or the deadline
# is hit.
#
# Safe by design:
#   - Only touches PRs authored by you (gh pr list --author "@me").
#   - Only merges when ALL required checks pass (the advisory Windows/macOS
#     lanes and the non-required `security` scanner are ignored).
#   - Plain `--squash --delete-branch` — NO --admin, NO branch-protection
#     changes. Branch protection requires 0 reviews for these (verify with
#     `gh api repos/<o>/<r>/branches/main/protection`).
#
# Usage:
#   bash scripts/qa_pr_babysitter.sh [branch_prefix] [deadline_min] [interval_sec]
#
#   branch_prefix  head-branch prefix to match   (default: qa)
#   deadline_min   stop after this many minutes  (default: 90)
#   interval_sec   seconds between scans          (default: 60)
#
# Run it backgrounded, or via the /loop skill for a recurring babysitter.
#
set -euo pipefail

PREFIX="${1:-qa}"
DEADLINE_MIN="${2:-90}"
INTERVAL="${3:-60}"

# The 7 REQUIRED checks per main branch protection (2026-06-13). If branch
# protection changes, update this list (gh pr checks shows all; required
# ones are in repos/<o>/<r>/branches/main/protection.required_status_checks).
REQUIRED='["pre-commit","lint","code-quality","coverage","platform-compat","CodeQL","test (ubuntu-latest, 3.12)"]'

deadline=$(( $(date +%s) + DEADLINE_MIN * 60 ))
echo "babysitter: prefix='${PREFIX}*'  deadline=${DEADLINE_MIN}m  interval=${INTERVAL}s"

while true; do
  # Open PRs by me whose head branch starts with the prefix.
  mapfile -t prs < <(gh pr list --author "@me" --state open \
    --json number,headRefName \
    --jq ".[] | select(.headRefName | startswith(\"${PREFIX}\")) | .number")

  if [ "${#prs[@]}" -eq 0 ]; then
    echo "no open ${PREFIX}* PRs remain — done."
    break
  fi

  for pr in "${prs[@]}"; do
    notpass=$(gh pr checks "$pr" --json name,bucket \
      --jq "[.[] | select(.name as \$x | ${REQUIRED} | index(\$x)) | select(.bucket != \"pass\")] | length" \
      2>/dev/null || echo 1)
    if [ "$notpass" -eq 0 ]; then
      echo "#$pr: required-green -> merging"
      gh pr merge "$pr" --squash --delete-branch 2>&1 | tail -1 || echo "#$pr merge errored (may already be merged)"
    else
      echo "#$pr: $notpass required check(s) pending"
    fi
  done

  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "deadline reached — stopping (some PRs may still be pending)."
    break
  fi
  sleep "$INTERVAL"
done
