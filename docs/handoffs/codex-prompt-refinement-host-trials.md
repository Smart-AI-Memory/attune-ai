# Agent work handoff

## Goal and acceptance

Execute issue #2455 live CLI trials and bounded policy refinements. Preserve
failures and distinguish lifecycle/state receipts from model behavior, desktop
rendering, and human outcomes. Normal preferences remain untouched.

## Scope

Branch codex/prompt-refinement-host-trials in /private/tmp/attune-prompt-refinement,
based on fetched main 705004a8a. PR #2454 is merged. Issue #2455 remains open for
installed desktop and human trials. No cached plugin or normal config was changed.

## Evidence and current state

See docs/specs/prompt-refinement/live-host-trials.md and its linked manifests,
observations, and event ledger: 41 attempts, 40 response records; all eleven
native Codex turns and eleven baseline Claude turns received hook state.
MCP-only Codex did not reliably check policy per turn. Metadata experiment was
reverted. Shared guidance now limits initial keyboard questions and preserves
format, approval wording, and labeled proposed scope.

## Verification receipts

- collaboration_preflight.py: 87 passed, no failures.
- Central prompt-refinement/MCP/SDK-guard/generated-help suites: 130 passed.
- Evidence validator: 41 records, both eleven-hook matrices, transitions,
  frozen case hash, raw permissions verified; isolated preferences cleaned up.
- Initial advisory review: three findings accepted and corrected. Final explicit
  GPT-5.6 Sol review: reviewer identity clarified; no code/evidence defects.
- Additional ledger/brand suites: 12 passed; pinned pre-commit checks passed.
  MkDocs build unavailable because the existing environment lacks the module.
- Final compressed wording passed local tests; live samples used the separately
  hashed longer wording. No causal improvement or installed desktop claim.

## Next action

Commit and open the reviewed phase PR. Keep
#2455 open for normal installed hook trust and desktop/human validation. Remove
private raw trial directory after phase PR review is resolved; retain sanitized
tracked evidence. Do not merge without current authorization.
