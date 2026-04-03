---
type: task
name: task-git-workflow
tags: [git, workflow, branching, merge]
source: developer-guidance
---

# Task: Common git workflow operations

Step-by-step guides for the git operations that trip
people up most: merge conflicts, interactive rebase,
cherry-pick, stash management, and branch cleanup.

## Prerequisites

- Git installed and a repository initialized
- Basic familiarity with `git add`, `git commit`,
  `git push`

## Resolve a merge conflict

### 1. Start the merge

```
git merge feature-branch
```

Git reports which files conflict.

### 2. Open the conflicted file

Look for conflict markers:

```
<<<<<<< HEAD
your version of the code
=======
their version of the code
>>>>>>> feature-branch
```

### 3. Edit to keep the right version

Remove the markers and keep the code that should win.
Sometimes the answer is a combination of both sides.

### 4. Stage and commit

```
git add <resolved-file>
git commit
```

Git pre-fills the commit message. Accept it or add
context about how you resolved the conflict.

### 5. Verify

```
git log --oneline --graph -5
```

Confirm the merge commit appears with both parents.

## Interactive rebase (clean up before PR)

Use this to squash, reorder, or reword commits on your
**local, unpushed** branch.

### 1. Count your commits

```
git log --oneline main..HEAD
```

Note how many commits you have (e.g., 5).

### 2. Start the rebase

```
git rebase -i HEAD~5
```

Your editor opens with a list of commits.

### 3. Choose actions

| Action | What it does |
|---|---|
| `pick` | Keep the commit as-is |
| `squash` (or `s`) | Combine with the previous commit |
| `reword` (or `r`) | Keep the commit but edit the message |
| `drop` (or `d`) | Delete the commit entirely |

Change `pick` to your chosen action for each line, save,
and close the editor.

### 4. Resolve any conflicts

If commits conflict during replay, git pauses. Resolve
the conflict, then:

```
git add <resolved-file>
git rebase --continue
```

### 5. Force-push your branch

Because rebase rewrites history, you need:

```
git push --force-with-lease
```

Use `--force-with-lease` instead of `--force` -- it
refuses to push if someone else has pushed to your branch
since your last fetch.

## Cherry-pick a commit

Copy a single commit from one branch to another without
merging the entire branch.

### 1. Find the commit hash

```
git log --oneline other-branch -10
```

### 2. Switch to your target branch

```
git checkout main
```

### 3. Cherry-pick

```
git cherry-pick abc1234
```

### 4. Handle conflicts if any

Same process as merge conflict resolution: edit, stage,
then:

```
git cherry-pick --continue
```

### 5. Verify

```
git log --oneline -3
```

The cherry-picked commit appears with a new hash.

## Stash management

Temporarily shelve uncommitted changes when you need to
switch branches.

### Save your work

```
git stash push -m "work in progress on login form"
```

Always use `-m` with a description. Unnamed stashes
pile up and become unidentifiable.

### List stashes

```
git stash list
```

### Restore a stash

```
git stash pop
```

This applies the most recent stash and removes it from
the stash list. If you want to keep the stash:

```
git stash apply stash@{0}
```

### Drop a stash you no longer need

```
git stash drop stash@{0}
```

## Branch cleanup

### Delete a merged local branch

```
git branch -d feature-branch
```

The `-d` flag refuses to delete unmerged branches.

### Delete a remote branch

```
git push origin --delete feature-branch
```

### Prune stale remote tracking refs

```
git fetch --prune
```

## Verification checklist

After any of these operations:

- [ ] `git status` shows a clean working tree
- [ ] `git log --oneline --graph -10` shows the
      expected history
- [ ] Tests still pass (`pytest` or your test runner)
- [ ] No unresolved conflict markers left in code

## Want to learn more?

- Say **"what are git workflow strategies?"** for branch
  strategy concepts (trunk-based vs feature branch)
- Say **"show me all git commands"** for the full
  reference with risk ratings
- Try **/release** to prepare a release branch with
  automated checks
- Try **/code-quality** to verify pre-commit hooks pass
  before pushing

## Related Topics

- **Concept**: Git workflow -- branch strategies, merge
  vs rebase, and conflict resolution philosophy
- **Reference**: Git workflow -- full command catalog
  with risk ratings and safer alternatives
- **Quickstart**: Git workflow -- 5-step merge conflict
  resolution
