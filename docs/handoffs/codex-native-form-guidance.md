# Agent work handoff

## Goal

Finish Codex built-in question guidance after #2450, with Attune forms
experimental and Antigravity using enhanced prompts by default.

## Acceptance criteria

Canonical guidance and projections agree; questions preserve answers and
corrections, respect cancellation, and remain pending while needed. Desktop
claims require actual observed host trials, not merely text assertions.

## Scope and assumptions

- Branch: codex/native-form-guidance, based on origin/main 4a8bd9c0c.
- Worktree: this task's isolated Codex checkout; dirty main untouched.
- Tier: structured one-shot under host-surface-parity D15.
- No release, auto-merge, new renderer, or durable answer storage.

## Current state

- Canonical elicit/planning skills now select Codex built-in questions and
  explain asynchronous lifetime, partial replies, correction, and cancellation.
- Antigravity native controls remain experimental after user keyboard issues.
- Claude's compatibility guidance is unchanged. Its lead should verify current
  native controls and implement the Claude-specific mapping separately.
- Mirrors and generated reference help have been reprojected.
- Evidence lives in the September 7 host-native probe; desktop acceptance of
  the revised guidance remains open pending actual trials.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Starting checkout safe | collaboration_preflight.py | 87 governance tests passed; clean task, dirty main preserved |
| Current base | git fetch origin main | advanced origin/main to 4a8bd9c0c before creating branch |
| Canonical projections | sync_agents_skills.py --write and generate_reference_templates.py | completed; only intended skills/references changed |
| Projection freshness | both projectors with --check | passed |
| Existing guidance/skill checks | CI venv pytest: test_sync_agents_skills.py and test_adaptive_review_guidance.py and test_ledger_rejection_format.py, --no-cov -n 0 | 61 passed |
| Diff whitespace | git diff --check | passed |
| Independent Claude review | explicit user-authorized subscription-only review of diff plus handoff/evidence | completed; 12 findings dispositioned in cross-review ledger, F1 premise rejected against exposed host contract, other guidance clarified |
| Revised guidance behavior | fresh desktop trial | not yet run |

## Next action

Validate the revised Codex native-question interaction with Patrick, including
fresh-task discovery. First ensure the receiving task loads this branch's
edited guidance: the bakery trial at 12:29 used old main (4a8bd9c0c), not
this branch’s revised guidance, so it cannot certify the revision. Do not repeat
the recording request until that setup is verified. The in-task feedback card was posted successfully but no
answers were received before Patrick said to proceed; do not count that as a
keyboard-test pass. Preserve incomplete acceptance; do not call full host parity
or release readiness complete. Claude's authorized review is preserved locally
under /private/tmp/native-form-guidance-review/claude-review.json.

Default Python's attune-rag installation could not import model_tiers during
collection. The existing /private/tmp/attune-2450-ci-venv/bin/python passed all
61 tests with absolute PYTHONPATH pointing to this worktree's src. No dependency
or production runtime changed to accommodate that environment issue.
