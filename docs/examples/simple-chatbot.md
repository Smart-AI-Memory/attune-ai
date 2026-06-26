---
description: "Example: Code Review Assistant with Memory — a beginner-to-intermediate walkthrough combining working (short-term) and persistent (long-term) memory."
---

# Example: Code Review Assistant with Memory

**Difficulty**: Beginner → Intermediate

**Time**: 15 minutes

**Core Features**: Working Memory (Redis-backed), Persistent
Memory, the `EmpathyLLM` chat loop

---

## Overview

Build a **Code Review Assistant** that demonstrates the two
kinds of memory that make Attune AI powerful:

| Memory Type | Backing store | Purpose | Example |
|-------------|---------------|---------|---------|
| **Working** | Redis (file-backed fallback) | Active session context | "Which files have I reviewed in this PR?" |
| **Persistent** | Pattern store | Long-lived patterns | "What issues has this codebase had historically?" |

**What you'll learn**:

- **Working memory**: track state within a session with `stash`
  and `retrieve`
- **Persistent memory**: remember patterns across sessions with
  `persist_pattern` and `search_patterns`
- **Combined power**: connect session context with historical
  patterns to anticipate issues

---

## Why Two Kinds of Memory?

```text
┌─────────────────────────────────────────────────────────────┐
│                    CODE REVIEW SESSION                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WORKING MEMORY (Redis)             PERSISTENT MEMORY       │
│  ─────────────────────────          ────────────────        │
│  • Files reviewed this session      • Historical bugs       │
│  • Issues found so far              • Developer patterns    │
│  • Current PR context               • Codebase weak spots   │
│                                                             │
│  Expires: End of session            Persists: Across runs   │
│                                                             │
│          ↓                                   ↓              │
│          └─────────────┬─────────────────────┘              │
│                        ▼                                    │
│              ANTICIPATORY INSIGHT                            │
│         "This auth change looks similar to the              │
│          bug we found in PR #98. Check line 42."            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Install with full extras (includes Redis support)
pip install "attune-ai[full]"

# Start Redis (optional — working memory falls back to disk)
docker run -d -p 6379:6379 redis:alpine
```

---

## Part 1: The Chat Loop (`EmpathyLLM`)

`EmpathyLLM` is the conversational engine. Call `interact`
with a `user_id`, the `user_input`, and optional `context`. It
returns a dictionary; the assistant's reply is under `content`.

```python
from attune.llm import EmpathyLLM

# Create the code review assistant
reviewer = EmpathyLLM(user_id="code_reviewer")

# Review a file
result = reviewer.interact(
    user_id="code_reviewer",
    user_input="Review src/auth/login.py for security issues",
    context={"file": "src/auth/login.py"},
)

print("=== File Review ===")
print(result["content"])
```

**Key point**: `interact` returns a dict. Read `result["content"]`
for the reply and `result["metadata"]` for details about the run.

---

## Part 2: Working Memory (Redis-backed)

Working memory tracks state **within a session**. It uses a
file-backed session as primary storage, with optional Redis for
real-time features. Store with `stash`, read back with
`retrieve`.

```python
from attune.memory import UnifiedMemory
from attune import AccessTier

# Working memory keyed to this reviewer
memory = UnifiedMemory(
    user_id="code_reviewer",
    access_tier=AccessTier.CONTRIBUTOR,
)

session_id = "pr-142-review"

# Record progress as you review
memory.stash(
    f"session:{session_id}",
    {
        "files_reviewed": ["src/auth/login.py"],
        "issues_found": 1,
    },
)

# Read it back later in the same session
state = memory.retrieve(f"session:{session_id}")
print("=== Session State ===")
print(f"Files reviewed: {state['files_reviewed']}")
print(f"Issues found: {state['issues_found']}")
```

**Key point**: Working memory lets the reviewer remember what it
just reviewed and track progress across turns of one session.

---

## Part 3: Persistent Memory (Patterns)

Persistent memory stores patterns **across sessions**. Record a
finding with `persist_pattern`; surface related history later
with `search_patterns`.

```python
from attune.memory import UnifiedMemory
from attune import AccessTier

memory = UnifiedMemory(
    user_id="code_reviewer",
    access_tier=AccessTier.CONTRIBUTOR,
)

# First review session: record what happened
memory.persist_pattern(
    content="SQL injection vulnerability in login query (line 42)",
    pattern_type="security_issue",
    metadata={
        "file": "src/auth/login.py",
        "pr_number": 98,
        "severity": "high",
    },
)

# ... weeks later, a new review touches the same module ...

# Surface related history
history = memory.search_patterns(
    query="auth",
    pattern_type="security_issue",
    limit=5,
)

print("=== Auth Module History ===")
for pattern in history:
    print(f"  {pattern['content']}")
```

**Key point**: Persistent memory lets the reviewer learn from
past reviews, remember where bugs occurred, and warn about
similar patterns in new code.

---

## Part 4: Combining Both Memories

The real power comes from **combining** working and persistent
memory. One `UnifiedMemory` instance exposes both: `stash`/
`retrieve` for the live session, `persist_pattern`/
`search_patterns` for history.

