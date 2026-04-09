---
name: author-docs
description: "Generate full documentation from source code with the 3-stage AI pipeline (outline, write, review). Triggers on: write docs, generate API reference, create README, AI doc generation."
argument-hint: "<source-path>"
---

# Author Docs

Generate full documentation from a source file using the
3-stage AI pipeline: outline → write → review. Output is
production-ready API references, guides, or READMEs.

## When to use

- New module needs an API reference
- Library needs a fresh README
- Internal docs need to be rewritten for external audiences

## Requirements

- `ANTHROPIC_API_KEY` must be set in the environment
- The `[ai]` extra must be installed:
  `pip install 'attune-author[ai]'`

## Scoping

Use `AskUserQuestion` to gather inputs:

```yaml
question: "What kind of documentation do you need?"
header: "Doc Type"
options:
  - label: "API reference"
    description: "Function/class signatures, args, returns, examples"
  - label: "User guide"
    description: "How-to walkthrough for end users"
  - label: "README"
    description: "Project overview, install, quick start"
  - label: "Module overview"
    description: "Architecture and component descriptions"
```

Then ask for `audience` (developers, beginners, ops) and
the target source path.

## Execution

1. Call the MCP tool `author_docs` with `target`,
   `doc_type`, `audience`, and optional `output_path`.
2. The pipeline runs three stages — show progress to the
   user as each stage completes.
3. If `output_path` is set, confirm the file was written.
   Otherwise show the content inline.

## Delegating to the doc-writer agent

For larger jobs (multi-file modules, full directories),
delegate to the `doc-writer` subagent instead of calling
the tool directly. The agent has more turns to work with
and can iterate on multiple files.

## Output

```text
Stages: outline → write → review
Output: docs/api/auth.md (4827 chars)
```
