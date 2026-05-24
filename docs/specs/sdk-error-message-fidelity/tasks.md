# Spec: SDK Error Message Fidelity — Tasks

**Status:** draft (2026-05-24)

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

- [ ] **3.1** Add `sdk_stderr: str | None = None` and `sdk_error_kind: str | None = None` to `Run.to_record()` / `from_record()` in `src/attune/ops/runner.py`. Existing records without the keys read back as None.
- [ ] **3.2** `RunnerService._execute()` pulls the fields off the `WorkflowResult.metadata` (set in Phase 2.3) and stores on the `Run` before persistence.
- [ ] **3.3** `src/attune/ops/templates/run_view.html` — add the collapsible `<details>` block per [design.md](design.md) § "Persistence + render".
- [ ] **3.4** `src/attune/ops/static/css/main.css` — `.sdk-error-detail` + `.sdk-error-stderr` styles. Monospace, muted background, scroll-on-overflow.
- [ ] **3.5** Tests:
  - `test_run_record_round_trips_sdk_stderr_fields` — write Run with `sdk_stderr` + `sdk_error_kind`, read back, assert equal
  - `test_run_record_back_compat_missing_sdk_fields` — old-format record without keys, read back, assert both fields are None
  - `test_run_view_renders_collapsible_stderr_when_present` — Jinja render with mock Run carrying `sdk_stderr`, assert `<details>` block in output
  - `test_run_view_omits_stderr_block_when_absent` — same with None, assert no `<details>` block

**Acceptance:** persisted runs carry the fields, dashboard renders them, back-compat holds.

---

## Phase 4 — Four-workflow fan-out (`bug-predict`, `perf-audit`, `refactor-plan`, `security-audit`)

Goal: roll the Phase 2 pattern to the remaining four high-traffic SDK workflows. Should be mechanical copy of the Phase 2 changes per workflow.

- [ ] **4.1** Apply the Phase 2.1 / 2.2 pattern to each of: `src/attune/workflows/bug_predict.py`, `src/attune/workflows/perf_audit.py`, `src/attune/workflows/refactor_plan.py`, `src/attune/workflows/security_audit.py`.
- [ ] **4.2** One `test_<wf>_surfaces_real_cause_on_subprocess_failure` test per workflow (4 tests total). Tight, mirror the Phase 2.4 shape.
- [ ] **4.3** Simplify the PR #366 chip-classifier defense-in-depth per [decisions.md](decisions.md): the log-scan heuristic stops firing when `sdk_error_kind` is set on the persisted record. Read the typed `kind` from the record and render the chip directly. Keep the log-scan as a fallback for unmigrated workflows.

**Acceptance:** all six target workflows (Phase 2 two + Phase 4 four) surface real causes. Chip classifier reads typed field when present. CI green.

---

## Phase 5 — Long-tail workflows + retrospective

Goal: cover the remaining SDK-backed workflows, then close the spec.

- [ ] **5.1** Apply the pattern to: `test-audit`, `doc-audit`, `doc-gen`, `discovery-sweep`, the `secure-release` pipeline, and `deep-review`. Same test shape per workflow.
- [ ] **5.2** Manual verification across three induced failure modes:
  - `ANTHROPIC_API_KEY=invalid` → expect "auth" classification
  - Force a 429 (or mock at the SDK boundary) → expect "rate_limit"
  - `PATH=""` → expect "not_found"
- [ ] **5.3** Update `docs/COVERAGE_BUG_LOG.md` if any bugs surfaced during Phase 1–4 implementation.
- [ ] **5.4** Close this spec. Open follow-up specs for `NextAction.kind` schema cleanup (the `learn-*` chip fix in PR #452 deferred this) and any other surface that emerges.

**Acceptance:** all 12+ SDK-backed workflows migrated. Spec marked complete. Follow-up specs noted.

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
