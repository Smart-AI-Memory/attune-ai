# discovery-sweep

**Status:** Phase 1 complete · Phase 2A complete
**Created:** 2026-05-13
**Approved:** 2026-05-13
**Phase 1 shipped:** 2026-05-13 (105 tests, engine as Python API)
**Phase 2A shipped:** 2026-05-13 (127 tests total — PatternScanSource adapter + CLI wrapper + registry registration)
**Phase 2B remaining:** LLM-wrapping adapters, auto-fix, retirement eval, multi-module parallelism, RAG verification
**Owner:** Patrick + Claude (interactive)

---

## Context

Today, code/test improvement runs interactively with Claude as
the active driver — safe, high-quality, but doesn't scale.
Autonomous workflows exist (bug_predict, security_audit,
code_review, deep_review, perf_audit, test_audit) but no
orchestrator runs them as a coordinated sweep with curated
output. Raw output from individual workflows has known false
positives (perf-audit `dirs[:]`, bug-predict `subprocess_exec`,
deep-review fabrication) that make their findings untrustworthy
for a queue without filtering.

## Problem

Need read-only discovery at scale: parallel agent sweep,
verification layer that filters known false positives, curated
output queue tagged by resolution complexity. Resolution stays
interactive (current workflow unchanged).

## Goals (Phase 1)

1. Bounded-scope sweep workflow runnable foreground or as
   background job
2. Verification layer classifies each finding:
   - REJECT (drop, log to rejection-log)
   - UNSURE (batched questions file, reviewable cold)
   - ACCEPT (queue entry)
3. ACCEPT entries carry `resolution_complexity: routine |
   needs_patrick` metadata
4. Curated queue lives separately from `COVERAGE_BUG_LOG.md`
   until Patrick promotes items
5. Budget caps: $10 per sub-workflow invocation, $40 hard
   ceiling per module sweep
6. Verification rules grounded in existing CLAUDE.md lessons

## End State

```bash
attune workflow run discovery-sweep --path src/attune/security/
```

Produces three artifacts:

- `.claude/discovery-queue/<timestamp>-<scope>.jsonl` — ACCEPT
  findings, tagged
- `.claude/discovery-queue/<timestamp>-<scope>.questions.md` —
  UNSURE findings as reviewable-cold questions
- `.claude/discovery-queue/<timestamp>-<scope>.rejected.jsonl`
  — REJECT findings with rule that fired (for auditing
  verification quality)

Existing interactive resolution workflow untouched. Patrick
triages queue at his pace; promoted items flow to
`docs/COVERAGE_BUG_LOG.md` for fixing via existing
`crash/dead/mocked` taxonomy.

## Out of Scope (Phase 1) — committed for Phase 2

- Auto-fix for ROUTINE-tagged items
- Retirement evaluation for superseded workflows (test_audit
  prime candidate)
- Multi-module parallelism (sweep multiple paths concurrently)
- RAG-grounded verification (use attune-help / attune-rag to
  check findings against documented patterns)

---

## Verification Rules (seed set from CLAUDE.md lessons)

These become the initial denylist in Task 2. Each is grounded
in an existing CLAUDE.md lesson — not theoretical false
positives, but ones we've actually hit.

| Pattern | Why False Positive |
|---|---|
| `dirs[:] = [...]` in `os.walk` loop | Required for traversal filtering — not a memory leak |
| `create_subprocess_exec` flagged as eval | substring match against "exec" — not actual eval/exec |
| JS `regex.exec(text)` flagged as exec | Safe regex method, not Python exec |
| `eval()` / `exec()` inside `.write_text(...)` calls | Test fixture data, not executable code |
| `eval()` / `exec()` inside string literals (detection code) | Scanner self-reference |
| `except Exception` with `# noqa: BLE001` + `# INTENTIONAL:` | Documented intentional broad catch |
| `subprocess.run(...)` in fuzz target / test | Not shell injection in this context |
| structlog `logger.info("msg", key=value)` flagged as TypeError | Valid structlog kwargs syntax |
| Hardcoded `"fake"` / placeholder strings flagged as secrets | Pragma allowlist applies |

