# Design: Anthropic Memory-Tool Backend

> Technical design for the `BetaAbstractMemoryTool` adapter over
> attune's memory backends. See
> [`requirements.md`](requirements.md) for scope.

**Status:** complete — Phase 1 shipped (`memory/memory_tool.py`, PR #671); Phase 2 surfacing shipped as the `attune memory-agent` CLI; Option ③ (SDK-native-workflow surfacing) re-scoped out — see Phase 2 below.

---

## Interface (what Anthropic gives us)

Anthropic's Memory tool is **client-side**: the model emits commands;
the SDK's tool runner dispatches them to a backend you implement by
subclassing `BetaAbstractMemoryTool` (from
`anthropic.lib.tools`). The six commands:

| Command | Semantics (file model) | Maps to attune backend |
|---|---|---|
| `view` | List a dir / read a file under `/memories` | `keys(prefix*)` + `retrieve(path)` |
| `create` | Write a new file | `stash(path, content)` |
| `str_replace` | Replace a substring in a file | `retrieve` → `str.replace` → `stash` |
| `insert` | Insert text at a line | `retrieve` → splice → `stash` |
| `delete` | Remove a file | `delete(path)` |
| `rename` | Move a file | `retrieve(old)` → `stash(new)` → `delete(old)` |

The backend is the storage; the model never sees attune internals.

## Mapping decision: working-memory KV, not long-term

The Memory tool is **file/path-addressed with in-place text edits**
(`str_replace`, `insert`). That is a key/value document model, not a
semantic-search model. So:

- **v1 stores memory files as working-memory KV** keyed by path:
  `stash(path, text)` / `retrieve(path)` / `keys()` / `delete(path)`.
  This is exactly the surface PR #667 just made correct against AMS
  0.14.0 (`update_working_memory_data(merge_strategy="merge")` so
  multi-key writes don't clobber).
- **Long-term semantic recall stays on `/recall`** (the
  `remember`/`search` surface). The Memory tool is not the place to
  expose embeddings — keep the two interfaces honest about what they
  do (R-non-goal).

> Consequence for R5 (shared store): the Memory-tool view and
> SessionStart recall share the *backend and namespace*, but the
> Memory tool reads/writes the KV tier while SessionStart recall
> reads the long-term tier. v1 keeps them in one namespace so an
> operator can see both; a later phase can add an opt-in "promote a
> memory file to a searchable finding" bridge if wanted. Flag this
> as a design question for the morning.

## Component shape

```
attune_redis/ (or attune.memory)
  memory_tool.py
    class AttuneMemoryTool(BetaAbstractMemoryTool):
        def __init__(self, backend: MemoryBackend, *, root="/memories",
                     user_id: str | None = None): ...
        # six command handlers, each:
        #   1. _validate_path(cmd.path)         # traversal guard
        #   2. _redact(content)                 # session-redaction gate
        #   3. backend.<op>(...)                # stash/retrieve/keys/delete
        #   4. return the Anthropic-shaped result / raise -> is_error
```

- `backend` is attune's `MemoryBackend` (file by default, AMS when
  configured) — **R2**, no new storage.
- `_validate_path` reuses `attune.security.path_validation` semantics
  adapted to the virtual `/memories` root — **R4**.
- `_redact` reuses the session-redaction gate so secrets never
  persist — **R4**.
- `user_id` namespaces the key prefix when present — **R4**.

## Why client-side Memory tool, not Managed-Agents memory stores

Anthropic has **two** memory surfaces:

1. **Memory tool** (`memory_20250818`) — client-side, you own the
   backend. Works on the **first-party API and the subscription/Agent
   SDK path** attune already targets. ← **this spec**.
2. **Managed Agents memory stores** — server-side, Anthropic-hosted,
   requires the Managed Agents product (API-keyed, hosted
   orchestration).

attune is subscription-first and self-hosts its memory on Redis, so
the **client-side Memory tool is the correct alignment surface** —
it lets attune *be the backend* rather than hand memory to Anthropic's
hosted store. (Confirmed against the `claude-api` skill reference.)

## Testing (R6)

- **Mocked unit tests:** all six commands against a mock backend —
  path validation, redaction, read-modify-write correctness for
  `str_replace`/`insert`, `rename` = copy+delete, `view` of dir vs
  file.
- **Live integration test:** drive the adapter through the SDK
  `tool_runner` (or call the handlers directly) against AMS 0.14.0;
  write via Memory tool → read back via `backend.retrieve`; auto-skip
  without AMS (mirrors `test_integration.py`).
- **Drift guard:** assert the adapter implements every abstract
  method of `BetaAbstractMemoryTool` (so an SDK bump that adds a
  command fails loudly).

## Open questions for the morning

1. **Home:** `attune_redis/memory_tool.py` (rides the Redis package)
   vs `attune.memory.memory_tool` (backend-agnostic, file default).
   Leaning `attune.memory` so the file backend works with zero infra
   and AMS is the upgrade.
2. **Shared-namespace vs separate:** KV tier (Memory tool) and
   long-term tier (recall) in one namespace (operator sees both) vs
   separate (cleaner isolation). v1 proposal: one namespace,
   document the tier split.
3. **Promote-to-searchable bridge:** ship in v1 or defer? Proposal:
   defer — keep v1 honest about file-vs-semantic.


## Phase 2 — surfacing (decided 2026-06-08)

Phase 1 shipped the bridge but left it unreachable (exported nowhere,
zero consumers). Phase 2 makes it runnable.

**Shipped: `attune memory-agent "<prompt>"` (option ①).** A single-shot
agent on the **raw `anthropic` SDK** `client.beta.messages.tool_runner`,
with `make_memory_tool(...)` attached and the `context-management-2025-06-27`
beta. Claude reads/writes `/memories` persisted on attune's backend (file
by default, Redis AMS when configured). This is the concrete, runnable
form of the dual-vendor claim. Requires `ANTHROPIC_API_KEY` — the Memory
tool is raw-API-only.

**Re-scoped out: wiring the bridge into SDK-native workflows (option ③).**
Verified against `claude_agent_sdk` 0.1.63: `ClaudeAgentOptions.tools` is a
tool-name **allowlist** (`list[str] | ToolsPreset`), `betas` does **not**
include `memory_20250818`, and there is **no field** to pass a
`BetaAbstractMemoryTool`. Custom tools reach the agent SDK only via
`mcp_servers` / `create_sdk_mcp_server`. So the bridge composes with the
raw `anthropic` SDK only. The *goal* behind ③ (workflows with persistent
Redis-backed memory) is reachable via a separate **SDK-MCP** tool — a
different surface that overlaps the existing `memory_store`/`retrieve` MCP
tools, so it is deferred pending a use case those don't already cover.
