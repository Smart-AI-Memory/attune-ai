# Spec: consolidate-claude-md-lessons

> **Status:** complete (2026-06-06, PRs #646 + #647). All
> high-redundancy clusters consolidated (435→~327 lessons, −1202
> lines, ~15%); editorial ceiling reached. Domain singletons left
> intact by design — see [decisions.md](decisions.md) D1.

## Goal

Cut `.claude/CLAUDE.md`'s Lessons Learned section (402 lessons /
**6,973 lines**, loaded every session) by merging genuine
redundancy — **without losing a distinct lesson**. Target a
~30–40% line cut, not an arbitrary lesson cap. Efficiency, not
amputation.

## Cluster inventory (ranked by consolidation yield)

Counts overlap — a lesson can match several keywords — so these are
**not additive**; they're a heat map of where redundancy concentrates.

| Cluster      | Lessons | Lines |
|--------------|--------:|------:|
| test         | 45      | 628   |
| ci           | 31      | 550   |
| workflow     | 28      | 510   |
| path         | 27      | 428   |
| merge        | 18      | 336   |
| worktree     | 10      | 308   |
| windows      | 12      | 223   |
| spec         | 12      | 219   |
| sdk          | 12      | 219   |
| tag          | 14      | 210   |
| coverage     | 7       | 157   |
| pypi         | 7       | 143   |
| gh pr        | 8       | 125   |
| security     | 6       | 123   |
| pre-commit   | 9       | 141   |
| stash        | 5       | 97    |
| ruff         | 7       | 94    |
| rebase       | 4       | 90    |
| css          | 4       | 86    |
| squash       | 5       | 80    |
| xdist        | 3       | 76    |
| codeql       | 5       | 74    |

**60 lessons** carry an explicit cross-reference ("Pairs with…",
"Companion…", "same root cause…", "extends the existing…") — these
self-declare their redundancy and are the safest, highest-yield
merges.

## Method (batch-assisted, reviewable PR)

Extract is batch; **merge is judgment** (no shell can safely delete
a lesson); verify is batch.

```bash
# EXTRACT a cluster to a working file (change KW)
cd /Users/patrickroebuck/attune-ai
git show origin/main:.claude/CLAUDE.md > /tmp/cm.md
KW='worktree'
awk -v kw="$KW" '/^- \*\*/{b=(tolower($0)~tolower(kw))} b' /tmp/cm.md > /tmp/cluster.md
grep -cE '^- \*\*' /tmp/cluster.md   # lesson count
wc -l < /tmp/cluster.md              # line count
```

Then: read `/tmp/cluster.md`, write consolidated lessons, apply to
`CLAUDE.md` with the Edit tool (not a shell splice — safer on a 7k
file). Verify per cluster:

```bash
# after edits, on the working copy
grep -cE '^- \*\*' .claude/CLAUDE.md   # lesson-count delta
wc -l .claude/CLAUDE.md                # line delta
# dangling cross-refs: every "Pairs with X" should still resolve
```

## Execution order

Work cross-linked lessons first (lowest risk), then the largest
clusters. One docs PR, cluster-by-cluster commits so each merge is
reviewable in isolation. See [tasks.md](tasks.md).

## Guardrails (the bar Patrick set)

- Merge genuine redundancy only; **never drop a distinct lesson** —
  fold specifics into sub-bullets under a richer header.
- Preserve every still-true cross-reference.
- Behavior-neutral: this is editorial, not a rules change.