Verification rules are extensible — adding to the list as new
false positives surface is a Phase 1 deliverable.

---

## Resolution Complexity Triggers (ACCEPT → needs_patrick)

A finding flips to `needs_patrick` if any apply:

- Touches 3+ files OR changes public API OR modifies shared
  base class
- Security-adjacent: anything in `src/attune/security/`,
  eval/exec, path validation, webhook URLs
- Contradicts a CLAUDE.md lesson (fix would re-introduce a
  documented antipattern)
- Tier/budget/cost-model change
- "Test mocks production" smell — proposed fix would lose real
  coverage
- Low-confidence: verification rule fired ACCEPT but couldn't
  name a specific failing input

Otherwise: `routine`.

---

## Tasks

<task id="1" name="finding-schema-and-file-formats">
  <objective>
    Define the Finding dataclass and the three output file
    formats (queue/questions/rejected). Establish the
    serialization contract that downstream tasks build on.
  </objective>

  <files-to-create>
    <file path="src/attune/workflows/discovery_sweep/__init__.py">
      Package init. Re-exports Finding, VerificationStatus,
      ResolutionComplexity enums.
    </file>
    <file path="src/attune/workflows/discovery_sweep/schema.py">
      Finding dataclass with fields:
      - source_workflow: str (e.g. "bug_predict")
      - file_path: str
      - line: int | None
      - severity: Literal["high", "medium", "low"]
      - message: str
      - raw_finding: dict (preserve original for audit)
      - verification_status: Literal["accept", "reject", "unsure"]
      - resolution_complexity: Literal["routine", "needs_patrick"] | None
      - verification_reasoning: str
      - sweep_id: str
      - timestamp_utc: str (isoformat with +00:00)

      VerificationStatus and ResolutionComplexity enums.
    </file>
    <file path="src/attune/workflows/discovery_sweep/serialization.py">
      JSONL writers/readers for queue and rejected files.
      Markdown writer for questions file (human-readable,
      reviewable cold — each entry includes the original
      finding, what made verification unsure, and which
      sub-workflow flagged it).
    </file>
    <file path="tests/unit/workflows/discovery_sweep/test_schema.py">
      Round-trip serialization tests (JSONL queue, JSONL
      rejected, markdown questions). Schema validation tests.
    </file>
  </files-to-create>

  <validation>
    <check>Finding dataclass round-trips JSONL without loss</check>
    <check>Markdown questions file is parseable back to Findings</check>
    <check>All three file formats include sweep_id for traceability</check>
    <check>timestamps are timezone-aware (lesson: never naive datetimes)</check>
  </validation>

  <risks>
    <risk severity="low">
      Schema-too-narrow risk: adding fields later is cheap
      (dataclass) but renaming is expensive across the queue
      file format. Mitigation: pad the schema slightly with
      optional fields that may matter (e.g. estimated_fix_cost
      as Optional[float]).
    </risk>
  </risks>
</task>

