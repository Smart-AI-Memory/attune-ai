---
feature: hooks
depth: concept
generated_at: 2026-05-31T14:15:05.550139+00:00
source_hash: 42b6f3d8928cb9d9f896c40c595715ed3473820bfdc5f12e14e2889aea7c4d0a
status: generated
---

# Hooks

## How it works

Hook system — pre/post-tool events, webhooks, and hook executor.

The main building blocks are:

- **`HookEvent`** — Hook event types matching Claude Code lifecycle.
- **`HookType`** — Type of hook action.
- **`HookDefinition`** — Definition of a single hook action.
- **`HookMatcher`** — Matcher for determining when a hook should fire.
- **`HookRule`** — A complete hook rule with matcher and actions.

Under the hood, this feature spans 15 source
files covering:

- Hook Configuration Models
- Hook Executor
- Hook Registry

## What connects to it

This feature relates to: hooks, webhooks, events, automation.

Other parts of the codebase interact with
hooks through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `HookEvent` | Hook event types matching Claude Code lifecycle. | `src/attune/hooks/config.py` |
| `HookType` | Type of hook action. | `src/attune/hooks/config.py` |
| `HookDefinition` | Definition of a single hook action. | `src/attune/hooks/config.py` |
| `HookMatcher` | Matcher for determining when a hook should fire. | `src/attune/hooks/config.py` |
| `HookRule` | A complete hook rule with matcher and actions. | `src/attune/hooks/config.py` |
