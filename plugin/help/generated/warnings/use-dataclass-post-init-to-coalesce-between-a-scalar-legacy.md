---
type: warning
name: use-dataclass-post-init-to-coalesce-between-a-scalar-legacy
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Warning: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat

## Condition

attune-help 0.9.0 added `Feature.doc_paths: list[str]` alongside the existing `Feature.doc_path: str | None`

## Risk

Ignoring this guidance may cause: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat

## Mitigation

1. attune-help 0.9.0 added `Feature.doc_paths: list[str]` alongside the existing `Feature.doc_path: str | None`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat
