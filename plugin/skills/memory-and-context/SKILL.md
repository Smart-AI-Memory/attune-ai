---
name: memory-and-context
description: "Store, retrieve, search, and manage persistent memory across sessions. Triggers on: store memory, save this, retrieve, forget, manage memory, context, pattern."
argument-hint: "<operation: store|retrieve|search|forget>"
disable-model-invocation: true
---

# Memory and Context

**IMPORTANT: Start your response with a context preamble.**

Call `help_lookup(topic="memory", mode="preamble")` and
display the returned `preamble` text as a blockquote. Then
tell the user they can say "tell me more" for a step-by-step
guide, or answer the scoping questions below to proceed.

If the MCP call fails, fall back to:

> **Memory and Context** — Stores and retrieves persistent context across sessions — notes, preferences, project state.

## Scoping

Before running, ask:

1. **Operation**: "What do you need? Store, retrieve,
   search, or forget?"
2. **Key/query**: "What key or search term?"
3. **Classification** (store only): "PUBLIC, INTERNAL,
   or SENSITIVE?"

## Execution

### Shared command workspace (preferred)

Open adapter `memory-and-context` with the selected operation and scoped
arguments. Present its widget or returned Markdown and collect its bound
action before calling the existing memory tool. Store and forget are external
writes and require explicit confirmation; retrieve and search remain
read-only. Publish the exact tool response as `operation_result`.

After a successful store or forget, follow the workspace's returned
`memory_retrieve` verification request and publish it as
`verification_result`. Store succeeds only when the same value and
classification are retrieved; forget succeeds only when the post-delete read
misses. Never render stored values—especially SENSITIVE values—in the
workspace. A failed backend call must say “did not complete.” Preserve these
decisions and verification receipts in compact text when the shared tools are
unavailable.

Based on the user's answer, call the appropriate MCP
tool:

- Store: `memory_store(key, value, classification)`
- Retrieve: `memory_retrieve(key)`
- Search: `memory_search(query, pattern_type)`
- Forget: `memory_forget(key, scope)`

attune-ai's memory system sits ABOVE Anthropic's native
memory features. It provides security-classified storage,
cross-agent pattern sharing, and a structured pattern
lifecycle that native memory
does not offer. Use the decision table below to determine
which system to use for a given task.

## When to Use This Skill

### Layer Positioning

| Use Case | Use Anthropic Native | Use attune-ai |
|----------|----------------------|---------------|
| "Remember my code style" | CLAUDE.md | -- |
| "What did we do last session?" | Session Memory | -- |
| "Store this pattern for reuse across agents" | -- | memory_store (shared library) |
| "Classify this finding as SENSITIVE" | -- | Security pipeline |
| "Coordinate memory across 3 parallel agents" | -- | Redis pub/sub |
| "Promote this pattern after 5 successful uses" | -- | Pattern lifecycle |
| "Track what this project uses" | Auto Memory | -- |

The rule is simple: if Anthropic's native memory handles
it, use that. If you need classification, cross-agent
sharing, or pattern lifecycle management, use attune-ai.

## Memory Operations

MCP tools for memory management.

### memory_store

Store structured knowledge in attune-ai memory.

**Parameters:**

- **key** (required): Unique identifier for the
  stored data.
- **value** (required): Content to store. Can be a
  string, dict, or structured object.
- **classification** (optional): Security
  classification. One of `PUBLIC` (default),
  `INTERNAL`, or `SENSITIVE`. See Security
  Classification below.
- **pattern_type** (optional): Category string for
  pattern matching and lifecycle management.

**When to use:** Cross-agent patterns,
security-classified data, structured knowledge that
must persist beyond a single session or be shared
across agents.

**When NOT to use:** Simple preferences belong in
CLAUDE.md. Conversation history is handled by native
Session Memory.

**Example:**

```python
memory_store(
    key="python-import-ordering",
    value="stdlib first, then third-party, then local. Enforce with isort.",
    classification="PUBLIC",
    pattern_type="coding-convention"
)
```

### memory_retrieve

Retrieve data by key or pattern ID.

**Parameters:**

- **key** (required): The key or pattern_id to retrieve.

**Returns:** The stored value, or null if not found.

### memory_search

