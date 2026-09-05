# Agent work handoff

## Goal

Preserve the seven chair-approved adaptive-session-interactions requirements
and the proposed task ladder in Git for later execution.

## Acceptance criteria

Approved text, provenance, dissent and resume boundaries are tracked; all five
tasks load with their constraints/dependencies; the spec remains parked;
only the spec package, this handoff and review ledger enter the commit.

## Scope and assumptions

- Branch/worktree: codex/adaptive-session-interactions-spec in the integrating
  Codex worktree; preservation base be15968fa (origin/main fetched 2026-09-05).
- Provider/session: Codex advisory to Patrick; Claude remains the global lead.
- Assumptions: Patrick's exception authorizes spec preservation and commit,
  not implementation. Claude's main checkout was dirty and was not updated.

## Current state

- Status: requirements approved; five proposed tasks parked, none started.
- Changed files: five files under docs/specs/adaptive-session-interactions,
  this handoff, and two appended rows in docs/specs/cross-review/receipts.md.
- Decisions: [spec decisions](../specs/adaptive-session-interactions/decisions.md)
  preserve all seven approvals and the commit-only authority boundary.
- Risks or open questions: only one of three roundtable replies passed the
  compiler; no multi-seat consensus. T1 must identify actual consumer/file
  scope and reconcile current work; no renderer optimization is justified.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Approved product scope preserved | Compare parsed ASI bodies against locally compiled chair-approved requirements | 7/7 identical; original mapping retained |
| Future reader receives full tasks | read_spec comparison of IDs, names, objectives, copied context, checks, and dependencies | 5/5 preserved; sequential dependencies |
| Execution has not started | load_state of canonical tasks file | None; no completed/current/auto-run state written |
| Spec is discoverable and parked | status_line_gate and canonical phase files | PASS; approved requirements, parked tasks with Resume-Trigger |
| Document gates accept preserved scope | run_boundary for requirements and tasks with actual spec paths | All five applicable receipts PASS |
| Package is portable | Resolve relative links in all five spec files | 32/32 resolve |
| Tracked status and ledger conventions hold | Serial keyless status/precision/rejection/provenance guard tests | 105 passed |
| Commit checks accept scope | Pinned pre-commit over all seven intended files | All applicable hooks passed |

Final tests and commit checks are recorded in
[spec evidence](../specs/adaptive-session-interactions/evidence.md).

## Next action

For a future execution request, read
[the canonical tasks](../specs/adaptive-session-interactions/tasks.md), run
collaboration preflight and reconcile live Git/code/active work. Obtain the
applicable task go and pass the execution gates before using the workspace
resume route, which enters execution. Do not treat this handoff as authority
or a go. Delete this branch handoff when its PR merges; durable spec content
remains in the spec directory.
