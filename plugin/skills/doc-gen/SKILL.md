---
name: doc-gen
description: "Generate documentation from source code. Creates Google-style docstrings, README sections, API references, and module overviews. Triggers on: generate docs, write documentation, document this, create README, API docs, doc-gen, explain this module, docstrings."
argument-hint: "<path or module to document>"
---

# Doc Gen

Generate documentation from source code with structured
outlines and Google-style formatting.

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
doc_gen(path="<target module>")
```

For a full documentation audit first:

```
doc_audit(path="<target>")
```

Then generate docs for gaps found:

```
doc_gen(path="<gap file>")
```

For a complete pipeline (audit + generate + review):

```
doc_orchestrator(path="<target>")
```

## Output Format

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

## Follow-Up

After presenting results, offer:

- "Want me to apply these docstrings to the files?"
- "Should I audit the rest of the project?"
- "Want a README section generated from this?"
