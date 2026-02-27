# DocumentManagerWorkflow (Deprecated)

> **Deprecated in v4.0.0.** Use `DocumentGenerationWorkflow`
> instead. Will be removed in v5.0.0.

## Overview

**Patterns Used:** `single-stage`
**Complexity:** SIMPLE
**Stages:** 1 (process at CAPABLE tier)

## Migration

Replace all usages:

```python
# Before (deprecated)
from attune.workflows.document_manager import (
    DocumentManagerWorkflow,
)

# After
from attune.workflows.document_gen import (
    DocumentGenerationWorkflow,
)
```

## Related Workflows

- `DocumentGenerationWorkflow` - the replacement
- `document_gen/chunked_generation.py` - chunked doc gen
- `document_gen/polish_stage.py` - polish/refinement

---

**Generated:** 2026-01-09 | **Updated:** 2026-02-26
**Status:** Deprecated
