# Triage a code-quality report

> **Canonical source:** [`.help/templates/code-quality/task.md`](https://github.com/Smart-AI-Memory/attune-ai/blob/main/.help/templates/code-quality/task.md). Edit there; mirror here.

Use this procedure after running `/code-quality` to decide what to fix now, what to fix in this PR, what to defer, and what to ignore.

## Pick your scope first

The scope you choose determines depth, time, and signal density. Pick before you run.

| Scope | Recommended depth | Time | Best for |
|-------|-------------------|------|----------|
| Single file | `quick` | seconds | Spot-check during edits |
| Module / subdirectory | `standard` | ~1 min | Pre-PR review |
| Whole repo | `deep` | ~3 min | Inherited code, periodic baselines |

If you don't know which to pick, start with `standard` on the module you touched in this PR. Going wider rarely surfaces issues you'll act on; going narrower misses cross-file architecture problems.

## Read the summary score

The first line of the report is a 0–100 health score. Use it to triage urgency, not as a metric to optimize.

| Score | What it means | Next action |
|-------|---------------|-------------|
| 90–100 | Excellent | Ship. Skim findings; fix anything trivial inline. |
| 75–89 | Good | Fix Security findings in this PR; queue Quality for follow-up. |
| 50–74 | Needs work | Stop and triage before merging. Likely 1–2 categories of systemic issues. |
| 0–49 | Poor | Don't merge. Open issues for each finding category and address them as separate PRs. |

The score averages across the four reviewers, so a 78 can hide a critical Security finding. Always read the Security section before trusting the score.

## Triage by section

The report has four sections, in this priority order.

**Security.** Treat every finding as fix-now unless you can prove it's a false positive. The security-reviewer catches injection vectors, unsafe deserialization, hardcoded credentials, and auth bypasses. If a finding cites a file and line, open that file before deciding to defer.

**Quality.** Includes likely bugs (mutable defaults, broad exceptions, null dereferences) and style issues. Fix likely bugs in this PR; style issues can defer to a cleanup sweep. The reviewer doesn't distinguish between the two — you do, by reading the description.

**Performance.** Static analysis catches O(n²) loops, leaky resource handling, and obvious memory anti-patterns. Defer unless the finding is in a hot path or marked high severity. Profiling beats static analysis here, so don't over-invest.

**Architecture.** High coupling, circular imports, god classes, module sprawl. Almost never fix in the same PR as a feature — these are refactor PRs. Open an issue and move on unless the finding is blocking the feature itself.

## What to do next

When findings cross feature boundaries, follow up with the matching specialist:

- Security findings that need deeper investigation: `/security-audit` on the affected files.
- Likely-bug findings in code you're about to extend: `/bug-predict` to surface similar patterns.
- Architecture findings that warrant a refactor: `/refactor-plan` on the implicated module.
- Test-coverage gaps surfaced by Quality: `/smart-test` to fill them.

When you've fixed the highest-priority findings, re-run `/code-quality` on the same scope to confirm the score improved and no new findings emerged.

## Verify success

Triage is complete when:

- Every Security finding is either fixed, has an issue link, or has a documented false-positive justification.
- Quality findings split cleanly into "fixed in this PR" and "tracked in issue/backlog."
- Performance and Architecture findings are either fixed, deferred with a link, or explicitly accepted.
- A fresh `/code-quality` run on the same scope shows no new findings introduced by your fixes.
