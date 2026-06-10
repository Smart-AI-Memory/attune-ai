---
type: quickstart
name: plugin-quickstart
feature: plugin
depth: quickstart
generated_at: 2026-06-10T07:07:04.681583+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Quickstart: Install the attune-ai plugin

Add attune-ai skills to Claude Code with one command.

```
claude plugin marketplace add Smart-AI-Memory/attune-ai && claude plugin install attune-ai@attune-ai
```

**Result:** 17 skills available via slash commands in Claude Code.

## Step 1: Verify the plugin loaded

Open a Claude Code session and run `/attune`. The hub skill responds with
guided discovery — if it answers, the plugin's skills and hooks are active.

## Step 2: Read your session orientation

Start a new session in a project directory. The plugin's SessionStart hooks
print a **Session orientation** block automatically: your worktree and
branch, the last commit, and any in-flight specs found under `docs/specs/`.

**Result:** You know where you are and what work is open before typing
anything.

## Step 3: Check in-flight specs

The orientation block lists each in-flight spec with its phase and status
(for example `docs/specs/my-feature — design approved`). To browse them
directly, look in `docs/specs/<slug>/` — each spec keeps its
`requirements.md`, `design.md`, and `tasks.md` there.

**Result:** An empty list means no in-flight specs exist yet — start one
with `/spec`.

## Step 4: Resume interrupted work

When you return after a break, the plugin builds a resume prompt from your
most recent in-flight spec and the current git state, so a fresh session
can pick up exactly where the last one stopped.

**Result:** The formatted resume prompt Claude Code displays when you
return to an interrupted session.

**Next:** Type `/attune` in any session to route a request to the right
workflow, or `/help` for the full command reference.
