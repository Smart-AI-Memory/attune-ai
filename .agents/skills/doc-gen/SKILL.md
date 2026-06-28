---
name: doc-gen
description: "Generate documentation from source code — docstrings, READMEs, API references. Triggers on: generate docs, write documentation, document this, create README, API docs, doc-gen."
---
# Doc Gen

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="doc-gen", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Doc Gen** — Generates documentation from your source code — docstrings, README sections, API references.

## Scoping

Before running, ask:

1. **Target**: "Which file or module needs documentation?"
2. **Type**: "What kind of docs?"
   - Docstrings — Add or update Google-style docstrings
   - README — Generate a README section for a module
   - API reference — Generate full API documentation
   - Overview — High-level module explanation

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `doc_gen` | Generate documentation for a module |
| `doc_audit` | Check for stale or missing docs |
| `doc_orchestrator` | Full documentation maintenance pipeline |

## Execution

For docstring generation:

```
doc_gen(source_path="<target module>")
```

For a full documentation audit first:

```
doc_audit(path="<target>")
```

Then generate docs for gaps found:

```
doc_gen(source_path="<gap file>")
```

For a complete pipeline (audit + generate + review):

```
doc_orchestrator(path="<target>")
```

## Output Format

**Prefer the rich panel.** If the tool response includes `panel_html`,
pass it to `mcp__visualize__show_widget` — the universal report panel
(title, score, findings/category sections; from
`attune.workflows.report_panel`). It shows an explicit "did not
complete" state on failure, never a false "clean". Fall back to the
markdown below when the widget surface is unavailable.

```markdown
## Documentation Report

**Files:** X | **Functions Documented:** Y | **Gaps:** Z

### Generated Docstrings
| File | Function | Status |
|------|----------|--------|

### Gaps Remaining
| File | Missing |
|------|---------|
```

## Help

After presenting results, call:

```
help_lookup(topic="doc-gen", mode="workflow_help")
```

If templates are returned, offer: "I have tips about
documentation generation — want to see them?"

## Follow-Up

After presenting results, offer:

- "Want me to apply these docstrings to the files?"
- "Should I audit the rest of the project?"
- "Want a README section generated from this?"
