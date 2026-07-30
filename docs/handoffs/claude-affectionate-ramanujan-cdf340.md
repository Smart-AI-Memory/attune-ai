# Agent work handoff

## Goal

The retired category framing ("workflow" + "OS") (ratified out
2026-07-29 in favor of "AI Workflow-harness") cannot re-enter
living surfaces: G5 (`scripts/check_brand_drift.py`) blocks it as
a hard-tier token, with fires-on-violation tests.

## Acceptance criteria

- `scripts/check_brand_drift.py` hard-fails on the retired framing
  (case-insensitive, hyphen/wrap tolerant) outside the documented
  historical exclusions.
- `tests/unit/gates/test_brand_drift.py` proves fire, non-fire
  lookalikes, and exclusions.
- The live tree passes the gate once PR #1766 (ops +
  API_REFERENCE sweep) and this branch are both on main.
- Cross-review run per D11b (governance-surface diff).

## Scope and assumptions

- Branch/worktree: `claude/affectionate-ramanujan-cdf340` in
  `.claude/worktrees/pr-spec-completion-metrics-02e786`
- Provider/session: Claude (lead), autonomous session 2026-07-29
- Assumptions: PR #1766 merges first and owns the sweep of
  `src/attune/ops/__init__.py`, `src/attune/ops/templates/home.html`,
  `docs/reference/API_REFERENCE.md`. This branch swept the four
  stragglers #1766 missed.

## Current state

- Status: gate + tests + straggler sweep committed (683c77c8d);
  waiting on #1767 (Windows countersign skip hotfix) then #1766
  before push/PR.
- Changed files: `scripts/check_brand_drift.py`,
  `tests/unit/gates/test_brand_drift.py`,
  `.claude/plans/attune-author.md`, `attune-ai-dev/build_og.py`,
  `plugins/attune-author/README.md`, `plugins/attune-help/README.md`
- Decisions: hard tier (not ratchet) — post-sweep the phrase has
  zero legitimate living instances, so no allowlist is needed.
  Regex `workflow[\s-]+os\b` keeps `workflows`/`OSS`/`OSes` out.
- Risks or open questions: main's Windows lanes were broken by the
  D11c countersign chmod test (all PRs red) — hotfix PR #1767.
  `website/public/` mirror still carries the phrase until the
  framework-docs rebuild regenerates it from the swept docs
  (excluded surface, self-heals on main).

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Gate fires on variants, passes lookalikes/exclusions | `pytest tests/unit/gates/test_brand_drift.py -o addopts=` | 10 passed |
| Live tree post-#1766 has no other violations | `python scripts/check_brand_drift.py` on this branch | fails ONLY on the 3 #1766-owned files |
| Windows break is the countersign chmod test | `gh run view 30504640717 --log-failed` | DID NOT RAISE on all 5 lanes |

## Next action

When #1766 is merged: `git merge origin/main`, run
`python scripts/check_brand_drift.py` (must exit 0), push, open PR,
run `/cross-review` per D11b, delete this handoff on merge.
