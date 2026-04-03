---
type: reference
name: task-git-workflow
tags: [git, workflow, branching, merge]
source: developer-guidance
---

# Reference: Git commands and conventions

Complete catalog of common git scenarios with commands,
risk ratings, and safer alternatives.

## Conflict resolution

| Scenario | Command | Notes |
|---|---|---|
| Merge a branch | `git merge feature` | Creates a merge commit |
| Abort a failed merge | `git merge --abort` | Restores pre-merge state |
| See conflicted files | `git diff --name-only --diff-filter=U` | Lists only unresolved files |
| Accept theirs for one file | `git checkout --theirs path/file` | Overwrites your version |
| Accept yours for one file | `git checkout --ours path/file` | Overwrites their version |
| Mark a file resolved | `git add path/file` | Stages the resolved version |

## Rebase

| Scenario | Command | Reversible? | Risk |
|---|---|---|---|
| Rebase onto main | `git rebase main` | Yes (reflog) | Low if unpushed |
| Interactive rebase | `git rebase -i HEAD~N` | Yes (reflog) | Medium -- rewrites history |
| Abort mid-rebase | `git rebase --abort` | N/A | Safe |
| Continue after conflict | `git rebase --continue` | N/A | Safe |
| Skip a conflicting commit | `git rebase --skip` | Yes (reflog) | Medium -- drops a commit |

## Cherry-pick

| Scenario | Command | Reversible? | Risk |
|---|---|---|---|
| Pick one commit | `git cherry-pick <hash>` | Yes (`git revert`) | Low |
| Pick a range | `git cherry-pick A..B` | Yes (`git revert`) | Medium -- may conflict |
| Pick without committing | `git cherry-pick -n <hash>` | Yes (`git checkout .`) | Low |
| Abort mid-cherry-pick | `git cherry-pick --abort` | N/A | Safe |

## Stash

| Scenario | Command | Reversible? | Risk |
|---|---|---|---|
| Stash with message | `git stash push -m "desc"` | Yes (`git stash pop`) | Low |
| Stash including untracked | `git stash push -u -m "desc"` | Yes (`git stash pop`) | Low |
| List all stashes | `git stash list` | N/A | Safe |
| Apply most recent | `git stash pop` | N/A | Low |
| Apply specific stash | `git stash apply stash@{N}` | N/A | Low |
| Drop a stash | `git stash drop stash@{N}` | No | Medium -- data lost |
| Drop all stashes | `git stash clear` | No | High -- all stashed work lost |

## Recovery with reflog

| Scenario | Command | Notes |
|---|---|---|
| View recent HEAD history | `git reflog -20` | Shows where HEAD has been |
| Recover after bad rebase | `git reset --hard HEAD@{N}` | N from reflog output |
| Recover a deleted branch | `git checkout -b name HEAD@{N}` | Must find the commit in reflog |
| Find a lost commit | `git reflog --all \| grep "keyword"` | Searches all ref updates |

## Bisect (find the breaking commit)

| Scenario | Command | Notes |
|---|---|---|
| Start bisect | `git bisect start` | Enters bisect mode |
| Mark current as bad | `git bisect bad` | HEAD has the bug |
| Mark a known-good commit | `git bisect good <hash>` | Git checks out the midpoint |
| Mark each step | `git bisect good` or `git bisect bad` | Repeat until git finds the culprit |
| End bisect | `git bisect reset` | Returns to original branch |
| Automate with a test | `git bisect run pytest tests/test_foo.py` | Fully automated binary search |

## Dangerous commands and safer alternatives

| Dangerous command | What it does | Safer alternative | Why it's safer |
|---|---|---|---|
| `git push --force` | Overwrites remote history | `git push --force-with-lease` | Refuses if remote has new commits |
| `git reset --hard` | Discards all uncommitted changes | `git stash push -m "backup"` then reset | Changes are recoverable from stash |
| `git checkout .` | Discards all unstaged changes | `git stash push -m "backup"` | Same -- recoverable |
| `git clean -fd` | Deletes all untracked files | `git clean -fdn` (dry run first) | Shows what would be deleted |
| `git branch -D` | Force-deletes unmerged branch | `git branch -d` | Refuses if branch is not merged |
| `git rebase` on shared branch | Rewrites commits others have pulled | `git merge` | Preserves shared history |

## Reset vs revert

| Command | Modifies history? | Safe on shared branches? | Use case |
|---|---|---|---|
| `git revert <hash>` | No (adds a new commit) | Yes | Undo a commit that's already pushed |
| `git reset --soft HEAD~1` | Yes (moves HEAD back) | No -- only for unpushed | Undo the last commit, keep changes staged |
| `git reset --mixed HEAD~1` | Yes (moves HEAD back) | No -- only for unpushed | Undo the last commit, keep changes unstaged |
| `git reset --hard HEAD~1` | Yes (moves HEAD back) | No -- only for unpushed | Undo the last commit and discard changes |

## Branch naming conventions

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<short-description>` | `feat/user-auth` |
| Bug fix | `fix/<issue-or-description>` | `fix/login-timeout` |
| Hotfix | `hotfix/<description>` | `hotfix/security-patch` |
| Release | `release/<version>` | `release/2.1.0` |
| Chore | `chore/<description>` | `chore/update-deps` |
| Docs | `docs/<description>` | `docs/api-reference` |

Use lowercase, hyphens, no spaces. Keep names under 50
characters.

## Commit message conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body -- explain why, not what>

<optional footer -- BREAKING CHANGE, issue refs>
```

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build, CI, tooling changes |
| `perf` | Performance improvement |
| `ci` | CI configuration changes |

**Summary rules:**

- Use imperative mood ("add" not "added")
- Keep under 70 characters
- No period at the end
- Reference issue numbers in the footer (`Closes #42`)

## Want to learn more?

- Say **"what are git workflow strategies?"** for branch
  strategy concepts and trade-offs
- Say **"how do I resolve a merge conflict?"** for the
  step-by-step walkthrough
- Say **"I have a merge conflict"** for the 5-step
  quickstart
- Try **/release** to automate release branch preparation
  with health checks and changelogs
- Try **/code-quality** to verify pre-commit hooks and
  commit conventions

## Related Topics

- **Concept**: Git workflow -- branch strategies, merge
  vs rebase, and conflict resolution philosophy
- **Task**: Git workflow -- step-by-step guides for
  conflicts, rebasing, cherry-pick, and stash
- **Quickstart**: Git workflow -- 5-step merge conflict
  resolution
