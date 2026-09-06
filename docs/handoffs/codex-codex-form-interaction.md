# Agent work handoff

## Goal

Advance the approved Task 1B increment-3 Codex form interaction.

## Acceptance criteria

One same-task validated interaction, exactly-once completion, negative
lifecycle and trust-boundary tests, and measured actual host display/submission.

## Scope and assumptions

- Branch: codex/codex-form-interaction; base a9e98f671.
- Worktree: /private/tmp/attune-codex-form-interaction-20260906.
- D14 lifts the increment-3 hold only for the bounded milestone.
- Zero API spend; manual merge; no unrelated worktree changes.

## Current state

Plan status and executable package prerequisites reconciled. Initial policy,
receipt store and native runtime implemented; public handler is discoverable
but returns no_supported_surface without a server-installed runtime. No
production evidence snapshot or installation-key provisioning is installed.
Production parity and live host acceptance are not complete.

Changed surfaces: surface_policy.py, surface_runtime.py, server.py,
tool_schemas.py, elicitation exports, behavioral/stdIO tests, producer baseline
and registry, existing capability projections, and plan/receipt documents.
Two same-provider advisory reviews found six defects, all fixed with negative
tests; no different-model or live-host acceptance receipt is claimed.

## Verification

- Preflight: 87 governance tests passed; dirty main left untouched.
- Released non-editable forms 0.14.0: seven targets enumerated and three
  canonical renderer evidence receipts replayed before mutation.
- origin/main fetched and verified at a9e98f671; no open sibling PRs.

## Next action

Continue the authorized milestone: implement trusted production evidence/key
bootstrap and session-teardown wiring, satisfy route evidence requirements,
then collect actual Codex cold/warm display and submission measurements.
Do not enable routing with synthetic reports. The six new producer obligations
remain pending (161 total). Deferred host adapters and full Task 1B remain open.

Local receipts: /private/tmp/form-interaction-coverage.log (72 passed, 95.04%),
/private/tmp/form-interaction-gates.log (806 passed),
/private/tmp/form-interaction-registration.log (94 passed),
/private/tmp/form-interaction-hooks.log (pinned hooks), and
/private/tmp/form-interaction-whole.log (full suite). The full-suite wrapper
/private/tmp/run_form_interaction_suite.py isolates Redis and provider credentials.
Use PYTHONPATH=src with the existing interpreter at
/Users/patrickroebuck/.codex/worktrees/9c6c/attune-ai/.venv/bin/python.
The pre-commit help hook needs UV_NO_SYNC=1 and that existing venv to avoid
creating a new environment; UV_CACHE_DIR=/private/tmp/attune-form-uv-cache.
The real MCP stdio test uses only fixture-owned answers and installs the
committed inference guard. It is not evidence of native paint.


Final local verification: whole configured tree 26,017 passed, 242 skipped,
3 xfailed (70.63s); pinned hooks passed. No API-backed review, host display
claim, merge, or release. The tool remains registered (stable core inventory)
and fails closed until a trusted runtime is installed.
