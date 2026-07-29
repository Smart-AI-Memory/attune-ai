---
feature: cross-review
summary: One-shot second-opinion diff review by a different-model seat, advisory only
tags: [review, roundtable, multi-llm]
source_globs:
  - src/attune/roundtable/review.py
nav:
  help: cross-review
  mkdocs:
    how-to: how-to/cross-review
    architecture: architecture/cross-review
    reference: reference/cross-review
---

## Overview

Cross-review sends the real diff you are about to ship to ONE
non-authoring seat at the round table — a **different model**
(Codex or Antigravity) with different blind spots — and renders
its reply as an advisory findings list. The whole mechanism lives
in `attune.roundtable.review`: it resolves the diff read-only,
briefs the seat under an honest truncation manifest, posts the
reply to the shared board, and renders a dogfood-ledger row.

The binding posture is a spec requirement, not a style choice:
**board-only advisory**. A run "succeeds" whenever the review RAN
— including a clean `NO FINDINGS` reply and an ABSENT seat.
Nothing in this feature may gate a merge, wire an exit code, or
block a command. Only a chair ruling backed by the spec's dogfood
ledger can ever upgrade that posture.

Cross-review is deliberately smaller than the full round table:
one seat, one pass, no deliberation, no promotion loop of its own.
It exists because a second model reading the actual diff catches
contract gaps the authoring model reasons past — the first dogfood
ledger rows record exactly that.

## Concepts

### Advisory by construction

`run_review()` returns `ok: True` for every completed run and a
`status` naming what happened: `findings`, `clean`, `absent`, or
`format_noncompliant`. There is no failure exit code to couple a
gate to. Board unreachability degrades to `board: skipped
(<reason>)` — recorded, never fatal.

### The mandatory reply format

The brief instructs the seat to reply with one line per finding —
`FINDING: <file>:<line> [low|medium|high|critical] <claim>` — or
the single line `NO FINDINGS`. `lint_review()` checks compliance;
a noncompliant reply is **flagged, never repaired** — the run
reports `format_noncompliant` and shows the raw reply, so you see
what the seat actually said rather than a cleaned-up fiction.

### The honest truncation manifest

Diffs are packed per-file under a budget (`DIFF_CAP_CHARS`,
60,000 characters). Files that fit are sent whole; files that do
not fit are named in the manifest as omitted. The manifest rides
everywhere the review does — in the brief the seat sees, in the
board post, and in the rendered result — so a partial review is
always visibly partial.

### Seats

The default reviewer seat is `codex` (chair-ruled, OPEN-1). Any
seat in the round table's `SEAT_RECIPES` works — pass
`seat="antigravity"` for the alternative. A seat whose CLI is not
installed or not authenticated produces an `absent` run, which is
a valid, recorded outcome — not an error.

### The dogfood ledger

Every real run appends one row to
`docs/specs/cross-review/receipts.md`: date, seat, target, files
sent/omitted, findings count, and a disposition the human rules
(`not-triaged` until then). Rows are honest by contract — only
real runs, no synthetic entries. The ledger is both the receipt
trail and the evidence base any posture change must cite.

## Quickstart

From a Claude Code session in your repo, run the skill:

```text
/cross-review
```

It reviews the current branch against its merge-base with
`origin/main`, briefs the default seat, and renders the findings
as an advisory list plus the ledger row. Variants:

```text
/cross-review staged
/cross-review seat=antigravity
```

## Tasks

### Review the current branch from Python

```python
from attune.roundtable import Board
from attune.roundtable.review import run_review

board = Board()  # local Redis; omit to skip board posting
result = run_review(".", seat="codex", board=board)
print(result["status"], len(result["findings"]))
for f in result["findings"]:
    print(f["severity"], f["file"], f["line"], f["claim"])
```

### Review only the staged diff

```python
from attune.roundtable.review import run_review

result = run_review(".", mode="staged")
```

`mode="staged"` reviews `git diff --cached`; the default
`mode="branch"` reviews merge-base vs `HEAD` against `base_ref`
(default `origin/main`).

### Append the ledger row

```python
from attune.roundtable.review import ledger_row

row = ledger_row(result, disposition="not-triaged")
```

Append the row to `docs/specs/cross-review/receipts.md` and edit
the disposition once you have triaged the findings.

### Pick the other seat

```python
from attune.roundtable.review import run_review

result = run_review(".", seat="antigravity")
```

## Reference

### `run_review` — `attune.roundtable.review`

```python
def run_review(
    repo_root,                  # str | Path
    seat="codex",               # any SEAT_RECIPES key
    mode="branch",              # "branch" | "staged"
    base_ref="origin/main",
    board=None,                 # attune.roundtable.Board | None
    invoke_seat=...,            # injectable; defaults to the table's runner
) -> dict: ...
```

Result keys: `ok` (always `True` for a completed run), `status`
(`findings` / `clean` / `absent` / `format_noncompliant`), `seat`,
`thread` (board thread id), `findings` (list of dicts with
`file`, `line`, `severity`, `claim`), `reply` (raw text),
`manifest` (`sent` / `omitted` file lists), `target`
(description), `board` (`posted` or `skipped (<reason>)`).

### Module constants

