# Upgrading to 13.0.0

13.0.0 is mostly a **hardening** release — failure paths that only
matter when something goes wrong now behave correctly (see the
[changelog](../../CHANGELOG.md)). Most projects upgrade with **no code
changes**. The major version marks a handful of breaking or
behavior-changing items; the table below tells you in one glance whether
any apply to you.

## Are you affected?

| If you… | What changed | Action |
|---|---|---|
| import `attune.hooks.HookRegistry` / `HookExecutor` / `HookConfig` (or `HookDefinition` / `HookEvent` / `HookMatcher` / `HookRule` / `HookType`), or `attune.commands.CommandContext` / `CommandExecutor` / `create_command_context` | **Removed** (§1) | switch to Claude Code's own hooks |
| relied on a memory pattern staying visible **across projects** | INTERNAL scoping is now enforced (§2a) | expect cross-project reads to be denied |
| treated a memory store as **fire-and-forget** (ignored its return value) | durability is now truthful (§2b) | check the return; a `False`/failure is now real |
| assumed `memory_search` results were **scope-filtered** | search is documented as ungoverned (§2c) | don't rely on search for isolation |
| pin `attune-forms` **below 0.7.0** | dependency floor raised (§3) | allow `attune-forms>=0.7.0,<1.0` |
| call the `doc_gen` MCP tool with `doc_type`/`audience`, `attune_set_level` with a boolean, or `memory_store` with `classification` | MCP tool-schema tightening (§4) | drop the dropped params; pass an int level |

**If none of these describe you, you're done — upgrade normally.** The
common case (file-based memory, the plugin's hooks, `attune-forms`
unpinned or already ≥0.7.0) needs nothing.

---

## 1. Removed: the dormant in-package hook-execution engine

**Affected if** your code imports any of: `attune.hooks.HookRegistry`,
`HookExecutor`, `HookConfig`, `HookDefinition`, `HookEvent`,
`HookMatcher`, `HookRule`, `HookType`, or `attune.commands.CommandContext`,
`CommandExecutor`, `create_command_context`.

This in-package engine (`attune/hooks/executor.py`, `registry.py`,
`config.py`, `commands/context.py`) had **no live caller** inside attune
— it never ran the hooks Claude Code actually executes. Those are the
scripts under `attune/hooks/scripts/`, wired through the plugin's
`hooks.json`. The engine was removed under the removing-dead-code gate
(chair-ruled DELETE, #2125).

**What to do:** use Claude Code's own hook system — the plugin
`hooks.json` plus scripts under `attune/hooks/scripts/`. See
[docs/hooks.md](../hooks.md). If you had built your own runner on top of
the removed classes, it was running against dead code and produced no
effect; there is nothing to preserve.

## 2. Changed: memory durability & scoping

The library-review memory tier changed behavior code may have relied on.
Review anything that assumed the old (permissive) scoping or treated a
write as fire-and-forget.

### 2a. INTERNAL workspace scoping is now enforced (#2129)

**Affected if** you relied on an `INTERNAL`-classified pattern created in
one project being visible from another.

Scoping that was *documented but not enforced* is now enforced: an
`INTERNAL` pattern is visible only within the workspace that created it.
Cross-workspace reads that previously succeeded will now be denied.

**What to do:** if you intentionally shared patterns across projects,
classify them `PUBLIC` (visible everywhere) rather than relying on the
old leak. `SENSITIVE` remains creator-only; `PUBLIC` remains everyone.

### 2b. Memory writes are truthfully durable (#2128)

**Affected if** you call a memory store and ignore its result.

A write that reported success without actually landing now either
persists or surfaces the failure. A store that returns `False` (or
raises) is telling you the write did **not** land — previously that same
call could silently drop and still look successful.

**What to do:** check the return value of store operations; handle a
falsy/failed result instead of assuming success.

### 2c. `memory_search` is documented as ungoverned (#2129)

**Affected if** you used `memory_search` and assumed its results were
access-scoped.

Search is a raw read path: it is **not** classification- or
workspace-filtered, so it can surface `SENSITIVE` or cross-workspace
records that `memory_retrieve` would deny. This is now documented
explicitly so callers don't assume isolation search never provided.

**What to do:** don't use `memory_search` as an authorization boundary.
Use `memory_retrieve` (which enforces ownership) when isolation matters.

### 2d. Contended/unreachable stores degrade instead of hanging (#2130)

**No action needed** — lock acquisition is now atomic and recall
connection attempts are bounded, so a contended or unreachable store
degrades gracefully rather than hanging. This only removes failure
modes.

## 3. Dependency floor: `attune-forms >= 0.7.0`

**Affected if** you pin `attune-forms` below `0.7.0`.

The floor is raised to `attune-forms>=0.7.0,<1.0` (#2131). The MCP
elicitation schema is now sourced from the library, so the server
advertises 0.7.0's full construct vocabulary (adds `deliberation`,
`triage`, `confirm`, `ranking`, `assumption_review`).

**What to do:** allow `attune-forms>=0.7.0,<1.0` in your environment.
A plain `pip install -U attune-ai` resolves it for you.

## 4. MCP tool-schema tightening

**Affected if** you call these MCP tools with the named inputs:

- **`doc_gen`** no longer accepts `doc_type` / `audience` — both were
  dropped from the underlying workflow in the v4.2.0 SDK migration and
  had been silently ignored. Remove them from your calls; the generated
  shape is chosen from the source.
- **`attune_set_level`** rejects a boolean `level`. `True`/`False`
  previously slipped through as `1`/`0`; pass an integer `1`–`5`.
- **`memory_store`** now honors an explicit `classification` on the
  persisted long-term pattern (previously ignored). Omit it to keep
  automatic classification — passing a value **overrides** auto-detection,
  so don't send `PUBLIC` on content that should stay `SENSITIVE`.

**What to do:** drop the removed `doc_gen` params, pass an integer level,
and set `memory_store`'s `classification` only when you mean to override
auto-classification.

---

## Not sure whether you're affected?

- Grep your code for the removed symbols in §1 — no hits means §1
  doesn't apply.
- If you only use file-based memory through the CLI/plugin and never
  import `attune.memory` directly, §2 is transparent to you.
- If you don't pin `attune-forms`, §3 is automatic.
- If you don't call the MCP tools in §4 with those inputs, §4 doesn't
  apply.

## See also

- [CHANGELOG.md](../../CHANGELOG.md) — the full 13.0.0 entry
- [docs/hooks.md](../hooks.md) — Claude Code hooks (the §1 replacement)
