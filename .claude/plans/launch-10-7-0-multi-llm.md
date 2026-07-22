# 10.7.0 Launch — The Multi-LLM Release

**Created:** 2026-07-22
**Version note:** chair renumbered the release 10.6.0 → 10.7.0 in-session 2026-07-22 (multi-LLM wave widens the scope); the RELEASE_10_6_0_drafts.md doc and Monday-runbook tag references need the same rename at the sitting.
**Source:** /brainstorm session (chair-ratified direction)

## Problem

10.7.0 ships Monday 07-27 with a genuine story — one plugin, three
AI coding agents (Claude, Codex, Antigravity/Gemini) sharing memory,
handing off work, and giving second opinions — but the launch
materials (Draft A/B in `docs/process/RELEASE_10_6_0_drafts.md`)
predate the story's arrival and read as a feature roundup. The
story's proof points (handoff round-trip, Codex canary, Antigravity
probe) are honestly UNPROBED until after the lift.

## Goals (chair-ratified 2026-07-22)

- Must: launch ARTICLE — the multi-LLM story with `[RECEIPT: …]`
  placeholder slots filled from Monday's real transcripts. (This
  jumps the queue ahead of the planned v10 "deletion release"
  article — explicit chair call, recorded here.)
- Must: LinkedIn post — Draft B reworked around the story; the
  honesty-gate items rendered as a visible checklist for the
  chair's post-time ruling.
- Must (weighted): docs feature pages for
  cross-provider-session-handoff and cross-review via the
  author-feature single-source playbook — these ARE the T4 tasks of
  both specs. Staged on branches; the doc-import gate correctly
  blocks them from main until the tools merge.
- Must (weighted): website updates staged as ready-to-apply diffs
  (feature page + counts). Counts are verified against LIVE
  registries only POST-lift per website-content-accuracy;
  `website/lib/features.ts` is canonical.
- Nice-to-have: roundtable demo walkthrough (live today — can be
  recorded any time this week).

## End State

Four staged artifacts + one runbook line by Saturday night. Nothing
published early; no claim without a receipt. **Fire is TUESDAY
07-28, after the lift and live receipts** — the receipt transcripts
are part of the story, not a footnote (chair-ratified over a
Monday architecture-framed fire).

## Approach

1. Wed: article draft (story spine: provider boundary is where
   context dies; receipts discipline as differentiator; roundtable
   ruling provenance as the meta-story — the table picked its own
   next features).
2. Wed/Thu: Draft B rework + honesty-gate checklist.
3. Thu/Fri: feature-page masters for handoff + cross-review
   (author-feature playbook, code-verified against the held
   branches #1605/#1607); staged branches, PR post-lift.
4. Fri/Sat: website diffs staged (features.ts + counts + multi-LLM
   feature page); apply + verify post-lift.
5. Mon (sitting, already runbooked): lift, receipts, publish
   10.7.0.
6. Tue: apply website/docs PRs → fill receipt slots → chair rules
   the honesty gate → publish article + post.

## Next Steps

- [ ] Article draft with receipt placeholders
- [ ] Draft B rework + honesty checklist
- [ ] Feature-page master: cross-provider-session-handoff (spec T4)
- [ ] Feature-page master: cross-review (spec T4, OPEN-2 cadence
      language stays provisional until the Monday ruling)
- [ ] Website diff branch (counts verified post-lift only)
- [ ] Starter: Tuesday fire sequence (done same evening as this
      plan)

## Open Questions

- Honesty-gate ruling on Draft B — chair, at post time.
- Whether the roundtable demo records this week (nice-to-have).
- Article venue/order: this replaces v10 "deletion release" as next
  article; deletion-release drops to the article backlog.
