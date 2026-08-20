# Upgrading to 13.0.0

13.0.0 mostly makes things you already rely on more dependable — the
failure paths that only matter when something goes wrong now behave
correctly (see the [changelog](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CHANGELOG.md)). **Most projects
upgrade with no code changes.** A few items change observable behavior
or a public surface; the table below is a 30-second check for whether
any touch you.

## Do you need to change anything?

| Situation | What's different in 13.0.0 | What to do |
|---|---|---|
| You share `INTERNAL` memory across projects (§1a) | `INTERNAL` is now scoped to its workspace | classify shared patterns `PUBLIC` |
| You ignore a memory store's return value (§1b) | writes now report failure truthfully | check the return value |
| You treat `memory_search` as an access boundary (§1c) | search is (and always was) unscoped — now documented | use `memory_retrieve` for isolation |
| You pin `attune-forms` below 0.7.0 (§2) | floor raised to `>=0.7.0,<1.0` | widen the pin |
| You call `doc_gen` with `doc_type`/`audience`, `attune_set_level` with a boolean, or `memory_store` with `classification` (§3) | schemas dropped inputs that did nothing | drop the dropped params; pass an int level |
| You import `attune.hooks.*` or `attune.commands.*` internals (§4) | a dead engine was removed | use Claude Code's hooks |

**If none of these describe you, you're done — upgrade normally.** The
common case (file-based memory, the plugin's hooks, `attune-forms`
unpinned or already ≥0.7.0) needs nothing.

---

## 1. Memory is more dependable — and a little stricter

The library-review memory tier makes writes honest and scoping real.
Both are improvements; each has one narrow case where you'd adjust.

### 1a. INTERNAL memory is now scoped to its workspace (#2129)

Scoping that was documented but never enforced is now real: an
`INTERNAL`-classified pattern is visible only inside the project that
created it, closing a quiet cross-project leak.

**You only need to act if** you were relying on that cross-project
visibility — classify patterns you mean to share as `PUBLIC` (visible
everywhere). `SENSITIVE` stays creator-only; `PUBLIC` stays everyone.

### 1b. Memory writes are now honest about failure (#2128)

Your writes now either land or tell you they didn't. A store that
returns `False` (or raises) means the write did not persist — where
before, that same call could silently drop and still look successful.
Your data is safer, and failures are visible instead of hidden.

**You only need to act if** your code ignores store return values: start
checking them and handle a failed write.

### 1c. `memory_search` is documented as an unscoped read (#2129)

One thing to know rather than a change: `memory_search` is a raw read —
it is not classification- or workspace-filtered, so it can surface
`SENSITIVE` or cross-workspace records that `memory_retrieve` would deny.
It always worked this way; 13.0.0 documents it so no one assumes an
isolation it never provided.

**What to do:** don't use `memory_search` as an authorization boundary.
Reach for `memory_retrieve` (which enforces ownership) when isolation
matters.

### 1d. Contended or unreachable stores degrade instead of hanging (#2130)

**Nothing to do** — lock acquisition is now atomic and recall connection
attempts are bounded, so a busy or unreachable store fails fast and
degrades gracefully instead of hanging. This only removes failure modes.

## 2. `attune-forms` now requires 0.7.0+

**This touches you only if** you pin `attune-forms` below `0.7.0`.

The floor is raised to `attune-forms>=0.7.0,<1.0` (#2131), and the MCP
elicitation schema is now sourced from the library — so the server
advertises 0.7.0's full construct vocabulary (adds `deliberation`,
`triage`, `confirm`, `ranking`, `assumption_review`) with no
hand-maintained mirror to drift.

**What to do:** allow `attune-forms>=0.7.0,<1.0`. A plain
`pip install -U attune-ai` resolves it for you.

## 3. MCP tool schemas dropped inputs that never worked

**This touches you only if** you call these MCP tools with the named
inputs:

- **`doc_gen`** no longer accepts `doc_type` / `audience`. Both were
  dropped from the underlying workflow in the v4.2.0 SDK migration and
  had been silently ignored ever since — removing them just stops
  advertising inputs that did nothing. The generated shape is chosen
  from the source.
- **`attune_set_level`** now rejects a boolean `level`. `True`/`False`
  previously slipped through as `1`/`0`; pass an integer `1`–`5`.
- **`memory_store`** now honors an explicit `classification` on the
  persisted long-term pattern (it was ignored before). Omit it to keep
  automatic classification — an explicit value **overrides**
  auto-detection, so don't send `PUBLIC` on content that should stay
  `SENSITIVE`.

**What to do:** drop the removed `doc_gen` params, pass an integer level,
and set `memory_store`'s `classification` only when you deliberately want
to override auto-classification.

## 4. A dead in-package hook engine was removed

**Almost certainly not you** — this touches only code that imports
`attune.hooks.HookRegistry`, `HookExecutor`, `HookConfig`,
`HookDefinition`, `HookEvent`, `HookMatcher`, `HookRule`, `HookType`, or
`attune.commands.CommandContext`, `CommandExecutor`,
`create_command_context`.

The reassuring part: this engine never actually ran anything. It had
**no live caller** inside attune — the hooks Claude Code executes are the
scripts under `attune/hooks/scripts/`, wired through the plugin's
`hooks.json`, which never touched it. It was removed as dead code
(chair-ruled DELETE, #2125).

**What to do:** use Claude Code's own hook system — the plugin
`hooks.json` plus the scripts under `attune/hooks/scripts/`. See
[docs/hooks.md](../hooks.md). If you had built a runner on the removed
classes, it was running against dead code and had no effect, so there is
nothing to preserve.

---

## Not sure whether anything applies?

- If you only use file-based memory through the CLI/plugin and never
  import `attune.memory` directly, §1 is transparent to you.
- If you don't pin `attune-forms`, §2 is automatic.
- If you don't call the MCP tools in §3 with those inputs, §3 is moot.
- Grep your code for the symbols in §4 — no hits means §4 is moot.

## See also

- [CHANGELOG.md](https://github.com/Smart-AI-Memory/attune-ai/blob/main/CHANGELOG.md) — the full 13.0.0 entry
- [docs/hooks.md](../hooks.md) — Claude Code hooks (the §4 replacement)