Search memory for patterns matching a query.

**Parameters:**

- **query** (required): Search string to match
  against stored keys and values.
- **pattern_type** (optional): Filter results to a
  specific pattern type category.

**Returns:** A list of matching memory entries,
ranked by relevance.

### memory_forget

Remove data from memory.

**Parameters:**

- **key** (required): The key or pattern_id to remove.
- **scope** (optional): Which storage layer to remove
  from. One of:
  - `"session"` -- Short-term session storage only.
  - `"persistent"` -- Long-term persistent storage only.
  - `"all"` -- Both layers. This is the default.

## Context Operations

Session-scoped key-value store for transient state.
Context values are discarded when the session ends.
Use these for temporary coordination data that does
not need to persist.

### context_get

Get a session context value.

**Parameters:**

- **key** (required): The context key to retrieve.

**Returns:** The stored value, or null if not set.

### context_set

Set a session context value.

**Parameters:**

- **key** (required): The context key to set.
- **value** (required): The value to store.

**Example:**

```python
context_set(key="current_review_file", value="src/attune/workflows/base.py")
file = context_get(key="current_review_file")
```

## Security Classification

When storing data with `memory_store`, choose the
appropriate classification level.

- **PUBLIC**: Safe to share across agents and sessions.
  No special handling. This is the default.
- **INTERNAL**: Limited to current project or team
  scope. Not shared externally.
- **SENSITIVE**: PII is scrubbed before storage. Data
  is encrypted with AES-256-GCM. All access is audit
  logged.

Choose the minimum classification that meets your
needs. Over-classifying creates unnecessary overhead.

**Example -- storing a security finding:**

```python
memory_store(
    key="vuln-2026-02-cve-1234",
    value={"severity": "HIGH", "file": "src/auth.py", "line": 42, "description": "Hardcoded credential"},
    classification="SENSITIVE",
    pattern_type="security-finding"
)
```

## Pattern Lifecycle

Patterns progress through three stages:

1. **Staged**: Initial storage, awaiting validation.
   Created by any `memory_store` call with a
   `pattern_type`.
2. **Validated**: Confirmed useful through repeated
   access (automatic) or explicit promotion. The system
   tracks access frequency and confidence scores.
3. **Promoted**: Available in the shared library for
   cross-agent access. Other agents and sessions can
   discover and use promoted patterns.

The system handles lifecycle transitions automatically
based on confidence thresholds and usage frequency. You
do not need to manually promote patterns in most cases.

**Creating a staged pattern:**

```python
memory_store(
    key="error-handling-api-calls",
    value="Always wrap external API calls in try/except with specific exceptions. Log before re-raising.",
    pattern_type="coding-convention"
)
```

This pattern starts as Staged. After it is retrieved
or matched 5+ times with positive outcomes, the system
promotes it to Validated, then eventually to Promoted.

## Redis Upgrade Path

By default, attune-ai uses in-memory storage. All
features described in this skill work without Redis.

**What Redis adds:**

- Multi-agent coordination via pub/sub channels.
- Sub-millisecond lookups for large memory stores.
- Shared state across sessions and agents running in
  parallel.
- Pattern persistence with configurable TTL.

**Upgrade:**

```bash
# Redis client libraries ship with attune-ai core — nothing extra to
# install; you only need a running Redis / Agent Memory Server.
pip install attune-ai
```

Zero configuration needed -- connects to
`localhost:6379` by default. For custom configuration,
set the `ATTUNE_REDIS_URL` environment variable:

```bash
export ATTUNE_REDIS_URL="redis://custom-host:6380/0"
```

If Redis disconnects mid-session, the system falls
back to in-memory storage gracefully. No data loss
occurs for the current session; cross-agent
coordination pauses until reconnection.

## Anti-Patterns

- DO NOT use `memory_store` for simple preferences --
  use CLAUDE.md instead.
- DO NOT push Redis on developers who do not need
  multi-agent coordination.
- DO NOT store conversation history -- native Session
  Memory handles this.
- DO NOT over-classify data as SENSITIVE -- use PUBLIC
  unless the data genuinely contains PII or
  credentials.
- DO NOT bypass the pattern lifecycle by manually
  marking patterns as Promoted -- let the confidence
  system validate them.
