---
type: reference
subtype: procedural
name: skill-cross-review
category: skill
tags: [skill, plugin]
source: plugin/skills/cross-review/SKILL.md
---

# Reference: Skill: cross-review

One-shot second-opinion review of a real diff by a DIFFERENT model (Claude, Codex or Antigravity) — advisory only, board-recorded. Triggers on: cross review, second opinion, ask another model to review, pre-merge check from codex.

**Usage:** `/cross-review [staged] [seat=claude|codex|antigravity]`

## Binding posture (spec requirement, not style)

Board-only ADVISORY. Never wire this skill's output into a merge
gate, CI check, exit code, or blocking path — that violates
`docs/specs/cross-review/requirements.md` (Binding posture). Only a
chair ruling backed by the spec's dogfood ledger can upgrade it.

## What it does

Phase T2 of `docs/specs/cross-review/`: the moderator (this
session) resolves the current branch's diff vs its merge base
(default) or the staged diff, briefs ONE non-authoring seat with
the ACTUAL diff under an honest truncation manifest, posts the
reply to the board, renders findings as advisory items, and
appends a dogfood-ledger row. All mechanics live in
`attune.roundtable.review` — do not reimplement them inline.

## Steps

1. **Spend gate**: state seat + target (one line) and get a go
   (session-durable, same rule as `/roundtable`).
   An existing explicit review request is the go for that seat/target.
   For an explicitly requested Claude subscription review, use
   `seat="claude", claude_auth="subscription"`. The launcher checks saved
   Pro/Max authentication in a child with API credentials removed, disables
   tools/custom integrations, and refuses ambiguous/API authentication.
   It does not raise or disable the API spend cap or modify interactive
   authentication. Subscription entitlement is not an invoice/overage receipt.
2. **Run** (module does target resolution, brief, invocation,
   lint, board post):

```bash
SEAT="codex" MODE="branch" python -c "import os, json; from attune.roundtable import Board; from attune.roundtable.review import run_review; b=None
try:
    b=Board(); b.ensure_functions()
except Exception as e: print(f'board unavailable: {e}')
print(json.dumps(run_review('.', seat=os.environ['SEAT'], mode=os.environ['MODE'], board=b), ensure_ascii=False))"
```

   `MODE="staged"` reviews the staged diff. Seat default is
   PROVISIONAL (`review.DEFAULT_SEAT`) until OPEN-1 is ruled.
3. **Render** the result as an advisory list: severity, file:line
   anchor, claim — plus the truncation manifest verbatim when any
   file was omitted (a partial review must say so). ABSENT and
   `format_noncompliant` results render as-is; never fabricate or
   repair findings.
4. **Ledger row** (R5): append `review.ledger_row(result)` to
   `docs/specs/cross-review/receipts.md`, offering the user the
   disposition edit (`real` / `noise` / `not-triaged`). Only real
   runs — no synthetic rows.
5. **Promotion**: findings worth keeping go through the roundtable
   Step 6 promotion flow (`/roundtable promote <thread>`); the
   board thread is TTL'd, the ledger row is durable.

## Arguments

- `/cross-review` — review the current branch vs merge-base.
- `/cross-review staged` — review the staged diff.
- `/cross-review seat=antigravity` — pick the reviewer seat.

## Scoped re-lane (partial manifests)

When a lane returns a PARTIAL manifest that omitted substantive
files, re-run scoped to exactly those files instead of accepting
clean-on-partial: pass `paths=[...]` (repo-relative) to
`run_review` — the brief, result (`scoped_to`), and ledger row all
state the scope. The scope fails CLOSED: any requested path not in
the diff raises `ReviewTargetError` (a scoped lane must review
everything it was asked to — re-issue with only in-diff paths).
Governance surfaces (`.claude/gates/`, `pyproject.toml`,
`.github/`, `codecov.yml`) rank just behind tests in the packing
order, so on D11-class diffs they are unlikely to be omitted in
the first place.

## Complete-file reviews

For a review that must cover every changed file, pass `require_complete=True`.
Inspect the manifest before claiming coverage. If an individual file exceeds
60,000 characters, a scoped re-lane at the same cap cannot include it. An
explicit `diff_cap_chars` override (maximum 250,000) can accommodate a larger
brief; the default remains 60,000. The larger manifest records its actual cap.
`require_complete=True` refuses any remaining omissions before a seat starts.
The subscription launcher supplies the brief on stdin, avoiding command-line
argument limits. Never describe a partial or absent review as complete.

## Related Topics

_No related topics yet._
