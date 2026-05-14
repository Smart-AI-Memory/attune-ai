#!/usr/bin/env bash
# Audit git worktrees and surface housekeeping signals.
#
# Categorizes each worktree (except the main checkout and any
# worktree passed via $AUDIT_EXCLUDE_WORKTREE) into one of:
#
#   - active    — has an open PR, OR is the current checkout
#   - safe      — PR merged/closed AND working tree clean AND no
#                 unpushed commits → safe to `git worktree remove`
#   - risk      — has uncommitted work, OR has commits not on origin,
#                 OR is on a no-PR branch with a non-trivial state
#
# Outputs a short Markdown summary suitable for inclusion in the
# daily briefing. Exit code is always 0 — this is an informational
# audit, not a gate.
#
# Usage:
#   bash scripts/audit_worktrees.sh
#   bash scripts/audit_worktrees.sh --json    # raw JSON, no markdown
#
# Env:
#   AUDIT_EXCLUDE_WORKTREE  Comma-separated worktree basenames to skip
#                            (in addition to the main checkout).
#   AUDIT_SOFT_CAP          Worktree-count threshold for a sprawl
#                            flag (default 10).
#
# Notes:
#   - Requires `gh` for PR state lookups; without it, every worktree
#     is treated as having no PR (more conservative).
#   - `git fetch --prune` is NOT run by the script. The caller (the
#     briefing) is responsible for refreshing remote refs.

set -uo pipefail

JSON_MODE=0
if [[ "${1:-}" == "--json" ]]; then
    JSON_MODE=1
fi

SOFT_CAP="${AUDIT_SOFT_CAP:-10}"
EXCLUDE_RAW="${AUDIT_EXCLUDE_WORKTREE:-}"
IFS=',' read -ra EXCLUDE_ARR <<<"$EXCLUDE_RAW"

# Locate the main checkout (the one without a separate worktree
# branch — git worktree list --porcelain shows it as "bare" or as
# the first entry pointing at HEAD without a branch line).
MAIN_CHECKOUT=""
while IFS= read -r line; do
    if [[ "$line" =~ ^worktree[[:space:]] ]]; then
        path="${line#worktree }"
        # Read the next non-empty line; if it's a "branch" line
        # naming main, treat this as the main checkout.
        :
    fi
done < <(git worktree list --porcelain)

