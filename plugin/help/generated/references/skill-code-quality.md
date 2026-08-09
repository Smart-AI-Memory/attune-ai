---
type: reference
subtype: procedural
name: skill-code-quality
category: skill
tags: [skill, plugin]
source: plugin/skills/code-quality/SKILL.md
---

# Reference: Skill: code-quality

Code review to find quality issues, style violations, and code smells. Triggers on: review, code review, quality, lint, code smell, analyze code.

**Usage:** `/code-quality <path or directory to review>`

## Scoping

Before running, ask:

1. **Scope**: "Which files or directory should I review?"
2. **Depth**: "Quick scan, thorough, or deep review?"
   - Quick: code_review only
   - Thorough: code_review + bug_predict combined
   - Deep: deep_review (security + quality + test gaps)

## Execution

**Quick scan:**

```
code_review(path="<user-specified path>")
```

**Thorough analysis:**

```
code_review(path="<user-specified path>")
bug_predict(path="<user-specified path>")
```

Merge and deduplicate results from both tools.

**Deep review** (multi-pass: security, quality, test gaps):

```
deep_review(path="<user-specified path>")
```

## Output Format

**Prefer the rich panel.** If the tool response includes `panel_html`,
pass it to `mcp__visualize__show_widget` — the universal report panel
(title, score, findings/category sections; from
`attune.workflows.report_panel`). It shows an explicit "did not
complete" state on failure, never a false "clean". Fall back to the
markdown below when the widget surface is unavailable.

```markdown

## Code Quality Report

**Health:** X/100 | **Files:** Y | **Issues:** Z

### Issues by Category

| Category | Count | Severity |
|----------|-------|----------|
| Style | X | Low |
| Correctness | Y | High |
| Security | Z | Critical |
| Predicted Bugs | W | Medium |

### Details

| File | Line | Issue | Source |
|------|------|-------|--------|

### Predicted Bug Risks

| File | Pattern | Confidence |
|------|---------|------------|
```

## Help

After presenting results, call:

```
help_lookup(topic="code-quality", mode="workflow_help")
```

If templates are returned, offer: "I have tips about
code quality reviews — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to fix these issues?"
- "Should I generate tests for the risky areas?"
- "Want to run a security-focused deep scan?"

## Related Topics

_No related topics yet._
