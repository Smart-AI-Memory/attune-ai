---
type: concept
name: task-git-workflow
tags: [git, workflow, branching, merge]
source: developer-guidance
---

# Concept: Git workflow strategies

## What

A git workflow is the branching, merging, and release
strategy your team follows. Choosing the right one
determines how easily you ship code, how often you hit
conflicts, and how painful rollbacks are. The three major
strategies are trunk-based development, feature branching,
and gitflow.

## Why

The wrong workflow creates friction at every step. A solo
developer using gitflow drowns in ceremony. A 20-person
team committing directly to `main` steps on each other
constantly. The workflow should match team size, release
cadence, and risk tolerance.

## The three strategies

| Strategy | Best for | Branch lifetime | Release cadence | Conflict risk |
|---|---|---|---|---|
| Trunk-based | Small teams, CI/CD | Hours | Continuous | Low (small diffs) |
| Feature branch | Most teams | Days | On merge | Medium |
| Gitflow | Regulated releases | Days to weeks | Scheduled | High (long-lived branches) |

### Trunk-based development

Everyone commits to `main` (or merges very short-lived
branches). Code ships continuously. Feature flags hide
incomplete work.

- **Pro:** Minimal merge conflicts, fast feedback
- **Con:** Requires strong CI and feature flags
- **Use when:** You deploy multiple times per day

### Feature branching

Each feature gets a branch off `main`. When done, the
branch is merged back via pull request.

- **Pro:** Isolates work, enables code review
- **Con:** Long-lived branches diverge and conflict
- **Use when:** You review code before merging

### Gitflow

Separate branches for `develop`, `release/*`, `hotfix/*`,
and `main`. Releases are cut from `develop`, stabilized,
then merged to `main`.

- **Pro:** Clear release process, parallel release prep
- **Con:** High ceremony, frequent merge conflicts
- **Use when:** You have scheduled releases with QA gates

## Merge vs rebase

| Approach | What it does | When to use | Trade-off |
|---|---|---|---|
| Merge commit | Creates a merge node preserving both histories | Shared branches, PRs | Cluttered history but safe |
| Rebase | Replays your commits on top of the target | Local feature branches before PR | Clean history but rewrites commits |
| Squash merge | Combines all branch commits into one | Feature branches with messy history | Clean main, loses per-commit detail |

**The golden rule:** Never rebase commits that other people
have pulled. Rebase is for your local, unpushed work.

## Conflict resolution philosophy

Conflicts are not failures -- they are information. Two
people changed the same thing, and git is asking you to
decide which version wins. The best conflict resolution
happens *before* the conflict:

- **Pull often.** The longer you wait, the more your
  branch diverges.
- **Keep branches short-lived.** Merge within days, not
  weeks.
- **Communicate.** If two people are editing the same
  file, talk before branching.

When you do hit a conflict, resolve it by understanding
*why* both changes were made, not by blindly picking one
side.

## Want to learn more?

- Say **"how do I resolve a merge conflict?"** for the
  step-by-step guide
- Say **"show me all git commands"** for the full
  reference with dangerous-command warnings
- Say **"I have a merge conflict"** for the 5-step
  quickstart
- Try **/release** when preparing a release branch
- Try **/code-quality** to check for pre-commit hook
  issues before merging

## Related Topics

- **Task**: Git workflow -- step-by-step guides for
  conflicts, rebasing, cherry-pick, and stash
- **Reference**: Git workflow -- full command catalog
  with risk ratings and safer alternatives
- **Quickstart**: Git workflow -- 5-step merge conflict
  resolution