<task id="2" name="verification-rule-engine">
  <objective>
    Build the verification layer: a rule engine that classifies
    Findings as ACCEPT / REJECT / UNSURE based on grounded
    rules from CLAUDE.md lessons. This is the load-bearing
    component — its quality determines whether the queue stays
    signal.
  </objective>

  <files-to-create>
    <file path="src/attune/workflows/discovery_sweep/verification.py">
      VerificationRule protocol:
        def classify(finding: Finding, source_text: str)
            -> tuple[VerificationStatus, str]  # status + reasoning

      VerificationEngine: runs ordered rule list against a
      finding, returns first matching classification.

      Default rule order: REJECT rules first (denylist of
      known false positives), then ACCEPT rules, fall through
      to UNSURE.
    </file>
    <file path="src/attune/workflows/discovery_sweep/rules/__init__.py">
      Rule registry. Imports all built-in rules.
    </file>
    <file path="src/attune/workflows/discovery_sweep/rules/known_false_positives.py">
      REJECT rules for the 9 patterns in the spec's seed set:
      - DirsSliceAssignmentRule (os.walk dirs[:] pattern)
      - SubprocessExecRule (create_subprocess_exec false-eval)
      - JsRegexExecRule (.exec on regex objects)
      - WriteTextEvalFixtureRule (eval/exec inside .write_text)
      - IntentionalBroadExceptRule (# noqa: BLE001 + # INTENTIONAL:)
      - SubprocessInFuzzTargetRule
      - StructlogKwargsRule
      - SecretsPragmaRule
      Each rule reads the source line + context and decides.
    </file>
    <file path="tests/unit/workflows/discovery_sweep/test_verification.py">
      For each rule, a test fixture using a real code snippet
      from the codebase (or a minimal repro) that should be
      REJECTED. Tests are the regression net for the
      verification quality.
    </file>
    <file path="tests/unit/workflows/discovery_sweep/fixtures/false_positives/">
      Directory of minimal source files demonstrating each
      false positive. Tests reference these.
    </file>
  </files-to-create>

  <validation>
    <check>Each REJECT rule fires correctly on its target false-positive fixture</check>
    <check>Each REJECT rule does NOT fire on a control case (genuine bug with similar surface)</check>
    <check>VerificationEngine returns UNSURE when no rule matches</check>
    <check>Verification reasoning is human-readable (used in rejected.jsonl audit log)</check>
  </validation>

  <risks>
    <risk severity="medium">
      Over-aggressive REJECT rule masks a real bug. Mitigation:
      every REJECT rule must have a paired control test
      (similar-looking code that IS a real bug, where the rule
      must NOT fire). Asymmetric: false-negative on REJECT is
      worse than false-positive on ACCEPT, because UNSURE
      lands in the questions file (recoverable) but REJECT
      drops to audit log (less visible).
    </risk>
    <risk severity="medium">
      Rule order matters for correctness. Mitigation: rules
      that REJECT must include source-context checks that are
      narrow enough to not collide with ACCEPT rules. Tests
      cover ordering.
    </risk>
  </risks>
</task>

<task id="3" name="resolution-complexity-classifier">
  <objective>
    For findings that reach ACCEPT, classify resolution
    complexity as `routine` or `needs_patrick`. This is the
    tag Patrick filters by when triaging the queue.
  </objective>

  <files-to-create>
    <file path="src/attune/workflows/discovery_sweep/complexity.py">
      ComplexityClassifier with rules:
      - is_cross_cutting(finding) — touches 3+ files via grep
        of message text; OR finding.file_path is in shared
        base class registry
      - is_security_adjacent(finding) — file path under
        src/attune/security/, OR finding mentions eval/exec/
        path-validation/webhook
      - contradicts_lesson(finding) — fix would re-introduce
        a known antipattern (cross-reference with rule
        registry from Task 2)
      - is_tier_or_budget_change(finding) — mentions
        ModelTier, budget, cost
      - is_mocks_production_smell(finding) — finding is in a
        test file AND mentions mock/patch with a production
        path
      - is_low_confidence(finding) — verification reasoning
        contains "couldn't determine" / "ambiguous" markers

      Returns ResolutionComplexity (routine | needs_patrick).
    </file>
    <file path="tests/unit/workflows/discovery_sweep/test_complexity.py">
      Test each trigger with a positive fixture (should be
      needs_patrick) and negative fixture (should stay
      routine).
    </file>
  </files-to-create>

  <validation>
    <check>Each trigger fires correctly on its positive fixture</check>
    <check>Each trigger does NOT fire on its negative fixture</check>
    <check>Routine is the default — any trigger flips to needs_patrick</check>
  </validation>

  <risks>
    <risk severity="low">
      Over-tagging needs_patrick reduces throughput; under-
      tagging risks Patrick missing items he wanted to see.
      Mitigation: err toward needs_patrick when ambiguous;
      Patrick can downgrade in triage.
    </risk>
  </risks>
</task>

<task id="4" name="sweep-workflow-orchestrator">
  <objective>
    Implement the DiscoverySweepWorkflow as a BaseWorkflow
    subclass. Runs N sub-workflows on a bounded path,
    enforces budget caps, aggregates findings, runs them
    through verification + complexity classification, and
    writes the three output files.
  </objective>

  <files-to-create>
    <file path="src/attune/workflows/discovery_sweep/workflow.py">
      DiscoverySweepWorkflow(BaseWorkflow):
        name = "discovery-sweep"
        description = "Orchestrated read-only discovery
          sweep — runs N sub-workflows on a bounded path,
          verifies findings against known-false-positive
          rules, and produces a curated queue."

      Configurable sub-workflows (default: bug_predict,
      security_audit, code_review, perf_audit, deep_review).

      Per-workflow budget: $10 (env override:
      ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD).
      Sweep budget ceiling: $40 (env override:
      ATTUNE_DISCOVERY_SWEEP_BUDGET_USD). Hard kill on
      ceiling.

      Output directory: .claude/discovery-queue/ (configurable
      via --output-dir).
    </file>
    <file path="src/attune/workflows/discovery_sweep/budget.py">
      BudgetTracker — tracks per-workflow + total spend,
      raises SweepBudgetExceeded when ceiling hit.
    </file>
    <file path="tests/unit/workflows/discovery_sweep/test_workflow.py">
      Tests with mocked sub-workflow results:
      - Aggregates findings from multiple sub-workflows
      - Verification runs on every finding
      - Complexity classification on ACCEPT findings
      - Writes three correct files
      - Budget cap halts further sub-workflow invocation
      - sweep_id is consistent across all output files
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="src/attune/workflows/__init__.py">
      <change location="discover_workflows registry">
        Register DiscoverySweepWorkflow.
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>attune workflow list shows discovery-sweep</check>
    <check>Mocked end-to-end sweep produces all three output files with consistent sweep_id</check>
    <check>Budget cap triggers SweepBudgetExceeded after threshold</check>
    <check>Sub-workflow failure (one of N raises) does not abort sweep — failure recorded, sweep continues with remaining workflows</check>
  </validation>

  <risks>
    <risk severity="high">
      MCP-invoked sub-workflows lose intermediate context (per
      "MCP-invoked SDK workflows ALREADY isolate" lesson). The
      orchestrator must NOT rely on intermediate
      AssistantMessage text — only final_output. Mitigation:
      audit each sub-workflow's WorkflowResult shape before
      consuming.
    </risk>
    <risk severity="medium">
      $40 ceiling is a guess. May need adjustment after first
      real-scope sweep. Mitigation: log per-sub-workflow spend
      to telemetry so future tuning is data-driven.
    </risk>
  </risks>
</task>

<task id="5" name="python-api-and-extension-guide">
  <objective>
    Ship the engine as a tested Python API for Phase 1. Document
    the ``FindingSource`` Protocol so Phase 2 adapter work is
    cold-readable. CLI registration (``attune workflow run
    discovery-sweep``) and real sub-workflow adapters are
    explicit Phase 2 deliverables — registering an empty
    workflow today would be more confusing than not registering
    it. (Decision 2026-05-13.)
  </objective>

  <files-to-create>
    <file path="docs/workflows/discovery-sweep.md">
      User-facing docs:
      - Phase 1 boundary: engine-only, Python API surface
      - When to use (bounded scope, read-only discovery)
      - When NOT to use (auto-fix, whole-repo)
      - Quickstart: instantiate DiscoverySweepWorkflow with a
        list of FindingSource instances, call .run(scope)
      - FindingSource protocol contract and an example adapter
      - Reading the three output files
      - Extending verification rules and complexity triggers
      - Phase 2 roadmap pointer (CLI + real adapters)
    </file>
    <file path="tests/unit/workflows/discovery_sweep/test_smoke.py">
      End-to-end smoke test against the Python API: instantiates
      the orchestrator with a stub FindingSource emitting a
      known false-positive + a fresh finding, asserts the three
      output files exist with the expected structure (one
      REJECT, one UNSURE), and the sweep_id is consistent
      across all files.
    </file>
  </files-to-create>

  <validation>
    <check>Python API smoke test produces all three output files with expected counts</check>
    <check>FindingSource protocol contract is documented with a worked example</check>
    <check>Phase 2 roadmap pointer in docs/workflows/discovery-sweep.md links to docs/specs/discovery-sweep/phase-2.md</check>
  </validation>

  <risks>
    <risk severity="low">
      Engine-only ship limits Phase 1 user value to extension
      authors. Acceptable — Phase 1's intent was always the
      verification + queue logic, not the adapter implementations.
    </risk>
  </risks>
</task>

<task id="6" name="documentation-and-phase-2-deferral-record">
  <objective>
    Document Phase 1 usage and create the Phase 2 deferral
    record so the deferred items don't get lost.
  </objective>

  <files-to-create>
    <file path="docs/specs/discovery-sweep/decisions.md">
      Mirror of this spec file's key decisions. Records:
      - Discovery-vs-resolution split rationale
      - Verification-rules-grounded-in-lessons approach
      - Resolution complexity tagging vs queue-entry gating
        (the reframe from chat)
      - Phase 2 commitments (auto-fix, retirement eval,
        multi-module parallelism, RAG verification)
    </file>
    <file path="docs/specs/discovery-sweep/phase-2.md">
      Phase 2 planning placeholder. Lists each deferred item
      with a one-paragraph sketch:
      - Auto-fix for ROUTINE-tagged items (needs reversibility
        guarantees — likely git-stash-before-fix pattern)
      - Workflow retirement evaluation (test_audit candidate
        — compare sweep output vs test_audit on same scope)
      - Multi-module parallelism (asyncio + shared budget
        accounting)
      - RAG-grounded verification (use attune-help/attune-rag
        to check whether a finding contradicts documented
        patterns)
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="CHANGELOG.md">
      <change location="Unreleased section">
        Add entry: "Added: discovery-sweep workflow — read-only
        discovery sweep with verification layer grounded in
        CLAUDE.md lessons. Produces curated queue with
        resolution-complexity tagging. Phase 1 of multi-phase
        spec."
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Phase 2 doc lists all 4 deferred items with sketches</check>
    <check>CHANGELOG entry exists under Unreleased</check>
    <check>docs/specs/discovery-sweep/decisions.md exists and is in markdown-formatting-rules compliance</check>
  </validation>

  <risks>
    <risk severity="low">
      Phase 2 sketches diverge from actual implementation.
      Acceptable — sketches are commitments to scope, not
      design specs.
    </risk>
  </risks>
</task>

---

## Decisions Resolved (2026-05-13)

1. **File formats:** JSONL for queue + rejected (tool
   consumption, jq-friendly, streaming-friendly); markdown
   for questions (human consumption, reviewable cold).
2. **Git tracking:** `.claude/discovery-queue/` gitignored by
   default. Patrick can opt to commit a specific queue file
   if he wants the audit trail in git. Add to `.gitignore` in
   Task 1.

---

## Out of Scope (Phase 1) — committed for Phase 2

Repeated here for visibility:

- **CLI registration** (`attune workflow run discovery-sweep`) —
  pairs with the real adapters below since the workflow has no
  built-in sources of its own
- **Real FindingSource adapters** wrapping bug_predict,
  security_audit, code_review, perf_audit, deep_review
- Auto-fix for ROUTINE-tagged items
- Retirement evaluation for superseded workflows
- Multi-module parallelism
- RAG-grounded verification
