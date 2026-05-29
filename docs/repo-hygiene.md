# Repo hygiene — bringing a workspace to pristine

A repeatable, **non-destructive** method for cleaning up a git repo or
multi-repo workspace that has accumulated drift: a diverged local
`main`, uncommitted edits, stale branches, and abandoned worktrees.

Pairs with [`scripts/audit_worktrees.sh`](../scripts/audit_worktrees.sh),
which *detects* the mess. This doc is how you *resolve* it safely.

## What "pristine" means

- `git status` is clean (modulo files you deliberately ignore).
- Local `main` == `origin/main` (no ahead/behind divergence).
- Every worktree has a live purpose (open PR) or is removed.
- No stale local/remote branches.
- **And nothing of value was lost getting there.**

## The method

> **inventory → preserve → sync → prune → verify**

The skill is entirely in *preserve* and *verify*. Anyone can
`reset --hard` and `worktree remove --force`; the discipline is
confirming what you'd throw away **before** you throw it.

### 1. Inventory

```bash
git status -sb                       # divergence + dirty/untracked
git log --oneline origin/main..HEAD  # local commits not pushed
git log --oneline HEAD..origin/main  # upstream commits not pulled
git worktree list
git branch                           # local branches
```

For each piece of drift, classify it before acting:
**valuable-and-unsaved**, **already-upstream (redundant)**, or
**stale/superseded**.

### 2. Preserve (the load-bearing step)

For anything that *might* be valuable and isn't yet on `origin`:

- **Uncommitted edits** → commit them on a fresh branch off
  `origin/main` and open a PR. Do this **before** any reset.
  - If `git switch -c …` aborts on untracked-file collisions (common
    after others' work merged upstream), use an isolated worktree
    instead: `git worktree add <tmp> origin/main -b <branch>`, copy the
    files in, commit, PR, remove the worktree.
- **An unpushed local commit** → decide: still wanted (rebase onto
  `origin/main` and PR it) or superseded (drop it — see prune). If the
  intent is still valid but the commit is stale, redo it *fresh* off
  current `main` rather than resurrecting a conflicting old commit.

### 3. Sync

Once everything valuable is preserved on a branch/PR:

```bash
git switch main
git reset --hard origin/main   # drops stale local commits; matches upstream
```

`reset --hard` overwrites tracked files and absorbs untracked
duplicates that are now tracked upstream. It will **not** delete
untracked files that aren't upstream — remove those explicitly only
after confirming they're preserved or worthless.

### 4. Prune — verify before deleting

**Worktrees.** Before removing, check each for unsaved value:

```bash
git -C <worktree> status -sb
git -C <worktree> log --oneline origin/main..HEAD   # unpushed commits?
```

- Clean + merged/redundant → `git worktree remove <path>`.
- Has uncommitted edits → confirm they're **newer** than `origin/main`
  before discarding. (Worktree files are often *older* — e.g. a
  `tasks.md` still saying "pending" where main says "done". That's not
  unsaved work; it's stale. Discard with `--force`.)

**Branches.** Distinguish *merged* from *unique content* — squash-merges
leave a branch looking unmerged even though its outcome shipped:

```bash
git branch --merged origin/main      # zero unique commits → safe: git branch -d
git branch --no-merged origin/main   # has commits → inspect, don't auto-delete
```

For a `--no-merged` branch, don't trust the commit count alone. Check
whether its **content** already reached `origin` another way, and what
spec/feature it maps to:

```bash
git log --oneline origin/main..<branch>   # what's unique
# map to a spec; if that spec is already 'complete'/shipped on main,
# the branch is dev-history, not an unshipped feature.
```

Delete with `-D` once confirmed superseded. Local branch deletion is
reflog-recoverable for ~90 days, so superseded-but-uncertain is
low-risk — but genuinely ambiguous branches are worth surfacing to a
human rather than auto-deleting. Delete merged remote branches too:
`git push origin --delete <branch>`.

### 5. Verify

```bash
git status -sb                 # clean; main == origin/main
git worktree list              # only what should remain
git branch                     # only main + live PR branches
bash scripts/audit_worktrees.sh
```

## Two rules that keep it safe

1. **Recover before you reset.** Never `reset --hard` /
   `worktree remove --force` until the valuable bits are committed on a
   branch/PR. Cleanup and data loss differ only by this ordering.
2. **"Unmerged" ≠ "unique content."** A branch can be `--no-merged` yet
   fully shipped (squash merge). Check content and spec status, not just
   the merge flag, before deleting.

## Worked example

See the 2026-05-29 attune workspace cleanup: a diverged `main` (1
stale federation commit + behind upstream), uncommitted SDD-template
edits, two at-risk worktrees, and 16 stale branches → resolved to
pristine. The template edits were *recovered* into a PR (not nuked);
worktree edits were confirmed stale before discarding; 5 "federation"
branches proved to be exact duplicates of the one dropped commit; the
remaining branches mapped to already-shipped specs. Net: dropped 1
commit, pruned 2 worktrees + 16 branches, recovered 1 piece of real
work, **lost nothing**.
