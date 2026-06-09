# Phase 1 triage — reviving the dormant integration suite (2026-06-09)

Phase 0 ([phase0-findings.md](phase0-findings.md)) decided **GO, reframed**:
revive the existing 351-test suite, don't build new infra. Phase 1 is
prune → wire. This doc records the prune + the verified state so the CI
job (next PR) wires a known-green subset.

## Done this PR — prune the dead

Deleted two test files referencing modules/dirs that no longer exist
(they broke collection / failed wholesale, pure rot from never running):

- `test_tier1_api.py` — imported `dashboard.backend.api` (the dashboard
  backend was removed ~3 months ago). Broke collection of the subtree.
- `test_vscode_python_bridge.py` — exercised the `vscode-extension/`
  (removed; see CLAUDE.md "vscode-extension no longer exists"). 6 fails.

## Verified state — true keyless run (CI-representative)

`pytest tests/integration -m "" -k "not with_auth"` with
`ANTHROPIC_API_KEY` **unset** (matches keyless CI), 2 dead files removed:

**302 passed · 16 failed · 18 skipped.**

(Note: with a key set locally, a few more "fail" because some no-auth
tests opportunistically call the real API — including one surfacing the
Opus-4.8 `max_tokens` vs `thinking.budget_tokens` 400. Keyless is the
CI-true number.)

## Cleanup backlog — the 11 files still red (next PRs, before wiring as required)

| File | Cause (sampled) | Fix shape |
|---|---|---|
| `test_discovery_sweep_{bug_predict,dependency_check,doc_audit,perf_audit,security_audit,test_audit}_integration.py` (×6) | **Timeout >25s / worker crash** — real heavy workflow analysis on fixtures | longer timeout + serialize (not `-n`), or trim fixtures |
| `rag/test_rag_workflow.py` | Stale assertion — asserts the **pre-#543** error-result shape | update to the sdk-error-message-fidelity shape |
| `test_tier1_tracking.py` (×3) | (to triage) | — |
| `test_graceful_degradation.py` (×3) | (to triage) | — |
| `test_llm_integration.py` (×2) | (to triage; some are real-API-shaped) | mock the boundary or mark auth-gated |
| `test_telemetry_integration.py` (×1) | (to triage) | — |

## Next (the CI job)

Wire a CI job (likely a separate `integration-tests.yml`, **non-required**
initially) that runs the **green subset** (the ~9 passing no-auth files),
keyless, `--timeout` + serialized for the slow ones, so 300+ tests run on
every PR and stop rotting. Promote to required once the 11-file backlog is
cleared. The 8 auth-required files → opt-in nightly / `workflow_dispatch`
gated on `ANTHROPIC_API_KEY`.
