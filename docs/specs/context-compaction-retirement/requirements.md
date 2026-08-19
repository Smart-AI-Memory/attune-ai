# Context Compaction Retirement — Requirements

**Status:** draft (2026-08-18) — OQ1 and OQ2 ruled by the chair
(see `decisions.md` D1/D2, this date). No code changes are
authorized until the chair reads and merges the spec PR; this
document records the removing-dead-code gate's findings and the
now-ruled disposition.
**Slug:** `context-compaction-retirement`
**Provenance:** "resume work on context management" session
(2026-08-18). #2088 shipped the live half of `attune.context`
(fit_source budget ladder); auditing the module for the next unit
of work surfaced the dormant half. Gate applied:
`.claude/rules-tail/attune/removing-dead-code.md`.

## Problem

`attune.context` is two features sharing a package. One is live;
the other is dormant, EmpathyOS-motivated, and documented as
working when it is not wired at all.

**Live (out of scope — keep):** `TokenBudgetAllocator`,
`ASTSkeletonGenerator`, `fit_source()` — consumed by four workflow
prompt sites since #2088. Their named follow-ups (Redis AST cache,
gated on scale evidence) stay deferred per #2088.

**Dormant (this spec's scope):**

| Surface | LOC | Evidence of dormancy |
|---|---|---|
| `context/compaction.py` | 468 | consumed only by `manager.py` |
| `context/manager.py` | 449 | consumers: an unregistered hook script and the `attune.commands` framework, itself consumed by nothing outside its own package |
| `hooks/scripts/pre_compact.py` | 212 | absent from `plugin/hooks/hooks.json` and every settings surface; referenced only by its own tests and docs |
| `context/inflater.py` | 59 | zero consumers; named as deferred future work in #2088 |

## Removal signals (gate criteria, with receipts)

1. **Zero usage evidence.** No hook registration, no CLI or MCP
   route reaches `ContextManager` (`context_get`/`context_set` in
   `mcp/server.py` are an unrelated in-memory dict). Callers are
   tests, `__init__` exports, and the dormant commands framework.
2. **Orphaned motivation.** `CompactState` preserves
   `trust_level` / `empathy_level` from `CollaborationState` — the
   EmpathyOS model whose core was deleted in 9.0.0 (#1073). The
   state being "preserved" is never populated in any live path.
3. **Docs cite fiction.** `docs/how-to/context-management.md`
   claims the flow is "automatic when hooks are configured",
   diagrams a `PostCompact` hook (no such Claude Code event), and
   names `save_before()` / `restore_after()` (no such methods —
   the real names are `save_for_compaction` / `restore_state`).
   The doc-import gate passes because the symbols import; the
   wiring claims are still false.
4. **Superseded.** The problem it targets is solved by shipped,
   dogfooded features: `session_stash`/`session_recall` hooks,
   tracked `docs/handoffs/<branch-slug>.md`, the memory corpus,
   and the harness's own context summarization.

Two signals suffice; four fire.

## Proposed disposition (for review, not ratified)

- R1. Delete `context/compaction.py`, `context/manager.py`,
  `hooks/scripts/pre_compact.py`, and their exports. The
  `context_manager` field and its runtime import in
  `attune.commands.context.CommandContext` (line 357 imports
  `ContextManager` at runtime, not just under TYPE_CHECKING) are
  removed IN THE SAME CHANGE, unconditionally — R1 must not leave
  a broken import path regardless of how OQ2 is later ruled.
- R2. Delete or rewrite the two docs pages; grep for
  `::: attune.context` mkdocstrings blocks and `search-index.json`
  refs before merge (the #279 lesson).
- R3. `ContextInflater`: **RULED (D1)** — deleted with R1.
  Resurrect from git history if a provider-adapter consumer ever
  materializes.
- R4. Breaking-change discipline: `feat!:` with changelog entry;
  the live trio's exports are unchanged.
- R5. Regression guard: a test asserting `attune.context.__all__`
  is exactly the live-trio surface (D1 ruled the inflater deleted),
  so the dormant half cannot silently return.

## Counter-case (strongest argument against)

Compaction-state preservation maps to a real pain — Claude Code
does fire `PreCompact`, and #2088 was merged yesterday by a lead
that chose deferral over deletion for the inflater. A future
rebuild on current rails (memory corpus instead of
CollaborationState) might reuse the `CompactState` persistence
shape. Against this: the rebuild would keep neither the EmpathyOS
fields nor the unwired plumbing, so history (`git log`) preserves
everything a rebuild needs; keeping 1,100 dormant LOC on PyPI as
public API is the more expensive way to store it.

## Open questions for the chair

Both ruled 2026-08-18 — see `decisions.md`:

- OQ1. Inflater: **delete** (D1).
- OQ2. `attune.commands`: **out of THIS spec only**; its own gate
  pass is pickable future work, no standing exemption (D2 — chair
  accepted the lead's pushback against a permanent exclusion).
