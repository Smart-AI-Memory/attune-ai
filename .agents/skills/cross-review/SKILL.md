---
name: cross-review
description: "One-shot second-opinion review of a real diff by a DIFFERENT model (Claude, Codex or Antigravity) — advisory only, board-recorded. Triggers on: cross review, second opinion, ask another model to review, pre-merge check from codex."
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
MODE="branch" python -c "import os, json; from attune.roundtable import Board; from attune.roundtable.review import run_review; b=None
try:
    b=Board(); b.ensure_functions()
except Exception as e: print(f'board unavailable: {e}')
print(json.dumps(run_review('.', mode=os.environ['MODE'], board=b), ensure_ascii=False))"
```

   `MODE="staged"` reviews the staged diff. Pass `seat=` only to
   override; omitted, it resolves to a seat that is NOT the
   moderating host (see below), so the run is a cross-review by
   construction rather than by the moderator remembering to be one.
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
- `/cross-review seat=claude` — from a non-Claude host this resolves to
  the machine's Pro/Max login automatically (`claude_auth="auto"`). From
  a Claude host, or an unknown one, it stays on `"api"` and refuses at a
  zero session spend cap. Pass `claude_auth="api"` to force the billable
  route.

## Seat defaults follow the host

`run_review` resolves an omitted seat against the MODERATING host:

| Host | Default seat |
|---|---|
| Claude | `codex` (OPEN-1's ruled value, unchanged) |
| Codex | `claude` |
| none / ambiguous | `codex` (`review.DEFAULT_SEAT`) |

OPEN-1 (2026-07-28) fixed the default at `codex` when Claude was the
only host, so the ruled value and "a non-authoring seat" were the
same thing. They part company on a Codex-hosted run, where the ruled
value would brief the AUTHORING seat on its own diff. Detection is
environment-marker based and fails OPEN; every result carries `host`
and `self_review`, so a missed marker shows up in the ledger row
instead of hiding inside a clean verdict. **Check `self_review` before
trusting a clean result** — a seat reviewing itself reads identically
to a real cross-review. It is `true`/`false` when the host was
detected and `null` when it was not: `null` means independence is
UNVERIFIED, not confirmed, so treat it like `true` for trust purposes.

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
