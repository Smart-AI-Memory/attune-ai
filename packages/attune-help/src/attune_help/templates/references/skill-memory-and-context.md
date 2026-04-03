---
type: reference
subtype: procedural
name: skill-memory-and-context
category: skill
tags: [memory, skill, plugin, reference]
source: plugin/skills/memory-and-context/SKILL.md
---

# Memory and Context Reference

Complete reference for the memory and context skill —
every operation, storage behavior, search syntax, and
the distinction between persistent memory and session
context.

## Invocation

```
/remember <operation>
```

Or natural language:

```
remember that we use black with 100 char lines
what did I store about the auth module?
search my memories for deployment notes
forget the old migration steps
```

## All operations

Everything runs on your Claude subscription — no API
key or additional cost.

| Operation | What you type | What happens | Persists? |
|-----------|--------------|-------------|-----------|
| **Store** | "remember that X" | Saves a key-value pair | Yes |
| **Retrieve** | "recall the note about X" | Returns exact match by key | -- |
| **Search** | "search memories for X" | Full-text search across all memories | -- |
| **Forget** | "forget the note about X" | Deletes the memory permanently | -- |
| **Context set** | "set context: working on auth" | Stores session-only state | No (session) |
| **Context get** | "what's my current context?" | Returns session state | -- |

## Storing memories

When you store a memory, you provide a value and the
skill assigns (or you specify) a key:

```
remember (convention): imports are sorted with isort
```

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| **key** | Yes | Short identifier for recall | `import-ordering` |
| **value** | Yes | The content to store | `"stdlib first, then third-party, then local"` |
| **classification** | No | Security level | `PUBLIC` (default), `INTERNAL`, `SENSITIVE` |
| **pattern_type** | No | Category tag for filtering | `coding-convention`, `architecture-decision` |

The skill asks you to confirm the key and value before
saving. If you don't specify a key, one is generated
from the content.

### Security classification

Choose based on content sensitivity:

| Level | When to use | What happens |
|-------|-------------|-------------|
| **PUBLIC** | Most memories — conventions, patterns, notes | Stored normally (default) |
| **INTERNAL** | Project-scoped data not for external sharing | Scoped to project |
| **SENSITIVE** | Contains PII, credentials, or security findings | PII scrubbed, encrypted at rest, access logged |

Use PUBLIC unless the content genuinely contains
sensitive data. Over-classifying adds overhead with
no benefit.

## Retrieving memories

Retrieve by exact key or by describing what you need:

```
recall import-ordering
```

```
what's our convention for imports?
```

If the exact key matches, the memory is returned
immediately. If not, the skill falls back to search.

## Searching memories

Search scans keys, values, and tags:

```
search memories for anything about testing
```

```
/remember search "database"
```

| Search feature | How it works |
|----------------|-------------|
| **Full-text** | Matches against keys and values |
| **Tag filter** | Filter by pattern_type if provided |
| **Ranking** | Results ordered by relevance |

Results include the key, a snippet of the value, and
the classification level.

## Forgetting memories

Remove a memory permanently:

```
forget old-deploy-steps
```

| Scope | What it removes |
|-------|----------------|
| **session** | Session storage only (rare) |
| **persistent** | Long-term storage only |
| **all** | Both layers (default) |

You'll be asked to confirm before deletion.

## Session context

Context is temporary state for the current session.
It is discarded when the session ends.

```
set context: reviewing PR #47 for auth changes
```

```
what's my current context?
```

| Use case | Memory or context? |
|----------|--------------------|
| "I'm working on the payment module" | Context |
| "We decided to use Stripe over Square" | Memory |
| "Current PR is #47" | Context |
| "The deploy process requires VPN" | Memory |

**Rule of thumb:** if you'll need it tomorrow, store
it as memory. If you only need it for this session,
use context.

## Storage details

By default, memory is stored locally on disk. No
external services required.

| Backend | Storage location | Upgrade path |
|---------|-----------------|-------------|
| **Default** | `~/.attune/memory/` | Works out of the box |
| **Redis** | `localhost:6379` | `pip install 'attune-ai[memory]'` |

Redis adds sub-millisecond lookups for large memory
stores and shared state across parallel sessions. If
Redis disconnects, the system falls back to local
storage gracefully.

## Pattern lifecycle

Memories stored with a `pattern_type` enter the
pattern lifecycle:

| Stage | How it gets there | Visibility |
|-------|-------------------|-----------|
| **Staged** | Any `store` with a pattern_type | This session and agent |
| **Validated** | Accessed 5+ times with positive outcomes | Broader visibility |
| **Promoted** | High confidence, consistent use | Available across agents |

The system handles transitions automatically. You
don't need to manually promote patterns.

## Memory vs CLAUDE.md

| Content | Where to put it |
|---------|----------------|
| Permanent project rules (always apply) | CLAUDE.md |
| Things you discovered while working | Memory |
| Architecture decisions with rationale | Memory |
| Code style preferences (always apply) | CLAUDE.md |
| Debugging patterns for future reference | Memory |
| "I'm in the middle of X" | Context |
| Conversation history | Neither (handled by Claude natively) |

## Want to learn more?

- Say **"what is memory and context?"** to go back
  to the overview
- Say **"how do I use memory?"** for the step-by-step
  guide
- Say **"review my code"** for code quality tools
- Say **"tell me about security audit"** for
  vulnerability scanning
