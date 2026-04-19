---
type: task
feature: rag-grounding
depth: task
generated_at: 2026-04-19T06:51:25.750407+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# Work with rag grounding

Use RAG grounding when you need to generate code with citations to real Attune APIs, workflows, and CLI commands rather than invented features.

## Prerequisites

- Access to the project source code
- Familiarity with `src/attune/workflows/rag_code_gen.py`

## Set up the workflow

1. **Import the RagCodeGenWorkflow class:**
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow
   ```

2. **Initialize the workflow:**
   ```python
   workflow = RagCodeGenWorkflow()
   ```

## Execute code generation

1. **Prepare your generation request:**
   Include the specific code generation task you need completed.

2. **Run the workflow:**
   ```python
   result = workflow.execute(
       # Add your parameters here based on your generation needs
   )
   ```

3. **Process the result:**
   The workflow returns a `WorkflowResult` containing the generated code with proper citations to Attune ecosystem components.

## Verify success

Check that the generated code:
- References actual Attune APIs and workflow names
- Includes source file citations for any patterns used
- Contains no invented features (the system prompt enforces this)

## Key files

- `src/attune/workflows/rag_code_gen.py` — Contains `RagCodeGenWorkflow` class

## Extend the workflow

If you need custom behavior, subclass `RagCodeGenWorkflow`:

```python
class CustomRagWorkflow(RagCodeGenWorkflow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add custom initialization

    def execute(self, **kwargs):
        # Add custom execution logic
        return super().execute(**kwargs)
```
