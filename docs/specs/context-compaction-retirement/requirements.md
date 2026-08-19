# Context Compaction Retirement — Requirements

**Status:** draft (2026-08-18) — awaiting chair review. No code
changes are authorized by this document; it records the
removing-dead-code gate's findings and proposes a disposition.
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
  `hooks/scripts/pre_compact.py`, and their exports; retire
  `attune.commands.context.CommandContext`'s `context_manager`
  field or the commands framework question is taken up separately.
- R2. Delete or rewrite the two docs pages; grep for
  `::: attune.context` mkdocstrings blocks and `search-index.json`
  refs before merge (the #279 lesson).
- R3. `ContextInflater`: chair picks — delete with R1 (zero
  consumers, gate says dormant), or keep as the one surviving
  deferral since #2088 named it deliberately. Lead recommends
  delete; resurrect from git history if a provider-adapter
  consumer ever materializes.
- R4. Breaking-change discipline: `feat!:` with changelog entry;
  the live trio's exports are unchanged.
- R5. Regression guard: a test asserting `attune.context.__all__`
  is exactly the live trio, so the dormant half cannot silently
  return.

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

- OQ1. R3 — inflater: delete or keep?
- OQ2. Does the `attune.commands` framework (loader/parser/
  registry, zero external consumers) get its own gate pass, or is
  it out of scope permanently?
