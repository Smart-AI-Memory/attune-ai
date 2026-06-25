# claude-agent-sdk 0.2.x Migration — Requirements

**Status:** complete (2026-06-16) — 0.2.x adopted (#917, ships 8.7.0);
pyproject pins `claude-agent-sdk>=0.2.101,<0.3.0`, lockfile at 0.2.105.
Reconciled from stale "approved" and archived 2026-06-24.
**Owner:** Patrick + agent
**Created:** 2026-06-16

---

## Context

`attune-ai` pins `claude-agent-sdk>=0.1.60,<0.2.82` with the
lockfile at `0.1.63`. The `<0.2.82` ceiling is a deliberate guard,
documented inline in `pyproject.toml`:

> "Ceiling `<0.2.82` holds back the 0.2.x breaking changes (MCP
> background connection, TodoWrite->Task tools) so a routine
> `uv lock --upgrade` can't land them silently ... Remove the cap
> deliberately when adopting 0.2.x."

This spec is that deliberate adoption.

The SDK is used in 24 `src/` files, funneled through one seam,
`src/attune/workflows/agent_sdk_adapter.py`, plus 18
`ClaudeAgentOptions` construction sites. Recon (2026-06-16)
established the real blast radius:

- attune is **already** on the `claude_agent_sdk` package — the
  `claude_code_sdk` -> `claude_agent_sdk` /
  `ClaudeCodeOptions` -> `ClaudeAgentOptions` rename is done.
- **`TodoWrite` is not referenced** anywhere in `src/` — the
  TodoWrite->Task tools rename does not affect attune.
- The adapter already version-guards some behavior
  (`_cli_supports_task_budget`, subagent transcripts, error
  classification).

So the migration is moderate and bounded: the work is the
**behavioral** breaking changes, not symbol renames.

---

## Problem

The deliberate `<0.2.82` cap blocks adopting the 0.2.x line and
accumulates upgrade debt. Lifting it safely requires handling the
0.2.x behavioral changes and proving the suite still passes against
an actual 0.2.x install — not a constraint-only bump that leaves the
lock at `0.1.63` (which validates nothing).

---

## Goals

- Move the pinned and locked `claude-agent-sdk` onto the 0.2.x line
  (lock at `0.2.101`).
- Handle the 0.2.x behavioral breaking changes so every workflow,
  MCP-tool path, subagent-transcript path, and budget/pacing control
  behaves as before.
- Keep the full test suite and the budget-capped `integration-auth`
  tests green against 0.2.x.
- Replace the pyproject pin with a new deliberate cap and update the
  inline comment to document the adoption.

## Non-goals

- Adopting 0.3.x (the new cap deliberately guards against it).
- Refactoring the `agent_sdk_adapter.py` seam beyond what the
  migration requires.
- Adopting new 0.2.x features (session store, effort levels,
  structured outputs) — those are follow-ups, not this migration.

---

## Decisions

- **d1 (2026-06-16, approved):** Target pin is
  `>=0.2.101,<0.3.0`, lock at `0.2.101` — adopt the 0.2.x line and
  keep a deliberate cap against the next major. Update the pyproject
  comment to document the deliberate adoption and the new guard.

---

## Known behavioral risks (to verify empirically)

- **MCP background-connection default.** 0.2.x connects MCP servers
  in the background by default; a session may start before servers
  report `connected`. Verify attune workflows that rely on MCP tools
  (including attune's own MCP server) tolerate the `pending` window,
  or set `MCP_CONNECTION_NONBLOCKING` / per-server `alwaysLoad`.
- **System-prompt default.** 0.2.x reportedly no longer applies the
  Claude Code system prompt by default. Audit the 18
  `ClaudeAgentOptions` sites: any that relied on the default need an
  explicit `system_prompt` preset.
- **Settings-sources default.** Confirm filesystem settings loading
  matches prior behavior (reported restored in late 0.2.x, but
  verify against the locked `0.2.101`).

These are hypotheses from the SDK migration guide, cross-checked
against the code. Phase 0 measures which actually bite.

---

## End state / Done when

- `pyproject.toml` pin is `>=0.2.101,<0.3.0` with an updated
  deliberate-cap comment; `uv.lock` resolves `claude-agent-sdk` to
  `0.2.101`.
- All identified behavioral changes are handled in code (explicit
  `system_prompt` where attune relied on the default; MCP readiness
  handled).
- Full suite green and `integration-auth` green against 0.2.x.
- A regression guard exists for any behavioral shim introduced.
- CHANGELOG entry added; PR merged with required CI green.
