#!/usr/bin/env bash
# salvage_worktree_diff.sh — read-only salvage of a stranded worktree's
# uncommitted diff onto a fresh branch in the CURRENT checkout.
#
# Usage: scripts/salvage_worktree_diff.sh <source-worktree> <new-branch> \
#            [--base <ref>]            (default base: origin/main)
#
# Mechanizes the recovery recipe that ran by hand four times on
# 2026-09-11 (#2516–#2519): a session's worktree is left holding real,
# uncommitted work. Rather than committing INTO that worktree (another
# agent's, possibly still open), the diff is lifted verbatim onto a
# fresh branch cut from current main, and the source worktree stays
# untouched as the backup until the PR merges.
#
#   1. Refuse to run inside the source worktree, or from a dirty
#      checkout. Everything about the source is READ-ONLY: the script
#      never writes there (GIT_OPTIONAL_LOCKS=0 keeps git from even
#      refreshing the source's index).
#   2. Capture the tracked diff — `git diff --binary HEAD`, staged AND
#      unstaged, so nothing a session `git add`ed is dropped — and the
#      untracked file list. Nothing to salvage -> exit 2.
#   3. Fetch the base's remote branch, then `git checkout -b <branch>
#      <base>` here.
#   4. `git apply --check`, then apply; copy each untracked file to the
#      same relative path (never over a file that already exists here).
#   5. Identity receipt: the diff here must equal the captured patch
#      with `index` lines and `@@` hunk headers ignored. Then a receipt
#      of files, +/- counts, untracked copies, and the next steps.
#
# Committed-but-unpushed work on the source branch is NOT salvaged —
# this handles the uncommitted diff only; cherry-pick commits yourself.
#
# Exit status:   0  branch created, patch applied, identity held
#                1  refused — inside the source, dirty checkout, base
#                   fetch/checkout failed, patch does not apply, an
#                   untracked file collides with a file here, or the
#                   identity receipt differs
#                2  nothing to salvage (no tracked diff, no untracked)
#               64  usage
set -euo pipefail

usage() {
    echo "usage: $0 <source-worktree> <new-branch> [--base <ref>]" >&2
    exit 64
}

refuse() {
    echo "refused: $*" >&2
    exit 1
}

SRC=""
BRANCH=""
BASE="origin/main"
while [ $# -gt 0 ]; do
    case "$1" in
        --base)
            [ $# -ge 2 ] || usage
            BASE="$2"
            shift 2
            ;;
        --base=*)
            BASE="${1#--base=}"
            shift
            ;;
        -*)
            usage
            ;;
        *)
            if [ -z "$SRC" ]; then
                SRC="$1"
            elif [ -z "$BRANCH" ]; then
                BRANCH="$1"
            else
                usage
            fi
            shift
            ;;
    esac
done
[ -n "$SRC" ] && [ -n "$BRANCH" ] && [ -n "$BASE" ] || usage

# --- 1. locate both checkouts; refuse the unsafe starting states -------
if ! SRC_TOP=$(git -C "$SRC" rev-parse --show-toplevel); then
    echo "not a git worktree: $SRC" >&2
    exit 64
fi
if ! CUR_TOP=$(git rev-parse --show-toplevel); then
    echo "run this from inside the checkout that receives the branch" >&2
    exit 64
fi
# git apply from a subdirectory silently ignores paths outside it.
cd "$CUR_TOP"
[ "$SRC_TOP" != "$CUR_TOP" ] || refuse "the current checkout IS the" \
    "source worktree ($SRC_TOP); run from the checkout that receives" \
    "the branch, never inside the source"
[ -z "$(git status --porcelain)" ] || refuse "the current checkout is" \
    "dirty; commit, stash, or clean it before salvaging into it"

# --- 2. read-only capture from the source ------------------------------
PATCH=$(mktemp)
HERE=$(mktemp)
trap 'rm -f "$PATCH" "$HERE"' EXIT
GIT_OPTIONAL_LOCKS=0 git -C "$SRC_TOP" diff --binary HEAD > "$PATCH"

UNTRACKED=()
while IFS= read -r -d '' entry; do
    case "$entry" in
        '?? '*) UNTRACKED+=("${entry:3}") ;;
    esac
done < <(GIT_OPTIONAL_LOCKS=0 git -C "$SRC_TOP" status --porcelain -z \
    --untracked-files=all)

if [ ! -s "$PATCH" ] && [ "${#UNTRACKED[@]}" -eq 0 ]; then
    echo "nothing to salvage: $SRC_TOP has no tracked diff and no" \
        "untracked files" >&2
    exit 2
fi
# git emits worktree-relative paths; keep the copy inside this tree.
for path in ${UNTRACKED[@]+"${UNTRACKED[@]}"}; do
    case "$path" in
        /* | ../* | */../* | */.. | ..)
            refuse "untracked path escapes the worktree: $path"
            ;;
    esac
done

# --- 3. fresh branch from the (refreshed) base ---------------------------
REMOTE="${BASE%%/*}"
if [ "$REMOTE" != "$BASE" ] && git remote get-url "$REMOTE" >/dev/null 2>&1
then
    git fetch "$REMOTE" "${BASE#*/}" || refuse "fetch of $BASE failed"
fi
git checkout -b "$BRANCH" "$BASE" \
    || refuse "could not create $BRANCH from $BASE"

# --- 4. apply the patch; copy the untracked files ------------------------
for path in ${UNTRACKED[@]+"${UNTRACKED[@]}"}; do
    [ ! -e "$CUR_TOP/$path" ] || refuse "untracked file would overwrite" \
        "an existing file here: $path ($BRANCH is at $BASE, nothing applied)"
done
if [ -s "$PATCH" ]; then
    git apply --check "$PATCH" || refuse "the patch does not apply to" \
        "$BASE ($BRANCH is at $BASE, nothing applied); if the source" \
        "branch has commits ahead of $BASE, cherry-pick those first"
    git apply "$PATCH"
fi
for path in ${UNTRACKED[@]+"${UNTRACKED[@]}"}; do
    mkdir -p "$(dirname "$CUR_TOP/$path")"
    cp -p "$SRC_TOP/$path" "$CUR_TOP/$path"
done

# --- 5. identity receipt ---------------------------------------------------
normalize() {
    grep -v -e '^index ' -e '^@@ ' "$1" || true
}
git diff --binary HEAD > "$HERE"
if DELTA=$(diff <(normalize "$PATCH") <(normalize "$HERE")); then
    echo "identity: IDENTICAL (index lines and @@ hunk headers ignored)"
else
    echo "identity: DIFFERS — the diff here is not the captured patch:" >&2
    echo "$DELTA" >&2
    exit 1
fi

echo
echo "== salvage receipt =="
echo "source:  $SRC_TOP (HEAD $(git -C "$SRC_TOP" rev-parse --short HEAD))"
echo "         UNTOUCHED — it stays the backup until the PR merges"
echo "branch:  $BRANCH from $BASE ($(git rev-parse --short HEAD))"
echo "here:    $CUR_TOP"
git diff --stat HEAD
echo "untracked copied: ${#UNTRACKED[@]}"
for path in ${UNTRACKED[@]+"${UNTRACKED[@]}"}; do
    echo "  $path"
done
cat <<EOF
next:
  1. run the tests against THIS worktree's source, not main's mapping:
     PYTHONPATH=$CUR_TOP/src ANTHROPIC_API_KEY="" \\
       .venv/bin/python -m pytest <targets> -q
  2. git add -A && git commit -F <message-file>
  3. git push -u origin $BRANCH
     gh pr create --base ${BASE#*/} --head $BRANCH --body-file <body-file>
EOF
