---
type: quickstart
name: task-git-workflow
tags: [git, workflow, branching, merge]
source: developer-guidance
---

# I Have a Merge Conflict

Five steps to resolve it and get back to work.

## Step 1: See which files conflict

```
git status
```

Files marked `both modified` have conflicts.

## Step 2: Open the first conflicted file

Look for these markers:

```
<<<<<<< HEAD
your version
=======
their version
>>>>>>> feature-branch
```

Everything between `<<<<<<<` and `=======` is your code.
Everything between `=======` and `>>>>>>>` is theirs.

## Step 3: Decide what to keep

Delete the markers and keep the right code. Sometimes
that means keeping yours, sometimes theirs, sometimes a
blend of both.

```python
# Before (conflicted)
<<<<<<< HEAD
def get_user(user_id: int) -> User:
    return db.query(User).get(user_id)
=======
def get_user(user_id: int) -> User | None:
    return db.query(User).filter_by(id=user_id).first()
>>>>>>> feature-branch

# After (resolved -- kept the better return type
# and the safer query)
def get_user(user_id: int) -> User | None:
    return db.query(User).filter_by(id=user_id).first()
```

Repeat for every conflict in the file, then repeat for
every conflicted file.

## Step 4: Stage and commit

```
git add .
git commit
```

Git fills in a merge commit message. Accept it or add a
note about how you resolved the conflict.

## Step 5: Verify nothing broke

```
git log --oneline --graph -5
pytest
```

The merge commit should appear in the log, and your tests
should still pass.

**Done.** The conflict is resolved and committed.

## Quick fixes for common situations

| Situation | What to do |
|---|---|
| You want to abort the whole merge | `git merge --abort` |
| You know their version is correct for a file | `git checkout --theirs path/file && git add path/file` |
| You know your version is correct for a file | `git checkout --ours path/file && git add path/file` |
| You accidentally committed a bad resolution | `git revert HEAD` to undo the merge commit |
| Conflict happened during rebase, not merge | Resolve the file, then `git add . && git rebase --continue` |

## Want to learn more?

- Say **"what are git workflow strategies?"** for branch
  strategy concepts -- trunk-based, feature branch, and
  gitflow
- Say **"walk me through rebase and cherry-pick"** for
  the full step-by-step guide to all git operations
- Say **"show me all git commands"** for the complete
  reference with risk ratings and safer alternatives
- Try **/release** to prepare a release branch with
  automated health checks
- Try **/code-quality** to verify pre-commit hooks pass
  before pushing

## Related Topics

- **Concept**: Git workflow -- branch strategies, merge
  vs rebase, and conflict resolution philosophy
- **Task**: Git workflow -- step-by-step guides for
  conflicts, rebasing, cherry-pick, and stash
- **Reference**: Git workflow -- full command catalog
  with risk ratings and safer alternatives
