# Requirements — Vercel Noise Cleanup

**Status:** draft — awaiting approval before design.md and tasks.md

User-facing stories and the contracts they imply. See `decisions.md`
for context and the chosen resolution path. `design.md` and `tasks.md`
are intentionally omitted — they will be written after Patrick reviews
this file and decisions.md.

---

## Personas

- **Patrick (project owner)** — runs PRs daily; uses
  `statusCheckRollup` and `gh pr checks` to triage whether a PR is
  ready to merge. Needs every failure to mean something.
- **Contributor** — opens a PR, sees a failing check, and wonders
  whether to investigate or ignore it. Needs a clean signal.
- **Automated admin-merge tooling** — the `auto-approve-owner`
  workflow and the manual `gh pr merge --squash --admin` pattern
  both rely on the failure list being meaningful.

---

## User stories

### US-1 — Failures mean something

**As Patrick, when I look at the "failed checks" section of any PR, I
want every entry there to be a real signal I need to act on.**

Currently, `Vercel – attune-ai` appears as a failure on 100% of PRs
(confirmed across PRs #303, #306, #320, #343 and all 30 most-recent
closed PRs). The CLAUDE.md lessons section explicitly instructs agents
to ignore it. That documented workaround is the evidence this
requirement is unmet.

Acceptance criteria:

- After the fix is applied, a new PR's commit-status rollup contains
  zero entries with the substring `attune-ai` in the `context` field
  whose `state` is `failure`.
- Equivalently:
  `gh api repos/Smart-AI-Memory/attune-ai/statuses/<sha>`
  returns no entry matching `{"context": "Vercel – attune-ai",
  "state": "failure"}` for any new commit pushed after the fix.
- The CLAUDE.md lesson excerpt that says "every PR fails
  Vercel-attune-ai permanently (legacy preview), so the 'failures'
  field ... is always non-empty — Vercel – attune-ai is fail-ignore"
  is no longer accurate and can be removed in a follow-up cleanup.

### US-2 — Contributors see a clean check list

**As a contributor opening a pull request, I do not want to be
confused by a check that is expected to fail.**

Acceptance criteria:

- `gh pr checks <any-new-PR-number>` contains no row with name
  `Vercel – attune-ai`.
- The PR's GitHub UI shows the commit status rollup as either all
  green or failing only on checks that represent real problems with
  the contributor's code.

### US-3 — The working Vercel preview keeps working

**As Patrick, I want the working site preview — whichever Vercel
project it is — to continue posting a successful check and a
deployment URL on every PR.**

This is the non-regression requirement. The fix must not break the
`Vercel – website` check.

Acceptance criteria:

- After the fix, `Vercel – website` still appears as `state: success`
  on new PRs with the `target_url` pointing to a valid Vercel preview
  URL.
- The website's production deployment is unaffected (the fix targets
  the `attune-ai` project, not the `website` project).
- No Vercel preview comment that currently appears on PRs is removed.

---

## Acceptance criteria (summary)

| # | Criterion | Testable via |
|---|-----------|-------------|
| AC-1 | Zero `Vercel – attune-ai` failure statuses on new PRs | `gh api .../statuses/<sha>` |
| AC-2 | `Vercel – website` still posts `success` on new PRs | same API |
| AC-3 | Production site (`attune-ai.com` or equivalent) is reachable | `curl -I <url>` |
| AC-4 | No required status check pointing at `Vercel – attune-ai` exists | `gh api .../branches/main/protection` |

---

## Non-functional requirements

### NFR-1 — No required-check bypass needed

The `Vercel – attune-ai` check is currently **not** a required status
check for branch protection on `main`. The fix must not accidentally
make it one, and must not require bypassing branch protection to apply
(e.g. via `--admin` flags).

### NFR-2 — Reversible

The chosen fix must be reversible within one working day if it turns
out the `attune-ai` Vercel project was serving a purpose that this
spec did not discover (e.g. a staging environment not documented
anywhere in the repo).

### NFR-3 — No repo-level changes required

The fix lives entirely in Vercel project settings or the Vercel ↔
GitHub integration — no `.github/workflows/` edits, no branch
protection changes, no `.vercel/` config edits in the repo.

### NFR-4 — Agent-accessible documentation

The CLAUDE.md lesson that documents the workaround
("fail-ignore" pattern) must be updated after the fix lands, so
future agents don't carry stale instructions.
