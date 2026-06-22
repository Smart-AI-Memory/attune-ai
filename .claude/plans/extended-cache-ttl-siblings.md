# Plan: Extended Cache TTL — Sibling Packages

**Spec**: [specs/extended-cache-ttl-siblings/](../../specs/extended-cache-ttl-siblings/)
**Created**: 2026-06-22

---

## Summary

`attune-rag` shipped an env-driven extended prompt-cache TTL
(`ATTUNE_RAG_CACHE_TTL=1h` → 1-hour `cache_control` window via
`_cache_control()` in `attune_rag/providers/claude.py`). This plan
mirrors that helper into the sibling packages so the longer window
is reachable there too, byte-identical when the env var is unset.

---

## Tasks

- **Task A — attune-ai** (this repo): add `_cache_control()` to
  `src/attune/llm/providers/anthropic.py` (env var
  `ATTUNE_CACHE_TTL`) and route all three `cache_control` emit
  sites through it. Tests + `-m "not live"` suite. One PR.
- **Task B — attune-author** (separate repo, separate PR):
  same mirror. **Do not start in the attune-ai session.**

See [the spec](../../specs/extended-cache-ttl-siblings/tasks.md)
for per-task status.

---

## Reference

- Source helper: `attune-rag/src/attune_rag/providers/claude.py`
  (`_cache_control`).
- Mirror tests: `attune-rag/tests/unit/providers/test_claude_cache_ttl.py`.
