---
type: task
name: cross-review-task
feature: cross-review
depth: task
generated_at: 2026-07-29T00:49:32.207827+00:00
source_hash: 68691bdb8533cb43d997bbec5457fa5ba004c65c48af6cfc90d4d4c8c87a638d
status: generated
---

# One-shot second-opinion diff review by a different-model seat, advisory only

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
