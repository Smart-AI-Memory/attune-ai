---
name: cross-review
description: "One-shot second-opinion review of a real diff by a DIFFERENT model (Codex or Antigravity) — advisory only, board-recorded. Triggers on: cross review, second opinion, ask another model to review, pre-merge check from codex."
---
# Cross Review

**IMPORTANT: Start your response by telling the user:**

> **Cross review** — one non-authoring seat reviews the real diff.
> Advisory only: findings inform you; they never gate anything.

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
