# 10.6.0 Demo Outline — "One Plugin, Three AI Coding Agents"

**Created:** 2026-07-23 · **Status:** staged (records after the
07-27 lift + receipts; releases launch week with the Tuesday
07-28 fire) · **Format:** recorded screen demo, ~9 min, plus a
2-minute social cut · **Companion materials:**
[LAUNCH_10_6_0_article_draft.md](LAUNCH_10_6_0_article_draft.md),
[RELEASE_10_6_0_drafts.md](RELEASE_10_6_0_drafts.md)

Narrative order is chair-ratified (roundtable
`q-user-friendliness-001`, 2026-07-23): a compressed
single-provider win as the on-ramp, then the NEW multi-LLM
features carry the demo. Emphasis: what 10.6.0 ADDS. Honesty
gate applies throughout — every on-screen claim is a live run or
a receipt; no mockups, no staged output.

---

## Cold open (0:00–0:40) — the problem

- Split screen: a Claude Code session rich with project context;
  beside it a fresh Codex session that knows nothing.
- One line, on screen: **"The provider boundary is where context
  dies."**
- Thesis: 10.6.0 makes your AI coding agents share memory, hand
  off work, and second-guess each other — Claude, Codex, and
  Antigravity/Gemini, one plugin.

## Act 1 (0:40–2:00) — the five-minute win, compressed

Purpose: establish trust fast; this is the on-ramp, not the story.

- `pip install attune-ai` (zero-config, subscription-first — call
  out "no API key required" as the line executes).
- One real workflow on a real repo (bug-predict or
  security-audit), receipt on screen.
- Beat line: "That's day one. Everything from here is what
  10.6.0 adds."

## Act 2 (2:00–4:30) — NEW: memory that crosses providers

The `session_memory_*` MCP tools (cross-provider-memory-transport,
new in 10.6.0).

- In Claude Code: a session finding gets stashed (show the Stop
  hook stash or an explicit capture).
- **The reveal:** open Codex — `codex` lists the same
  `session_memory_*` tools; `session_memory_recall` returns the
  finding Claude stashed. `[RECEIPT: post-lift Codex canary
  transcript — R8 #4]`
- Honesty beat (D2/R5, on screen): Claude gets automatic
  lifecycle hooks; other providers get the SAME memory via MCP —
  automatic hooks are not promised on Codex/Antigravity.
- Mention, don't tour: the new ops `/memory` page shows the live
  index the providers share (one glance, no dashboard crawl).

## Act 3 (4:30–6:30) — NEW: hand the session across the boundary

`handoff_create` / `handoff_resume`
(cross-provider-session-handoff, new in 10.6.0).

- In Claude Code mid-task: `handoff_create` — show the handoff
  validating against actual git state (branch, changed files,
  next action).
- In Codex: `handoff_resume` — the second provider verifies the
  handoff against the working tree before continuing, then picks
  up the task. `[RECEIPT: live round-trip transcript]`
- Beat line: "Providers become interchangeable seats on one task
  — parity by adapters, not by promises."

## Act 4 (6:30–8:00) — NEW: the second opinion

`cross_review` + the round table (cross-review new in 10.6.0;
agent-round-table flips shipped/living on the 07-27 fire).

- `/cross-review` on a REAL diff from this repo: a different
  provider reviews it adversarially, findings advisory-only.
  State the posture honestly on screen: "advisory, never a merge
  gate until dogfooded quality earns it."
- Zoom out to the round table: three seats deliberating a real
  question, chair ruling promotion.
- **The meta-beat (the story's kicker):** the features in this
  demo were themselves picked by the table — show the promoted
  report `docs/reports/roundtable/q-multi-llm-obvious-win-001.md`
  (the ruling that chose handoff + cross-review as the next two
  features). The product plans itself; the human stays the chair.

## Close (8:00–9:00) — receipts, then the ask

- Flash the receipts trail: the 06:00 scheduled clean-run log
  `[RECEIPT: Monday fire, green]`, the Codex canary, the
  Antigravity probe `[RECEIPT: post-publish register+probe]`.
  Line: "Every claim you just watched has a transcript."
- Install line + docs (attune-ai.dev — links resolve; the docs
  redirect shipped 07-23).
- Day-2 invitation: "Start single-provider. When you hit a
  judgment call, ask the table."

---

## 2-minute social cut (for the LinkedIn post)

Cold open (condensed, 0:15) → Act 2 reveal only (Codex recalling
Claude's memory, 0:45) → Act 3 handoff round-trip (0:40) →
receipts flash + install line (0:20). No Act 1, no meta-beat —
one boundary-crossing miracle per minute.

---

## Production notes

- **Record AFTER the Monday lift and receipts** (Tuesday morning
  is the slot): the demoed tools must be live on PyPI 10.6.0 and
  the `[RECEIPT]` beats must exist. Recording order: Acts 1/4
  any time post-lift; Act 2's Codex beat needs the marketplace
  re-sync canary; the Antigravity mention in the close needs the
  post-publish probe.
- **Cut-don't-fake rule (binding):** any beat whose receipt
  doesn't exist by record time is CUT, not simulated. The
  fallback demo is Acts 1 + 4 + roundtable (all live today).
- Cross-review cadence/default-seat language stays PROVISIONAL
  until the OPEN-1..3 rulings at the Monday sitting — script says
  "advisory second opinion," never a cadence promise.
- What deliberately does NOT appear (UX-roundtable do-not list):
  the 25-skill catalog crawl, the ops dashboard tour, telemetry,
  config surfaces. One paved path per act.
- Terminal hygiene: fresh sessions, no secrets on screen
  (`anthropic.env` never opened), repo = attune-ai itself
  (dogfood is the credibility).

## Open items

- [ ] Chair rules the recording slot (Tue morning fits the fire
      sequence).
- [ ] Fill `[RECEIPT]` beats from Monday's transcripts (same
      slots the article uses).
- [ ] Chair honesty-gate pass on the final cut before publish
      (same ruling moment as Draft B).
