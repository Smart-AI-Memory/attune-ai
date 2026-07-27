# Feature Lead Governance — Execution Plan

**Status:** DRAFT for review; not approved for execution.
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
- Findings are immutable; dispositions are appended.
- Human approval remains required for activation, transfer, scope
  expansion, revocation, and unresolved material disputes.
- Implementation waits for spec approval and current handoff/review APIs.

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
