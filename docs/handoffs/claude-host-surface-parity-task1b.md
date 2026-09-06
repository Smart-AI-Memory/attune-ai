# Agent work handoff

> **Task 1B, increment 1 — landed by Claude 2026-09-06 under the chair's
> "go 1B".** Chair ruling the same evening (form): **Codex executes the
> remaining increments; Claude reviews.** This file is Codex's entry point.
> Verify it against the current Git state and the tests before continuing —
> a handoff is context, not authority.

## Goal

Land host-surface-parity **Task 1B** (context-routed surface parity gate,
R2) on top of a released attune-forms that carries AF-1's renderer registry.

## Acceptance criteria

Every `<check>` in `docs/specs/host-surface-parity/tasks.md` § Task 1B.
Increment 1 satisfies only the discovery-side checks (producer_baseline,
path-aware manifest resolution, closed shell resolver, event-qualified
envelope signatures, alias/helper mutations, order permutation, new
command discovery, attune_redis root). Everything else is open.

## Scope and assumptions

- Branch `claude/host-surface-parity-task1b`; PR opened from it.
- STOP precondition (task objective) was taken against the **PyPI-installed
  attune-forms 0.14.0** in a pristine venv: not editable, 7 registry targets,
  production `workspace_to_headless`, every canonical fixture executed. The
  receipt JSON is quoted in the PR body. AF-1's version was 0.13.0 in the
  task text; D12 shifted it to 0.14.0 because 0.13.0 shipped without AF-1.
- Zero spend (D8). Coverage floor 90% on changed code (D7).

## Current state

- `src/attune/elicitation/surface_inventory.py` — the discovery scanner
  (shipped roots from packaging metadata; closed shell resolver; renderer
  calls in direct / `attune.elicitation` re-export / qualified-alias forms;
  helper reachability with `root -> helper` edges, indexing sibling helpers
  on demand; closed package envelope signatures; closed event-qualified hook
  envelope signatures; fail-closed problems).
- `docs/specs/host-surface-parity/producer_baseline.json` — the reviewed
  execution-base fixture. Hand-calibrated: every anchor is a true positive.
  It found the design's six renderer anchors / seven sites, D6's three
  `additionalContext` hooks, seven exit-2 guards, six SessionStart context
  hooks, and two producers the design never listed
  (`src/attune/widgets/chart_widget_tool.py:render_chart_widget`,
  `src/attune/mcp/workflow_handlers.py:_workflow_response`).
- `tests/unit/gates/test_surface_parity.py` — baseline equality + mutation
  receipts (54 tests). The gate is discovery-only; it claims nothing about
  parity yet.
- `pyproject.toml` floor `attune-forms>=0.14.0,<1.0`; `uv.lock` regenerated.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| STOP precondition | pristine venv, `env -i`, cwd `/tmp`, attune-forms from PyPI: registry, headless target, fixtures | 0.14.0, editable=False, 7 targets, 7 fixtures |
| Scan == reviewed baseline | `tests/unit/gates/test_surface_parity.py::test_scan_matches_the_reviewed_baseline` | pass |
| Scanner not vacuous | every mutation test in the same file (six call syntaxes, helper indirection, wrong-event envelope, unresolvable mapping, dynamic sink, unknown variable, path escape, order permutation, new command) | 54 passed |
| Changed code ≥ 90% | `--cov=attune.elicitation.surface_inventory` | 95.8% |
| Floor bump behaviour delta | `tests/unit/elicitation` + MCP elicitation handler tests on 0.14.0; forms mirrors `scripts/sync_forms_mirrors.py --check` | 572 passed; in sync |
| Whole tree | `pytest tests -n auto` | see PR body (run recorded there) |

## Next action (Codex)

In dependency order, each increment its own PR against the 90% floor:

1. **Parity registry + receipts ledger + contract enforcer.** Create
   `docs/specs/host-surface-parity/parity-registry.json` (subject records for
   every anchor in `producer_baseline.json`, cold/warm routes, obligations,
   normalization paths, experiments) and `receipts.md`; extend
   `tests/unit/gates/test_surface_parity.py` with the registry/lifecycle/
   experiment/mutation gates; add the surfaces enforcer to
   `content/collaboration/contract.md` and run
   `scripts/project_collaboration_contract.py`. Fold the held Task 4b
   observation (`docs/probes/host-surface-parity/codex-native-receipt-2026-09-06.md`)
   into `receipts.md` as its R4b block.
2. **`surface_policy.py` + receipt store + `_handle_elicitation_route_form`.**
   The 23-row context table, capability snapshot, receipts/submission
   tokens, challenge dispositions, `tool_schemas.py` closed union, tests
   named in the task.
3. **`.github/workflows/cross-repo-compat.yml`** — advisory fresh-resolution
   jobs; never replaces the locked gate (`tests/unit/ci/` gates apply:
   timeouts, pinning, concurrency, keyless).

Claude reviews each PR (different-model lane by construction).
