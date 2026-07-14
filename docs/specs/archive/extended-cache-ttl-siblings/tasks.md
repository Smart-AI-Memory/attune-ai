# Tasks: Extended Cache TTL — Sibling Packages

**Status**: ✓ complete (2026-06-22) — both tasks shipped.
Task A (attune-ai) and Task B (attune-author) merged.

---

## Task A — attune-ai ✓ complete 2026-06-22

Mirror `attune-rag`'s `_cache_control()` into attune-ai's Claude
provider.

1. ✓ **Add `_cache_control()` helper** to
   `src/attune/llm/providers/anthropic.py` reading
   `ATTUNE_CACHE_TTL` (`1h` → extended marker; unset/`5m`/other →
   default).
2. ✓ **Route all three emit sites** through the helper
   (`generate`, `analyze_large_codebase`, `generate_stream`) —
   no remaining hardcoded `{"type": "ephemeral"}`.
3. ✓ **Wire-shape tests** —
   `tests/llm/test_anthropic_cache_ttl.py`: parametrized helper
   test plus default + `1h` assertions at each emit site (mocked,
   `-m "not live"`).
4. ✓ **Suite green** — `tests/llm/` 283 passed; full `-m "not
   live"` run clean.

PR: [attune-ai#998](https://github.com/Smart-AI-Memory/attune-ai/pull/998)

## Task B — attune-author ✓ complete 2026-06-22

Same mirror in attune-author's Claude provider path. **Separate
repo, separate PR.** Implemented as a local `cache_control()` in
`src/attune_author/doc_gen/_cache.py`, reading the package-local
`ATTUNE_AUTHOR_CACHE_TTL` (behavior byte-identical when unset).

PR: [attune-author#81](https://github.com/Smart-AI-Memory/attune-author/pull/81)
— merged 2026-06-22 (`5fdbe9fd`).
