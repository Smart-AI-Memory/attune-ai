# Project-Aware Guidance

**Created:** 2026-02-24
**Updated:** 2026-02-24
**Source:** /brainstorm session + codebase review
**Target Version:** v3.5.0

## Problem

After completing a workflow, Attune suggests generic next
steps ("try `/testing` next") rather than suggestions
grounded in the user's actual project state. Users who
finish their first workflow don't get a compelling,
contextual reason to explore deeper — they go quiet.

## Goals

- **Accurate** (must-have) — suggestions grounded in real
  project analysis (coverage gaps, security patterns,
  code quality signals), not generic menus
- **Guided** (must-have) — each suggestion uses Socratic
  discovery to walk the user into the next workflow,
  not just name it
- **Richer forms** (nice-to-have, future) — XML/HTML
  form elements for more expressive discovery UI

## End State

After any workflow completes, Attune:

1. Analyzes project context (project index, workflow
   history, code patterns, prior results)
2. Surfaces 2-3 prioritized, specific suggestions
3. Each suggestion explains *why* based on real findings
4. User picks one and is immediately guided into it
   via Socratic discovery

**Example:** User runs `/dev review` and gets:

> Your review found 3 modules with unvalidated file
> paths. Want to walk through securing them?
>
> Your test coverage is 43% — I can generate tests
> for the 5 most critical uncovered functions.
>
> There are 12 TODO comments older than 30 days.
> Want to triage them?

## Existing Foundation

Codebase review reveals significant reusable
infrastructure:

### Already Built

| Component | Location | Reuse |
| --- | --- | --- |
| `format_workflow_result()` | `workflows/output.py` | Accepts `recommendations` param — can render suggestions today |
| `_format_recommendations()` | `workflows/test_gen/report_formatter.py` | Existing pattern for formatting next-steps |
| `suggest_compact.py` | `hooks/scripts/` | Proven hook-based suggestion with state persistence |
| SBAR handoff format | `hooks/scripts/pre_compact.py` | Structured situation/assessment/recommendation model |
| `socratic_router.py` | `socratic/` | Routes intent to `AskUserQuestion` — the Socratic bridge already exists |
| `TierRecommendation` | `telemetry/feedback_models.py` | Confidence-scored recommendation pattern |
| `FileRecord.needs_attention` | `project_index/scanner.py` | Per-file attention signals with reasons — designed for this |
| `ProjectSummary` health metrics | `project_index/` | Coverage gaps, staleness, complexity, untested files |
| `WorkflowHistoryStore` | `workflows/history_utils.py` | SQLite workflow run history for pattern detection |

### Gaps to Fill

1. **No `NextAction` dataclass** — need a standard
   format for suggestions with priority, reasoning,
   confidence, and workflow target
2. **No workflow-to-workflow mapping** — no registry
   that says "after code-review, consider security-audit"
3. **No post-execution hook** — `_finalize_execution()`
   saves history and stops heartbeat but doesn't
   generate guidance
4. **No suggestions field on `WorkflowResult`** —
   `metadata` dict exists but isn't structured for this
5. **No cross-session persistence** — suggestions
   don't survive session boundaries

## Approach

### Phase 1: Data Model (small — single session)

- Add `NextAction` dataclass to `data_classes.py`:
  - `priority` (high/medium/low)
  - `workflow_name` (target workflow)
  - `description` (user-facing, specific)
  - `reasoning` (why this suggestion, with evidence)
  - `confidence` (0.0-1.0)
- Add `suggestions: list[NextAction]` field to
  `WorkflowResult`

### Phase 2: Suggestion Registry (small — single session)

- Create `src/attune/workflows/suggestions.py`
- Static workflow-to-workflow mappings with conditions:

```python
WORKFLOW_TRANSITIONS = {
    "code-review": [
        Transition(
            target="security-audit",
            condition=lambda r: any(
                f.severity == "high"
                for f in r.findings
                if "security" in f.category
            ),
            template="Found {count} security findings — "
                     "want a deeper security audit?",
        ),
        Transition(
            target="test-gen",
            condition=lambda r: r.coverage < 0.8,
            template="Coverage is {pct}% — I can generate "
                     "tests for the {n} most critical gaps.",
        ),
    ],
}
```

### Phase 3: Engine + Integration (medium — core work)

- `SuggestionEngine` combines three signal sources:
  1. Registry mappings (workflow result conditions)
  2. ProjectIndex signals (`needs_attention`,
     `critical_untested_files`, staleness)
  3. Workflow history patterns (what succeeded together)
- Hook into `_finalize_execution()` in
  `execution_mixin.py`
- Render via existing `format_workflow_result(
  recommendations=...)` in `output.py`
- Keep analysis on CHEAP tier — runs after every
  workflow

### Phase 4: Socratic Bridge (small — leverages existing)

- Present top 2-3 suggestions via `AskUserQuestion`
  with descriptive options showing evidence
- Selected suggestion seeds the next workflow's
  Socratic discovery with pre-filled context
- Use existing `socratic_router.py` to route the
  selected action

## Technical Notes

- `FileRecord.needs_attention` + `attention_reasons`
  are already computed during scanning but unused for
  guidance — this is the primary signal source
- `format_workflow_result()` already accepts a
  `recommendations` parameter — Phase 3 can render
  suggestions without new output infrastructure
- Follow the `suggest_compact.py` pattern for state
  persistence to avoid repeating suggestions
- Follow SBAR format from `pre_compact.py` for
  structuring suggestion reasoning

## Next Steps

- [ ] Add `NextAction` dataclass to `data_classes.py`
- [ ] Add `suggestions` field to `WorkflowResult`
- [ ] Create `suggestions.py` with transition registry
- [ ] Build `SuggestionEngine` with 3 signal sources
- [ ] Hook into `_finalize_execution()` completion path
- [ ] Render via `format_workflow_result(recommendations)`
- [ ] Present via `AskUserQuestion` with evidence
- [ ] Add tests for suggestion relevance and accuracy
- [ ] Add suggestion state persistence (avoid repeats)

## Open Questions

- Should suggestions persist across sessions (via
  memory) or be ephemeral? The `suggest_compact.py`
  pattern supports persistence — likely worth it.
- How many signals are enough to be accurate without
  being slow? Start with 3 (registry + index +
  history), measure latency.
- Should the user be able to dismiss/snooze a
  suggestion category? Yes, but defer to Phase 5.
- Should `NextAction` include an `auto_execute` flag
  for high-confidence suggestions? Consider for
  future iteration.
