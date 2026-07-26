# 10.6.0 Demo Outline — "One Plugin, Three AI Coding Agents"

**Created:** 2026-07-23 · **Revised:** 2026-07-23 per roundtable
review `q-demo-outline-review-001` (chair-ruled amendments A1–A8;
report in [docs/reports/roundtable/](../reports/roundtable/q-demo-outline-review-001.md))
· **Status:** staged (records after the 07-27 lift + receipts;
releases launch week with the Tuesday 07-28 fire) · **Format:**
recorded screen demo, **~7:45 target**, plus a ~2-minute social
cut · **Companion materials:**
[LAUNCH_10_6_0_article_draft.md](LAUNCH_10_6_0_article_draft.md),
[RELEASE_10_6_0_drafts.md](RELEASE_10_6_0_drafts.md)

Narrative order is chair-ratified (`q-user-friendliness-001`):
a compressed single-provider win as the on-ramp, then the NEW
multi-LLM features carry the demo as ONE continuous task. Honesty
gate throughout — every on-screen claim is a live run or a
receipt; no mockups, no staged output, and the **three-agent
title is conditional on the Antigravity beat recording green**
(fallback pre-written below).

---

## Cold open (0:00–0:45) — demonstrate the loss, don't assert it (A1)

- Claude Code names a specific, real repo fact on screen: "The
  failure is in X because Y."
- Cut to a fresh Codex session. Ask it: "What did Claude just
  learn?" It cannot answer.
- Caption: **"Every new AI session starts from zero. You are the
  only thing carrying context between them."** Then: "Let's
  cross it."
- Thesis: 10.6.0 makes your AI coding agents share memory, hand
  off work, and second-guess each other — one plugin.

## Act 1 (0:45–1:45) — the on-ramp, 60 seconds, pinned (A2)

- Pinned command: `attune security-audit .` (swap only if a
  faster receipted workflow exists at record time — pin the
  choice before recording, no script drift).
- Install shown as a jump-cut with a **persistent on-screen 4×
  badge** and "full unedited run linked below" — the compression
  mechanic is itself a receipt.
- Claim narrowed to what the visible path proves: "no API key
  for subscription-backed use."
- Beat line: "That's day one. Everything from here is what
  10.6.0 adds."

## Act 2 (1:45–5:15) — ONE task crosses the boundary (A3, A4, A5)

The `session_memory_*` transport + `handoff_create`/
`handoff_resume` demoed as a single causal story — not two
feature tours. The operator visibly triggers every boundary
crossing; nothing implies autonomous coordination. A persistent
task card tracks continuity: **Finding / Branch / Changed files /
Next action**.

1. **Reproducibility beat (A3, 20–30s):** the actual command /
   config stanza that wires attune into Codex, on screen, before
   any reveal. If the real path is longer than ~30s, show it
   honestly — a reveal the viewer can't reproduce reads as
   staged. `[RECEIPT: marketplace re-sync canary — R8 #4]`
2. Claude finds the bug cause and captures the finding (operator
   triggers the capture).
3. **The reveal:** Codex runs `session_memory_recall` and
   returns the exact finding Claude stashed. `[RECEIPT: post-lift
   Codex canary transcript]`
   - Honesty beat (D2/R5, on screen): Claude gets automatic
     lifecycle hooks; other providers get the SAME memory via
     MCP — automatic hooks are not promised on Codex/Antigravity.
4. `handoff_create` in Claude — tied to the current branch and
   diff (branch, changed files, next action visible on the task
   card).
5. `handoff_resume` in Codex — **hold the git-verification
   receipt on screen (A5)** as it validates refs and tree before
   continuing: "Handoffs are git-verified session contracts, not
   loose prompt copies." Codex then performs the stated next
   action. `[RECEIPT: live round-trip transcript]`
6. **Conditional third seat:** if the post-publish Antigravity
   probe is green by record time, show Antigravity querying the
   same shared memory alongside Codex. `[RECEIPT: Antigravity
   register+probe — R8 #6]` — see the fallback rule below.
- Mention, don't tour: the new ops `/memory` page is the shared
  index at a glance.

## Act 3 (5:15–6:45) — the second opinion (A6)

- `/cross-review` on a REAL diff from this repo — and show a
  **concrete finding the second provider actually caught**. That
  finding is the value demo.
- Posture stated honestly on screen: "advisory, never a merge
  gate until dogfooded quality earns it."
- Roundtable stinger (3 seconds, one spoken line over a flash of
  the promoted report header): "The features you just watched
  were chosen by this table — ruling linked." The full
  self-planning story lives in the article, not here.
- Closing line: **"The models advise. You decide."**

## Close (6:45–7:45) — a readable evidence card, then the ask (A7)

- Hold a three-row evidence card long enough to read — each row:
  claim, provider pair, timestamp, version, transcript link:
  1. Cross-provider recall — passed
  2. Handoff / tree verification — passed
  3. Independent review — passed
- Line: "Every claim you just watched has a transcript."
- One CTA: **"Install the plugin. Run one workflow. Cross
  providers when the task needs another seat."** Install line +
  docs (attune-ai.dev — links resolve; redirect shipped 07-23).

---

## ~2-minute social cut (A8)

- **0:00–0:10 — the miracle first:** Codex executing
  `session_memory_recall` and returning Claude's finding.
  Caption: "Codex just remembered something Claude learned."
- 0:10–0:20 — ten seconds of context (the cold-open loss beat,
  compressed).
- 0:20–0:30 — `pip install attune-ai` flash (scrollers must see
  how to try it).
- 0:30–1:10 — the handoff round-trip.
- 1:10–1:30 — evidence card + CTA.

---

## Production notes

- **Record AFTER the Monday lift and receipts** (Tuesday morning
  is the slot): tools live on PyPI 10.6.0; `[RECEIPT]` beats must
  exist. Act 2's Codex beats need the marketplace re-sync canary;
  the third-seat beat needs the post-publish Antigravity probe.
- **Cut-don't-fake (binding):** any beat whose receipt doesn't
  exist at record time is CUT, not simulated.
- **Segment isolation (contingency):** record each boundary
  crossing as an independently usable segment, so a failed
  Antigravity or marketplace beat cuts cleanly without
  destroying the Claude→Codex story.
- **Pre-written two-provider fallback:** if the Antigravity probe
  is not green, the demo renames to the Claude/Codex
  collaboration story ("one plugin, your agents share memory")
  and Antigravity appears only in the evidence/adapter matrix —
  a probe mention never poses as participation.
- Cross-review cadence/default-seat language stays PROVISIONAL
  until the OPEN-1..3 rulings at the Monday sitting — script
  says "advisory second opinion," never a cadence promise.
- What deliberately does NOT appear (UX-roundtable do-not list):
  the 25-skill catalog crawl, the ops dashboard tour, telemetry,
  config surfaces. One paved path per act.
- Terminal hygiene: fresh sessions, no secrets on screen
  (`anthropic.env` never opened), repo = attune-ai itself
  (dogfood is the credibility).

## Open items

- [ ] Chair rules the recording slot (Tue morning fits the fire
      sequence).
- [ ] Antigravity go/no-go: decided by the post-publish probe
      BEFORE recording the third-seat beat (fallback above).
- [ ] Verify the real Codex wiring path length for the A3 beat;
      if >30s, script the honest longer version.
- [ ] Fill `[RECEIPT]` beats from Monday's transcripts (same
      slots the article uses).
- [ ] Chair honesty-gate pass on the final cut before publish
      (same ruling moment as Draft B).
