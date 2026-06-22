# Tasks: Extended Cache TTL — Sibling Packages

**Status**: in progress (2026-06-22) — Task A (attune-ai) done;
Task B (attune-author) deferred to a separate session + PR.

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

PR: _(linked on open)_

## Task B — attune-author ⬜ pending

Same mirror in attune-author's Claude provider path. **Separate
repo, separate PR — not started in the attune-ai session.** Pick
the package-local env var name (`ATTUNE_AUTHOR_CACHE_TTL` or reuse
`ATTUNE_CACHE_TTL` — decide at task time) and route its emit
site(s) through a local `_cache_control()` copy.
