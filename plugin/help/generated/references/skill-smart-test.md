---
type: reference
subtype: procedural
name: skill-smart-test
category: skill
tags: [skill, plugin]
source: plugin/skills/smart-test/SKILL.md
---

# Reference: Skill: smart-test

Find test gaps and generate tests for uncovered code. Triggers on: generate tests, write tests, test coverage, find untested code, test gaps, smart test, what needs testing.

**Usage:** `/smart-test <path or module to test>`

## Scoping

Before running, ask:

1. **Target**: "Which file or module needs tests?"
2. **Approach**: "What kind of testing?"
   - Gap analysis — Find untested public functions
   - Generate tests — Write pytest tests for a module
   - Both — Audit gaps then generate tests for them

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `test_audit` | Coverage audit and gap detection |
| `test_generation` | Generate unit tests with edge cases |
| `test_gen_parallel` | Batch test generation (10-50 modules) |

## Execution

For gap analysis:

```
test_audit(path="<target>")
```

For targeted test generation:

```
test_generation(module="<target module>")
```

For batch generation across many modules:

```
test_gen_parallel(top=10)
```

## Output Format

**Prefer the rich panel.** If the tool response includes `panel_html`,
pass it to `mcp__visualize__show_widget` — the universal report panel
(title, score, findings/category sections; from
`attune.workflows.report_panel`). It shows an explicit "did not
complete" state on failure, never a false "clean". Fall back to the
markdown below when the widget surface is unavailable.

```markdown

## Test Gap Analysis

**Coverage:** X% | **Untested Functions:** Y

### Gaps by Priority

| File | Function | Risk | Coverage |
|------|----------|------|----------|

### Generated Tests

| File | Tests Created | Edge Cases |
|------|---------------|------------|
```

## Help

After presenting results, call:

```
help_lookup(topic="smart-test", mode="workflow_help")
```

If templates are returned, offer: "I have tips about
test generation — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to generate tests for the top gaps?"
- "Should I run the generated tests to verify?"
- "Want to see coverage for a different module?"

## Related Topics
- **Reference**: Tool: Test Audit (`test_audit`)
- **Reference**: Tool: Test Generation (`test_generation`)
- **Reference**: Tool: Test Gen Parallel (`test_gen_parallel`)