```python
from attune.llm import EmpathyLLM
from attune.memory import UnifiedMemory
from attune import AccessTier

reviewer = EmpathyLLM(user_id="code_reviewer")
memory = UnifiedMemory(
    user_id="code_reviewer",
    access_tier=AccessTier.CONTRIBUTOR,
)

session_id = "pr-200-review"
files = ["src/payments/stripe.py", "src/payments/webhooks.py"]

# Pull historical context BEFORE reviewing
history = memory.search_patterns(query="payments", limit=5)
print("=== Historical Context ===")
for pattern in history:
    print(f"  {pattern['content']}")

# Track this session's plan in working memory
memory.stash(
    f"session:{session_id}",
    {"files_to_review": files, "issues_found": 0},
)

# Ask the assistant to review, with both contexts available
result = reviewer.interact(
    user_id="code_reviewer",
    user_input="Review PR #200: Payment processing update",
    context={"session_id": session_id, "files": files},
)
print("=== Combined Memory Review ===")
print(result["content"])

# Record a finding in BOTH memories
memory.persist_pattern(
    content="API key exposed in error message (line 78)",
    pattern_type="security_issue",
    metadata={"file": "src/payments/stripe.py", "line": 78},
)
memory.stash(
    f"session:{session_id}",
    {"files_to_review": files, "issues_found": 1},
)
```

---

## Part 5: Complete Working Example

Save as `code_review_assistant.py`:

```python
#!/usr/bin/env python3
"""Code Review Assistant — working and persistent memory.

Usage:
    python code_review_assistant.py <pr_number> <file1> [file2] ...
    python code_review_assistant.py 142 src/auth/login.py
"""

import sys

from attune.llm import EmpathyLLM
from attune.memory import UnifiedMemory
from attune import AccessTier


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python code_review_assistant.py <pr_number> <file1> ...")
        sys.exit(1)

    pr_number = sys.argv[1]
    files = sys.argv[2:]

    print("Code Review Assistant")
    print("=" * 50)
    print(f"PR: #{pr_number}")
    print(f"Files: {', '.join(files)}")
    print()

    reviewer = EmpathyLLM(user_id="code_reviewer")
    memory = UnifiedMemory(
        user_id="code_reviewer",
        access_tier=AccessTier.CONTRIBUTOR,
    )
    session_id = f"pr-{pr_number}-review"

    # Surface any historical patterns for these files
    history = memory.search_patterns(query="security", limit=5)
    if history:
        print("Historical issues:")
        for pattern in history:
            print(f"  • {pattern['content']}")
        print()

    print("Commands: 'review <file>', 'issue <description>', 'done'")
    print()

    issues_found = 0
    files_reviewed: list[str] = []

    while True:
        try:
            user_input = input("review> ").strip()
            if not user_input:
                continue

            if user_input.lower() == "done":
                memory.stash(
                    f"session:{session_id}",
                    {
                        "files_reviewed": files_reviewed,
                        "issues_found": issues_found,
                    },
                )
                print(f"\nReview complete! Issues found: {issues_found}")
                break

            if user_input.lower().startswith("issue "):
                description = user_input[len("issue "):]
                memory.persist_pattern(
                    content=description,
                    pattern_type="security_issue",
                    metadata={"pr_number": pr_number},
                )
                issues_found += 1
                print(f"Issue recorded ({issues_found} so far).")
                continue

            result = reviewer.interact(
                user_id="code_reviewer",
                user_input=user_input,
                context={"session_id": session_id, "files": files},
            )
            files_reviewed.append(user_input)
            print()
            print(result["content"])
            print()

        except KeyboardInterrupt:
            print("\nReview cancelled (not saved)")
            break


if __name__ == "__main__":
    main()
```

---

## Memory Value Summary

| Feature | Working (Redis) | Persistent (Patterns) |
|---------|-----------------|-----------------------|
| **What it stores** | Current session state | Historical patterns |
| **Lifetime** | Session duration | Across runs |
| **API** | `stash` / `retrieve` | `persist_pattern` / `search_patterns` |
| **Use case** | "What have I reviewed so far?" | "What bugs has this code had?" |
| **Example** | PR #142 review progress | "auth/ has had 5 security bugs" |

**The magic**: When combined, the assistant can say:

> "You're reviewing auth code (working context) and this module
> has had 3 security issues in the past (historical pattern).
> Line 52 looks similar to the bug we found in PR #98. Want me
> to flag it?"

---

## Next Steps

1. **Add GitHub integration** — auto-post review comments.
2. **Team patterns** — share persistent memory across a team.
3. **Custom rules** — add domain-specific review patterns.
4. **Metrics dashboard** — track review effectiveness over time.

---

## Troubleshooting

**Redis not connected**

Working memory falls back to a file-backed session
automatically, so reviews still work without Redis. To enable
real-time Redis features, start a local instance:

```bash
docker run -d -p 6379:6379 redis:alpine
```

**No historical patterns showing**

Run a few review sessions first so `persist_pattern` has
something to surface. Then `search_patterns` will return them.

---

**Need help?** See the API Reference.
