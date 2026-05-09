---
type: faq
name: use-dataclass-post-init-to-coalesce-between-a-scalar-legacy
tags: [git, python]
source: .claude/CLAUDE.md
---

# FAQ: What is the best practice for use dataclass __post_init__ to coalesce between a scalar legacy field and a new list field when widening a schema with backward compat?

## Answer

attune-help 0.9.0 added `Feature.doc_paths: list[str]` alongside the existing `Feature.doc_path: str | None`. Rather than branch at every read site (`feature.doc_paths or [feature.doc_path] if feature.doc_path else []`), `__post_init__` keeps the two attributes in sync: if `doc_paths` is set, populate `doc_path = doc_paths[0]`; if `doc_path` is set alone, populate `doc_paths = [doc_path]`.

```
Feature.doc_paths: list[str]
```

## Related Topics
- **Error**: Detailed error: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat
