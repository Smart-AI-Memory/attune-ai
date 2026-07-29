# Cross Review

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

<!-- attune-generated: source_hash=68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d feature=cross-review kind=how-to generated_at=2026-07-29 -->
