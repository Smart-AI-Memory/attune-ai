---
type: error
name: use-dataclass-post-init-to-coalesce-between-a-scalar-legacy
confidence: Verified
tags: [git, python]
source: .claude/CLAUDE.md
---

# Error: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat

## Signature

Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat

## Root Cause

attune-help 0.9.0 added `Feature.doc_paths: list[str]` alongside the existing `Feature.doc_path: str | None`. Rather than branch at every read site (`feature.doc_paths or [feature.doc_path] if feature.doc_path else []`), `__post_init__` keeps the two attributes in sync: if `doc_paths` is set, populate `doc_path = doc_paths[0]`; if `doc_path` is set alone, populate `doc_paths = [doc_path]`. Loader coerces YAML scalar legacy `doc_path:` into `doc_paths=[...]`; writer always emits the list form. Consumers read whichever attribute is convenient. One `__post_init__`, no branches at call sites. Pattern generalizes to any additive schema widening from scalar → list.

## Resolution

1. attune-help 0.9.0 added `Feature.doc_paths: list[str]` alongside the existing `Feature.doc_path: str | None`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Use dataclass `__post_init__` to coalesce between a
  scalar legacy field and a new list field when widening
  a schema with backward compat
