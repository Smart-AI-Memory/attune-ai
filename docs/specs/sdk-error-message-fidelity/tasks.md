# Spec: SDK Error Message Fidelity — Tasks
**Status:** Phases 1-5 shipped in v7.3.0 (2026-06-01); Phase 6 added for v7.4.0
> Five phases, each shipping as its own PR. Phase 1 is the recommended
> first commitment; Phases 2–5 build on it. Phase 1 can be approved
> and shipped independently — it adds the primitives without touching
> any workflow.

---

## Phase 1 — Primitives (no workflow changes yet)

Goal: ship `SdkSubprocessError`, the classifier, and the capture helper as standalone, well-tested building blocks in `agent_sdk_adapter.py`. No call sites change yet.

- [ ] **1.1** Add `SdkErrorKind` `Literal[...]` and `SdkSubprocessError` dataclass-exception to `src/attune/workflows/agent_sdk_adapter.py` per [design.md](design.md) § "SdkSubprocessError shape".
- [ ] **1.2** Add `_CLASSIFIERS` tuple table and `classify_subprocess_failure(stderr)` function. Order tuples most-specific-first so `api_quota` wins over `auth` when both patterns match.
- [ ] **1.3** Add `capture_subprocess_failure(args, env, timeout_s)` helper. Route output through `attune.security.session_redaction.redact()` before returning.
- [ ] **1.4** Add `_last_subprocess_argv(exc)` extractor that pulls the failing argv from the SDK exception. **Test against installed `claude-agent-sdk` version** — if the attribute path drifts, the test fails loud and Phase 2 stays blocked until fixed.
- [ ] **1.5** Tests in `tests/unit/workflows/test_sdk_error_fidelity.py`:
  - Classifier branches: one test per `SdkErrorKind` value (6 total — including `unknown` fallback)
  - Most-specific-wins ordering (e.g. an "API quota" message containing "401" still classifies as `api_quota`)
  - `capture_subprocess_failure` against a synthetic failing command (`["false"]` or similar) — should return non-empty redacted output
  - `capture_subprocess_failure` timeout path — synthetic sleep command, timeout=1s, asserts the "(capture-call timed out)" string
  - `capture_subprocess_failure` OSError path — invalid argv, asserts the "(capture-call also failed)" string
  - `redact()` integration — synthetic stderr containing an `sk-`-prefixed token comes out scrubbed
  - `_last_subprocess_argv` happy-path + drift guard

**Acceptance:** ≥15 unit tests, all green. Coverage on `agent_sdk_adapter.py` ≥ existing baseline + the new lines. No production behavior change (call sites still use `sdk_error_message`).

---

## Phase 2 — Two-workflow pilot (`code-review` + `dependency-check`)

Goal: replace the `sdk_error_message(exc, ...)` call in two high-traffic workflows with the new `SdkSubprocessError` flow. Validate the API + UX on a small surface before fanning out.

- [ ] **2.1** Modify `src/attune/workflows/code_review.py`'s broad-except branch per [design.md](design.md) § "Call-site integration". Pass `sdk_stderr=...` and `sdk_error_kind=...` to `_error_result()`.
- [ ] **2.2** Modify `src/attune/workflows/dependency_check.py` the same way.
- [ ] **2.3** Extend `_error_result()` on `BaseWorkflow` (or wherever it lives) to accept + thread the two new kwargs into the returned `WorkflowResult`'s metadata.
- [ ] **2.4** Tests:
  - `test_code_review_surfaces_real_cause_on_subprocess_failure` — mock `claude_agent_sdk.query` to raise the generic `Exception("Command failed ...")`, mock `capture_subprocess_failure` to return a stub stderr with "specified API usage limits", assert the returned `WorkflowResult.error` contains "Anthropic API quota reached" and NOT the legacy three-cause menu
  - Same for `test_dependency_check_surfaces_real_cause_on_subprocess_failure`
  - Happy-path regression: existing `code_review` / `dependency_check` success tests still pass unmodified

**Acceptance:** both workflows surface real causes on induced failures. CI green. No happy-path regressions.

---

## Phase 3 — Persistence + render

Goal: thread `sdk_stderr` + `sdk_error_kind` through the runner so they land in `<runs_dir>/<workflow>/<run-id>.json` and render in the dashboard.

**Split 2026-05-31** during implementation: the runner spawns the CLI as a subprocess and doesn't directly hold `WorkflowResult` objects, so the original 3.2 ("pull off WorkflowResult.metadata") requires a side-channel architectural decision (CLI emits `ATTUNE_RUN_META key=value` stdout lines à la `ATTUNE_DS` for discovery-sweep; runner parses them from the stdout stream it's already reading line-by-line). Splitting into 3a (schema + render — independent and useful) and 3b (CLI side-channel + runner consumer — wires the data flow) lets each ship as a smaller PR.

### Phase 3a — Schema + render (independent)

- [ ] **3a.1** Add `sdk_stderr: str | None = None` and `sdk_error_kind: str | None = None` to `Run` dataclass + `Run.to_dict()` / `to_record()` / `from_record()` in `src/attune/ops/runner.py`. Existing records without the keys read back as None.
- [ ] **3a.2** `src/attune/ops/templates/run_view.html` — add the collapsible `<details>` block per [design.md](design.md) § "Persistence + render". Block is no-op until 3b lands (no run has `sdk_stderr` populated yet).
- [ ] **3a.3** `src/attune/ops/static/css/main.css` — `.sdk-error-detail` + `.sdk-error-stderr` styles. Monospace, muted background, scroll-on-overflow.
- [ ] **3a.4** Tests:
  - `test_run_record_round_trips_sdk_stderr_fields` — write Run with `sdk_stderr` + `sdk_error_kind`, read back, assert equal
  - `test_run_record_back_compat_missing_sdk_fields` — old-format record without keys, read back, assert both fields are None
  - `test_run_view_renders_collapsible_stderr_when_present` — Jinja render with mock Run carrying `sdk_stderr`, assert `<details>` block in output
  - `test_run_view_omits_stderr_block_when_absent` — same with None, assert no `<details>` block

**Acceptance:** schema fields round-trip, dashboard renders when fields present, back-compat holds.

### Phase 3b — CLI side-channel + runner consumer (wires the flow)

- [ ] **3b.1** Add `src/attune/ops/run_meta_stdout.py` module mirroring `attune.workflows.discovery_sweep.ds_stdout` — `ATTUNE_RUN_META_VERSION 1` schema line, `ATTUNE_RUN_META sdk_error_kind=<kind>` and `ATTUNE_RUN_META sdk_stderr_b64=<base64>` lines, `parse_line()` helper. Env-gated via `ATTUNE_RUN_META_EMIT=1` so legitimate users piping to a file don't see the lines (see existing CLAUDE.md lesson on `ATTUNE_DS_EMIT`).
- [ ] **3b.2** `_print_workflow_result()` in `src/attune/cli_commands/workflow_commands.py` calls the emitter after printing the formatted output when `WorkflowResult.metadata` carries the keys AND `ATTUNE_RUN_META_EMIT=1` is set.
- [ ] **3b.3** `RunnerService._execute()` sets `ATTUNE_RUN_META_EMIT=1` in the subprocess env, parses each captured stdout line through `run_meta_stdout.parse_line()`, stashes the values onto `Run.sdk_stderr` / `Run.sdk_error_kind` before persistence. Emitted lines are filtered out of `run.lines` so the user-facing log doesn't show them.
- [ ] **3b.4** Tests:
  - Round-trip emitter ↔ parser (analogous to `ds_stdout` tests)
  - `_print_workflow_result` emits the line when both metadata keys + env var are present; emits nothing otherwise
  - `RunnerService._execute()` end-to-end with a synthetic command that emits the side-channel lines — verify `Run.sdk_stderr`/`Run.sdk_error_kind` populated and the marker lines absent from `run.lines`

**Acceptance:** induced subprocess error in any Phase 2 workflow surfaces the redacted stderr + classified kind on the run-view page.

---

## Phase 4 — Four-workflow fan-out (`bug-predict`, `perf-audit`, `refactor-plan`, `security-audit`)

Goal: roll the Phase 2 pattern to the remaining four high-traffic SDK workflows. Should be mechanical copy of the Phase 2 changes per workflow.

- [ ] **4.1** Apply the Phase 2.1 / 2.2 pattern to each of: `src/attune/workflows/bug_predict.py`, `src/attune/workflows/perf_audit.py`, `src/attune/workflows/refactor_plan.py`, `src/attune/workflows/security_audit.py`.
- [ ] **4.2** One `test_<wf>_surfaces_real_cause_on_subprocess_failure` test per workflow (4 tests total). Tight, mirror the Phase 2.4 shape.
- [ ] **4.3** Simplify the PR #366 chip-classifier defense-in-depth per [decisions.md](decisions.md): the log-scan heuristic stops firing when `sdk_error_kind` is set on the persisted record. Read the typed `kind` from the record and render the chip directly. Keep the log-scan as a fallback for unmigrated workflows.

**Acceptance:** all six target workflows (Phase 2 two + Phase 4 four) surface real causes. Chip classifier reads typed field when present. CI green.

---

## Phase 5 — Long-tail workflows (shipped 2026-06-01)

Goal: cover the remaining SDK workflows that still used the legacy `sdk_error_message` helper.

**Scope correction (2026-06-01):** Phase 5 originally named `test-audit`, `doc-audit`, `doc-gen`, `discovery-sweep`, `secure-release`, and `deep-review` as the six targets. During implementation we found that only `deep-review` actually used the legacy helper — the other five had hand-rolled error messages (`"Agent SDK error: <type>: <exc>"`) that don't surface the misleading three-cause menu. Five DIFFERENT workflows DID use the legacy helper (per the spec-named-work-scope-drifts-from-code-reality lesson). PR #544 shipped the actually-broken set; the spec-named hand-rolled-message workflows move to Phase 6.

- [x] **5.1** Apply the pattern to: `simplify-code`, `deep-review`, `research-synthesis`, `rag-code-gen`, `release-prep`. (PR #544 — shipped 2026-06-01.)
- [x] **5.2** Manual verification deferred — Patrick's `claude` CLI auth was broken in-session, making the invalid-auth case trivially redundant. Test mocks cover all three classification paths. Will re-verify when next running a live SDK workflow.
- [x] **5.3** No new bugs surfaced during Phase 1–4 implementation. COVERAGE_BUG_LOG.md unchanged.
- [x] **5.4** Phases 1-5 shipped in v7.3.0 (2026-06-01). Phase 6 added below.

**Acceptance:** 11 of 16 SDK-backed workflows migrated (Phase 2: 2 + Phase 4: 4 + Phase 5: 5). Helper `sdk_error_message` still exists for Phase 6 workflows; deletion happens after Phase 6.

---

## Phase 6 — Hand-rolled-message workflows (v7.4.0 candidate)

Goal: extend the typed-kind SDK error flow to the remaining 5 SDK workflows that have hand-rolled error messages instead of the legacy helper.

These workflows don't have the misleading three-cause menu — they fail with `"Agent SDK error: <type>: <exc>"`. Less bad than the legacy menu but still less rich than the typed-kind flow.

- [ ] **6.1** Apply the pattern to: `test-audit`, `doc-audit`, `doc-gen` (if it has a separate SDK workflow file), `discovery-sweep`, `secure-release` pipeline. Same test shape per workflow.
- [ ] **6.2** Once all 16 SDK workflows are migrated, delete the `sdk_error_message` helper from `agent_sdk_adapter.py`. Update its `__all__` export to remove the legacy name. Add a drift-guard test that grep-fails if any workflow re-imports `sdk_error_message`.
- [ ] **6.3** Close this spec. Open follow-up specs for `NextAction.kind` schema cleanup (the `learn-*` chip fix in PR #452 deferred this) and any other surface that emerges.

**Acceptance:** All 16 SDK-backed workflows migrated. Helper deleted. Spec marked complete.

---

## Out of scope (parking lot)

- Forking or upstream-patching `claude-agent-sdk` — explicit non-goal per [decisions.md](decisions.md)
- Retry/backoff on transient errors — surface, don't recover
- Table-driven classifier with per-project overrides — defer until classifier exceeds ~8 entries
- Exit-code propagation — sibling spec [`workflow-failure-exit-propagation`](../workflow-failure-exit-propagation/) owns it
- Predicting every possible error class — five-shape menu + unknown fallback is the v1 surface

---

## Rollback plan

Each phase is a single squash-merge commit. Rollback = `git revert <commit>`. Phase ordering is designed so reverting later phases leaves earlier phases working:

- Revert Phase 5 → six workflows still on the new pattern, long-tail workflows on the old `sdk_error_message`
- Revert Phase 4 → two workflows on new pattern, chip classifier reverts to log-scan-only
- Revert Phase 3 → workflows still classify errors, but persistence + render fall back to the legacy "error" string
- Revert Phase 2 → no call sites use the new primitives; classifier + capture helper are dead code in `agent_sdk_adapter.py` (test coverage flags but doesn't fail)
- Revert Phase 1 → back to current behavior; no schema changes to migrate back
