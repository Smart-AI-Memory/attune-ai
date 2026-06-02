---
type: error
name: rag-grounding-error
feature: rag-grounding
depth: error
generated_at: 2026-06-02T10:56:02.693151+00:00
source_hash: 0c56c05d50048a3426da1a4782fa4bdecd9fc2a19dcd7d2d0957aa7b55b42550
status: generated
---

# RAG grounding errors

## Common error signatures

Failures in RAG-grounded code generation typically fall into three categories:

- **Fabricated references** — `RagCodeGenWorkflow.execute()` produces output that cites attune APIs, workflow names, or CLI commands that do not exist. This happens when retrieved context is insufficient and the model fills gaps with invented details.
- **Missing or empty retrieval context** — `execute()` receives no `<passage>` content, so the grounded prompt contains no real citations. The resulting `WorkflowResult` may be structurally valid but factually unsupported.
- **Prompt injection via passage content** — content inside a retrieved `<passage>` block contains text that attempts to override the system prompt (for example, a literal `</passage>` tag or an embedded directive). The system prompt in `RagCodeGenWorkflow` is designed to treat such content as documentation, not as instructions, but unexpected output can indicate a bypass attempt.

## Where errors originate

All observable failures trace back to `RagCodeGenWorkflow` in `workflows.rag_code_gen`. The two entry points to check first are:

- `RagCodeGenWorkflow.__init__(**kwargs)` — misconfigured or missing keyword arguments may cause failures before retrieval begins.
- `RagCodeGenWorkflow.execute(**kwargs)` — retrieval, prompt construction, model invocation, and `WorkflowResult` assembly all happen here. Most grounding failures originate in this method.

## How to diagnose

1. **Inspect the `WorkflowResult` for citation provenance.** Grounding failures often show up as output that references workflows, APIs, or CLI commands not present in any `<passage>` block. Compare the cited sources in the result against the actual retrieved passages to identify fabricated references.

2. **Check what context was passed to `execute()`.** If the passages supplied to `execute()` are empty or irrelevant, the model has no ground truth to cite. Confirm that retrieval returned non-empty, on-topic content before attributing the failure to the generation step.

3. **Look for prompt injection artifacts.** If `execute()` returns output that appears to follow instructions embedded in retrieved text — rather than answering the user's question — review the passage content for embedded directives. The system prompt instructs the model to ignore such content, so anomalous instruction-following suggests the passage content warrants sanitization upstream.

4. **Review `__init__` kwargs for misconfiguration.** If the workflow raises before producing any output, the failure likely originates in `__init__`. Capture the full traceback to confirm whether the raise site is in initialization or execution, then verify that all required keyword arguments are present and correctly typed.

## Source files

- `src/attune/workflows/rag_code_gen.py`

**Tags:** `rag`, `retrieval`, `grounding`, `faithfulness`, `citation`
