# Adaptive session interactions — Decisions

## D1 — Requirement approval and limited review coverage (2026-09-05)

Thread: `q-adaptive-session-interactions-001`. One approved round used three
CLI invocations. Antigravity's response passed the compiler; Claude and
Codex responses failed its format contract and were excluded from consensus.
The chair approved the moderator-refined requirements with that limitation
explicitly disclosed. Approval is a chair ruling, not a claim of independent
three-provider agreement.

| Requirement | Candidate board ID | Chair ruling ID | Disposition |
| --- | --- | --- | --- |
| ASI-1 | 12 | 19 | Approved |
| ASI-2 | 13 | 19 | Approved |
| ASI-3 | 14 | 19 | Approved |
| ASI-4 | 15 | 20 | Approved |
| ASI-5 | 16 | 20 | Approved |
| ASI-6 | 17 | 20 | Approved |
| ASI-7 | 18 | 21 | Approved |

The canonical collector accepted the three batches at successor revisions
5, 6 and 7; revision 7 is terminal. No requirement remains unruled or
declined. These are text-mediated canonical action receipts, not evidence
that a rich widget was visible or useful. No action nonce is needed in the
tracked record.

The full transcript, raw replies and original action envelopes remain
machine-local under the roundtable local-first rule. Optional source report:
`~/.attune/reports/roundtable/q-adaptive-session-interactions-001.md`.
The tracked requirements and this curated record suffice to resume; neither
Redis availability nor that local report is a prerequisite.

## D2 — Approved refinements and retained counter-cases

- Selection follows immediate need and explicit preference scope. The
  counter-case is that adding a binding check can duplicate policy; ASI-7
  therefore requires a demonstrated gap before code.
- Both action surfaces use the canonical collector. A receipt from one
  surface does not prove another surface's usability. ASI-3 accepts named
  human attestation of usability while keeping precise paint time separate.
- Independent unknowns can stay batched in a text fallback. Dependent
  questions remain sequential; wholesale sequential fallback was not adopted.
- One existing schema-bounded workspace choice is the first trial; exact
  consumer selection remains conditional on T1. Readiness precedes usefulness
  measurement. Latency is descriptive until evidence justifies renderer work.
- The inspected selector does not pass chosen to its routing decision.
  No repair of the alleged chosen-input confound is part of the approved scope.

The full approved dissent register remains in [requirements](requirements.md#dissent-register).

## D3 — Repository preservation, not execution (2026-09-05)

After all seven approvals, Patrick instructed: “update the repo for the
purposes of committing the spec for safety and so it can be executed at a
later date.” This supersedes the repository freeze only for this spec package,
its handoff and supporting review records. Implementation, host trials,
renderer changes, paid provider calls and interference with Claude's active
work are not authorized by that instruction.

The feature remains under the existing lead/chair governance; this commit
assigns no new lead authority and does not approve the proposed task ladder.
Each task must pass its existing review and execution gates when resumed.

Preservation branch: codex/adaptive-session-interactions-spec, based on
be15968fa2259d9fdc15d8e5eb8af70261d866a0. Main was observed dirty and was not updated.
No open PR was returned by the live overlap check at preservation time.

## D4 — Editorial portability corrections (2026-09-05)

The seven approved requirement bodies are preserved unchanged from the local
compiled artifact. The original interaction table is restored above ASI-1.
Status/provenance notes now distinguish completed requirement approvals from
pending execution; ASI-5's historical proposal qualifier is explained rather
than silently changing its approved body. Dissent is retained.

The original five task contexts are copied into their parsed objectives so
the existing task reader cannot discard them. Task IDs, names, dependencies
and validation checks remain the original ladder. This is preservation of
instructions, not an expansion of implementation scope. Canonical phase files
use recognized status tokens; the highest phase is parked with a concrete
resume trigger. See [evidence](evidence.md) for validation receipts.

## D5 — Rulings on Antigravity's critique after T1 (2026-09-05, chair via triage form)

T1 (`t1-inventory.md`, PR #2429) re-read Antigravity's board message 6
against the code. Four of its eight critiques were already in the approved
text and were confirmed by probe (ASI-1 guidance-first, ASI-4 collector
clause, ASI-5 schema-bound consumer, ASI-7 read-only characterization).
The chair ruled the remaining items (response `resp-20260905-153010-c5dbd526`):

| Item | Ruling | Effect |
| --- | --- | --- |
| Amend ASI-2 to name the existing markdown surface as the form text fallback | **adopt** | ASI-2 gains the amendment bullet; the router's `widget`/`ask`-only range and the missing MCP tool are recorded as a known limit, not fixed |
| Record Antigravity's proposed ASI-8 (sequential text intake) as declined with reason | **adopt** | dissent register carries the decline and the reason (the surface exists and batches) |
| Record that the repository freeze was lifted for this spec package by the 2026-09-05 planning form | **modify → ruled** | The chair modified the proposed docs-only scope to the wider reading (response `resp-20260905-153232-f6db1cd2`, single-select): **the no-repo-change instruction is lifted entirely for this feature; per-task gos are the only remaining gate.** Implementation is still not authorized — T2 waits on the chair's acceptance of T1 and its own go — but no freeze stands between a go and execution. ASI-7's freeze bullet carries a matching amendment note. |
| Answer Antigravity's follow-up (board message 8): freeze the CommandWorkspaceHost action path as the T4 trial boundary | **adopt** | the **`spec` adapter's review-stage choice** (`redo_plan` / `approve_plan`) is the named T4 consumer boundary, as T1 selected; roundtable rulings and the consequential `create_spec` / `start_execution` choices are excluded from the first trial |

Counter-case retained: naming a text-fallback surface in a requirement
binds the pilot to a library seam that has no MCP tool today; if T2 finds
the seam unreachable from the named host, the amendment is a pointer to
library behavior, not a promise of host behavior.