| Name | Value | Meaning |
| --- | --- | --- |
| `DEFAULT_SEAT` | `"codex"` | Reviewer seat when none is passed |
| `DIFF_CAP_CHARS` | `60_000` | Per-run diff budget for the manifest |

The reviewer reply budget is `ROLE_REPLY_CHARS["reviewer"]`
(16,000 chars) from `attune.roundtable.compiler`.

### Supporting functions

| Function | Does |
| --- | --- |
| `resolve_target(repo_root, mode, base_ref)` | Read-only per-file diff resolution; raises `ReviewTargetError` on unresolvable targets |
| `budget_manifest(per_file, cap_chars)` | Packs files under the budget; returns `sent` / `omitted` |
| `build_brief(target, manifest)` | Renders the reviewer brief with the diff and manifest |
| `lint_review(text)` | Returns format problems; empty list means compliant |
| `parse_findings(text)` | Parses `FINDING:` lines into dicts |
| `ledger_row(result, disposition)` | Renders the receipts.md ledger row |

### Entry points

| Surface | Form |
| --- | --- |
| Skill | `/cross-review [staged] [seat=codex\|antigravity]` |
| Python | `attune.roundtable.review.run_review` |

There is deliberately no CLI command, no MCP tool, and no
suggested cadence: invocation is manual (chair-ruled, OPEN-2).

## Comparison

- **vs `/roundtable`** — the round table convenes every seat for
  deliberation with a chair-ruled promotion flow; cross-review is
  one seat, one pass, on a concrete diff. Use the table for design
  questions, cross-review for "does another model see a problem in
  this change?"
- **vs `/deep-review`** — deep-review is a multi-pass review by
  the same model family driving your session; cross-review's value
  is precisely that the reviewer is a DIFFERENT model with
  different blind spots.
- **vs CI review bots** — cross-review never gates anything; it is
  advisory input to a human, recorded on the board and in the
  ledger.

## Failure modes

### Risk areas

- **Absent seat** — the seat CLI is missing or unauthenticated.
  The run records `absent` with the exit code and reply head; this
  is a valid outcome, not an error to retry blindly.
- **Board unreachable** — local Redis down. The review still runs;
  the result records `board: skipped (<reason>)`.
- **Oversized diff** — files beyond the 60k budget are omitted and
  named in the manifest. A review that saw only part of the diff
  says so everywhere the result renders.
- **Format noncompliance** — a seat that replies in prose is
  reported as `format_noncompliant` with the raw reply preserved.
  Findings are never fabricated from prose.

### Diagnosis order

1. `status` first: `absent` → check the seat CLI and its auth;
   `format_noncompliant` → read the raw reply.
2. `manifest` next: were the files you care about in `sent`?
3. `board` last: `skipped (...)` names the reason; the review
   itself is unaffected.

## FAQ seeds

- **Q:** Can I make a red cross-review block my merge?
  **A:** No. The binding posture is board-only advisory; wiring it
  into a gate violates the spec. A chair ruling backed by ledger
  evidence is the only upgrade path.
- **Q:** What does it mean when the seat finds nothing?
  **A:** `NO FINDINGS` is a compliant, recorded outcome
  (`status: clean`) — it is evidence, not silence.
- **Q:** Which seat should I use?
  **A:** Default `codex`. The first dogfood ledger (five runs,
  2026-07-28) recorded codex producing substantive findings on all
  three targets while antigravity returned `NO FINDINGS` on both
  of its — evidence behind the fixed default.
- **Q:** Does cross-review modify my repo?
  **A:** No. Git access is read-only (allowlisted subcommands
  only); the one write surface is the ledger row you append
  yourself.

## Notes & tips

- Same-diff runs across two seats are cheap comparative evidence —
  the T3 dogfood used exactly that pairing to test the default.
- The board thread id (`review-<branch-slug>-<stamp>`) is in every
  result; findings worth keeping go through the roundtable
  promotion flow, since board threads are TTL'd and the ledger row
  is what endures.
- Reviewing another branch: check it out in a detached scratch
  worktree and pass that worktree as `repo_root` — the resolver
  reviews whatever `HEAD` is.

## Design & extension

### Design decisions

- **D1 — composition over new machinery**: seat recipes, the
  invocation runner, the board, and the compiler's role budgets
  are the round table's; review.py only adds diff resolution,
  the brief, lint, and rendering.
- **D2 — read-only git with an everywhere-visible manifest**: the
  resolver allowlists `branch` / `merge-base` / `diff` /
  `rev-parse`; truncation is always declared.
- **D3 — mandatory format, flagged never repaired**.
- **D4 — advisory rendering, no exit-code coupling**.
- **D5 — per-run ledger rows, honest by contract**.
- **OPEN-1..3 (chair-ruled)** — fixed `codex` default, manual-only
  invocation, 60k diff cap ratified on the T3 ledger's diff-size
  evidence.

### Extension points

- **Seat rotation** — the ruled default is fixed `codex`, but
  rotation was explicitly left open pending more ledger evidence;
  `seat=` already accepts any recipe key.
- **Posture upgrade** — the only sanctioned path: accumulate
  ledger rows whose triaged finding quality earns a chair ruling.
- **New seats** — anything added to the round table's
  `SEAT_RECIPES` is immediately usable as a reviewer.
