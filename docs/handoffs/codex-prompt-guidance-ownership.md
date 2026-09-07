# Agent work handoff

## Goal

Keep prompt guidance in its existing canonical owners while routing work by
risk, ambiguity, dependency and continuity rather than file-count shortcuts.

## Acceptance criteria

The contract owns tiers and shared communication requirements; XML eligibility
and schema have one owner; the decision tree references both and reaches the
structured one-shot tier after spec/XML checks. Existing XML consumers keep their
input contract. Projections match and always-loaded rules stay under budget.

## Scope and assumptions

- Branch/worktree: codex/prompt-guidance-ownership, isolated clone.
- Provider/session: Codex implementation, Claude advisory review.
- Assumptions: Patrick's “proceed as recommended” authorizes the reviewed split;
  it does not authorize merge, expanded agent authority or a new prompt benchmark.

## Current state

- Status: six guidance/projection files updated; Claude reviewed all six with no omissions.
  Eight clarifications were accepted and seven findings rejected with evidence;
  exact claims and reasons are in the cross-review ledger.
- Changed files: shared contract, XML rule, decision routine, root/IDE AGENTS and
  Claude instructions. Claude's non-generated duplicate cutoff was also removed.
- Decisions: no new guidance reference; no task-success or XML-superiority claim.
  Prior question review: q-prompt-criteria-ownership-20260907 (3 sent, 0 omitted).
- Risks or open questions: no untriaged advisory findings; no merge approval.

## Verification

| Claim | Failure-sensitive probe | Result |
| --- | --- | --- |
| Existing governance remains consistent | Existing-environment collaboration_preflight.py | 87 tests passed; 0 failed checks |
| Projections, residency and XML input paths remain valid | Projector, rules, spec-reader and wizard-decomposer suites | 85 passed including review-ledger gates |
| Rule residency remains bounded | Existing residency test and byte count | 17,659 / 20,000 bytes |
| Formatting and projection hooks pass | Pinned pre-commit on six changed files | Passed |

## Next action

Review the draft PR and its recorded Claude findings. Do not merge without
Patrick's approval. No runtime code or parser schema changed.
