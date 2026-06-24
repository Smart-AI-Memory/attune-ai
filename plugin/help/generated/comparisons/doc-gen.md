---
name: doc-gen
source: content/features/doc-gen.md
tags:
- docs
- documentation
- generation
type: comparison
---

# Generate new documentation from source code with three specialized subagents

## Comparison

Doc-gen is the **creation** workflow in a family of three
documentation tools the `/doc-gen` skill routes between:

| Tool | Role |
|------|------|
| `doc-gen` (this feature) | Generate new documentation from source code. |
| `doc_audit` | Check for stale or missing documentation. |
| `doc_orchestrator` | Run a full documentation maintenance pipeline. |

Reach for **doc-gen** when you need new content written for a
module that lacks it; reach for **doc_audit** to find what's stale
or missing first; reach for **doc_orchestrator** when you want the
end-to-end maintenance pass. A common flow is doc_audit to find the
gaps, then doc-gen to fill them.
