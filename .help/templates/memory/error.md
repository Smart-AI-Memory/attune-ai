---
type: error
name: memory-error
feature: memory
depth: error
generated_at: 2026-07-14T15:58:54.095241+00:00
source_hash: cba94c001e0b9e2f41279e9caa28b69cdc1ff0b0c62ec76baa038dc0e48cb5b6
status: generated
---

# Two-tier memory subsystem — short-term working storage, long-term pattern lookup, and security

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `TypeError: __init__() missing 1 required positional argument: 'user_id'` | `UnifiedMemory()` constructed without `user_id` | Pass `user_id` — it is required | high |
| `persist_pattern` / `stage_pattern` returns `None` | Long-term storage unavailable (e.g. no writable `storage_dir`) | Check `health_check()` / `get_backend_status()`; confirm storage config | medium |
| `retrieve` returns `None` for a key you stashed | The entry expired (`ttl_seconds`) or the backend isn't persistent | Re-stash with a longer TTL; check `supports_persistence()` | medium |
| Cross-process reads don't see another process's writes | The backend isn't distributed (in-process store) | Check `supports_distributed()`; configure Redis | medium |
| `recall_pattern` returns `None` for a real id | `check_permissions=True` and the caller's `access_tier` is insufficient | Use a higher `access_tier`, or pass `check_permissions=False` for trusted callers | medium |
| A `SENSITIVE` pattern stored unencrypted | `encryption_enabled` is off in the config | Enable encryption in `MemoryConfig` | medium |

### Risk areas

- **`user_id` is required.** `UnifiedMemory` is per-user; there is no
  zero-arg constructor.
- **Protocol vs. `UnifiedMemory` signatures differ.** The protocol's
  `stash(key, value, ttl, agent_id)` is not `UnifiedMemory`'s
  `stash(key, value, ttl_seconds)` — don't conflate them.
- **Capabilities are deployment-dependent.** Real-time, distribution,
  and persistence vary by backend — check before relying on them.

### Diagnosis order

1. Confirm construction: `UnifiedMemory(user_id="...")`.
2. `health_check()` / `get_backend_status()` for backend state.
3. `get_capabilities()` to confirm realtime/distributed/persistence.
4. For a missing short-term key, check the TTL and
   `supports_persistence()`.
5. For a missing pattern, check `pattern_id`, `access_tier`, and
   `check_permissions`.
