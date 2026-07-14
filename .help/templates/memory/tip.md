---
type: tip
name: memory-tip
feature: memory
depth: tip
generated_at: 2026-07-14T15:58:54.095241+00:00
source_hash: cba94c001e0b9e2f41279e9caa28b69cdc1ff0b0c62ec76baa038dc0e48cb5b6
status: generated
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `UnifiedMemory`, `MemoryConfig`, and the security/loader classes
  re-exported from `attune.memory`, plus the `MemoryBackend` /
  `SearchableMemoryBackend` protocols from `attune.memory.backend`.
  Submodule internals (`mixins/`, `short_term/`, `long_term_*`) may
  change.
- **Let classification run.** Keep `auto_classify=True` unless you have
  a reason to set the level yourself.
- **Check capabilities, don't assume.** Use `get_capabilities()` /
  `supports_*()` before relying on real-time or cross-process behavior.
- **Close when done.** Call `close()` (or `save()`) to flush and
  release the backend.
