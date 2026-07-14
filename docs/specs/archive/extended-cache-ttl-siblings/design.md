# Design: Extended Cache TTL — Sibling Packages

**Status**: complete (2026-06-22) — both tasks shipped; reconciled at 2026-07-14 triage (was: approved)

---

## Source of truth

`attune_rag/providers/claude.py`:

```python
def _cache_control() -> dict[str, str]:
    if os.getenv("ATTUNE_RAG_CACHE_TTL", "5m").strip().lower() == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}
```

Read per-call (not memoized) so tests can flip the value with
`monkeypatch.setenv`; the cost is one `os.getenv` on an
already-networked path.

---

## Task A — attune-ai

**File**: `src/attune/llm/providers/anthropic.py`

Add a module-level `_cache_control()` identical to the rag helper
except the env var is `ATTUNE_CACHE_TTL` (no `_RAG_` infix — this
is the general-purpose provider).

**Emit sites routed through the helper** (three today):

| Method | What it caches |
|--------|----------------|
| `generate()` | system-prompt prefix block |
| `analyze_large_codebase()` | codebase-files block |
| `generate_stream()` | system-prompt prefix block |

Each previously held a literal `{"type": "ephemeral"}`; all three
now call `_cache_control()`.

---

## Why per-package copies, not a shared module

The helper is ~16 lines and the env var name differs per package
by design (a rag dashboard sweep and an attune-ai workflow run are
independently tunable). A shared module would couple the release
cadence of otherwise-independent PyPI packages for no real saving.
This matches the existing rag precedent; see requirements
Non-goals.

---

## Testing

Mock the `anthropic` client; assert the `cache_control` dict at
each emit site for both the default (env unset) and `1h`. Mirrors
`attune-rag/tests/unit/providers/test_claude_cache_ttl.py`. No live
API — runs under `-m "not live"`.
