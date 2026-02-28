# TODO Report

**Generated:** 2026-02-28
**Scope:** `src/attune/` — actionable code TODOs only
**Excluded:** string literals, prompt templates, docstrings, and
scanner/detector code that references TODO as a pattern

---

## Summary

| Priority | Count |
|----------|-------|
| High (unimplemented features) | 4 |
| Medium (LLM integration stubs) | 2 |
| Low (minor gaps) | 2 |
| **Total actionable** | **8** |

---

## High — Unimplemented Logic (blocks correct behavior)

### 1. Structural workflow stage body is a placeholder

**File:** [src/attune/workflow_patterns/structural.py:80](../../src/attune/workflow_patterns/structural.py#L80)
**File:** [src/attune/workflow_patterns/structural.py:165](../../src/attune/workflow_patterns/structural.py#L165)

```python
# TODO: Implement processing logic
# TODO: Implement {stage} logic
```

**Impact:** Any workflow using `structural.py` stages silently does
nothing. This is a real gap if structural patterns are used in
production workflows.

**Suggested fix:** Implement the stage dispatch logic or raise
`NotImplementedError` with a clear message so callers know the
stage is not yet supported.

---

### 2. Test maintenance crew generates empty test files

**File:** [src/attune/workflows/test_maintenance_crew.py:355](../../src/attune/workflows/test_maintenance_crew.py#L355)
**File:** [src/attune/workflows/test_maintenance_crew.py:364](../../src/attune/workflows/test_maintenance_crew.py#L364)
**File:** [src/attune/workflows/test_maintenance_crew.py:370](../../src/attune/workflows/test_maintenance_crew.py#L370)

```python
# TODO: Import the module being tested
# TODO: Implement actual tests
# TODO: Add more test cases based on the source code
```

**Impact:** `test_maintenance_crew` generates skeleton test files
with no actual test logic. Files pass syntax checks but provide
zero coverage.

**Suggested fix:** Wire in the LLM call to generate real test
bodies, or mark the workflow as `alpha` in the registry so users
know it produces scaffolding only.

---

### 3. Orchestration strategies list is incomplete

**File:** [src/attune/orchestration/_strategies/__init__.py:19](../../src/attune/orchestration/_strategies/__init__.py#L19)

```python
# advanced: ToolEnhanced, PromptCached, etc. (TODO)
```

**Impact:** Advanced orchestration strategies are advertised but
not registered. Selecting them would fail silently or fall back
to defaults.

**Suggested fix:** Either implement `ToolEnhanced` and
`PromptCached` strategies, or remove them from documentation
until they are ready.

---

## Medium — LLM Integration Stubs (features exist but are mocked)

### 4. Keyboard shortcuts parser skips LLM feature discovery

**File:** [src/attune/workflows/keyboard_shortcuts/parsers.py:300](../../src/attune/workflows/keyboard_shortcuts/parsers.py#L300)

```python
# TODO(llm-integration): Implement LLM-based feature discovery
```

**Impact:** Keyboard shortcut parsing falls back to static rules
rather than using LLM to discover context-specific shortcuts.
Feature works but is less intelligent than intended.

**Suggested fix:** Wire in an LLM call using the existing
`CHEAP` tier — this is a low-cost, bounded prompt.

---

### 5. Progressive test generation skips LLM API call

**File:** [src/attune/workflows/progressive/test_gen.py:175](../../src/attune/workflows/progressive/test_gen.py#L175)

```python
# TODO(llm-integration): Call LLM API with _prompt
```

**Impact:** The progressive test generation workflow builds a
prompt but never sends it. Returns empty or default output.

**Suggested fix:** Add the `anthropic` client call using the
existing pattern from `workflows/base.py`.

---

## Low — Minor Gaps (non-blocking)

### 6. Test generator missing step completion logic

**File:** [src/attune/test_generator/generator.py:268](../../src/attune/test_generator/generator.py#L268)

```python
# TODO: Add step completion logic
```

**Impact:** Step completion tracking is missing, so progress
reporting during test generation is inaccurate. Tests still
generate correctly.

**Suggested fix:** Add a `step.complete()` call or emit a
completion event after each generation step.

---

### 7. Orchestration test generation uses placeholder test bodies

**File:** [src/attune/orchestration/tools/test_generation.py:326](../../src/attune/orchestration/tools/test_generation.py#L326)
**File:** [src/attune/orchestration/tools/testing.py:467](../../src/attune/orchestration/tools/testing.py#L467)

```python
TODO: Implement actual test logic for lines {missing_lines[:5]}
```

**Impact:** These are inside LLM prompt templates — the LLM is
being asked to fill in the test logic. The TODO is intentional
scaffolding passed to the model. Low risk but confusing if read
out of context.

**Suggested fix:** Rename to `<implement test logic here>` or
similar to distinguish from actual code TODOs.

---

## Not Actionable (excluded)

These lines reference TODO as data, not as work items:

| File | Why excluded |
|------|-------------|
| `prompts/examples.py:194-196` | Example output shown to users |
| `workflows/refactor_plan.py:47-50` | Severity config for TODO scanner |
| `workflows/refactor_plan_report.py:17-20` | Severity config for TODO scanner |
| `workflows/code_review_analysis_mixin.py:292+` | Regex/detection code |
| `workflows/bug_predict.py:302` | Detector checking for `# TODO` strings |
| `wizards/builtin/refactor_wizard.py:195` | Comment describing wizard stage |
| `workflows/document_gen/*.py` | LLM prompt instructions |
| `workflows/test_gen_parallel.py:75+` | LLM prompt instructions |

---

## Recommended Implementation Order

1. **`test_maintenance_crew.py`** — most user-visible, generates
   empty files that look like real output
2. **`structural.py`** — silent failure is worse than a clear error
3. **`progressive/test_gen.py`** — quick fix, just add the API call
4. **`keyboard_shortcuts/parsers.py`** — low-cost LLM call
5. **`orchestration/_strategies/__init__.py`** — either implement
   or document as planned
6. **`test_generator/generator.py`** — minor, fix during next
   test generator pass
7. **`orchestration/tools/test_generation.py`** — rename for
   clarity, low priority
