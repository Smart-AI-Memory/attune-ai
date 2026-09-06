# Agent work handoff

## Goal

Advance the approved Task 1B increment-3 Codex form interaction in draft #2450.

## Acceptance criteria

Same-task validated interaction, exactly-once completion, negative lifecycle
and trust-boundary tests, and actual Codex display/submission measurements.

## Scope and assumptions

- Branch: codex/codex-form-interaction; base a9e98f671.
- Worktree: /private/tmp/attune-codex-form-interaction-20260906.
- D14 authorizes this bounded milestone. Zero API spend; manual merge.
- Main and other worktrees are untouched. #2444/#2449 are already merged.

## Current state

The stdio composition root now replays packaged evidence, validates exact
route obligations and provisions a private POSIX installation key before
installing the native runtime. Eight obligations are verified (three package,
five new native); 159 remain pending. Each replay crosses paired real SDK
streams; the child-process receipt also uses normal production bootstrap.
No all-verified synthetic report authorizes production routing.

The distinct surface-native-elicitation transport owns its lifecycle evidence.
Explicit route projection bindings preserve pending RICH/deferred obligations.
The timeout contract is server-deadline => render_failed, no new receipt.
The closed MCP output schema is enforced through structuredContent; the voice
formatter is skipped for this protocol response. Transport exit closes and
detaches runtime state. Acceptance, cancellation, malformed/duplicate/late
answers, expiry, shutdown and validation races have negative regressions.

Only the installation key survives restart. Windows activation fails closed
until a private credential-store/ACL adapter exists. Policy-warm public native
trials are unavailable: terminal completions expose no warm successor. Do not
relabel process reuse as policy warmth. Actual host paint/human submission is
still missing; keep the PR draft and do not claim the milestone complete.

## Verification

- Session preflight: 87 passed; dirty main preserved.
- Focused runtime/gate coverage: 338 passed, 95.84% over seven relevant modules.
- Gates/quality: 662 passed before final lifecycle changes; final whole run
  includes these guards. Complexity regression was refactored and five checks passed.
- Two full-run failures were diagnosed: the tool-list test needed the newly
  declared output_schema; three cost-default tests now use an empty private
  patterns directory instead of concurrently created/deleted repository files.
  Adjacent suites: 79 passed. No unrelated production code changed.
- Wheel built offline from cached build dependencies. Its normal stdio entry
  accepted decision/minutes/outcome with one render and one presentation,
  loaded forms 0.14.0 + MCP 1.28.1, and enforced the output schema.
- Wheel: /private/tmp/attune-form-preview-20260906/dist/attune_ai-16.2.1-py3-none-any.whl
- Wheel SHA256: 1109fcaaa3b1a275f798f278d4f693382691f13dc698c5d8a35f88b346fb9200
- Artifact receipt: /private/tmp/attune-form-preview-20260906/probe-home/receipt.json
  (fixture-owned answers; host_paint=false).
- Different-model read-only risk review: review_bootstrap_contract, gpt-5.6-sol,
  evidence-chain receipt; dispositions in the spec and cross-review ledgers.

## Next action

Finish current checks/push, configure the verified preview artifact, then
reload the preview MCP server in Codex and collect the actual host interaction.
No callable elicitation_route_form exists in the currently loaded old server.
Follow the existing milestone measurement brief; leave unavailable strata open.

## Commands and logs

Use PYTHONPATH=src with
/Users/patrickroebuck/.codex/worktrees/9c6c/attune-ai/.venv/bin/python.
Full suite wrapper /private/tmp/run_form_interaction_suite.py isolates Redis and
provider credentials. Logs: /private/tmp/form-bootstrap-whole.log,
/private/tmp/form-final-coverage.log, /private/tmp/form-bootstrap-hooks.log,
/private/tmp/form-wheel-probe.log. Pre-commit needs UV_NO_SYNC=1,
UV_PROJECT_ENVIRONMENT set to that venv and
UV_CACHE_DIR=/private/tmp/attune-form-uv-cache.
After any native code/fixture formatting, refresh executed receipts and their
single-source package projections with scripts/project_surface_runtime.py --write.

Final whole-suite receipt: 26,056 passed, 242 skipped, 3 xfailed in 73.04s.
