# TODO Report

**Generated:** 2026-02-28
**Reviewed:** 2026-02-28 (all 8 source files read)
**Scope:** `src/attune/` — actionable code TODOs only
**Excluded:** string literals, prompt templates, docstrings, and
scanner/detector code that references TODO as a pattern

---

## Summary (after source review)

| Classification | Count |
| -------------- | ----- |
| P2B — explicitly deferred with clear comment | 4 |
| False positive — TODO is inside output template | 3 |
| Informational docstring — no runtime impact | 1 |
| **Genuinely actionable** | **0** |

None of the 8 items require a code change now. All are either
intentionally deferred or located inside string templates that
generate user-facing scaffolding.

---

## Group A — Intentional Scaffolding in Output Templates

The TODOs below appear inside Python f-strings or string constants
that produce generated code for users. They are user guidance in
the output, not unimplemented framework logic.

### 1. Structural workflow stage body

**File:** [src/attune/workflow_patterns/structural.py:80](../../src/attune/workflow_patterns/structural.py#L80)
**File:** [src/attune/workflow_patterns/structural.py:165](../../src/attune/workflow_patterns/structural.py#L165)

```python
# TODO: Implement processing logic    ← inside a Python string template
# TODO: Implement {stage} logic       ← inside a Python string template
```

**Classification:** False positive — these lines are inside the
`code="""..."""` strings returned by `generate_code_sections()`.
They are scaffolding hints printed into the files that users
generate. The framework's own dispatch logic is complete.

---

### 2. Test maintenance crew generated test stubs

**File:** [src/attune/workflows/test_maintenance_crew.py:355](../../src/attune/workflows/test_maintenance_crew.py#L355)
**File:** [src/attune/workflows/test_maintenance_crew.py:364](../../src/attune/workflows/test_maintenance_crew.py#L364)
**File:** [src/attune/workflows/test_maintenance_crew.py:370](../../src/attune/workflows/test_maintenance_crew.py#L370)

```python
# TODO: Import the module being tested   ← inside generated test file string
# TODO: Implement actual tests           ← inside generated test file string
# TODO: Add more test cases              ← inside generated test file string
```

**Classification:** False positive — inside `_generate_test_code()`
string constant. The entire `TestMaintenanceCrew` class is
deprecated since v4.3.0 with an active `DeprecationWarning`. No
production caller reaches this code.

---

### 3. Test generator step completion

**File:** [src/attune/test_generator/generator.py:269](../../src/attune/test_generator/generator.py#L269)

```python
# TODO: Add step completion logic   ← inside an f-string template
```

**Classification:** False positive — inside a multi-line f-string
that generates integration test file content. This hint appears
in the user's generated test, not in the generator's own logic.

---

### 4. Orchestration placeholder test bodies

**File:** [src/attune/orchestration/tools/test_generation.py:337](../../src/attune/orchestration/tools/test_generation.py#L337)
**File:** [src/attune/orchestration/tools/testing.py:477](../../src/attune/orchestration/tools/testing.py#L477)

```python
TODO: Implement actual test logic for lines {missing_lines[:5]}
```

**Classification:** False positive — inside the template string
returned by `_generate_coverage_test_template()`. Already gated
behind `@pytest.mark.skipif` in the generated output, with a clear
reason string. Self-documenting.

---

## Group B — P2B: Explicitly Deferred LLM Integrations

These two TODOs are already clearly marked as P2B in the source.
No change needed — the comment is accurate and complete.

### 5. Progressive test generation skips LLM API call

**File:** [src/attune/workflows/progressive/test_gen.py:184](../../src/attune/workflows/progressive/test_gen.py#L184)

```python
# TODO(llm-integration): Call LLM API with _prompt
# Deferred: Requires LLM API integration (tracked in P2B debt register)
# For now, returns simulated test generation results
```

**Classification:** P2B — comment is correct and complete.
`ProgressiveTestGenWorkflow` is also deprecated since v5.3.0.

---

### 6. Keyboard shortcuts parser skips LLM feature discovery

**File:** [src/attune/workflows/keyboard_shortcuts/parsers.py:300](../../src/attune/workflows/keyboard_shortcuts/parsers.py#L300)

```python
# TODO(llm-integration): Implement LLM-based feature discovery
# Deferred: Requires LLM API integration (tracked in P2B debt register)
# Returns empty list until LLM analysis is available
```

**Classification:** P2B — comment is correct and complete.
`LLMFeatureAnalyzer.analyze_codebase()` returns `[]` cleanly; the
`CompositeParser` works fine without it.

---

## Group C — Informational Docstring

### 7. Orchestration strategies list

**File:** [src/attune/orchestration/\_strategies/\_\_init\_\_.py:19](../../src/attune/orchestration/_strategies/__init__.py#L19)

```python
# advanced: ToolEnhanced, PromptCached, etc. (TODO)
```

**Classification:** Informational docstring bullet — this line is
inside the module docstring listing planned strategies. All
currently-registered strategies work correctly.
`register_strategy()` exists as the extension point for when these
are implemented.

---

## Next review trigger

Re-examine these items when:

- LLM API integration work begins (P2B sprint) — revisit items 5–6
- Strategy layer is extended — revisit item 7
- `TestMaintenanceCrew` is fully removed — clean up item 2

---

## Previously flagged as "Not Actionable" (still excluded)

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
