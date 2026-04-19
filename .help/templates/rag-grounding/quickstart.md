---
type: quickstart
feature: rag-grounding
depth: quickstart
generated_at: 2026-04-19T06:52:24.603295+00:00
source_hash: 80a69ae7596bd83339fd059323793ff10c80f34f01389bf3e822225eb3c48f33
status: generated
---

# Quickstart: RAG-grounded code generation

Generate code that cites real attune APIs and patterns from your project's documentation using retrieval-augmented generation.

```python
from attune.workflows.rag_code_gen import RagCodeGenWorkflow

workflow = RagCodeGenWorkflow()
result = workflow.execute(query="How do I create a data pipeline?")
print(result.content)
```

## Run the workflow

1. **Create and execute the workflow** with your coding question:
   ```python
   from attune.workflows.rag_code_gen import RagCodeGenWorkflow

   workflow = RagCodeGenWorkflow()
   result = workflow.execute(query="How do I process user input in attune?")
   ```

2. **Review the generated code** which includes citations to source files:
   ```
   To process user input in attune, use the InputProcessor class from
   src/core/input.py. Here's an example:

   ```python
   processor = InputProcessor()
   validated = processor.validate(user_data)
   ```

   Source: src/core/input.py, line 45
   ```

3. **Verify the citations** by checking that referenced files and APIs exist in your project.

The workflow retrieves relevant documentation context and generates code that references actual attune features rather than hallucinated APIs.

**Next:** Run the workflow with questions specific to your use case to see how it grounds responses in your project's actual codebase.
