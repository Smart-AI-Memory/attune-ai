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
