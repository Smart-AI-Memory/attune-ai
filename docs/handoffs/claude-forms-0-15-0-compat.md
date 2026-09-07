# Agent work handoff

## Goal

attune-ai pins and passes against attune-forms 0.15.0 (host-surface-parity
AF-2, released 2026-09-07), with the package's new route-active
`form.host_question` target accounted for the way the approved AF-2 boundary
says: absent and ineligible until Task 2 registers the host profile and
adapter, never red, never satisfied by compatibility evidence.

## Acceptance criteria

- `pyproject.toml` floors `attune-forms>=0.15.0,<1.0`; `uv.lock` pins 0.15.0.
- Full tree (`pytest tests`) green locally against 0.15.0.
- `scripts/project_surface_runtime.py` (check mode) reports the packaged
  runtime registry in sync; renderer receipts re-locked to the 0.15.0 artifact.
- The parity gate derives no obligation for a route-active target whose
  `profile_id` is not in `host_profiles`, does not replay it, and rejects a
  receipt or pending row for it (tests pin all three).
- Router tests and the `elicitation_render_form` surface note follow the
  host-native default (D17).
- A different-model (Codex) review lane runs before the chair reads (D11:
  gate logic and receipts are enforcement surfaces).

## Scope and assumptions

- Branch/worktree: `claude/forms-0-15-0-compat` in
  `.claude/worktrees/attune-host-native-questions-3a81df`, off origin/main
  f80352f16.
- Provider/session: Claude (lead) executes at the chair's direction
  (2026-09-07, option 2); Codex reviews.
- Assumptions: the AF-2 handoff text ("the consuming attune-ai obligation is
  absent and ineligible — not red — until Task 2 locks the released artifact")
  is the ruling this encodes; the increment-2 rule that package-renderer
  evidence cannot be *waived* is untouched (a pending row for a `renderer:`
  key still fails). Task 2 itself is out of scope.

## Current state

- Status: implemented and verified locally; PR open for the Codex D11 lane.
- Changed files: `pyproject.toml`, `uv.lock`,
  `src/attune/elicitation/surface_registry.py`
  (`route_active_without_profile`, `_enhanced`, receipt owners),
  `src/attune/elicitation/surface_evidence.py` (replay skips route-active
  targets instead of raising), `src/attune/mcp/server.py` (surface note text),
  `docs/specs/host-surface-parity/parity-registry.json` (renderers re-locked,
  receipts refreshed), `src/attune/elicitation/surface_runtime_registry.json`
  (projection), `tests/unit/gates/test_surface_parity.py`,
  `tests/unit/elicitation/test_select_form_surface.py`, `CHANGELOG.md`.
- Decisions: the "absent" state is keyed on `host_profiles` membership, so
  registering the `claude-askuserquestion` profile is the single act that
  makes the obligation exist (Task 2's first step).
- Risks or open questions: `docs/specs/host-surface-parity/decisions.md`
  D17 (PR #2464) and this PR both touch CHANGELOG Unreleased; land
  sequentially (D13a). The route-active target is inventoried but not routed;
  `surface_policy` has no host-native arm until Task 2.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Lock pins 0.15.0 | `grep -A1 'name = "attune-forms"' uv.lock` | pass: version = "0.15.0" |
| Gate green against 0.15.0 | `pytest tests/unit/gates/test_surface_parity.py tests/unit/elicitation tests/unit/mcp/test_server_elicitation.py tests/unit/telemetry/test_form_events.py` | pass: 941 passed (was 15 failed, 14 errors before the change) |
| Projection in sync | `python scripts/project_surface_runtime.py` (check mode, exit code checked) | pass, after running `--write` LAST: the native receipts digest the edited modules' source |
| Full tree | `pytest tests` | pass: 26,087 passed, 266 skipped, 3 xfailed (99 s) |
| Pre-commit | black, ruff, whitespace on every changed file | pass |

## Next action

Codex: review this branch against the AF-2 boundary text and the D11 risk
class; report findings, do not push. Then the chair reads and merges; then
16.3.0 release prep.
