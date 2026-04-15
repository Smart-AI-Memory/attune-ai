---
type: quickstart
feature: doc-gen
depth: quickstart
generated_at: 2026-04-14T14:46:41.158188+00:00
source_hash: 67aadd029bbf773d9f478a4d4c750e25344dc6b0bd9e1edadbcf5151d83f3bff
status: generated
---

# Quickstart: doc gen

Generate comprehensive documentation from your codebase using AI-powered analysis.

```python
from attune.workflows.document_gen import DocumentGenerationWorkflow

workflow = DocumentGenerationWorkflow()
result = workflow.execute(path="./src")
print(result.output)
```

## Prerequisites

- Python environment with the attune package installed
- Source code directory you want to document

## Generate your first documentation

1. **Create a workflow instance** and point it at your source code:

```python
from attune.workflows.document_gen import DocumentGenerationWorkflow

workflow = DocumentGenerationWorkflow()
result = workflow.execute(path="./your-project-directory")
```

2. **Review the generated documentation** structure:

```python
print(result.output)
# Output includes:
# - Summary: Overview of your codebase
# - Outline: Documentation structure
# - Documentation: Full content with API references
# - Suggestions: Improvement recommendations
```

3. **Format the output** for human reading:

```python
from attune.workflows.document_gen import format_doc_gen_report

report = format_doc_gen_report(result.raw_data, {"path": "./your-project-directory"})
print(report)
```

**Expected output:** A structured markdown document with sections for summary, outline, detailed documentation, and improvement suggestions for your codebase.

**Next:** Save the generated documentation to a file and integrate it into your project's docs folder.
