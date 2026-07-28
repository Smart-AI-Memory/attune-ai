# Feature Lead Governance — Execution Plan

**Status:** approved (2026-07-27) — rulings applied; execution gated
by P1 (the cross-review usage-signal read).
**Canonical spec:** `docs/specs/feature-lead-governance/`

## Outcome

Attune can assign one provider-neutral feature lead to a bounded scope,
preserve independent cross-provider review, resolve preference-only
conflict without rewrite churn, and escalate authority disputes to the
human chair.

## Scope

- Governance core and tracked assignment artifact.
- MCP assignment lifecycle.
- Integration with cross-provider handoff and cross-review.
- Projected collaboration rules, documentation, and live dogfood.

## Constraints

- No permanent provider ownership.
- No model may waive repository rules or required evidence.
- Findings are immutable through every governance API; dispositions
  are appended per atomic finding; out-of-band edits are detected.
- Chair transitions (activation, cross-provider transfer, scope
  expansion, revocation) are evidenced by chair-merged PRs to the
  main-tracked registry (D7) — never by an MCP-relayed confirmation.
  Same-provider session succession is an automatic event.
- Implementation waits for the P1 activation gate (the cross-review
  usage-signal read) and consumes the SHIPPED handoff/board seams.

## Tasks

The executable task definitions live in
`docs/specs/feature-lead-governance/tasks.md`:

1. `featurelead-t1` — governance core.
2. `featurelead-t2` — MCP assignment surface.
3. `featurelead-t3` — handoff and cross-review integration.
4. `featurelead-t4` — projected contract, docs, and dogfood.

## Review gate

Patrick must rule on OPEN-1..4 in `requirements.md` and ratify or amend
Proposed D1..D6 in `decisions.md` before execution.
