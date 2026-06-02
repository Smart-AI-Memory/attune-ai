---
type: cli-reference
name: rag-grounding
tags: [rag, code-generation, grounding, workflows]
source: src/workflows/rag_code_gen.py
---

# rag-grounding CLI reference

## Description

`rag-grounding` runs the `RagCodeGenWorkflow`, which retrieves attune-help context and feeds citation-forced prompts to Claude. The workflow grounds every response in retrieved documentation, ensuring that referenced APIs, workflow names, and CLI commands come from the attune ecosystem rather than model priors. Output includes the generated code or explanation together with provenance citations.

## Usage

```
rag-grounding [OPTIONS]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show this message and exit |

## Output

The command writes a `WorkflowResult` to stdout. The result contains the generated code or explanation and the retrieved passages that grounded the response.

```
Retrieving attune-help context...
Running RagCodeGenWorkflow...

--- Result ---
<generated code or explanation>

--- Sources ---
[1] concepts/template-composition.md
[2] concepts/task-template-design-patterns.md
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Workflow completed and `WorkflowResult` was returned successfully |
| `1` | Workflow failed — check stderr for details |

## Related commands

- `attune-help` — browse the help templates that supply retrieval context to this workflow
- `attune-rag` — the retrieval layer this workflow calls to fetch attune-help passages

<!-- attune-generated: source_hash=0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550 feature=rag-grounding kind=cli-reference generated_at=2026-06-02 -->
