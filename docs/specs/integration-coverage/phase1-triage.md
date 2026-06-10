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

## Cleanup backlog — CLEARED (2026-06-09, follow-up PR)

Full triage verdict: **zero production bugs** — every red file was a
stale test or broken test infrastructure. The fixes:

| File | Root cause (verified) | Fix |
|---|---|---|
| `test_discovery_sweep_*_integration.py` (×6) | NOT timeouts — these hit the **real Anthropic API by design** ("Hits the real Anthropic API" in each docstring; keyless they spawn the subscription `claude` CLI → prose instead of stream-json, ~105 s, then fail). Pre-date the keyless CI job. | Env-gated: `pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"))` — they join the auth bucket and skip keyless. |
| `rag/test_rag_workflow.py` (×1) | Stale **pre-#543** error-shape assertion (`"Agent SDK failure"`). | Updated to the #543 fidelity shape: `"claude CLI subprocess failed"` + `metadata.sdk_error_kind == "unknown"`. |
| `test_tier1_tracking.py` (×1) | **Three-layer fixture rot**: (a) `mock_telemetry_dir` reset `_telemetry_store`, but a refactor renamed the singleton to `_store_instance` — isolation silently inert; (b) `TelemetryStore()` defaults to cwd-relative `.attune/` so tests polluted a real dir; (c) `_read_jsonl` returns oldest-first, so `executions[0]` ("latest") read a stale `workflow_id=None` record. `EMPATHY_TELEMETRY_DIR` is a ghost env var (read nowhere). | Fixture now monkeypatches `_store_instance` with a temp-dir store. |
| `test_graceful_degradation.py` (×3) | (a+b) Production moved from `raise ImportError` to **graceful degradation** (facade auto-falls-back to mock mode; coordinator sets `_degraded` + warns) — tests asserted the old contract; the `attune.memory.is_redis_available` patch target was also stale (production checks `MemoryFeatures.check_redis`). (c) `UsageTracker` buffers writes (`buffer_size=50`) — asserting `usage.jsonl` exists after one call needs a `flush()`. | Rewrote the two redis tests to assert degradation; added `tracker.flush()`. Fixed the coordinator's stale "Raises ImportError" docstring (only production change, docs-only). |
| `test_llm_integration.py` (×1) | Real-API test (`test_thinking_mode`) — only fails when a key leaks in from `~/.attune/anthropic.env` via `load_dotenv` (env var **unset**). With CI's `ANTHROPIC_API_KEY: ""` (empty) it skips correctly. | No change needed for keyless CI. (Its Opus-4.8 `max_tokens` vs `thinking.budget_tokens` 400 is the nightly-auth job's concern.) |
| `test_telemetry_integration.py` (×1) | Tested **removed functionality**: client-side response cache (mocked `workflow._cache`, which nothing reads — `_try_cache_lookup` is a permanent no-op since the semantic-cache retirement). | Rewrote to patch `_try_cache_lookup` directly, exercising the live cache-hit telemetry branch in `_call_llm`. |

Verified: `pytest tests/integration -k "not with_auth"` keyless →
**295 passed · 41 skipped · 0 failed (6 s, `-n auto`)**.

## CI job — wired, then promoted to the full suite

`.github/workflows/integration-tests.yml` (#704) ran an explicit
green-subset file list; with the backlog cleared it now runs
`tests/integration -k "not with_auth"` (job name
`integration (no-auth)`). Still **non-required** — promote to a
required check after a few weeks of green runs. Remaining follow-up:
the auth bucket (8 `*_with_auth` files + the 6 env-gated
discovery_sweep files) → opt-in nightly / `workflow_dispatch` gated on
`ANTHROPIC_API_KEY`.
