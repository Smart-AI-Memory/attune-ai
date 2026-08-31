---
name: smart-test
description: "Find test gaps and generate tests for uncovered code. Triggers on: generate tests, write tests, test coverage, find untested code, test gaps, smart test, what needs testing."
argument-hint: "<path or module to test>"
---

# Smart Test

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="smart-test", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Smart Test** — Finds untested code and generates pytest tests with edge cases and error paths.

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

### Shared command workspace (preferred)

Open adapter `smart-test` with the validated target and `gap`, `generate`, or
`both` approach. The bound audit action is read-only. Publish the actual audit
as `audit_result`, including exact proposed test paths before any generator is
called. Present the proposal widget or Markdown; only an explicitly confirmed
`generate_tests` action authorizes those paths.

After `test_generation`, publish `generation_result` with the exact files
reported from disk. The adapter independently hashes those files and rejects
writes outside or different from the approved set. Run the returned test
probe and publish its exact command and exit code as `validation_result`.
Generator or test failure must say “did not complete” and retain the written
paths for rollback; it may not claim tests were created successfully. Preserve
the same preview/write/validation gates in compact text when the shared tools
are unavailable.

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
