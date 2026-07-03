# Which memory is which

Attune ships several memory surfaces, and sessions often run beside a
host agent (Claude Code) that has its own. This page is the
orientation map: what each ring stores, where it lives, and which
command reaches it.

## The rings at a glance

| Ring | What it holds | Where it lives | Reach it via |
|------|---------------|----------------|--------------|
| Personal memory | Curated topics you capture (decisions, patterns, troubleshooting, reference) | `~/.attune/memory/<topic>/<kind>.md` | `attune memory capture` / `recall`, `personal_memory_*` MCP tools |
| Memory graph | Structured findings from workflows (patterns, bugs, context nodes + edges) | JSON graph on disk, per project | `memory_store` / `memory_search` MCP tools |
| Session memory (Redis/AMS) | Per-session working keys plus semantic long-term records | Redis Agent Memory Server, `attune` namespace | `redis_memory_*` MCP tools (needs the `[redis]` extra) |
| Host agent memory | Whatever your host agent (e.g. Claude Code) persists for itself | The host's own files (e.g. `~/.claude/.../memory/`) | The host reads it; attune does not |

## Which one do I want?

- **"Remember this decision for future sessions"** — personal memory.
  It is plain markdown you can read and edit; recall is keyword
  retrieval over the polished files.

  ```bash
  attune memory capture auth-architecture \
      "JWT over sessions - stateless scaling" --kind decision
  attune memory recall "why did we pick JWT"
  ```

- **"Store a structured finding a workflow produced"** — the memory
  graph. Workflows write typed nodes (bug, pattern, context) and link
  them; search is graph-aware.

- **"Share state across agents in this session, or search past
  sessions semantically"** — Redis/AMS session memory. Working-memory
  keys are session-scoped; long-term records are vector-searchable
  across sessions. Requires Redis and
  `pip install 'attune-ai[redis]'`.

- **"Why does my host agent already know X?"** — that is the host's
  own memory, not attune's. The two do not share storage. If a fact
  should be durable *inside attune*, capture it explicitly.

## Common confusions

**Personal memory vs. host memory.** Both persist across sessions and
both are markdown, so they blur together. The test: did you (or the
agent) run `attune memory capture`? Then it is attune's, portable to
any host. Did the host save it on its own? Then attune cannot recall
it.

**Session memory is two tiers.** `redis_memory_store` /
`redis_memory_retrieve` are exact key lookups in the current
session's working memory. `redis_memory_search` is semantic search
over long-term records, including other sessions'. Storing a key does
not make it semantically searchable — promotion to long-term is a
separate step (`redis_memory_promote`).

**Recall is keyword, not magic.** Personal-memory recall ranks by
word overlap with the polished files. Query with the words the memory
would contain ("redis connection timeout"), not vague references
("that fix from Tuesday").

## Health checks

```bash
attune memory topics        # personal memory reachable + populated?
```

Use the `redis_health_check` MCP tool for the Redis/AMS ring. If it
reports Redis support missing, install the extra:
`pip install 'attune-ai[redis]'`.

Every release is gated by `scripts/release_recall_gate.py`, which
installs the built wheel into a clean environment and proves the
capture-to-recall round-trip before publishing.
