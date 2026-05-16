# Bug Predict architecture

Predict likely bug locations based on code patterns and complexity.

## Purpose

The bug prediction subsystem orchestrates three specialized subagents — `pattern-scanner`, `risk-correlator`, and `prevention-advisor` — to analyze a codebase and produce a unified risk report. It owns scan orchestration, subagent coordination, false-positive suppression, and report formatting. It is **not** responsible for applying fixes, tracking historical trends across runs, or surfacing results outside the Claude Code conversation context.

## Key classes

| Class | Responsibility | File |
|-------|----------------|------|
| `BugPredictionWorkflow` | Orchestrates the three subagents in sequence and synthesizes their output into a single `WorkflowResult`. | `src/attune/workflows/bug_predict.py` |

## Supporting functions

| Function | Responsibility | File |
|----------|----------------|------|
| `format_bug_predict_report()` | Converts a raw result dict into the human-readable severity-grouped report shown in the conversation. | `src/attune/workflows/bug_predict.py` |
| `main()` | CLI entry point; parses arguments and delegates to `BugPredictionWorkflow`. | `src/attune/workflows/bug_predict.py` |

## Data flow

```
User input (path)
        │
        ▼
[BugPredictionWorkflow]
        │
        ├──► [pattern-scanner subagent]
        │       Detects dangerous_eval, broad_exception,
        │       incomplete_code; applies false-positive filters
        │       (_INTENTIONAL_KEYWORDS, _SCANNER_TEST_PATTERNS)
        │
        ├──► [risk-correlator subagent]
        │       Weighs cyclomatic complexity, change frequency,
        │       and code smells; produces per-file risk scores
        │
        └──► [prevention-advisor subagent]
                Generates prioritized refactoring and testing
                recommendations
        │
        ▼
  Synthesis (orchestrator prompt combines all three outputs)
        │
        ▼
[format_bug_predict_report()]
        │
        ▼
  Risk report (Summary / Bugs by severity / Suggestions)
```

Each subagent runs independently against the target path and reports structured markdown. `BugPredictionWorkflow` synthesizes those three outputs using `_TASK_PROMPT_TEMPLATE` before passing the combined result to `format_bug_predict_report()`.

## Design decisions

**Three subagents instead of one monolithic scanner.** Splitting detection (pattern-scanner), scoring (risk-correlator), and advice (prevention-advisor) into separate agents keeps each agent's context window focused. The tradeoff is an additional synthesis step, but it lets each agent be replaced or retrained independently without touching the others.

**False-positive suppression at scan time, not report time.** The `_INTENTIONAL_KEYWORDS` list (`fallback`, `ignore`, `optional`, `best effort`, `graceful`, `intentional`) and `_SCANNER_TEST_PATTERNS` are applied by `pattern-scanner` before results reach the orchestrator. Filtering early reduces noise in the synthesis prompt and keeps the final report from requiring a second-pass filter.

**Orchestrator holds no domain logic.** `BugPredictionWorkflow` only manages subagent dispatch and result synthesis; all pattern knowledge lives in the subagents. This means changing detection rules requires updating a subagent prompt, not the workflow class.

## Extension points

- **Add a new detection subagent** — append its name to `_SUBAGENT_NAMES` and update `_TASK_PROMPT_TEMPLATE` to include its domain and expected output format. The orchestrator will include it in the synthesis step automatically.
- **Change what is suppressed as a false positive** — add keywords to `_INTENTIONAL_KEYWORDS` or test-file name patterns to `_SCANNER_TEST_PATTERNS` in the pattern helpers module.
- **Customize the report format** — replace or wrap `format_bug_predict_report()`. The function takes a plain `dict` and `input_data` dict, so you can subclass nothing; just provide an alternative formatter and point `main()` at it.
- **Adjust the synthesis structure** — edit `_TASK_PROMPT_TEMPLATE` to add, remove, or rename report sections (currently: Summary, Bugs, Suggestions). The subagents are not coupled to this template.

For usage questions, see `tasks/use-bug-predict.md`.

<!-- attune-generated: source_hash=c4c1270dc9f702965624a9648b2eb72a439ab5e8009c5bf4c13f0018002eecde feature=bug-predict kind=architecture generated_at=2026-05-16 -->
