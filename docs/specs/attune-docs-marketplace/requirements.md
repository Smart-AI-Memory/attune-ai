# attune-docs Marketplace — Keep, Automate, or Retire

**Status:** D1 ratified 2026-06-22 — Option A (retire + consolidate)
**Owner:** Patrick + agent
**Created:** 2026-06-22

---

## Problem

The `Smart-AI-Memory/attune-docs` Claude Code plugin marketplace was
created in the 2026-04-08 two-marketplace split to give attune-help and
attune-author an independent release cadence and a distinct "help
platform" marketing story, separate from attune-ai the developer tool.

In practice the split's core promise was never delivered. The
marketplace is hand-synced, has no CI, and has drifted badly — new
users following the documented quickstart installed plugins roughly 15
minor versions behind the current release.

This spec decides what to do with it: **keep and automate**, or
**retire and consolidate**.

---

## Evidence (gathered 2026-06-22)

- **Frozen:** last commit `2026-05-06`; ~9 commits total, all from
  April–early May.
- **No automation:** the repo has no `.github/workflows` — every
  version bump is a manual copy step.
- **Stale plugin versions in the marketplace manifest:**

  | Plugin | attune-docs marketplace | PyPI latest | attune-ai pin |
  |--------|-------------------------|-------------|---------------|
  | attune-author | 0.6.2 | 0.21.0 | `>=0.21.0,<0.22` |
  | attune-help | 0.10.2 | 0.11.1 | `>=0.10.0` |
  | attune-gui | 1.1.1 | — | — |

- **Architecture:** attune-help and attune-author are Python packages
  on PyPI; the attune-docs plugins are thin Claude Code wrappers
  (plugin.json + skills/commands) around those packages. PyPI is the
  primary artifact; the marketplace adds the Claude-Code-native UX.
- **attune-ai's own marketplace is clean** — it lists only `attune-ai`
  (the extraction worked).
- **Strategic drift:** the stated direction since 2026-06-04 is to
  consolidate the whole docs/web surface onto `attune-ai.dev`. The
  April "two distinct product lines" framing has softened.
- **Weak usage signal:** overall project telemetry is ~0 real users;
  no open issues or PRs on attune-docs.

---

## What the split was meant to buy (and whether it did)

| Must-have from the April plan | Delivered? |
|-------------------------------|------------|
| Independent release cadence for all three plugins | No — attune-docs is frozen, not cadenced |
| Frictionless help-builder install (one marketplace) | Partially — works, but installs stale versions |
| Clean two-product marketing story | Undercut by the attune-ai.dev consolidation direction |
| All funnels work without cross-contamination | Yes (attune-ai marketplace is clean) |

---

## Goal

A single ratified decision, recorded in `decisions.md`, on the future
of the attune-docs marketplace — with a small, scoped execution plan
for whichever option is chosen. No code change ships until the decision
is ratified.

---

## Non-goals

- The website quickstart mitigation (lead with PyPI, flag the stale
  marketplace) is already handled in a separate website-only PR. This
  spec does not re-litigate that.
- Re-designing the PyPI packaging of attune-help / attune-author.

---

## Options

### Option A — Retire attune-docs, consolidate (recommended)

Fold the attune-help / attune-author Claude Code plugins back into the
`attune-ai` marketplace (or under `attune-ai.dev`), archive the
`attune-docs` repo, and update all references.

- **Pros:** matches the attune-ai.dev consolidation direction; removes
  a CI-less manual-sync liability permanently; one front door.
- **Cons:** reverses a deliberate April decision; reopens the
  "one suite vs two product lines" framing; one-time migration +
  reference cleanup; users who added the attune-docs marketplace need a
  migration note.

### Option B — Keep the split, automate it

Add a release-triggered CI job to attune-docs that bumps each plugin's
version on every attune-help / attune-author release, and bump the
three plugins to current now.

- **Pros:** preserves the independent-product story; least conceptual
  change.
- **Cons:** real release-engineering work in a second repo; runs
  against the consolidation grain; keeps two marketplaces to reason
  about.

### Option C — Status quo

Leave it stale.

- **Rejected:** it is the documented front door and actively ships
  ~15-version-stale plugins. Not acceptable even with the website
  mitigation in place.

---

## Recommendation

**Option A (retire + consolidate).** The split is a maintenance
liability whose stated benefit (independent cadence) is unrealized, and
the project is already consolidating onto attune-ai.dev. Retiring
attune-docs removes a structurally drift-prone surface rather than
investing release-engineering effort to prop up a direction that has
since changed.

Pick Option B only if the "two distinct product lines" marketing story
is something you still actively want.

---

## Open decisions (to ratify in decisions.md)

- **D1 — Direction:** A (retire/consolidate), B (keep + automate), or C.
- **D2 — If A:** target home for the help/author plugins —
  `attune-ai` marketplace vs `attune-ai.dev`.
- **D3 — If A:** migration note + redirect/README on the archived
  attune-docs repo so existing marketplace-adders aren't stranded.
- **D4 — If B:** sync trigger shape (release webhook vs scheduled job)
  and which repo owns it.

---

## Acceptance criteria

- D1 ratified in `decisions.md`.
- A scoped tasks.md exists for the chosen option.
- All in-repo references to the attune-docs marketplace are consistent
  with the decision (website already mitigated; docs/README updated to
  match the final direction).
