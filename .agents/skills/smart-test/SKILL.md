---
name: smart-test
description: "Find test gaps and generate tests for uncovered code. Triggers on: generate tests, write tests, test coverage, find untested code, test gaps, smart test, what needs testing."
argument-hint: "<path or module to test>"
---

# Smart Test

Find test gaps and generate tests for uncovered code.

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

## Follow-Up

After presenting results, offer:

- "Want me to generate tests for the top gaps?"
- "Should I run the generated tests to verify?"
- "Want to see coverage for a different module?"
