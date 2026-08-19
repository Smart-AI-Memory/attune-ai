# Context Compaction Retirement — Decisions

## D1 — OQ1: ContextInflater is deleted with R1 (chair, 2026-08-18)

Ruled via confirm construct (widget form, this session): **Approve**.
The inflater (59 LOC, zero consumers, the one deferral #2088 named)
is deleted in the same R1 change as the compaction stack. Git
history preserves the implementation for any future
provider-adapter rebuild. Consequence accepted with the ruling:
R5's `__all__` guard pins exactly the live trio
(`TokenBudgetAllocator`, `ASTSkeletonGenerator` — via the
allocator — and the module's public surface reduces to what
#2088's consumers use).

## D2 — OQ2: scope-only exclusion for attune.commands (chair, 2026-08-18)

Chair's initial position was "out of scope permanently." Lead
pushed back (pushback construct, this session): a PERMANENT
exemption would grant ~2,000 LOC with zero production consumers a
standing pass from the exact gate that caught this module.
**Chair accepted the pushback** and ruled: `attune.commands` is
out of THIS spec's scope only; its own removing-dead-code gate
pass is recorded as pickable future work, with no standing
exemption. R1 still unconditionally removes
`CommandContext.context_manager` and its runtime import so this
spec leaves no broken path regardless of when that pass runs.

**Pickable work recorded:** run the removing-dead-code gate over
`src/attune/commands/` (loader/parser/registry/models + command
`.md` corpus; consumers today are only its own tests — verify
against the tree at pick-up time, not this record).

## D3 — post-retirement review rulings (chair, 2026-08-19, decision-packet form)

From the post-retirement architecture review (full report:
`~/.attune/reports/reviews/context-arch-review-post-12.0.0-2026-08-19.md`;
repo stub: `docs/reports/review-context-post-retirement-2026-08-19.md`):

- **suggest_compact.py DELETED.** The removing-dead-code gate dogfood
  fired three signals: zero usage (absent from `plugin/hooks/hooks.json`
  and every settings surface — grep receipt in the review), orphaned
  motivation (manual-compaction nudge ported from everything-claude-code
  JS; the era this spec retired), and a false wiring claim ("Called by
  PreCompact hook" with no such registration). Removed with its test
  file, `hooks.scripts` export, coverage exclusion, and
  path-validation-gate allowlist entry. Same disposition path as its
  sibling `pre_compact.py` (R1). Resurrect from git history only with
  a real consumer.
- **fit_source telemetry: minimal-measurement approved.** #2095's
  `last_fit` is structurally dead in production (all four consumers use
  throwaway allocator instances) and nothing consumes the log line.
  Chair approved a small follow-up PR making rung outcomes actually
  observable. Budget ratification (the 1250/1000/750 folklore values)
  is DEFERRED until that measurement yields data.
- **POST_COMPACT enum member removed** from `HookEvent` — PostCompact
  is not a Claude Code lifecycle event (fiction signal #3,
  requirements.md); `PRE_COMPACT` KEPT (PreCompact is real, merely
  handler-less here).
- **Post-compact continuity contract documented** at
  `docs/architecture/post-compact-continuity.md` (the implicit
  4-hook contract made explicit).
- **D2 pickable work now tracked** in `TASKS.md` (Someday).
