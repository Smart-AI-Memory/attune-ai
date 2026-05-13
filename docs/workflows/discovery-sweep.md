# discovery-sweep

Read-only discovery sweep that orchestrates N sub-workflows on
a bounded scope, filters their output through a verification
rule engine grounded in `CLAUDE.md` lessons, and produces a
curated queue tagged by resolution complexity.

Resolution stays interactive — the sweep does NOT modify code.
Patrick triages the queue at his pace; promoted items flow to
`docs/COVERAGE_BUG_LOG.md` for fixing via the existing
interactive workflow.

## Status

Phase 1 + 2A shipped 2026-05-13. The CLI works:

```bash
attune workflow run discovery-sweep --path src/attune/security/
```

This dispatches `DiscoverySweepWorkflow` (a `BaseWorkflow`
subclass), which wraps `DiscoverySweepEngine` (the
orchestrator) and runs the default `PatternScanSource` adapter
— a deterministic, zero-LLM-cost scanner for bare except,
eval/exec, subprocess shell=True, and TODO/FIXME markers.

LLM-wrapping adapters (bug_predict, security_audit, etc.) are
Phase 2B — see
[phase-2.md](../specs/discovery-sweep/phase-2.md).

## When to use

- Bounded scope, read-only audit of one module or one workflow
  surface
- You want a curated queue tagged by resolution complexity
- You want a separate audit log of REJECTed findings so you
  can track verification-rule quality over time

## When NOT to use

- Whole-repo sweeps (Phase 1 is single-scope only)
- Auto-fix (resolution stays interactive)
- Anything that needs a `FindingSource` adapter that hasn't
  been written yet (Phase 2)

## Quickstart — CLI

```bash
attune workflow run discovery-sweep --path src/attune/security/
```

Output:

```text
sweep abc123def456 | scope=/abs/path/src/attune/security/ |
accept=3 | reject=1 | unsure=5 | spend=$0.00 |
queue=.claude/discovery-queue/abc123def456.jsonl
```

Three artifacts in `.claude/discovery-queue/`:

- `<sweep_id>.jsonl` — accepted findings (the queue)
- `<sweep_id>.rejected.jsonl` — rejected findings (audit log)
- `<sweep_id>.questions.md` — unsure findings (cold-readable)

## Quickstart — Python API

```python
from pathlib import Path

from attune.workflows.discovery_sweep import (
    DiscoverySweepEngine,
    Finding,
    FindingSource,
    PatternScanSource,
    Severity,
)


class MyAdapter:
    """A FindingSource that wraps your own sub-workflow."""

    name = "my_sub_workflow"
    estimated_spend_usd = 0.0

    def discover(self, scope, budget_usd, sweep_id):
        # Invoke your sub-workflow against `scope`, respect
        # `budget_usd`, then translate each raw finding into a
        # `Finding` with the canonical fields populated.
        # Track real spend on `self.estimated_spend_usd`.
        return [
            Finding(
                source_workflow=self.name,
                file_path="src/attune/example.py",
                line=42,
                severity=Severity.MEDIUM,
                message="some pattern detected",
                raw_finding={"pattern": "scanner_internal_id"},
                sweep_id=sweep_id,
            )
        ]


engine = DiscoverySweepEngine(
    sources=[PatternScanSource(), MyAdapter()]
)
result = engine.run(scope=Path("src/attune/security/"))
print(f"accepted={result.accept_count} "
      f"rejected={result.reject_count} "
      f"unsure={result.unsure_count}")
print(f"queue:     {result.queue_path}")
print(f"rejected:  {result.rejected_path}")
print(f"questions: {result.questions_path}")
```

## FindingSource Protocol

A `FindingSource` is the adapter between an existing
sub-workflow (bug_predict, security_audit, etc.) and the
discovery-sweep engine. Implementations MUST:

- Expose a string `name` matching the sub-workflow they wrap
- Implement `discover(scope, budget_usd, sweep_id) -> Iterable[Finding]`
- Expose `estimated_spend_usd` reporting actual USD spend
  (used for budget accounting and the sweep-level cap)
- Be side-effect free (no source-code edits, no commits)
- Respect the `budget_usd` ceiling on a best-effort basis

When `discover` raises, the orchestrator records the error in
`SweepResult.sub_workflow_errors` and continues with the next
source. When the sweep-level cap is exceeded, the orchestrator
halts further sources (`SweepResult.budget_halted = True`).

## Output files

The sweep writes three files into the output directory
(default: `.claude/discovery-queue/`, which is gitignored):

| File | Contents |
|---|---|
| `<sweep_id>.jsonl` | ACCEPTed findings (the queue) |
| `<sweep_id>.rejected.jsonl` | REJECTed findings (audit log) |
| `<sweep_id>.questions.md` | UNSURE findings (cold-readable) |

Each ACCEPTed finding carries `resolution_complexity`:
`routine` or `needs_patrick`. Filter by the tag at triage time.

## Budgets

Two caps, both configurable:

- **Per sub-workflow:** $10 default
  (env: `ATTUNE_DISCOVERY_SUBWORKFLOW_BUDGET_USD`)
- **Per sweep:** $40 default
  (env: `ATTUNE_DISCOVERY_SWEEP_BUDGET_USD`)

Crossing the sweep cap raises `SweepBudgetExceeded` internally
and halts further sub-workflow invocation. The current
sub-workflow's spend is still recorded for the audit log.

## Verification rules

The verification layer is a list of `VerificationRule` instances
applied in order. Each rule returns one of:

- `(REJECT, reasoning)` — known false positive, drop to audit log
- `(ACCEPT, reasoning)` — strong positive signal (Phase 1 ships
  no ACCEPT rules; everything that survives REJECT falls through)
- `None` — rule did not match; continue to the next rule

If no rule matches, the finding is classified as `UNSURE` and
lands in the questions file.

Built-in REJECT rules ship with paired control tests proving
they do NOT fire on similar-looking REAL bugs. The control
coverage is the regression net for the asymmetric-cost
invariant: a false REJECT is worse than a false ACCEPT because
REJECTed findings live in the audit log only.

To add a new REJECT rule:

1. Add a class to
   `src/attune/workflows/discovery_sweep/rules/known_false_positives.py`
2. Register it in
   `src/attune/workflows/discovery_sweep/rules/__init__.py`
3. Add a positive fixture +  control fixture in
   `tests/unit/workflows/discovery_sweep/fixtures/false_positives/`
4. Add positive + control test methods in
   `tests/unit/workflows/discovery_sweep/test_verification.py`

## Resolution complexity triggers

ACCEPTed findings flip from `routine` to `needs_patrick` when
any of these triggers apply (see
`src/attune/workflows/discovery_sweep/complexity.py`):

- `cross_cutting` — touches 3+ files OR mentions public API /
  shared base class
- `security_adjacent` — under `src/attune/security/` OR
  mentions eval/exec/path-validation/webhook
- `contradicts_lesson` — finding lands in CLAUDE.md lesson
  territory but didn't match any REJECT rule
- `tier_or_budget_change` — affects ModelTier, budget caps,
  cost model
- `mocks_production_smell` — test-file finding that suggests
  mocking production code
- `low_confidence` — verification reasoning includes
  uncertainty markers

Add new triggers in the same module and pass them to
`ComplexityClassifier(triggers=[...])`.

## Phase 2

See [phase-2.md](../specs/discovery-sweep/phase-2.md) for the
roadmap: real adapters, CLI registration, auto-fix for routine
items, multi-module parallelism, RAG-grounded verification.