# Simpler: main checkout is the one whose path is the repo root
# without `.claude/worktrees/` in it.
MAIN_CHECKOUT=$(git worktree list --porcelain | awk '
    /^worktree / { wt = substr($0, 10) }
    /^branch refs\/heads\/main$/ { print wt; exit }
')

# Collect (worktree_path, branch) tuples.
declare -a WT_PATHS WT_BRANCHES
while IFS='|' read -r wt br; do
    WT_PATHS+=("$wt")
    WT_BRANCHES+=("$br")
done < <(git worktree list --porcelain | awk '
    /^worktree / { wt = substr($0, 10) }
    /^branch / {
        br = substr($0, 8)
        sub(/^refs\/heads\//, "", br)
        print wt "|" br
    }
')

# Categorize each worktree.
declare -a SAFE_ROWS RISK_ROWS ACTIVE_ROWS
TOTAL=0

for i in "${!WT_PATHS[@]}"; do
    wt="${WT_PATHS[$i]}"
    br="${WT_BRANCHES[$i]}"
    base=$(basename "$wt")

    # Skip the main checkout entirely.
    if [[ "$wt" == "$MAIN_CHECKOUT" ]]; then
        continue
    fi

    # Skip caller-excluded worktrees (typically the worktree the
    # briefing itself is running from).
    skip=0
    for excl in "${EXCLUDE_ARR[@]:-}"; do
        if [[ -n "$excl" && "$base" == "$excl" ]]; then
            skip=1
            break
        fi
    done
    [[ $skip == 1 ]] && continue

    TOTAL=$((TOTAL + 1))

    # Working tree state.
    dirty=0
    if [[ -n "$(git -C "$wt" status --porcelain 2>/dev/null)" ]]; then
        dirty=1
    fi

    # Unpushed commits (vs upstream).
    unpushed=0
    has_upstream=0
    if git -C "$wt" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
        has_upstream=1
        unpushed=$(git -C "$wt" log '@{u}..' --oneline 2>/dev/null | wc -l | tr -d ' ')
    fi

    # PR lookup. State = OPEN | MERGED | CLOSED | (none).
    pr_state="none"
    pr_number=""
    if command -v gh >/dev/null 2>&1; then
        pr_json=$(gh pr list --head "$br" --state all \
            --json number,state --jq '.[0] // empty' 2>/dev/null || true)
        if [[ -n "$pr_json" ]]; then
            pr_number=$(printf '%s' "$pr_json" | sed -n 's/.*"number":\([0-9]*\).*/\1/p')
            pr_state=$(printf '%s' "$pr_json" | sed -n 's/.*"state":"\([^"]*\)".*/\1/p')
        fi
    fi

    # Bucket the worktree.
    row="$base|$br|$pr_state|$pr_number|$dirty|$unpushed|$has_upstream|$wt"

    if [[ "$pr_state" == "OPEN" ]]; then
        ACTIVE_ROWS+=("$row")
        continue
    fi

    if [[ "$pr_state" == "MERGED" || "$pr_state" == "CLOSED" ]]; then
        if [[ $dirty == 0 && $unpushed == 0 ]]; then
            SAFE_ROWS+=("$row")
        else
            RISK_ROWS+=("$row")
        fi
        continue
    fi

    # No PR. Riskiest case: dirty OR has unpushed commits OR has no
    # upstream (branch may be local-only).
    if [[ $dirty == 1 || $unpushed -gt 0 || $has_upstream == 0 ]]; then
        # Special case: ahead/behind main = 0/0 with no upstream
        # is just an empty Claude session — treat as safe.
        ahead=$(git -C "$wt" rev-list --count origin/main..HEAD 2>/dev/null || echo "?")
        behind=$(git -C "$wt" rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
        if [[ $dirty == 0 && $unpushed == 0 && "$ahead" == "0" ]]; then
            SAFE_ROWS+=("$row|ahead=$ahead|behind=$behind")
        else
            RISK_ROWS+=("$row|ahead=$ahead|behind=$behind")
        fi
    else
        SAFE_ROWS+=("$row")
    fi
done

# JSON output mode (for programmatic consumption).
if [[ $JSON_MODE == 1 ]]; then
    printf '{\n'
    printf '  "total": %d,\n' "$TOTAL"
    printf '  "soft_cap": %d,\n' "$SOFT_CAP"
    for label in active safe risk; do
        case "$label" in
            active) arr=("${ACTIVE_ROWS[@]:-}") ;;
            safe)   arr=("${SAFE_ROWS[@]:-}") ;;
            risk)   arr=("${RISK_ROWS[@]:-}") ;;
        esac
        printf '  "%s": [' "$label"
        first=1
        for row in "${arr[@]:-}"; do
            [[ -z "$row" ]] && continue
            IFS='|' read -ra parts <<<"$row"
            [[ $first == 0 ]] && printf ','
            first=0
            printf '\n    {"name": "%s", "branch": "%s", "pr_state": "%s", "pr_number": "%s", "dirty": %s, "unpushed": %s}' \
                "${parts[0]}" "${parts[1]}" "${parts[2]}" "${parts[3]}" "${parts[4]}" "${parts[5]}"
        done
        if [[ "$label" == "risk" ]]; then
            printf '\n  ]\n'
        else
            printf '\n  ],\n'
        fi
    done
    printf '}\n'
    exit 0
fi

# Markdown output mode.
echo "## Worktree health"
echo ""
echo "Total: ${TOTAL} (excluding main checkout)"
if [[ $TOTAL -gt $SOFT_CAP ]]; then
    echo ""
    echo "⚠️  Above soft cap of ${SOFT_CAP}. Run cleanup."
fi
echo ""

if [[ ${RISK_ROWS[@]+x} ]]; then
    echo "### 🚨 At-risk (${#RISK_ROWS[@]}) — inspect before removing"
    echo ""
    echo "| Worktree | Branch | PR | State |"
    echo "|---|---|---|---|"
    for row in "${RISK_ROWS[@]}"; do
        IFS='|' read -ra parts <<<"$row"
        flags=""
        [[ "${parts[4]}" == "1" ]] && flags="${flags}dirty "
        [[ "${parts[5]}" != "0" ]] && flags="${flags}+${parts[5]} unpushed "
        [[ "${parts[6]}" == "0" ]] && flags="${flags}no-upstream "
        pr_disp="${parts[2]}"
        [[ -n "${parts[3]}" ]] && pr_disp="#${parts[3]} ${parts[2]}"
        echo "| \`${parts[0]}\` | ${parts[1]} | ${pr_disp} | ${flags:-clean} |"
    done
    echo ""
fi

if [[ ${SAFE_ROWS[@]+x} ]]; then
    echo "### ✅ Safe to remove (${#SAFE_ROWS[@]})"
    echo ""
    echo "\`\`\`"
    for row in "${SAFE_ROWS[@]}"; do
        IFS='|' read -ra parts <<<"$row"
        echo "${parts[0]}"
    done
    echo "\`\`\`"
    echo ""
    echo "Remove with:"
    echo ""
    echo "\`\`\`bash"
    for row in "${SAFE_ROWS[@]}"; do
        IFS='|' read -ra parts <<<"$row"
        echo "git worktree remove ${parts[7]:-${parts[0]}}"
    done
    echo "\`\`\`"
    echo ""
fi

if [[ ${ACTIVE_ROWS[@]+x} ]]; then
    echo "### 🔵 Active (${#ACTIVE_ROWS[@]}) — open PR"
    echo ""
    for row in "${ACTIVE_ROWS[@]}"; do
        IFS='|' read -ra parts <<<"$row"
        echo "- \`${parts[0]}\` → PR #${parts[3]}"
    done
fi
