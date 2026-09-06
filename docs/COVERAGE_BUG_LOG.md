## 2026-08-01 — waves 2–6 of the coverage fleet (Sonnet lanes, Fable 5 lead)

Twelve more tests-only lanes (waves 2–6, PRs #1855–#1870; hybrid
routing — Sonnet seats, all receipts re-run centrally by the
lead). One production bug:

- **`authoring/fact_check/numeric_refs.py:75` — Class 2-adjacent
  (permanently dead check behind a broad except).** `_count_kinds`
  does `from attune.authoring.source_introspection import KINDS` —
  the symbol exists NOWHERE in the tree (repo-wide grep; the
  line's own `# type: ignore[attr-defined]` was the mask). The
  import always raises, the function always returns None via
  `except Exception`, and every "N kinds" numeric claim in prose
  has been silently unverifiable since authoring — a fact-checker
  whose check never ran. Found by the wave-6 Sonnet lane (#1869);
  fix is small (import the real registry or delete the check) and
  pickable post-demo. Third instance tonight of the
  `type: ignore`-masks-a-real-defect pattern (facade.py's two).

Notable non-bug findings: parser.py PyYAML-fallback and loader.py
default-path branches covered with real degraded-env triggers; the
executor lane's CancelledError-under-coverage-tracing authoring
hazard (lessons-queued); numeric_refs' Unicode-digit ValueError
guard proven unreachable through the public API.

## 2026-08-01 — six-lane coverage fleet (delegated lanes, Fable 5 lead)

Six parallel tests-only lanes (memory/short_term/facade,
memory/cross_session/coordinator, telemetry/approval_gates,
roundtable/triage_appendix, elicitation/fix_intake,
learning/storage — PRs #1848–#1853; all receipts re-run centrally
by the lead). Coverage: 80.5→99, 79.2→100, 78.8→100, 81.8→100,
83→99 (measured-first, stale Codecov refs), 80.7→100. Three
production bugs surfaced, all in `memory/short_term/facade.py`,
all currently masked by `# type: ignore`:

- **facade.py:187 — Class 1 (silent wrong behavior).**
  `DataSanitizer(self._base)` passes a `BaseOperations` instance
  into the `pii_scrub_enabled: bool` parameter — truthy, so PII
  scrubbing is silently ALWAYS enabled via the facade,
  `secrets_detection_enabled` is never wired, and the sanitizer's
  metrics land in a fresh `RedisMetrics` instead of the shared one.
- **facade.py:697 — Class 1 (misbind on the real path).**
  `enable_cross_session(session_id, credentials)` delegates to
  `enable(access_tier, auto_announce)` — arguments bind to the
  wrong parameters on the real-Redis path (mock mode raises first,
  which is why tests only ever saw the degradation branch).
- **facade.py:239–242 — Class 2 (dead code).** The first
  `_client` property is shadowed by a second definition at :728 at
  class-creation time; the first body can never execute. This is
  the facade's only sub-100 remainder (99%).

Design observation (not a bug): `learning/storage.py`
`clear_user_data` intentionally leaves corrupt `.json` files
behind (`continue` before `unlink`), so a corrupt file makes the
user dir unremovable — tolerated by the `rmdir` except and now
pinned by test.

## 2026-07-30 — Tier 3 shim corrections (coverage push, Fable 5)

`src/attune/coordination.py` 0% → 100% (shim contract test),
`src/attune/ops/__main__.py` 0% → 100% (entry-binding test),
`src/attune/ops/__init__.py` 50% → 100% (lazy-delegation tests).
One production bug found and fixed:

- **Class 2-adjacent (dead lazy branch shadowed by its own
  placeholder): `from attune.ops import Config` silently imported
  `None`.** The package bound `Config = None` at module scope "for
  static export" while the PEP 562 `__getattr__` carried the real
  lazy `attune.ops.config.Config` resolution — but module
  `__getattr__` only fires for MISSING attributes, so the
  placeholder always won and the resolver branch was dead code
  (masked from coverage by its own `pragma: no cover`). Any
  consumer doing `from attune.ops import Config` got `None` and a
  deferred `TypeError: 'NoneType' object is not callable` at first
  use; a grep found no internal consumers, so the trap was armed
  but unfired. Fix: the placeholder line deleted, `__getattr__` now
  reachable; `test_config_getattr_resolves_real_class` pins the
  contract. Detection note for the class: a `pragma: no cover` on
  a PEP 562 `__getattr__` hides exactly this shadowing failure —
  when a module defines both a placeholder AND a `__getattr__`
  branch for the same name, one of them is dead by construction.

## 2026-07-29 — release_prep_team.py orchestration pass (coverage push, Fable 5)

`src/attune/agents/release/release_prep_team.py` 78% → 100% via net-new
`tests/unit/agents/test_release_prep_team_orchestration.py` (10 tests:
assess_readiness fan-out with stub agents, confidence tiers, Redis-optional
init branches with a fake redis_lib). One finding, flagged not fixed:

- **Candidate bug (silent wrong result, class 1-adjacent — no crash):
  a FAILED security agent passes the Security gate via the -1
  sentinel.** `_evaluate_quality_gates` records `critical_issues = -1`
  when the security result has `success=False`, and `-1 <=
  max_critical_issues (0)` evaluates the gate as PASSED — greenest
  outcome on the exact path where the auditor never ran. Partial
  mitigation: `_identify_issues` adds a blocker when the failed
  result's findings carry an `"error"` key — but `_execute_tier`
  failure shapes vary per agent, so a failure without that key
  approves the release with a green Security row (actual=-1.0 is the
  only visible tell). NOT fixed in this pass: hardening the gate
  (sentinel → failed) changes release-gate semantics and needs a
  ruling; the current behavior is pinned by
  `test_failed_security_agent_sentinel_passes_gate` with a comment
  telling the fixer to rewrite it deliberately. Flagged as a chip.

  **DISPOSITION (same day, chair-ruled "go fix it"):** hardened —
  a failed OR absent security result now fails the Security gate
  (`security_ran and …`; the -1 sentinel stays as the display
  value), and `_identify_issues` blocks on EVERY failed agent with
  a fallback reason when no `error` key exists (the bug's other
  half: a failure with no diagnostic must not read quieter than
  one with). Pinned test rewritten to the new contract
  (`test_failed_security_agent_fails_gate_and_blocks`) plus a
  missing-result case. Class 1 (silent wrong result on a
  never-exercised path), counted as a coverage-push find.

## 2026-07-24 — elicitation/widget.py fixed element ids (dogfood, Fable 5)

`src/attune/elicitation/widget.py` (`form_to_widget_html`). Found by
DOGFOODING, not by a coverage push — logged here because this file is
the repo's record of bug *shapes*, and there is precedent for entries
outside the production-code classes (the 2026-06-13 test-isolation
entry). Fixed in #1648. Does not count toward the coverage-push
bug-find rate below.

- **Bug (composition), class 6 — two forms rendered into one page share
  element ids, so the second form's submit handler reads the FIRST
  form's fields.** `form_to_widget_html` emitted hard-coded ids
  (`attune-elicit-form`, `ae-submit`, `ae-error`) and its inline submit
  script resolved them via `document.getElementById`. Render two forms
  into one page — exactly what the dynamic-forms demo does, showing a
  basic beat and an advanced beat together — and the ids collide;
  `getElementById` returns the FIRST match, so submitting form 2
  silently posts form 1's answers. There is no exception and no console
  error: the payload is simply wrong. That is worse than a crash here,
  because the wrong answers then validate CLEANLY through
  `collect_form_response` and the caller gets a success receipt for
  data the user never entered.

  **Why coverage was structurally blind to it.** Every line of
  `form_to_widget_html` was already covered and the elicitation suite
  was 254 tests green. The defect does not live in any line — it is
  emergent from calling the function TWICE and letting both outputs
  coexist. No single-render test reaches it at any coverage level.
  That is the defining property of class 6: the unit is correct in
  isolation and wrong in composition, so line/branch coverage is not
  merely insufficient — it is the wrong instrument.

  **Class 3B also present — the test pinned the defect as the
  contract.** `test_includes_title_and_form_shell` asserted
  `'id="attune-elicit-form"' in html`, i.e. the exact buggy literal.
  Nothing was mocked (so not class 3 proper), but the suite would have
  actively RESISTED the fix: correcting the ids failed that assertion
  and it had to be rewritten. Hard-coding a generated identifier in an
  assertion converts "this value happens to be fixed" into "this value
  must be fixed."

  **Fix (#1648).** Ids carry a per-render suffix (random by default,
  injectable via a new optional `instance_id` for deterministic
  renders), and the scoped `<style>` block follows the suffixed id.
  The regression guard asserts that two renders produce DIFFERENT ids
  — the assertion a single-instance test cannot make.

  **Generalizes to:** any generated artifact carrying a fixed
  identifier that assumes one live instance — HTML element ids, temp
  filenames, singleton registry keys, fixed ports, cache keys. The
  detection move is composition, not coverage: instantiate twice and
  assert the two differ.

---

## 2026-07-16 — meta_workflows/cli_commands/agent_commands.py (QA, Opus 4.8)

`meta_workflows/cli_commands/agent_commands.py` (`create_agent`,
`create_team`), **~11% → 99%** (net-new
`tests/unit/meta_workflows/test_agent_commands.py`, 18 tests). No prior
test file anywhere imported this module.

- **Bug (crash), class 1 — `create-agent` crashes on EVERY successful
  invocation, both interactive and quick mode.** The command's final two
  lines split a Rich markup `[dim]...[/dim]` span across two separate
  `console.print()` calls:

  ```python
  console.print(f"\n[dim]Agent tier '{tier}' will cost approximately:")
  console.print(f"   {costs.get(tier, costs['capable'])} per execution[/dim]\n")
  ```

  Rich parses markup independently per `console.print()` call — there is
  no cross-call tag state — so the second call's lone `[/dim]` has no
  matching open tag and raises `rich.errors.MarkupError: closing tag
  '[/dim]' at position N doesn't match any open tag`. Typer's `CliRunner`
  (and a real terminal) surfaces this as exit code 1 with an unhandled
  exception, AFTER the JSON spec panel and any `--output` file save have
  already completed — so the command's core work (spec construction,
  file save) succeeds, but the process always exits non-zero and never
  prints its final cost-estimate line. `create-team`'s analogous final
  line (`console.print(f"...{...}[/dim]\n")`) is a single call and does
  **not** share this bug — confirmed via manual and automated testing
  that `create-team` exits 0 cleanly. This means every `attune-ai` user
  who has ever run `create-agent` (interactive or quick mode, any tier)
  has hit this crash — there is no successful invocation path. Likely
  fix: merge the two `console.print()` calls into one, or move the
  closing `[/dim]` onto the first call. **Not fixed here** — kept this
  PR test-only per the qa-batch-playbook cadence; tests assert the
  crash's exact `MarkupError` and message as the current real behavior.
  Filed as a follow-up for a dedicated one-line hotfix PR.
  **RESOLVED 2026-07-16** — merged the two `console.print()` calls into
  one; `test_agent_commands.py`'s success-path tests now assert
  exit_code 0 and the full (previously-unreachable) cost-estimate line.

---

## 2026-06-13 — test isolation: worktree_path_guard `_sdk_gate` import (Opus 4.8)

`tests/unit/hooks/test_worktree_path_guard.py`, **test-infra / isolation
bug** (not a production-code class — a test-harness defect). The 3
`TestScriptMainEntry` tests
(`test_script_with_empty_stdin_exits_0`,
`test_script_with_skip_context_exits_0`,
`test_script_catches_main_exception_and_exits_0`) fail with
`ModuleNotFoundError: No module named '_sdk_gate'` when the file is run in
isolation, but pass in the full suite.

- **Bug — order-dependent green via `sys.path` pollution.** The tests use
  `runpy.run_path(SCRIPT_PATH, run_name="__main__")`, which executes the
  `if __name__ == "__main__"` block of
  `src/attune/hooks/scripts/worktree_path_guard.py:170`
  (`from _sdk_gate import exit_if_sdk_subprocess`). `runpy.run_path` on a
  *file path* does NOT add the script's directory to `sys.path`, so that
  sibling-relative import only resolves when an earlier test in the run
  already inserted `src/attune/hooks/scripts` into `sys.path`. Run alone,
  that pollution is absent and the import fails. CI was green only by
  accident of ordering. Latent since PR #521 (commit c1b4cf33), not
  introduced by QA work. **Fix:** added `tests/unit/hooks/conftest.py`
  that inserts the absolute `src/attune/hooks/scripts` dir at the front of
  `sys.path`, so `_sdk_gate` resolves regardless of test order. Verified
  the file passes in isolation and the full `tests/unit/hooks/` dir stays
  green (312 passed, 1 skipped).

---

## 2026-06-13 — monitoring/otel_backend.py (QA, Opus 4.8)

`monitoring/otel_backend.py` (`OTELBackend`), **~import-only → 100%**.
The existing `test_otel_backend.py` `pytest.skip(allow_module_level=True)`
s the whole module when `opentelemetry` is absent, so its coverage was
effectively import-time only. New mock-based suite
(`test_otel_backend_export.py`, 23 tests) covers `log_call`,
`log_workflow` (incl. stage child-spans + skip/error branches),
`_init_otel` success/failure, `flush`, the `__init__`→`_init_otel` hop,
and the endpoint detection/availability parsing — all with
`opentelemetry` mocked, so it runs regardless of the `[otel]` extra.

- **Bug (crash) — `_check_otel_installed()` raises instead of returning
  False when `opentelemetry` is absent.** It does
  `importlib.util.find_spec("opentelemetry.trace")`, which raises
  `ModuleNotFoundError` (missing *parent* package) rather than returning
  `None`. Since `__init__` calls it bare
  (`self._otel_available = self._check_otel_installed()`),
  **`OTELBackend()` crashes in any env without the optional `[otel]`
  extra** — directly contradicting the module's "graceful fallback /
  optional dependency" design. The existing test suite masks this by
  skipping at module level. Fix: wrap the `find_spec` sweep in
  `try/except (ModuleNotFoundError, ValueError): return False`. Filed as
  a follow-up (not fixed in the coverage PR to keep it test-only).

---

## 2026-06-13 — serial `--cov` memory-suite pollution (Opus 4.8)

Classification: **test-infra / coverage-tooling interaction** (not
crash / dead / mocked — the closest legacy bucket is "mocked" only in
the sense that it corrupts test state, but nothing is actually mocked).
Surfaced during QA #5 `memory/` coverage work.

**Symptom.** Serial `pytest --cov=attune.memory.short_term.* tests/...`
runs intermittently fail ~13–32 tests with
`RuntimeError: cryptography library required when master_key is
provided` from
[encryption.py:54](../src/attune/memory/encryption.py) because
`HAS_ENCRYPTION` is `False`. Green without `--cov`; green with a
non-memory `--cov` target (e.g. `--cov=attune.cli_minimal` → 2612
passed).

**The hypothesis it disproves.** It is *not* a between-tests isolation
leak and there is *no* polluting test. It reproduces with a single
test file and from the main checkout, and `HAS_ENCRYPTION` is already
`False` before any test body runs. So a `monkeypatch` / fixture
"restore" fix does not apply.

**Real root cause** (traced with a `sys.addaudithook` import tracer):
`cryptography` ships its core as a Rust/PyO3 extension
(`cryptography.hazmat.bindings._rust`) that may be **initialized only
once per interpreter process**. With a `attune.memory.*` `--cov`
target, pytest-cov imports the coverage source at startup — before any
conftest. That import transitively eager-loads
`redis` → `redis.auth.token` → `PyJWT` → `cryptography`
(via [short_term/base.py:51](../src/attune/memory/short_term/base.py)),
initializing `_rust` once. The startup import then unwinds and evicts
the cryptography modules from `sys.modules` while PyO3's
**process-global** once-only counter stays incremented. When
`tests/conftest.py` re-imports the chain, `_rust` re-init raises
`ImportError: PyO3 modules ... may only be initialized once`, which
`encryption.py`'s `except ImportError` swallows → `HAS_ENCRYPTION =
False` for the whole session. Tests whose `skipif(not HAS_ENCRYPTION)`
read a *cached* `cryptography.fernet` (still `True`) don't skip — they
run and error.

CI is unaffected: coverage runs under xdist (`-n auto`), which
isolates workers. This only bites serial `--cov` used for local QA
coverage measurement.

**Fix.** Import `cryptography` exactly once, cleanly, before
pytest-cov's startup source import. Shipped as a `pytest11` plugin
([_pytest_crypto_pin.py](../src/attune/_pytest_crypto_pin.py),
registered in `pyproject.toml`) whose top-level import runs during
setuptools-entry-point loading — verified to beat pytest-cov.
Conftest-level pins were verified *too late* (the corruption predates
conftest). Verification: full original repro **32 failed + 13 errors →
2612 passed**. In a worktree (entry point not yet in editable
metadata), use the manual fallback
`-p attune._pytest_crypto_pin` (also verified green).

---

## 2026-05-16 — eighteenth module under test-quality-program (Opus 4.7)

First cycle after a two-day pause. Selected from the existing
2026-05-14 rubric cache (`memory/short_term/queues.py` shipped two
days ago; release_prep was the next-highest viable pick, deferred at
the time due to discovery-sweep collision risk that has since
cleared with #411): `workflows/release_prep.py`, score 1.71 (W=3 ×
gap=0.569 × risk=1.0 — capable/orchestration tier), **43.1%
covered → 100.00%**. **Zero production bugs surfaced.**

- `workflows/release_prep.py` (`ReleasePreparationWorkflow`) — no
  bugs. Module is the SDK-shell archetype documented in CLAUDE.md
  ("SDK-native workflow shell scaffold is reusable across 6+
  siblings — single-pass rename"). Existing test surface (6 tests)
  covered only class attributes; `execute()` and `_run_agent_prep()`
  had no behavioral coverage at all. The four execution branches
  (success, validation error, depth mapping, exception handling) +
  the SDK loop's two state branches (assistant_parts grows
  vs. result-only) are now all measured.

**Coverage delta:** 43.1% → 100.00% (line + branch, 52/52
statements, 6/6 branches).

**Tests:** 22 added under
`tests/unit/workflows/test_release_prep_execute.py`. Real
`claude_agent_sdk.AssistantMessage` / `ResultMessage` / `TextBlock`
instances per the existing CLAUDE.md lesson on isinstance-based
collectors; only `claude_agent_sdk.query` is mocked. Five test
classes mirror the sibling scaffold:
- `TestExecuteValidation` (2) — missing + empty path early-return
- `TestExecuteSuccess` (4) — happy path, metadata, result-only,
  empty-stream
- `TestExecuteDepthMapping` (5) — quick/standard/deep/unknown/default
- `TestExecuteExceptionHandling` (4) — ImportError, ConnectionError,
  TimeoutError, RuntimeError
- `TestRunAgentPrepDirect` (4) — collect path, empty path, all four
  subagent definitions, default depth kwarg
- `TestErrorResult` (3) — structure, stage metadata, timestamp bounds

### Implementation note: 4-subagent variant of the SDK-shell family

`release-prep` is the first 4-subagent variant in the SDK-native
workflow family. Siblings split: `dependency_check` (2), then
`bug_predict` / `perf_audit` / `refactor_plan` / `doc_audit` /
`document_gen` (3 each). The CLAUDE.md lesson explicitly calls
out "count subagents in the source before writing the
`test_passes_subagent_definitions` assertion" — release-prep's
4-subagent set (health-checker, security-scanner,
changelog-generator, release-assessor) is the asymmetric case.
The rest of the scaffold (depth mapping, exception branches,
_error_result shape) is identical to the 3-subagent siblings.

Stage name in `_error_result` returns `self.name = "release-prep"`
(the workflow's external name from `name = "release-prep"`), NOT
the internal stage list value `"agent-prep"` from `stages =
["agent-prep"]`. Test asserts on `"release-prep"`.

---

## 2026-05-14 — seventeenth module under test-quality-program (Opus 4.7)

Second cycle of the day, after the docstring fix on the rubric
script (PR #348) corrected the coverage-XML scope. Selected via
fresh rubric (now using `pytest tests/` not `pytest tests/unit/`):
`memory/short_term/queues.py`, score 1.71 (W=3 × gap=0.38 ×
risk=1.5 data-handling), **62.1% covered → 100.00%**. **Zero
production bugs surfaced.**

- `memory/short_term/queues.py` (`QueueManager`) — no bugs.
  Module is small (66 statements, 32 branches) and structurally
  symmetric: every public method has a mock-mode branch
  (covered by sibling tests transitively) and a real-Redis
  branch (previously uncovered, now covered via real
  `BaseOperations` + `MagicMock()` `_client`). All 4 `client
  is None` defensive returns behave correctly.

**Coverage delta:** 62.1% → 100.00% (line + branch).

**Tests:** 24 added under
`tests/unit/memory/short_term/test_queues.py`. Real
`BaseOperations` host, two-mode fixtures:
- `mock_base` / `mock_queue` — `use_mock=True` for in-memory
  round-trip tests
- `real_base_with_client` — `use_mock=False` patched past the
  auto-detect override (see implementation note below), with a
  `MagicMock` client for behavior assertions on lpush/rpush/
  lpop/blpop/llen/lrange
- `real_base_no_client` — `_client=None` for the four
  defensive-return branches

Determinism verified across 3 back-to-back runs and under `-n
auto` alongside the full memory test subtree (1487 passed, no
cross-test interference).

### Implementation note: BaseOperations auto-flips use_mock

`BaseOperations(use_mock=False)` silently flips `use_mock` to
`True` when Redis auto-detect finds the server unreachable
(seen in `redis_auto_detect_unavailable` log line during
fixture init). For tests that need the real-Redis branches to
fire against a fake client, explicit `base.use_mock = False`
after construction is required. Documented inline in the
fixture docstrings. This pairs with the existing CLAUDE.md
"xdist worker crashes on Windows can come from repeated socket
probes" lesson — both are consequences of BaseOperations doing
real network work at init time.

---

## 2026-05-14 — sixteenth module under test-quality-program (Opus 4.7)

Sixteenth module run, first after returning from a multi-day
gap. Selected via fresh rubric scoring:
`memory/security/secrets_detector.py`, weight 3, score 1.79
(rubric-reported 60.3% covered, actual 90.96% — see meta-finding
below). **Zero production bugs surfaced.**

- `memory/security/secrets_detector.py` — no bugs. Module's 28
  existing tests (`tests/security/test_secrets_detector.py`)
  already cover the real-content pattern-matching surface
  well. The remaining 4 spots were defensive edge cases:
  - `_create_context_snippet` invalid-line-number guard
  - `_create_context_snippet` long-line truncation (both
    left-edge and right-edge ellipsis branches, including the
    asymmetric `end < len(line)` comparison where end is
    bounded by `len(redacted_line)`)
  - `_calculate_entropy` empty-string `return 0.0` fast path
  - `_filter_overlapping_detections` different-line continue
    branch (loop skip when entropy and pattern detections sit
    on different lines)

**Coverage delta:** 90.96% → 100.00% (line + branch).

**Tests:** 9 added under
`tests/security/test_secrets_detector_edge_paths.py`. Per the
"focused fallback-paths" pattern from the test-quality-program
CLAUDE.md lesson — left the existing 435-line test file
untouched. Determinism verified across 3 back-to-back runs and
under `-n auto` alongside the full `tests/security/` subtree
(321 passed in 10.37s, no cross-test interference).

### Meta-finding: rubric input must include ALL test dirs

The rubric reported `secrets_detector.py` at 60.3% but the
actual coverage from `tests/security/test_secrets_detector.py`
running alone was 90.96%. Root cause: the rubric input
`coverage.xml` was generated with `pytest tests/unit/` only,
omitting `tests/security/`, `tests/integration/`, and other
non-unit subdirs. Any module whose primary tests live outside
`tests/unit/` shows up with spuriously low coverage in
`rubric_cache.csv`.

**Fix for next rubric refresh:** run coverage against `tests/`
(not `tests/unit/`) to capture all test paths. The default
`testpaths = ["tests"]` in `pyproject.toml` is already correct
for full collection; only the rubric-input command needs the
path widening.

---

## 2026-05-13 — fifteenth module under test-quality-program (Opus 4.7)

Fifteenth module run. Selected via the rubric's
top non-stale viable pick: `memory/short_term/transactions.py`,
weight 3, score 1.992, **55.7% covered → 96.30%**. **Zero bugs
surfaced.** Module is small (61 stmts / 20 branches), single
public method (`atomic_promote_pattern`), with clean mock/real
branching and explicit validation guards.

Highlights of the new test surface
(`tests/unit/memory/short_term/test_transactions.py`, 17 tests):

- Validation guards (empty pattern_id, out-of-range
  min_confidence) → `ValueError` with expected messages.
- Authorization gate (observer/contributor rejected;
  steward accepted) tested via real `AgentCredentials` +
  `AccessTier` instances.
- Mock-mode branches: not-found, expired-via-mock-timestamp,
  confidence-below-threshold (storage preserved), and
  successful promotion (storage deleted + cache invalidated).
- Real-Redis branches via the documented
  `base._client = MagicMock()` injection pattern: `client=None`,
  pattern-not-found, below-threshold, successful pipeline
  delete + cache invalidation, `redis.WatchError` race handler,
  and the best-effort `unwatch()` exception in `finally`.

Remaining 3 uncovered lines:
- Line 39 (`redis = None`) — unreachable fallback when `redis`
  is not installed.
- Lines 189-190 (`redis.WatchError` handler) — handler is
  exercised by a passing test, but coverage instrumentation
  doesn't credit it under the local non-xdist coverage run on
  this interpreter. PyO3 binding init-once quirk; xdist run
  shows green.

Lesson reinforced: when a test needs to raise a class from an
optional dep (`redis.WatchError`), reference it via the
already-imported source module (`_transactions_mod.redis.WatchError`)
rather than importing the optional dep again at test-module
top. This sidesteps the
"PyO3 modules compiled for CPython 3.8 or older may only be
initialized once" error path on macOS/Python 3.10.

---

## 2026-05-12 — fourteenth module under test-quality-program (Opus 4.7)

Fourteenth module run. Selected via the fresh
rubric: `workflows/test_runner_helpers.py`, weight 3,
score 2.125, **29.2% covered**. **Two Bug Class 2
findings — neither fixed inline.**

- `workflows/test_runner_helpers.py` (pytest output
  parsing + coverage XML analysis + test discovery)
  — primarily pure functions. Three helpers
  (`_get_previous_coverage`, `_log_file_test`) touch
  the telemetry store, mocked. `_find_test_file`
  walks the real filesystem in `tmp_path` via
  `monkeypatch.chdir`.

**Bug Class 2 #1 (this module):** `_find_test_file`
at lines 165-172 has a `try/except (ValueError,
IndexError): pass` block guarding
`source_path.parts.index("src")` and
`source_path.parts[src_idx + 1 : -1]`. The
surrounding `if "src" in source_path.parts:` guard
makes the `ValueError` impossible (we already
confirmed "src" is in parts). The slice operation
`parts[a:b]` never raises `IndexError` in Python.
Dead defensive code. The right fix is to drop the
try/except — not write a test for an unreachable
branch. Flagged for a sibling cleanup PR.

**Bug Class 2 #2 (related modules — skipped this
cycle):** `workflows/test_lifecycle.py` (535 lines,
0% covered) and `workflows/test_maintenance_cli.py`
(590 lines, 0% covered) are dead code.
`workflows/__init__.py:328` says "test-maintenance:
Removed — utility class, not a BaseWorkflow."
Neither module is imported anywhere outside its
sibling. Score 3.0 each on the rubric makes them
top picks, but writing tests for unused code is
exactly the trap the bug-log preamble warns
against. Flagged for a retirement PR similar to
`scaffolding` / `orchestrated_release_prep`
(referenced in tasks.md §Out-of-scope follow-ups).

**Coverage delta:** 29.2% → 98% line+branch on
`workflows/test_runner_helpers.py`. The 2% gap is
the dead-code try/except branch (line 171-172)
documented above. Will close to 100% when the dead
code is removed.

**Tests:** 26 added under
`tests/unit/workflows/test_test_runner_helpers.py`:
- `_parse_pytest_output` (5 tests including
  all-passing, mixed, errors, no-summary,
  unparseable)
- `_parse_pytest_failures` (4 tests including
  malformed FAILED lines + 10-entry cap)
- `_get_previous_coverage` (4 tests — 2-or-more
  records, single, empty, store-exception)
- `_analyze_coverage_files` (5 tests covering
  well-covered/critical/untested/mid-coverage
  thresholds + 10-entry caps)
- `_find_test_file` (6 tests — __init__ skip,
  module dir match, standard dir match, rglob
  fallback, no-match, no-tests-dir)
- `_log_file_test` (2 tests — happy + store
  exception)

**Pattern observation (informational):** This is
the second consecutive cycle where the rubric's
top measured-coverage picks were either dead code
or already well-covered (existing 16 silent-skip
tests in #287, dead defensive branches here). The
working-set picks are getting harder to
distinguish from "modules nobody actually uses."
A useful rubric refinement would tag modules by
**inbound-import count** — anything with zero
external consumers should drop off the working
set or get a retirement flag rather than a "low
coverage" flag. Not committing the change here;
flagged for a future rubric script update.

---

## 2026-05-12 — thirteenth module under test-quality-program (Opus 4.7)

Thirteenth module run. Selected via the fresh
rubric: `workflows/test_runner.py`, weight 3, score
2.649, **11.7% covered**. **0 production bugs
surfaced.**

- `workflows/test_runner.py` (Tier 1 telemetry
  wrappers) — no bugs. The module exposes three
  primary functions:
  - `run_tests_with_tracking()` — runs pytest via
    subprocess, parses output for pass/fail/skip
    counts, logs to `TelemetryStore`.
  - `track_coverage()` — parses `coverage.xml`,
    computes trend (improving/declining/stable) vs
    previous, logs to store.
  - `track_file_tests()` — runs per-file pytest,
    classifies the result, detects staleness when
    source mtime > test mtime.
  Plus two thin wrappers (`get_file_test_status`,
  `get_files_needing_tests`) that delegate to the
  store.

  All four exception paths (TimeoutExpired in main
  runner, generic Exception in main runner, same
  pair in `track_file_tests`) recover to a
  best-effort error record without crashing.
  Telemetry log failures are also caught with
  warnings, never propagated — a deliberate design
  choice given Tier 1 tracking is opt-in.

**Coverage delta:** 11.7% → 92% line+branch.

**Tests:** 24 added under
`tests/unit/workflows/test_test_runner.py`. Mocks
only `subprocess.run` (would actually run pytest)
and `get_telemetry_store` (would write to
`~/.attune/telemetry/...`); pytest-output parsing,
coverage.xml parsing (via `xml.etree` /
`defusedxml`), and `FileTestRecord` construction
use real implementations.

**Remaining 8%:** the `defusedxml` ImportError
fallback (line 19-20) which would require
selectively breaking defusedxml import (cross-test
contamination risk per CLAUDE.md lesson), plus
three classifier branches at lines 342-347
(`errors > 0` / `skipped == total` / final else)
that need precisely-shaped pytest output to
trigger. Stopping at 92% — marginal cost exceeds
marginal value for these specific branches.

**Coverage-omit note (informational):** the
`workflows/test_runner.py` filename starts with
`test_` which the `*/test_*.py` omit pattern in
pyproject.toml's `[tool.coverage.run]` config
should match — but the fresh `coverage.xml` does
record measurements for the file (line-rate
0.1169). The omit appears to NOT match nested
paths the way the lesson at the top of CLAUDE.md
suggests. Either the lesson is outdated, the
pattern matches only direct children, or coverage
.py instruments the file but then excludes it from
some other report path. Worth a follow-up
investigation but not blocking this cycle.

---

## 2026-05-12 — twelfth module under test-quality-program (Opus 4.7)

Twelfth module run. First cycle this session that
surfaced a real production bug — and notably, it's
exactly **Bug Class 3** from the log preamble:
"Tests that mocked around the bug — tests pass
because they mock the broken caller; coverage at
100% looks fine, production code is wrong."

Selected via a **fresh** rubric refresh (the morning
csv was stale by ~12 cycles): top measured-coverage
pick was `cli_commands/help_commands.py`, weight 5,
score 4.497, **10.1% covered**. Closer inspection
revealed the 10% was misleading: 16 tests existed in
`tests/unit/cli_commands/test_help_commands.py` but
all were silently skipped via
`pytest.importorskip("frontmatter")` because
`python-frontmatter` is only a transitive dep of
`attune-help`/`attune-author` (in the `[author]`
extra, NOT in `[dev]`).

**Bug Class 3 — variant: silently-skipped tests
masquerading as test coverage.** The 16 tests were
written, reviewed, and merged, but never ran in CI.
The `importorskip` guard was defensive (the module
references `attune.help.engine.populate` which uses
`frontmatter` internally), but the dep wasn't in any
extra that CI installed. Net effect: a weight-5 CLI
entry point shipped with effective 0% test coverage
despite appearing to have 16 tests.

**Fix (inline, sibling change):** added
`python-frontmatter>=1.0.0,<2.0.0` to the `[dev]`
extra in `pyproject.toml` with an inline comment
documenting why. `uv lock` confirmed clean 2-line
update to `uv.lock`. With the dep installed, the 16
existing tests run and lift coverage 5% → 73%.

**New tests (this PR):** 15 added under
`tests/unit/cli_commands/test_help_commands_gaps.py`
covering the remaining ~27%:
- `_get_generated_dir()` path resolution
- `_list_categories()` missing-category-dir +
  no-cross-links branches
- `_list_category()` empty-files branch
- `_show_template()` prefixed-name-not-found branch
- `_list_all_tags()` empty-tags branch
- `_record_feedback()` invalid-rating + happy +
  prefix-resolution branches (entire function had
  zero coverage)
- `cmd_help()` --feedback routing + missing-topic
  branch
- `cmd_help()` --deep / --detail verbosity branches

Patches use the source-module pattern (e.g.
`patch("attune.help.engine.list_tags", ...)`) per
CLAUDE.md lesson on lazy-imported names not being
patchable at the consuming module.

**Coverage delta:** 5% (effective 0%) → 100%
line+branch.

**Lesson captured separately in CLAUDE.md:** when
the rubric points at a "user-typed entry point" with
suspiciously low coverage AND nominal test files
exist, grep for `pytest.importorskip` in those test
files first. If a test file gates the entire module
on an `importorskip`, the dep is either misclassified
(should be in `[dev]`) or the tests are
defensive-only and never run in CI. Either way:
fix the gate before adding new tests, otherwise the
new tests also silently skip.

---

## 2026-05-12 — eleventh module under test-quality-program (Opus 4.7)

Eleventh module run. Second non-SDK pick after the
six SDK-native cycles. Selected via the rubric:
`memory/control_panel.py`, score 2.073. **0 production
bugs surfaced.**

**Rubric staleness flagged:** rubric_cache.csv from
2026-05-12 morning reported `covered_pct=53.9` for
this module, but at session time the existing
`tests/memory/test_control_panel.py` (851 lines),
`tests/memory/test_control_panel_security.py` (345),
`tests/unit/memory/test_control_panel.py` (849), and
`tests/unit/memory/test_control_panel_display.py`
(678) — together 2,723 lines of existing tests —
already gave 93% line+branch coverage. The csv
snapshot pre-dates work that landed earlier today.
Rubric refresh needed before the next cycle to avoid
re-picking already-saturated modules.

**Remaining 7% (this PR's target):** four
error-handling fallback branches:

- `get_statistics()` storage_bytes `Exception` →
  fallback to 0 (lines 229-231). Exercised by patching
  `Path.glob` to raise `OSError`.
- `get_statistics()` long-term `get_statistics()`
  `Exception` → log warning, leave counts at dataclass
  defaults (241-242). Exercised by patching
  `_get_long_term` to return a fake that raises.
- `health_check()` long-term unavailable branch
  (415-419). Exercised by pointing `storage_dir` at a
  nonexistent path.
- `_count_patterns()` `OSError`/`PermissionError`
  handler (491-493). Exercised by patching
  `Path.glob`.

**Coverage delta:** 93% → 99% line+branch. Only line
497 (`if __name__ == "__main__": main()`) remains
uncovered.

**Tests:** 7 added under
`tests/unit/memory/test_control_panel_error_paths.py`.
Uses `tmp_path` for real filesystem isolation;
patches `Path.glob` / `_get_long_term` at strategic
points to surface the fallback branches without
mocking the whole subsystem.

**Pattern observation:** When existing test files
already cover the happy path well, the right move is
a small targeted file that exercises the remaining
error-handling branches by name (commented line
references in the docstring). Cheaper than rewriting
the existing tests, keeps the diff focused.

---

## 2026-05-12 — tenth module under test-quality-program (Opus 4.7)

Tenth module run. Sixth Agent SDK-native workflow
through the program — `document_gen/workflow.py`.
Same shell pattern as the five prior SDK cycles
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`, `doc_audit`). One small divergence:
this workflow exposes a `default_context()` classmethod
for `WorkflowContext` composition (wires up
`PromptService` + `ParsingService`); three extra tests
cover it. **0 production bugs surfaced.**

- `workflows/document_gen/workflow.py`
  (`DocumentGenerationWorkflow`) — no bugs. Thin async
  shell around `claude_agent_sdk.query()` with three
  subagents (`outline-planner`, `content-writer`,
  `polish-reviewer`). The `default_context()`
  classmethod is a real composition surface but adds
  no behavior beyond constructing the two services
  with the given `xml_config` kwarg.

**Coverage delta:** 46.4% → 100% line+branch.

**Tests:** 24 added under
`tests/unit/workflows/document_gen/test_workflow_execute.py`
(21 SDK-shell + 3 `default_context()`). Also added
empty `__init__.py` for the new test sub-package to
match the existing `doc_audit/` layout.

**Generator-script ROI threshold crossed (informational):**
Six consecutive cycles from the same scaffold. The
generator script case is now stronger but I'm deferring
because the next likely module on the rubric
(`memory/control_panel.py`, weight 3, score 2.073)
isn't an SDK shell — it's a memory subsystem. Writing
the generator now would optimize for a pattern that's
about to recede from the working set. Re-evaluate if
two more SDK shells surface in a future rubric refresh.

---

## 2026-05-12 — ninth module under test-quality-program (Opus 4.7)

Ninth module run. Fifth Agent SDK-native workflow
through the program — `doc_audit/workflow.py`. Same
shell pattern as the four prior SDK cycles
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`). The scaffold transferred verbatim
with a subagent-name rename. **0 production bugs
surfaced.**

- `workflows/doc_audit/workflow.py` (`DocAuditWorkflow`)
  — no bugs. Thin async shell around
  `claude_agent_sdk.query()` with three
  `AgentDefinition` subagents (`staleness-checker`,
  `accuracy-reviewer`, `gap-finder`). Validates `path`,
  maps depth → max_turns, four-branch exception
  handling (`ImportError` / `ConnectionError` /
  `TimeoutError` / generic). Identical to its sibling
  workflows.

**Coverage delta:** 43.1% → 100% line+branch.

**Tests:** 21 added under
`tests/unit/workflows/doc_audit/test_workflow_execute.py`.
Same real-SDK-dataclass fixtures pattern; only
`claude_agent_sdk.query` mocked.

**Pattern note:** This is the fifth consecutive cycle
from the same scaffold (`dependency_check`,
`bug_predict`, `perf_audit`, `refactor_plan`,
`doc_audit`). The case for a generator script
(`scripts/scaffold_sdk_workflow_tests.py` taking
module path + subagent list as inputs) is increasingly
strong but still flagged-not-committed — each cycle
takes ~5 min by hand, so the script's payoff threshold
hasn't been crossed for one-off uses. If
`workflows/document_gen/workflow.py` (next obvious
sibling on the rubric) follows the same shape, the
script becomes a clear win.

---

## 2026-05-12 — eighth module under test-quality-program (Opus 4.7)

Eighth module run. First non-SDK cycle in today's
sequence after four consecutive Agent SDK shells
(`dependency_check`, `bug_predict`, `perf_audit`,
`refactor_plan`). Selected via the rubric working set:
`memory/short_term/caching.py`, score 2.287.
**0 production bugs surfaced.**

- `memory/short_term/caching.py` (`CacheManager`) — no
  bugs. The module is a 233-line pure-Python LRU cache
  with TTL fields (timestamps tracked but never expired
  by the cache itself — callers handle TTL semantics).
  Two-tier strategy: local in-memory dict-backed cache
  sitting in front of Redis. The LRU eviction path
  (`min(self._cache, key=lambda k: self._cache[k][2])`)
  fires only when `len(self._cache) >= self.max_size`;
  exercised with a 3-entry cache and a deliberate
  access-order shuffle. Disabled-mode branches in
  `get` / `add` / `contains` all return early. No dead
  code; no crash paths.

**Coverage delta:** 49.2% → 100% line+branch.

**Tests:** 28 added under
`tests/unit/memory/short_term/test_caching.py`. No
mocks needed — pure stdlib `time.sleep(0.001)` between
adds to ensure `last_access` ordering for the LRU
eviction tests. `get_stats()` hit-rate computation
exercised both with traffic (66.67%) and with zero
requests (the `if total > 0 else 0.0` guard).

**Pattern observation:** First module today where the
test design wasn't a single-pass rename. The
SDK-native scaffold doesn't transfer here — pure-Python
state-machine classes need explicit branch coverage
(disabled-mode return-early paths, division-by-zero
guards, LRU ordering invariants). Worth noting for
future rubric picks: SDK-native shells cluster in
`workflows/*`; pure data-structure modules cluster in
`memory/short_term/*`. The test scaffold should fork
along that boundary.

---

## 2026-05-12 — seventh module under test-quality-program (Opus 4.7)

Seventh module run. Fourth (and final) Agent SDK-native
workflow through the program — direct sibling of
`dependency_check.py` (PR #265), `bug_predict.py` (PR #266),
and `perf_audit.py` (PR #273). Pattern transfer test: the
test file was scaffolded by copying
`test_dependency_check_execute.py` and renaming
`DependencyCheck`/`inventory-assessor`/`update-advisor` →
`RefactorPlan`/`debt-scanner`/`impact-analyzer`/`plan-generator`,
adjusting the system prompt substring assertion, and bumping the
subagent count from 2 to 3. Everything else (fixture shape,
real-SDK-message construction, depth-mapping, exception
handling, `_error_result` shape) carried over unchanged.
**0 production bugs surfaced.**

- `workflows/refactor_plan.py` (`RefactorPlanWorkflow`) — no
  bugs. The module is a ~260-line thin async shell around
  `claude_agent_sdk.query()`: validates `path`, maps depth →
  max_turns, defines three `AgentDefinition` subagents
  (`debt-scanner`, `impact-analyzer`, `plan-generator`),
  collects `AssistantMessage` + `ResultMessage` stream output
  via `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`. Same
  four-branch exception conversion as `dependency_check`
  (`ImportError` / `ConnectionError` / `TimeoutError` /
  generic, with `# noqa: BLE001` on the catch-all). No dead
  code, no crash paths.

**Coverage delta:** 44.44% → 100.00% (line + branch).

**Tests:** 21 added under
`tests/unit/workflows/test_refactor_plan_execute.py`. Same
fixture/mocking shape as PRs #265, #266, #273: only
`claude_agent_sdk.query` is patched, with real SDK dataclass
instances (`AssistantMessage`, `ResultMessage`, `TextBlock`)
yielded by the fake generator so isinstance-based collectors
fire correctly. Determinism verified back-to-back and under
the full `tests/unit/workflows/` selection.

**Scaffold completion:** with `refactor_plan.py` shipped, all
four SDK-native sibling workflows
(`dependency_check`/`bug_predict`/`perf_audit`/`refactor_plan`)
have reached 96-100% coverage from the same one-page test
template. Four consecutive cycles with verbatim transfer makes
the case for codifying the scaffold as
`scripts/scaffold_sdk_workflow_tests.py` (flagged in
decisions.md by the perf_audit cycle). Zero production bugs
across all four — the pattern reliably finds nothing because
the modules are pure plumbing.

---

## 2026-05-12 — fifth module under test-quality-program (Opus 4.7)

Fifth module run. Second Agent SDK-native workflow through
the program (sibling pattern to the `dependency_check`
module shipped earlier today). Selected via the rubric
working set: `workflows/bug_predict.py`, score 2.636 —
top entry with measured coverage after the four `?`
coverage-omit artifacts above it. **0 production bugs
surfaced.**

- `workflows/bug_predict.py` (`BugPredictionWorkflow`) —
  no bugs. The module is a ~270-line thin async shell
  around `claude_agent_sdk.query()`: validates `path`,
  maps depth → max_turns, defines three `AgentDefinition`
  subagents (`pattern-scanner`, `risk-correlator`,
  `prevention-advisor`), collects `AssistantMessage` +
  `ResultMessage` stream output via
  `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`.
  Each specific exception type (`ImportError`,
  `ConnectionError`, `TimeoutError`, generic `Exception`)
  is converted to a structured `_error_result`. The
  catch-all `except Exception` is documented intentional
  with `# noqa: BLE001`. No dead code; no crash paths.
  Structurally identical to `dependency_check.py` — the
  test scaffold transferred with a one-pass rename
  (`_run_agent_check` → `_run_agent_predict`, two
  subagents → three, stage name "dependency-check" →
  "bug-predict", task-prompt phrase swap).

**Coverage delta:** 47.3% → 97% (line + branch). The
one uncovered line (271) is the bottom-of-file
`if __name__ == "__main__": main()` guard — standard
untestable boilerplate.

**Tests:** 21 added under
`tests/unit/workflows/test_bug_predict_execute.py`,
matching the shape established by
`test_dependency_check_execute.py`. Only
`claude_agent_sdk.query` is mocked; the
`AssistantMessage`, `ResultMessage`, and `TextBlock`
instances yielded by the fake generator are **real SDK
dataclass instances** (per CLAUDE.md lesson on
duck-typed fakes failing isinstance-based collectors).

**Pattern observation (continues prior session):** the
SDK-native shape is uniform across the four sibling
workflows (`dependency_check`, `bug_predict`, plus
unprocessed `perf_audit`, `refactor_plan`). Each ships
zero production bugs and lifts coverage to 97-100% via
the same test scaffold. After two consecutive cycles
with this pattern (#265 + this PR), it's reusable
enough to script as a per-workflow template; flagged
for consideration but not blocking. Composed data-
handling helpers (memory/security) remain the bug-rich
shape; the SDK-native shells are pure plumbing.

---

## 2026-05-12 — fourth module under test-quality-program (Opus 4.7)

Fourth module run. First Agent SDK-native workflow through
the program. Selected via the rubric working set after
`ops/cli.py` shipped (`workflows/dependency_check.py`,
score 2.685 — top entry with measured coverage data; the
score-4.0/3.0 rows above it are coverage-omit artifacts of
the `*/test_*.py` pattern in `pyproject.toml`, see note
below). **0 production bugs surfaced.**

- `workflows/dependency_check.py`
  (`DependencyCheckWorkflow`) — no bugs. The module is a
  ~230-line thin async shell around
  `claude_agent_sdk.query()`: validates `path`, maps depth
  → max_turns, defines two `AgentDefinition` subagents
  (`inventory-assessor`, `update-advisor`), collects
  `AssistantMessage` + `ResultMessage` stream output via
  `agent_sdk_adapter.collect_agent_output`, hands the
  result to `AgentSDKResultAdapter.from_agent_output`.
  Each specific exception type (`ImportError`,
  `ConnectionError`, `TimeoutError`, generic `Exception`)
  is converted to a structured `_error_result`. The
  catch-all `except Exception` is documented intentional
  with `# noqa: BLE001`. No dead code; no crash paths.

**Coverage delta:** 41.67% → 100.00% (line + branch).

**Tests:** 21 added under
`tests/unit/workflows/test_dependency_check_execute.py`.
Only `claude_agent_sdk.query` is mocked (would otherwise
make real API calls); the `AssistantMessage`,
`ResultMessage`, and `TextBlock` instances yielded by the
fake generator are **real SDK dataclass instances**, not
duck-typed `MagicMock`s — per the existing CLAUDE.md
lesson "Duck-typed test fakes fail isinstance-based
collectors silently." Determinism verified across 3
back-to-back runs and under `-n auto` alongside the full
`tests/unit/workflows/` + `tests/workflows/` subtree
(2373 passed, no cross-test interference).

**Rubric note (operational, not a bug):** the rubric's
top 11 rows above `dependency_check` all sit at `?`
covered_pct (scores 4.0 and 3.0 across
`workflows/test_*.py` files and
`workflows/test_gen/test_templates.py`). These are real
production modules but coverage.py never measures them
because the `*/test_*.py` omit pattern in
`pyproject.toml` matches their filenames. The rubric
should filter `?` covered_pct rows out of the
working-set top, or the omit pattern should be tightened
to `tests/test_*.py` so production modules with
"test_" in their name remain measurable. Flagged for a
follow-up rubric refinement; not blocking this cycle's
ship.

**Pattern observation (extends prior session's note):**
the bug-find pattern continues — composed data-handling
helpers (memory/security/query.py) surfaced 1 class-1
crash bug, while customer-facing entry points
(ops/cli.py) and now SDK-native orchestrators
(workflows/dependency_check.py) surface zero. The
SDK-native shape is uniform across `bug_predict`,
`perf_audit`, `refactor_plan` and the test pattern
established here should transfer with minor renames.

---

## 2026-05-12 — third module under test-quality-program (Opus 4.7)

Third module run, first weight-5 (user-typed entry) pick. Selected
via the rubric working set after `memory/short_term/conflicts.py`
shipped (`ops/cli.py`, score 3.19). **0 production bugs surfaced.**

- `ops/cli.py` (`attune ops` entry) — no bugs. Module is a thin
  argparse + uvicorn launcher (151 lines). Two minor style smells
  noted but not fixed in this PR: (a) line 82 imports uvicorn just
  to check availability and line 135 re-imports — redundant but
  cheap due to Python's import cache; (b) line 146
  `parser.parse_args(["ops", *sys.argv[1:]])` could double-inject
  "ops" if a user runs `python -m attune.ops ops --port 8000`,
  but the case is unrealistic. Not in scope.

**Coverage delta:** 36.2% → 100.00% (line + branch).

**Tests:** 19 added under `tests/unit/ops/test_cli.py`. Real
argparse, real `build_config`, real `create_app`. Only `uvicorn.run`
(would block) and `webbrowser.open` (would open real browser)
patched. Determinism verified across 3 back-to-back runs and under
`-n auto` alongside the full ops test subtree (142 passed, no
cross-test interference).

**Pattern observation:** weight-5 modules surfaced no bugs while
weight-3 data-handling modules surfaced 1 in 2 sessions. Early but
suggestive — customer-facing entry points tend to be defensively
written. The bug-hunt yield concentrates in composed helpers, not
in user-typed entry points. Worth re-evaluating after 5+ modules.

---

## 2026-05-12 — second module under test-quality-program (Opus 4.7)

Second module run after the PoC. Selected via the rubric working
set after the first pair shipped (score 3.35, third row at the
time). **0 production bugs surfaced.**

- `memory/short_term/conflicts.py` (`ConflictNegotiation`) —
  no bugs. Every public method validates inputs (empty
  conflict_id → `ValueError`, non-dict positions/interests →
  `TypeError`), gates permissions (CONTRIBUTOR for create,
  VALIDATOR for resolve, any tier for read), and round-trips
  cleanly through `ConflictContext.to_dict/from_dict` with
  documented TTLs. The 41 previously-uncovered lines were
  legitimate uncovered behavior, not hidden defects.

**Coverage delta:** 25.4% → 100.00% (line + branch).

**Tests:** 44 added under
`tests/unit/memory/short_term/test_conflicts.py`. Real
`BaseOperations(use_mock=True)` host (the established
short_term test pattern in `test_short_term.py`) composed
with `ConflictNegotiation`. No mocks of storage — the
mock-mode BaseOperations is a real in-memory store, faithful
to production semantics. Determinism verified across 3
back-to-back runs and under `-n auto` alongside the full
memory test subtree (1411 passed, no cross-test interference).

**Test-reliability note (class 5 nudge, not a bug):** structlog
emits to stdout, not Python's `logging` module. The two
log-event verification tests initially used `caplog`, which
returned empty records. Switched to `capsys` per the existing
CLAUDE.md lesson "structlog default output pollutes
stdout-captured CLI tests." Fixed inline before commit.

---

## 2026-05-12 — first PoC under test-quality-program spec (Opus 4.7)

First module pair taken through the formalized playbook
(`docs/specs/test-quality-program/`, spec PR #257).
Paired PR: `memory/security/query.py` + `memory/security/reports.py`.
Selected via rubric (top two scores in the working set: 3.99 and
3.80, both data-handling 1.5× risk). **1 production bug surfaced.**

- `memory/security/query.py` — **class 1** — a single audit log
  line with a malformed `timestamp` aborted iteration. Inner
  try-except caught only `JSONDecodeError`, so `ValueError` from
  `datetime.fromisoformat()` propagated to the outer broad except
  clause — the function logged once and returned whatever results
  had accumulated so far. Symptom: a query with date filters
  silently truncated its result set with no caller-visible
  indication. Fix: per-line try/except for `(ValueError,
  AttributeError)` inside the iteration loop, mirroring the
  JSONDecodeError handler. Continues iteration on bad lines,
  logs a warning per skip.

**Coverage delta:**

| Module | Before | After |
|---|---|---|
| `memory/security/query.py` | 11.2% | 100.00% |
| `memory/security/reports.py` | 11.2% | 100.00% |

**Tests:** 62 total (37 query, 25 reports). Real `AuditLogger`
host instances against `tmp_path` — criterion-5 "real objects
over mocks" of the meaningful-coverage definition. Determinism
verified across 3 back-to-back runs and under `-n auto`
alongside the full memory test subtree (1367 passed, no
cross-test interference).

**Notes on the second module:** `reports.py` surfaced no
production bugs. Every defensive `.get(..., default)` path is
real and reachable (the audit-log JSON shape isn't strictly
enforced upstream so missing keys do happen in production). No
Class 2 candidates. Demonstrates the spec's "absence of bugs is
also data" observation from prior sessions.

---

## 2026-05-09 — session 49f (Opus 4.7)

Executed `docs/specs/deprecated-module-retirement/` (drafted earlier
this session as the natural follow-on from the ignored-tests spec).
**2 production modules retired** — both Class 5.

### Bugs — Class 5 (deprecated production code outliving its tests)

- `src/attune/workflows/orchestrated_release_prep.py` (637 lines).
  Deprecated v5.2.0, scheduled for removal in v6.0, currently shipping
  in v6.6.0 — six minor versions overdue. Its targeted-coverage tests
  in `tests/unit/test_coverage_batch6.py` were retired here as part of
  the same commit (the only thing keeping the module's coverage
  numbers up). Replacement (`ReleasePrepTeamWorkflow` at
  `src/attune/agents/release/release_prep_team.py:359`) has shipped
  since v5.2.0 with its own live tests.
- `src/attune/scaffolding/` (entire package — 9 files, 2,254 lines
  including templates). Deprecated 2026-02-21 (PR #60); `__main__.py`
  prints a runtime deprecation notice on every invocation pointing at
  `attune workflow run`. Already excluded from coverage measurement
  in `pyproject.toml`. Tests for the CLI were retired in the
  ignored-tests spec (2026-05-09) on grounds of mock-driven decay
  (`sys.modules["test_generator"] = MagicMock()`).

### Why this deserves its own class

In Class 1/2/3, the *bug* is in the code under coverage analysis —
something that crashes, something unreachable, something the tests
mock around. In Class 5, the code itself isn't broken; it does what
it's supposed to do. The bug is the *survival* of the module past
its scheduled removal date. Coverage analysis surfaces it because
the module has either zero tests or only tests that exercise the
deprecated surface (which then look like waste during a coverage
push). The fix isn't a code change — it's a deletion.

The detection signature: a module with `.. deprecated::` in its
docstring, low-quality or no tests, and no callers in either the
internal codebase or sibling repos. If the scheduled-removal version
has already shipped, that's the strong signal.

### Side cleanups picked up while removing the deprecated modules

- `examples/orchestration/basic_usage.py` — Example 3 imported
  `attune.workflows.test_coverage_boost`, a module deleted in an
  earlier release. The example file had a dead import nobody
  noticed because the file isn't imported by anything else
  (examples aren't run by the test suite). Cleaned up as part of
  the rewrite for D1.
- `src/attune/agents/release/release_prep_team.py:362` — docstring
  referenced "the same interface as `OrchestratedReleasePrepWorkflow`,"
  a class about to be deleted. Updated.

### Tally update

| Class | Description | Count |
|-------|-------------|-------|
| 1 | Crash paths nobody triggered | 3 |
| 2 | Dead defensive code | 13 |
| 3 | Tests mocking around bugs | 1 |
| 4 | Load-bearing comments nobody re-validated | 1 |
| 5 | Deprecated production code outliving its tests | **2** |

---

## 2026-05-09 — session 49e (Opus 4.7)

Test-infrastructure spec executed (docs/specs/test-infrastructure/).
**3 production bugs surfaced**, none in the spec's target area — all
side effects of investigating it.

### Spec outcome (Phase 2A diagnosis)

The "biggest infrastructure debt" identified in the project-health
audit turned out to be a stale comment, not a real bug. `pytest.ini`
forced `-n 0` (sequential execution) for years based on a one-line
comment about "import timing issues with workflows package." Test #1
of the spec (flip `-n 0` → `-n auto`, run full suite) just worked:
14,073 tests pass under xdist in 101 seconds. The issue evidently
got fixed incidentally as the codebase evolved; nobody re-checked
the constraint.

This is a **fourth diagnostic pattern worth naming**: "load-bearing
comment that nobody re-validated." Different shape from Class 1/2/3,
because the bug is in the documented constraint, not the code.

### Bugs surfaced as side effects

- `plugin/.claude-plugin/marketplace.json` + `plugin/core/__init__.py`
  — version mismatch (6.3.0 vs plugin.json 6.6.0) from PR #204's
  release bump that didn't propagate. Surfaced by `test_all_versions_match`
  under the re-enabled parallel run, NOT introduced by it. Bumped both
  to 6.6.0.
- `tests/unit/plugins/test_plugin_config_validation.py` — test asserted
  `plugin/commands/` directory shouldn't exist (skills migration), but
  PR #204 intentionally added `plugin/commands/handoff.md`. Test wasn't
  updated. Replaced with `test_commands_directory_only_has_allowlisted_commands`
  with explicit allowlist.
- 463 stale help templates in `plugin/help/generated/`. The
  `Check Help Template Freshness` pre-commit hook is warn-only locally
  but in CI auto-regenerates and reports "files modified by hook" as
  a failure. This had been blocking dependabot PRs (#191, #192) for
  5+ days. Regenerated via `ATTUNE_DOCS_AUTOREGEN=1`; both PRs unblocked
  on rebase.

### Audit findings (task #4)

The four `--ignore`-d test files in `pytest.ini` were audited. All
four have real test debt totaling 88 failures. Resolution deferred
to a follow-up spec because each needs design work, not 5-minute
fixes. Findings documented inline in `pytest.ini`.

---

## 2026-05-09 — session 49d (Opus 4.7)

Targeted sweep using a new AST-based scanner
(`scripts/find_dead_defensive_code.py`) for the four Class 2 sub-patterns.
**2 production bugs surfaced**, both Class 2A (the most common shape).

### Tooling added

- `scripts/find_dead_defensive_code.py` — heuristic finder for 2A
  (exhaustive enum dispatch + dead default), 2B (post-loop fallback),
  2C (divisor guard hints). Walks the AST and emits candidates worth
  reading. Self-bootstraps the enum-member map by walking the source
  tree first.

### Bugs — Class 2A (default after exhaustive enum dispatch)

- `models/tasks.py:get_tasks_for_tier` — `if tier == ModelTier.X` for
  all three members of `ModelTier`, followed by `return []`. The
  trailing default was unreachable for known tiers and silently swallowed
  unknown ones. Replaced with `raise ValueError(f"Unknown ModelTier: ...")`
  and added a test for the raise path.
- `trust/circuit_breaker.py:should_require_confirmation` — same shape on
  `TrustState`. Trailing `return True  # Default to safe` was unreachable
  AND would have masked an incomplete dispatch if a new state were added.
  Replaced with `raise ValueError(f"Unknown TrustState: ...")` and a
  matching test.

This brings sub-pattern 2A's known instances to **6 across 6 unrelated
modules** (`meta_orch_estimation`, `meta_orch_analysis`, `explainer`,
`ab_testing/allocator`, `models/tasks`, `trust/circuit_breaker`). The
shape repeats reliably enough to argue it's a stable category.

The 2C scanner emitted 4 candidates that all need manual review (it
flags any `if x > 0:` guarding `/x`, regardless of whether the divisor
is structurally non-zero). Triaging those is left as future work.

---

## 2026-05-09 — session 49c (Opus 4.7)

13 modules pushed to 100% (or accepted ~98% for partial for-loop branches).
**2 production bugs surfaced** — both Class 2 (dead defensive code).

### Modules — 0 bugs

- `socratic/feedback_models.py` — 91.53% → 100% (4 zero-use guard branches in
  `get_score_for_context`)
- `socratic/collaboration_models.py` — 93.55% → 100% (roundtrip serialization
  for Comment/Vote/Change/CollaborativeSession + VotingResult.approval_rate
  zero-active branch)
- `socratic/success_models.py` — 93.92% → 100% (BOOLEAN-with-non-bool
  fall-through, LOWER_IS_BETTER no-max, RANGE infinite size, unknown
  direction default)
- `socratic/ascii_visualizer.py` — 90.00% → 100% (>3 tools, long agent string
  truncation, parallel marker, _center text-wider-than-width, empty-stage
  agent listing skip)
- `socratic/generator.py` — 95.45% → 100% (unknown-template skip,
  reporter-only/generator-only stages, real `_create_xml_agent`)
- `socratic/html_renderer.py` — 96.30% → 100% (show_when data attribute,
  option description span)
- `socratic/ab_testing/models.py` — 97.85% → 100% (avg_success_score
  zero-impressions short-circuit)
- `socratic/session.py` — 93.50% → 100% (can_generate at max_rounds,
  from_dict goal_analysis reconstruction)
- `workflows/progress.py` — 69.01% → 100% (full ProgressTracker lifecycle:
  callback errors, stage start/complete/fail/skip/fallback/retry, async
  callback path, factory)

### Bugs — Class 2 (dead defensive code)

- `socratic/explainer.py` — Defensive default `return explanation.to_markdown()`
  after the `OutputFormat` enum chain (TEXT/MARKDOWN/HTML/JSON all explicitly
  handled). The enum has exactly four values, all covered above. Removed and
  collapsed JSON branch into the natural-fall-through path.
- `socratic/ab_testing/allocator.py` — Defensive default
  `return self._fixed_allocation(user_id)` after the `AllocationStrategy`
  enum chain (FIXED/EPSILON_GREEDY/THOMPSON_SAMPLING/UCB all explicitly
  handled). Same pattern: 4 enum values, all covered. Replaced final
  `if`-check with direct `return self._ucb_allocation()`.

Both bugs are sub-pattern A of Class 2 — **"defensive default after
exhaustive enum dispatch."** Same shape, same fix. This is at least the
fourth instance of this exact pattern (also seen in
`meta_orch_estimation.py`, `meta_orch_analysis.py`, and `retry.py` post-loop
fallback variants).

---

## 2026-05-09 — session 49b (Opus 4.7)

6 additional modules pushed to 100% (or accepted ~96% for module-import
unreachable code). **0 production bugs surfaced.** Absence of bugs is also
data — these modules were already well-tested at edges; the coverage gaps
were genuine missing tests, not hidden defects.

- `resilience/circuit_breaker.py` — 87.93% → 100%
- `workflows/escalation/convenience.py` — 88.89% → 100%
- `workflows/progress_models.py` — 98.18% → 100%
- `workflows/state_mixin.py` — 97.67% → 100%
- `workflows/progress.py` — 69.01% → 100% (new test_progress_tracker.py)
- `workflows/telemetry_mixin.py` — 87.34% → 96.20% (module-import
  ImportError fallback at lines 29-31 is unreachable post-import; accepted)

---

## 2026-05-09 — session 49 (Opus 4.7)

11 modules pushed to 100%. 4 production bugs surfaced.

- `socratic/cli_console.py` — **class 1** — `Console.table()` raised
  `IndexError` when a row had more cells than headers (guard existed in the
  width-calculation loop, missing in the print loop). Fixed by mirroring the
  guard.
- `orchestration/meta_orchestrator.py` — **class 1** — `compose_team()` read
  `plan.phases`, but `ExecutionPlan` has no `phases` attribute. Every call
  raised `AttributeError`. Replaced with `[]` (matches what
  `DynamicTeamBuilder.build_from_plan` defaults to).
- `orchestration/meta_orch_analysis.py` — **class 2** — `_classify_domain`
  had an unreachable for-loop-fell-through branch (the inner `return`
  always fires when `max_score > 0`). Refactored to `max(scores, key=...)`.
- `resilience/retry.py` — **class 2** — three identical post-loop blocks
  (`if last_exception: raise last_exception`) were unreachable: the loop
  always raises or returns. Removed across `async_wrapper`, `sync_wrapper`,
  and `retry_with_backoff`. Kept the `RuntimeError` fallback, which IS
  reachable when `max_attempts < 1`.

---

## Prior cumulative sessions (retroactive — recovered from session notes)

Bugs found and fixed across earlier coverage pushes. Less granular because
they predate this log.

- `socratic/feedback_collector.py` — **class 3** — infinite recursion
  between `get_insights()` and `_generate_recommendations()`. Existing tests
  passed by mocking the recursive caller. Fixed by extracting a
  `_compute_domain_insights()` helper and breaking the cycle.
- `socratic/engine.py` — **class 1** — `_generate_success_criteria`
  constructed `SuccessMetric()` without the required `description` argument.
- `meta_workflows/pattern_memory.py` — **class 2** — unreachable
  `if form_response:` block (line 233) removed.
- `meta_workflows/llm_execution.py` — **class 2** — dead
  `raise RuntimeError("No tiers attempted")` removed.
- `meta_workflows/pattern_learner.py` — **class 2** — dead
  `if failure_count > 0:` removed (creating an entry always increments past
  zero).
- `models/provider_config.py` — **class 2** — dead `if model:` filter
  removed.
- `models/telemetry/analytics.py` — **class 2** — three dead defensive
  `if x > 0:` divisor guards removed.

---

## Tally

| Class | Description | Count |
|-------|-------------|-------|
| 1 | Crash paths nobody triggered | 3 |
| 2 | Dead defensive code | 13 |
| 3 | Tests mocking around bugs | 1 |
| 4 | Load-bearing comments nobody re-validated | 1 |
| 5 | Deprecated production code outliving its tests | 2 |
| 6 | Correct in isolation, broken in composition | 1 |

**Class 2 sub-patterns observed:**

- **2A — Defensive default after exhaustive enum dispatch.** A function
  switches on an enum, handles every value explicitly, then has a
  trailing default. Dead. (6 instances: `meta_orch_estimation`,
  `meta_orch_analysis`, `explainer`, `ab_testing/allocator`,
  `models/tasks`, `trust/circuit_breaker` — last two found by
  `scripts/find_dead_defensive_code.py`.)
- **2B — Post-loop fallback after a loop that always returns/raises.**
  `for ... try: return except: raise` patterns where the loop body
  guarantees exit, but a `if last_exception: raise` block sits beneath it
  anyway. Dead. (3 instances in `retry.py`.)
- **2C — Defensive divisor guard where divisor is structurally non-zero.**
  `if x > 0:` before division, where every code path that creates the
  entry also increments past 0. Dead. (3 instances in
  `telemetry/analytics.py`, 1 in `pattern_learner.py`.)
- **2D — Filter on already-filtered data.** `if model:` filter applied to
  a list whose construction already excluded falsy entries. Dead.
  (1 instance: `provider_config.py`.)

**Class 3 sub-patterns observed:**

- **3A — Test mocks around the bug.** The original class-3 shape: the
  mock stands in for the faulty path, so the defect never executes
  under test. (1 instance — the existing class-3 entry.)
- **3B — Test pins the defective value as the expected contract.**
  Nothing is mocked; the assertion hard-codes the buggy literal, so the
  suite RESISTS the fix rather than catching the bug — correcting the
  code fails the test and the assertion must be rewritten. (1 instance:
  `elicitation/widget.py`'s fixed element id, 2026-07-24 — see the
  class 6 entry.)

**Class 6 detection note.** Coverage cannot reach this class by
construction, so it needs a different probe: instantiate/render TWICE
and assert the two results differ in whatever identifier they carry.
Worth a sweep wherever generated artifacts embed fixed ids.

**Sessions where 0 bugs surfaced:** 1 (session 49b).

**Bug-find rate:** 18 bugs across 81 modules pushed to 100% = ~22% of
modules contain at least one production bug surfaced by the coverage push.
Plus 3 merge-artifact bugs surfaced by the test-infrastructure spec
(version mismatch, commands-directory test, stale templates) that aren't
strictly coverage-push finds but came from the same investigative posture.
Classes 5 and 6 sit outside that denominator too: class 5 is deprecation
debt rather than a defect, and the class 6 bug came from dogfooding, not
a coverage push. So the table now sums to 21 while the ~22% rate still
describes the 18 classes-1–4 coverage-push finds. (The class 5 row was
missing from this table until 2026-07-24 — it was recorded in the
session-49f snapshot above but never propagated here.)

Modules at 100%: 99 (cumulative across all sessions; +4 from the 2026-08-01 fleet — facade and fix_intake closed at 99% with their remainders classified: one dead-code region, one unreachable-without-mocking guard).

## 2026-08-16 — hooks/executor.py lane (weekly-report Tier 1)

One environment bug, security-relevant:

- **Webhook test suite silently skipped in EVERY environment,
  CI included — classification: dead.** `aiohttp` lived only in the
  `[all]` extra; CI installs `.[dev]` and local venvs sync the `dev`
  dependency group, so `tests/unit/hooks/test_executor_webhook_security.py`
  — the SSRF and DNS-rebinding-pin guards for `_execute_webhook` —
  `importorskip`'d away everywhere since the suite was written. The
  dev-group mirror guard was innocent (extra ≡ group held; both
  lacked aiohttp). Fix: aiohttp added to the `[dev]` extra + `dev`
  group (CVE floor pinned per `[all]`); the 15 webhook tests now run,
  plus 3 new tests for the branches they never reached (WEBHOOK
  dispatch through `execute()`, ≥400 raise, non-JSON fallback).
  Module 82.52% → 100%.

Addendum, same day: the dead-suite guard's first census caught a SECOND
instance — classification: dead. `bcrypt` lived only in
[backend]/[enterprise]/[all], so BOTH backend auth-security suites
(tests/backend/test_auth_security.py,
tests/unit/backend/test_auth_db_exceptions.py — 41 tests) had
importorskip'd away everywhere since they were written. Fixed in the
retro-tooling PR (bcrypt added to the [dev] extra + dev group);
tests/unit/test_no_dead_suites.py now guards the class with an empty
allowlist.

## 2026-08-26 — post-release self-review, 15.1.0 (release-execute step 16)

Two runner-launched runs against the shipped tree (`src` at
`6f259a86e`, verified from the filesystem — `pyproject.toml` on disk
AND the imported `__version__` both read 15.1.0, tree clean, 0 behind
`origin/main`): `code-review` run `19ddfd91bd4c` (334s, cost not
reported by the runner) and `bug-predict` run `ca0c52c6c121`, **58/100**
(263s, **$2.19**). Both exit 0 with `sdk_error_kind: None` and a report
present, so neither is the exit-0-with-traceback false success.

**No finding blocked the release.** Every one sits in code 15.1.0 did
not touch — the inverse of the 14.0.0 precedent, where the release's own
headline feature carried the worst defect. Four worth recording:

- **CORRECTION (same day): the 2026-08-22 "bug-predict emits zero
  structured findings" finding is FIXED, and the entry first written here
  claiming it still stood was MY OWN PROBE ERROR.** The original fix
  (`output_format=WORKFLOW_OUTPUT_SCHEMA` in `workflows/bug_predict.py`)
  works. Recounted with the right key:

      a6e92650d199 (14.0.0, 08-22)  sections=0  [none]        <- the real finding
      410497bd6f90 (interim)        sections=2  [Bugs=18, Next steps=8]
      ca0c52c6c121 (today, 15.1.0)  sections=2  [Bugs=15, Next steps=6]

  A findings-kind section carries its rows under **`findings`**; a
  next-steps section under `items`. My probe read
  `s.get("rows") or s.get("items")`, which is empty for the Bugs section
  by construction, so I read 15 real findings as zero and wrote up a
  regression that does not exist ("acquired a shape that hides it").
  Nothing was wrong with the workflow. **Classification: no bug — a
  fabricated finding, retracted.** Recorded rather than deleted because
  the failure is the point: this was the THIRD instance in one session of
  counting with the wrong key and reporting a confident number
  (`grep -l` files-vs-references at 8-vs-127; sections-vs-rows here;
  rows-vs-findings on the recheck). Each time the number was plausible,
  load-bearing, and wrong. The durable rule is to print the container's
  KEYS before counting anything inside it.

- **`agents/release/release_parsing.py:43` — contract violation,
  HIGH, verified in source.** `_parse_response` is typed `-> dict` and
  documented "never returns None", but Strategy 1 (XML delimiters) and
  Strategy 2 (markdown-fenced) both `return json.loads(...)` unguarded.
  An LLM emitting a fenced JSON ARRAY or bare scalar parses fine and
  returns a non-dict; consumers (`quality_agent.py:79-84`,
  `security_agent.py:158-163`) then raise TypeError, which is swallowed
  and surfaces as a spurious release-gate failure with
  `quality_score 0.0`. Strategy 3 already guards with
  `text.startswith("{")` — the other two were never given the same
  check. Failure mode bites DURING a release, which is where it is
  least welcome. Fix: `isinstance(result, dict)` guard after each
  `json.loads`, else fall through to the existing `{'parse_error': ...}`
  default. Not yet fixed.

- **`lessons/__init__.py:89` — unchecked negative index, HIGH, verified
  in source.** `text[text.find(_LESSONS_HEADING):]`. When the heading is
  absent `find` returns `-1` and `text[-1:]` silently slices the LAST
  CHARACTER instead of raising, producing a silently-wrong lesson parse
  rather than a loud failure. Not yet fixed.

- **`workflow_patterns/structural.py:37` + `output.py:36` — reported
  HIGH by code-review as "codegen silently ignores caller-supplied
  names, ships silently broken output today". DOWNGRADED to Low on
  verification.** Both lines do discard a `.get()` return value, but
  each file discards exactly the name its own templates never reference
  — confirmed by AST: `class_name` appears 1x in `structural.py`'s
  `generate_code_sections` (the dead call itself) and `workflow_name`
  1x in `output.py`'s. Nothing is ignored and no broken output ships;
  they are vestigial statements worth deleting for clarity. Ruff cannot
  catch them because `context.get(...)` is a CALL, so `B018`
  (useless-expression) does not fire. **Recorded because the severity
  was wrong, not the observation** — an unverified read of this finding
  would have held the release.

Remaining findings (structural, none blocking): two competing config
systems half-migrated (`config/legacy.py` vs UnifiedConfig);
`ModelTier` defined 5+ times and `ModelProvider` twice; `BaseWorkflow`
composing 14 mixins behind a ~20-param constructor; a parallel
mixin-AND-service layer for the same capabilities; `workflows/` as a
133-file catch-all; `ops/routes/specs.py:93` doing synchronous
filesystem work inside `async def` handlers on the event loop.
`BaseWorkflow` is genuinely defined 3x (`agent_factory/base.py`,
`plugins/base.py`, `workflows/base.py`) — unlike the `WorkflowConfig`
collision, which 15.1.0 resolved and which now has a shrink-only gate.


## 2026-08-22 — post-release self-review, 14.0.0 (release-execute step 16)

Two dashboard-launched runs against the shipped tree (`src` at
`c47ae532`, verified from the filesystem rather than a ref):
`code-review` 74/100 (308s, $4.26, run `06e56c93ab9f`) and
`bug-predict` 60/100 (200s, $2.03, run `a6e92650d199`). 23 findings,
none Critical, no High security. Three worth recording:

- **The release-audit stage's own scanner walks every file 4x more
  than it needs to — classification: perf, in code this release
  shipped.** `classes/rules.py:474` `scan_source` loops the 8-rule
  pack calling `rule.check(tree, path)` per rule, but only TWO
  visitor classes exist (`_V1Sweep` :129, `_R7Visitor` :324) — so
  each rule constructs and runs a full traversal and then filters by
  rule id, giving 8 full AST walks where 2 suffice. Verified by
  reading both visitors and counting `RULES` (8). This is the
  per-release sweep AND the continuous gates, so it burns ~4x the
  necessary CPU repo-wide on every CI push. Fix is mechanical: run
  each sweep once, slice hits by `rule_id`. FIXED in #2187 — 751
  files, 121 hits before and after with 0 mismatches, traversals
  8 -> 2 per file, guarded by a mutation-checked traversal-count
  test. D11 lane (codex) came back clean before the chair read it.

- **`_get_commit_diff` never got the hardening its sibling has —
  classification: latent security (Low).**
  `patterns/git_extractor.py:242` passes refs straight to
  `subprocess.run`, while `_get_commit_info` in the SAME file rejects
  `-`-prefixed refs (:213) and pins the argument list with `--`
  (:210). Verified by reading both. A partial fix that stopped one
  function short: git option-injection remains reachable through the
  diff path. Not yet fixed.

- **`bug-predict` has produced ZERO structured findings in every run
  since at least 2026-08-02 — classification: dead surface.** The
  report carries a rich prose summary (naming resource leaks and
  unchecked `split()[0]`/`int()` on user input) but `sections: []`
  and `suggestions: []`. Checked all six historical run records in
  `~/.attune/ops/runs/bug-predict/`: 6/6 have `sections=0,
  findings=0`, while every one reports `completed` / exit 0. So the
  ops findings UI and any `sections`-consuming automation have been
  getting nothing from this workflow for three weeks, and the run
  looks healthy the whole time. The adapter builds sections from
  per-heading structured `items`
  (`workflows/agent_sdk_adapter.py:1717`); bug-predict's output does
  not populate them. NOT a 14.0.0 regression — it predates the
  release. Half of the step-16 pair only delivers value if a human
  reads the prose.

Note on the step itself: the first attempt at this self-review was
LOST — the ops dashboard had been launched from inside a Claude Code
session, so session teardown killed the in-flight run before
`_persist_run` could write a record. Relaunched `nohup`-detached.
Separately, a ref-level check (`git rev-parse origin/main:src` vs the
tag) nearly pointed the review at a main checkout that was 17 commits
BEHIND `origin/main`; caught by a version disagreement, not by git.
Both are lessons in the 2026-08-22 outbox batch.

## 2026-08-24 — 14.1.0 post-release self-review (release-execute step 16)

**Tree verified from the filesystem**: worktree detached at merge SHA
`9f91c9b757c2b66a3786803755dc3a9baface8ff`; on-disk pyproject AND
imported `__version__` both 14.1.0 before any run.

**Runner-launched runs (the recording path) — ALL FAILED at $0:**
code-review `6fb48d4803a4` + `f7c4f64e2a56`, bug-predict
`aa6f7933a92f` + `a74c126a148f` (exit 1, `sdk_error_kind: unknown`;
second pair launched with `ANTHROPIC_API_KEY` verified present in the
server env — same failure). No scores or costs exist for the pair; per
step 16's own rule those runs are NOT claimed as a completed review.

**Top finding (severity: HIGH — filed #2227, verify-note inline):** the
CLI/ops-runner spawn path fails deterministically in this environment —
verbose repro of the exact runner command surfaced
`ModuleNotFoundError: No module named 'opentelemetry'` +
`Exception: Claude Code returned an error result: success`
(is_error-on-success), while the in-process path executed 16+ billed
workflow runs the same night without a single transport failure
(receipts: probe registry records, live NO_GO/DEGRADED/sweep receipts in
the 14.1.0 changelog). VERIFIED by side-by-side execution, not
inference; localizes the fleet roundtable's doc-gen/research-synthesis
"deterministic SDK failure" class to the spawn context. Second finding
(severity: MEDIUM, recorded in #2227): the run-record's `sdk_stderr`
health probe reported an unrelated auth condition ("subscription
disabled") because it probes a bare `claude` without the workflow env —
a misleading-diagnostic class.

**Analytical coverage note (context, not a substitute claim):** this
release's tree DID receive an unusually deep behavioral pass the same
night — 14 planted-defect probes across 16 workflow surfaces (~$14
billed) finding 5 real production defects, 4 fixed in-release — but the
canonical step-16 run-pair remains BLOCKED on #2227 and is owed once
that lands. This entry is the receipt of what actually ran and what
did not.

**UPDATE 2026-08-24 ~03:25 UTC — owed runner pair EXECUTED; #2227
closed (PR #2229, merged 03:18:32Z, squash `62fb4d124`).** Root cause
decomposed by live bisection, all probes $0: (1) the deterministic
$0 signature was the API key at its console usage cap (`400 …
specified API usage limits`), not a spawn-context transport defect —
the CLI wraps api_error results as `subtype:"success", is_error:true`
and the SDK's ProcessError replacement names only the subtype, so the
real cause was dropped twice; (2) the "subscription disabled" stderr
probe message was an artifact of probing a bare `claude` in the
parent env, where `CLAUDE_CODE_ENTRYPOINT=claude-desktop` flips auth
to the org-disabled subscription path; (3) the `opentelemetry`
ModuleNotFoundError is benign SDK-internal DEBUG noise. Fix on main:
in-stream error-text capture → classified `SdkSubprocessError`,
`sdk_error_from_exception()` in all 14 workflow catch-alls, probe env
mirrors the SDK child. After the chair raised BOTH spend limits
(org + workspace), the exact runner command completed end-to-end on
the 14.1.0 tree (`PYTHONPATH=<main>/src python -m attune.cli_minimal
workflow run <wf> --path <main>/src/attune`):

- **code-review**: exit 0, **$4.77, 353.7s** — real findings
  (telemetry feedback-loop Redis N+1s, models↔workflows dependency
  cycle, agent_sdk_adapter god-module split, Empathy-naming
  excision remainder).
- **bug-predict**: exit 0, **$2.34, 275.7s** — real findings
  (unchecked `json.loads` on Redis data in
  `memory/redis_memory_coordination.py:252` [HIGH], `gather`
  fan-outs without `return_exceptions` in 5 team/batch sites,
  blanket BLE001 ignore for `src/attune/**`).

Pair total $7.11 (estimate band $3–8). The step-16 obligation for
14.1.0 is now DISCHARGED with receipts; findings above are triage
candidates, not yet filed issues.

## 2026-08-27 — 16.0.0 post-release self-review (step 16 receipt)

Both runs ops-runner-launched (server on the merge-SHA-identical
worktree tree, `85252d3a7`; tree identity verified by tree-hash
compare) and persisted to `~/.attune/ops/runs/`:

- **code-review** run `58395f0fbc57` — score **72/100**, $5.92,
  440s. 39 findings (Security 10: 3 High; Quality 11; Performance 7;
  Architecture 11). Top finding [HIGH, verify-the-claim: read
  `backend/api/users.py:24` and trace `Depends(security)` vs
  `verify_token` call sites]: **17 backend endpoints inject
  HTTPBearer but never call verify_token — any syntactically valid
  bearer header authenticates destructive routes** (account
  deletion, purchases, license deactivation). Same class as the
  2026-08-02 review's "Critical backend auth gap" — RECURRING,
  strongest candidate for immediate triage.
- **bug-predict** run `8ba0979ddd58` — risk **44/100**
  (moderate-low), $3.09, 298s. 16 findings (5 HIGH). Tops
  [verify-the-claim notes inline]: `classes/reconcile.py:122`
  fail-open — `r.get('headSha', head_sha)` treats a record MISSING
  headSha as matching the target SHA (read the dict-get default);
  `orchestration/ghosts/worktree.py` — four `subprocess.run` git
  calls with no `timeout=` (grep confirms); `release_parsing.py`
  `_parse_response` — raw `json.loads` of model text with no schema
  validation feeding decision logic (the known silent-green LLM
  parsing class).

Pair total **$9.01** (band $5–10). Step 16 for 16.0.0 is DISCHARGED
with receipts; findings are triage candidates, not filed issues. The
release notes may now claim the review happened.

## 2026-08-27 — backend/api bearer-token verification (dormant-code hardening)

Verified and fixed the code-review lead (run `58395f0fbc57`) that
"17 endpoints skip `verify_token`". **Classification: Class 1
(latent security defect) in DORMANT code** — the `backend/`
FastAPI app is deployed nowhere (verified 2026-08-27: no Vercel
Python project, `smartaimemory.com/api/health` 404s, `BACKEND_URL`
unset in prod), so this is hardening, not a live incident.

**Verification (traced all 20 `Depends(security)` sites):** the "17"
is confirmed exactly. The bare `HTTPBearer` proved a header was
*present* (missing header → auto-reject) but never validated the
token, so any non-empty bearer — forged or expired — was accepted
and the handler returned 2xx.
- **Genuinely unverified (17):** `analysis.py` ×6 (`create_session`,
  `get_session`, `analyze_project`, `analyze_file`,
  `get_analysis_history`, `delete_session`), `subscriptions.py` ×7,
  `users.py` ×4.
- **Already verified (3):** `auth.py` `refresh_token`,
  `get_current_user`, `validate_license` — all reach
  `AuthService.verify_token` (`jwt.decode`, raises 401).
- **Adjacent finding, out of the 17-scope:** `wizards.py` has *zero*
  auth dependency on its routes.

**Fix:** single-sourced the JWT decode into module-level
`auth_service.verify_access_token`; new `backend/api/dependencies.py`
`require_principal` dependency verifies the token and returns the
principal; the 17 routes now use `Depends(require_principal)`.
Regression guard: `tests/unit/backend/test_api_bearer_verification.py`
(58 tests) proves a forged bearer → 401 on each of the 17 via a real
`TestClient`, plus expired-token and helper unit coverage. No new
`except` sites (the two in `verify_token` were relocated within
`auth_service.py`), so the broad-except ratchet is unaffected.

Note: this is the FIX receipt for the finding recorded in the
step-16 self-review entry above (run `58395f0fbc57`). Shipped in
PR #2342.

## 2026-08-28 — post-release self-review, 16.1.0 (release-execute step 16)

Two runner-launched runs against the shipped tree (`8f65df82a` = tag
`v16.1.0`, verified FROM THE FILESYSTEM — `pyproject.toml` on disk AND
the imported `__version__` both read 16.1.0, imported from this
worktree's `src/`, HEAD == the tag): `code-review` run `a233ac84e95b`,
**84/100** (310s, **$5.62**) and `bug-predict` run `7060f5cac173`,
**58/100** (248s, **$2.54**). Total **$8.17**. Both exit 0 with
`sdk_error_kind: None` and a report present, so neither is the
exit-0-with-traceback false success. 23 findings (15 + 8); **no
Critical, and no High in Security or Bugs** — the three Highs are all
architectural.

**Launch-path note:** a server was already listening on the default
port 8765 reporting **version 15.1.0 with `project_root` = the MAIN
checkout**. Running the review through it would have reviewed the wrong
tree with older code and still produced a confident-looking receipt.
These runs used a second server on **:8766** pinned to
`--project-root <this worktree at v16.1.0>` with
`PYTHONPATH=<worktree>/src`; `/api/info` confirmed `16.1.0` + the
worktree path before either run started. The stale 8765 process was
left alone (it may belong to another session).

**Spend-mode note:** the first server launch could NOT see
`ANTHROPIC_API_KEY` (verified by counting the var in the process
environment, never printing it). It was relaunched with the key
sourced; the non-zero costs above are the receipt that these were real
runs and not $0 simulated no-ops.

### Verified findings (probe run, not relayed)

Five load-bearing claims were checked against the tree. **All five
CONFIRMED, and two are worse than the finding states:**

- **[High] Layering inversion, `models/` -> `ops/` — CONFIRMED, and it
  is BIDIRECTIONAL.** `models/sdk_adapter.py:30` and
  `models/sdk_errors.py:28` both `from attune.ops.session_redaction
  import redact`, and `ops/runner.py:843` imports
  `attune.models.telemetry.run_context`. The finding named the first
  direction only. `session_redaction` is stdlib-only and misfiled.
- **[High] Duplicate `WORKFLOW_REGISTRY` — CONFIRMED, but there are
  THREE, not two, and their VALUE TYPES DIFFER:**
  `workflows/__init__.py:373` (`dict[str, type[BaseWorkflow]]`),
  `routing/workflow_registry.py:38` (`dict[str, WorkflowInfo]`), and
  `orchestration/_strategies/nesting.py:193`
  (`dict[str, WorkflowDefinition]`). Three same-named globals with three
  incompatible types is a sharper hazard than the reported duplication.
- **[High] MCP god-class — CONFIRMED structurally.** `mcp/server.py`,
  `mcp/tool_schemas.py`, and the handler mixins
  (`workflow_handlers.py`, `memory_handlers.py`, `handoff_handlers.py`)
  all exist as separate edit sites, consistent with the 3-site claim.
- **[MEDIUM] `ops/server.py:162` fire-and-forget task — CONFIRMED.**
  `asyncio.create_task(watch_and_persist(run, config))` with no
  reference retained; per CPython docs the loop keeps only a weak
  reference, so the task can be GC'd mid-flight.
- **[MEDIUM] `project_index/index.py` per-file `ProjectScanner` —
  CONFIRMED.** Three separate constructions (`:401`, `:407`, and one
  inside `_is_excluded`), the last called per file, recompiling the glob
  regex set O(N) times per refresh.

### Not verified (relayed as reported)

The remaining **18** findings were NOT probed and are recorded as
model claims, not established facts — chiefly the two Low security
items (non-defused XML parsing in `validation/xml_validator.py:95`;
caller-supplied command string in `workflows/test_runner.py:70`), the
duplicated `_post` helper across three roundtable modules, the
remaining async-task-loss sites (`llm/interaction.py:162`,
`workflows/discovery_sweep/workflow.py:425`), and the coverage-omit
gap naming production modules excluded from the gate. Each needs its
own probe before it is treated as real.

**No finding blocked the release**, and — as with 15.1.0 and unlike the
14.0.0 precedent — none sits in code 16.1.0 actually changed. The
release's own diff (the stale entry-point detector, the round-table
kind single-sourcing) drew no findings at all.

**Reach baseline (US-4): incomplete.** Quoted verbatim from
`scripts/reach_snapshot.py --verify-before 2026-08-28`:

> WARNING: NO COMPLETE BEFORE-SNAPSHOT in the 24-72h pre-tag window
> (planned tag 2026-08-28T00:00:00+00:00). the 24h window floor has
> passed — the release may continue only with this incomplete-receipt
> warning attached (US-4); do not capture a substitute at tag time.

No substitute was captured at tag time, per US-4. The AFTER snapshot is
queued for 24-72h post-tag.

## 2026-09-06 — inference-isolation CI repair (#2445)

- **Crash:** `tests/_inference_guard.py` decoded the Windows Popen
  audit event's absent executable as a filesystem path, aborting pytest.
  The guard now checks the command even when the override is absent and
  handles quoted Windows executable paths; simulated Windows audit events
  retain inference and Python-bootstrap rejection checks.
- **Mocked:** local warm tokenizer caches and the default integration
  exclusion hid CI-only network attempts. CI now prepares static tokenizer
  data before pytest; the no-auth integration lane uses fixture-owned AMS
  HTTP readback, explicit file-backend MCP dispatch, and an intercepted SDK
  401. The inference guard remains active through these tests.

### 2026-09-06 — #2445 cache path rejected before CI jobs start (crash)

The CI repair used `runner.temp` in job-level `env`, a context GitHub does
not allow there. Runs 34021720623 and 34021720221 failed workflow validation
before test jobs existed; local YAML parsing could not catch expression
context validity. Use `github.workspace` with a sibling cache directory and
reject runner-context expressions in job environments with a schema test.
The same shared path still covers setup and every pytest step on all OSes.

### 2026-09-06 — #2445 unlocked SDK transport upgrade (mocked)

CI installs Anthropic 1.4.0/httpx2 2.12.0; the lockfile validation environment
used Anthropic 0.125.0/httpx 0.28.1. The invalid-key fixture passed the older
HTTP client to the new SDK and failed before the mocked 401. More seriously,
the test guard only wrapped httpx: httpx2 could bypass the HTTP endpoint rule
for a local proxy (external Python sockets were still denied). No live probe
was used. Guard both installed transport generations, intercept both core
pools in regression tests, and match SDK fixtures to the SDK's HTTP backend.
Validation now includes a disposable environment resolved like CI and the
locked legacy environment; no production authentication is changed.

### 2026-09-06 — #2445 Windows command-line decoding (crash / mocked)

Windows Popen audits a serialized command string even when its caller passes
argv. Non-POSIX shlex does not decode the CRT quoting used by list2cmdline:
14 Windows tests crashed on quoted multiline Python programs. The same
parser also missed a quoted inference executable inside a serialized cmd
wrapper. Regression tests fail against the old guard for both cases without
launching a process. The guard now decodes backslash/quote parity before
applying the existing inference checks, including nested wrappers.

One nested pytest controller/worker probe additionally exhausted its 15s
startup timeout on Windows 3.12. That probe alone gets 60s; its assertions
that inference is blocked before process creation are unchanged. No live
provider calls, broad skips, or interactive-auth changes are involved.

### 2026-09-06 — #2445 cold-child fixture boundaries (crash)

After the quoting repair, Windows 3.11/3.12/3.14 passed. Windows 3.10 and
3.13 exposed a race in the cold pytest probe: the checkout and fixture live
on different drives, so pytest's ancestor traversal visits shared temporary
siblings; another worker removes a guard folder before pytest's Windows
same-file comparison stats it. Explicit fixture-local `--confcutdir` bounds
collection while `-p tests.conftest` still loads the real guard. A collector
assertion reproduces the over-broad traversal deterministically (2 failures
without the boundary; all 3 controller/worker cases pass with it).

Two Windows 3.10 probes also replaced their process environment without
SystemRoot, preventing Python hash-randomization startup before the guard
could run. The test fixtures retain only that required Windows runtime
variable alongside their declared fake credentials. The credential-scrubbing
and blocked-inference assertions remain unchanged.

### 2026-09-06 — spec drift probe depends on runner scheduling (mocked)

#2444 run 34025993709 reported one Windows 3.12 failure: the real-Git dirty
spec test returned no findings. The scanner intentionally stops after a
2.5s overall budget; the test previously required both worktrees to be
visited within that wall-clock budget. A loaded runner can exhaust it
without violating scanner behavior. The exact cutoff was not logged in
that failed run, so timing is the diagnosed failure mechanism, not a
measured duration receipt. Behavioral probes now use a module-local steady
clock while retaining real Git/filesystem calls and their subprocess
timeouts. A separate deterministic test exhausts the budget before the
dirty worktree and requires no finding. Production limits are unchanged.

### 2026-09-06 — cross-review auth classification and clean-venv cache (crash)

The default Claude seat treated saved Max authentication as an API launch,
so a zero API cap refused the explicitly requested subscription review.
A separate opt-in launcher verifies subscription auth with API credentials
removed, disables tools/custom integrations, and leaves API launch checking
unchanged. Intercepted-process regressions verify refusal before inference
for API, unknown or malformed authentication and incomplete diff coverage.

After #2445 merged, #2444's clean-venv smoke check attempted a tiktoken
vocabulary download inside pytest. The inference guard correctly refused
that unregistered endpoint. The other CI jobs prepared this static data,
but contributing-smoke did not. Its cache is now prepared before the literal
CONTRIBUTING setup script runs; no guard exception or skipped assertion was
added. Failed job: 101473769814, test_token_estimator.
