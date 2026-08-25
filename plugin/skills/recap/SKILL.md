---
name: recap
description: "Structured end-of-session review — what shipped, where the time went, lessons, risks, open items — then persist the cross-session handoff starter. Triggers on: recap, end of session review, session retro, wrap up, what did we get done today."
---

# End-of-Session Review

**IMPORTANT: Start your response by telling the user:**

> **Recap** — Reviewing this session (what shipped, detours, lessons,
> risks, open items), then persisting the cross-session handoff.

## What It Does

Writes a review of THIS session — the conversation you are in right
now — then rewrites `.attune/next_session_starter.md` so the next
session starts current. Everything in it must be grounded in what
actually happened: real files touched, real commands run, real
outcomes. If a line could apply to any session, cut it.

Prefer this over an ad-hoc summary any time the session is winding
down.

## Before Writing

Skim back over the session and collect:

- Deliverables and their verified end state (deployed? pushed?
  tested? or only claimed?)
- Detours: what took longer than expected, and the eventual root
  cause
- Anything left half-done, temporary, or dev-only
- Credentials, config, or infrastructure created along the way —
  especially anything now orphaned
- Ideas that surfaced but weren't acted on

If a repo is available, `git log --oneline` over the session's
commits is a quick honesty check on what actually shipped.

## Structure

Use these sections, in this order. Drop any section with nothing
real to say — an empty section padded with filler is worse than no
section.

### What shipped

Concrete deliverables, each with its verified end state ("live and
tested", "pushed but not deployed", "written but unreviewed").
Distinguish what was verified from what is assumed — claims carry
their basis.

### Where the time went

Two to four sentences of honest narrative: the session's arc, the
main detour, and its root cause. A root cause named here doesn't
get re-debugged later.

### Lessons

Generalizable takeaways, phrased so they transfer to future
sessions. Prefer "check X before debugging Y" over a play-by-play.
A lesson worth keeping permanently belongs in `.claude/lessons.md`
(this repo's corpus) — say so when one qualifies.

### Opportunities

Forward-looking: improvements, features, or cleanups the work
surfaced but didn't include. Make each one actionable. This section
is for genuinely good ideas, not an obligation to brainstorm.

### Risks / watch items

Things that could bite later: temporary states that read as
permanent, orphaned credentials or secrets, stale local copies,
dev-phase settings that must change before production. Name the
trigger for when each needs attention.

### Open items

What remains, who owns each item (user, Claude, or a third party),
and whether anything is blocking.

## Tone

Honest over flattering. If something failed, is fragile, or was
abandoned, say so plainly — the review's value is that a future
reader can trust it. Keep the whole review readable in about a
minute; selectivity beats compression.

## Persist The Handoff

After presenting the review, carry its substance forward so the
next session starts current — this is the second half of the job,
not an optional extra.

The handoff file is `.attune/next_session_starter.md` at the repo
root (the git toplevel). At the next session start,
`starter_prompt_nudge.py` (SessionStart hook) surfaces it, and
`starter_reconciler.py` fact-checks every named thread against
git / `gh` / PyPI and prints a freshness banner. Write threads by
name so the reconciler can verify them:

- PR numbers as `#1234` — checked MERGED / OPEN / CLOSED via `gh`.
- Full branch names with their prefix (`release/`, `hotfix/`,
  `claude/`, `feat/`, `fix/`) — checked exists / gone on origin.
- Exact `X.Y.Z` versions — compared against the latest on PyPI.
- Spec paths as `docs/specs/<slug>` — cross-read against the
  spec's status line (a queued item on a CLOSED spec gets a
  warning).

A thread the file doesn't name can't be verified — vague references
defeat the machinery. The reconciler also warns when `main` has
newer merges than the starter's newest named PR, so naming the most
recent PR you know about keeps that check honest.

Rewrite the whole file each run (it describes the present; git
holds history) with these sections:

- **Headline** — the single next action, stated so it's checkable.
- **State (verified this session)** — what works now, with how it
  was verified.
- **Open threads** — numbered, each with its named artifacts and
  who owns it.
- **Gotchas** — environment quirks, dev-only settings, anything
  that reads as permanent but isn't.

After writing, stamp provenance so the reconciler trusts the file:

```bash
python src/attune/hooks/scripts/starter_reconciler.py --stamp
```

The stamp records repo / branch / HEAD SHA / timestamp as
frontmatter. An unstamped starter gets a "no provenance" warning on
every verdict; a stamped one older than 48 hours is flagged STALE;
a starter stamped for a DIFFERENT repo gets verification skipped
entirely rather than plausibly-wrong verdicts.

Commit and push the update following the session's branch
convention — an unpushed handoff dies with the machine it was
written on.

There is also a global `~/.attune/next_session_starter.md`, but in
this repo it is a retiring LEGACY surface (surfaced only when no
project-scoped handoff exists) — prefer the project-local file. For
branch-scoped multi-step work, the tracked
`docs/handoffs/<branch-slug>.md` convention (from
`templates/agent-handoff.md`) is surfaced first by the same hook
and remains the right home for per-branch handoffs.

If there is no repo (pure conversation), skip this section — the
in-chat review is the whole deliverable.
