---
type: task
name: use-memory-and-context
tags: [memory, skill, task]
source: plugin/skills/memory-and-context/SKILL.md
---

# How to Use Memory and Context

## Quick start

The fastest way: just say what you want to remember.

```
remember that our API returns 422 for validation errors, not 400
```

Or recall something from a previous session:

```
what did we decide about error codes?
```

That's it. The skill stores and retrieves your notes
across sessions using your Claude subscription.

## Storing a memory

Tell the skill what to remember in plain language:

```
remember that we use structlog, not stdlib logging
```

```
store a note: the auth module was refactored on March 15
```

```
/remember store "deployment requires VPN access"
```

You'll be asked to confirm the key and content before
it's saved. If you want to tag the memory for easier
searching later, just mention it:

```
remember (convention): always use UTC for timestamps
```

## Recalling context

Ask for a specific memory by describing what you need:

```
what's our logging convention?
```

```
recall the note about deployment
```

```
/remember retrieve auth-refactor-date
```

If the skill finds an exact key match, it returns
that memory. If not, it searches across all your stored
memories for the closest match.

## Searching memory

When you're not sure of the exact key, search:

```
search my memories for anything about testing
```

```
what do I have stored about the API?
```

```
/remember search "database migration"
```

Search looks across keys, values, and tags. Results
are ranked by relevance.

## Forgetting a memory

Remove something you no longer need:

```
forget the note about old deployment process
```

```
/remember forget old-deploy-steps
```

You'll be asked to confirm before deletion. This is
permanent — the memory is removed from all storage.

## Temporary session context

For state that only matters right now (not across
sessions), use context:

```
set context: I'm working on the payment module
```

```
what's my current working context?
```

Context is discarded when the session ends. Use it
for tracking what you're doing right now, not for
things you'll need later.

## Example workflow

A typical pattern across two sessions:

**Session 1** — you discover something:

```
> remember that redis connections need explicit close()
>   or they leak file descriptors in tests
Stored: redis-connection-cleanup
  "redis connections need explicit close() or they
   leak file descriptors in tests"
```

**Session 2** — you need that knowledge:

```
> I'm seeing file descriptor leaks in my test suite.
>   Do I have any notes about that?
Found: redis-connection-cleanup
  "redis connections need explicit close() or they
   leak file descriptors in tests"
```

## Want to learn more?

- Say **"tell me more"** for the full reference
  with all operations, storage details, and search syntax
- Say **"what is memory and context?"** to go back
  to the overview
- Say **"how do I run a security audit?"** for
  vulnerability scanning
