# Positioning Review — 2026-08-29

**Status:** decisions ratified (Patrick, chair, 2026-08-29, in
session — chat-mode positioning review). This file is the tracked
record; the chat is context, not authority. Numbering continues
the series (DEC-1…9 live in the 2026-07 assessments).

**Scope:** how attune-ai presents its features across surfaces
(README, website, PyPI, plugin marketplace). Copy execution is
tracked in the execution map below, not here.

## Decisions

### DEC-10 — Memory is the shelf; receipts are the differentiator

Positioning has two jobs: the category shelf (how people find
you) and the differentiator (why they pick you off it). Memory is
the shelf — it is what people search, the company is named Smart
AI Memory, and DEC-3 already ruled memory THE pillar. Receipts
("the agent's word is not the evidence") is the differentiator:
nearly unowned in the ecosystem, viscerally felt ("it said the
tests pass"), and native to this repo's culture (contract
principle 1, "the receipt beats the promise").

Guardrails, from the pressure test:

- **Receipts stays a scoped claim** ("receipt-verified
  workflows"), never the whole-product identity — advisory
  workflows (research-synthesis, doc-gen) don't produce receipts,
  and the brand invites its own audit. The 14.1.0 planted-defect
  registry is load-bearing marketing infrastructure: the receipt
  for the receipts.
- **First use always self-defines** via the contrast clause
  ("receipts, not promises") — guards the literal
  billing-artifact misreading.
- **"Trust" is an internal editorial rule only**, never public
  copy. The test for above-the-fold placement everywhere: does
  this reduce forgetting, bluffing, or monologuing? If not, it
  folds. "Trust layer" was pressure-tested and rejected as public
  copy (vendor-language, excludes nothing, web3 shelf collision).

### DEC-11 — Taglines are assigned by surface, not unified

One universal tagline is not the goal; one universal *story* is.

- **Precision surfaces** (README top, PyPI description): keep
  "Persistent memory and receipt-verified workflows for Claude
  Code."
- **Persuasion surfaces** (website hero): "Give your agent a
  memory. Make it show receipts." with the existing README line
  as subhead ("Your agent stops starting from zero — and its word
  stops being the evidence.").

### DEC-12 — Audience: the solo Claude Code power user

Position for the individual dev, explicitly, for at least a
quarter. The architecture is single-player today (local-first,
per-machine Redis, one human chairing the roundtable);
distribution is self-serve; the receipts pain lands hardest solo.
Enterprise vocabulary ("platform", "governance", "orchestration
layer") stays out of public copy. Counter-case recorded: memory's
largest economic value is team-level (shared lessons corpus =
org memory) — the team story stays a one-line roadmap whisper
and is revisited when a second person shares a corpus.

### DEC-13 — Cross-provider memory is framed as anti-lock-in

Mentioned inside the memory pillar as its second beat, framed as
asset ownership, not "multi-platform": the corpus is git-tracked
markdown in the user's own repo; Redis serves it. Name exactly
the three verified providers (Claude Code, Codex, Antigravity) —
never claim the universe. Ratified sample copy for the slot:

> Your memory is git-tracked files in your repo — served to
> Claude Code, Codex, or Antigravity alike. Switch agents; keep
> everything.

### DEC-14 — Multi-LLM stops being a standalone pillar

The website folds the multi-LLM pillar into the two it supports:
portability is a property of the memory (DEC-13);
cross-review/roundtable are properties of the receipts culture.
Fewer top-level concepts at first contact, each carrying more.

**DEC-14a rider (2026-08-29, chair-directed, same session):** the
fold's first execution under-weighted the round table — pillar
copy became a single bullet, and the chair flagged it as one of
the site's strongest points. The fold STANDS (no sixth parallel
pillar), but the round table gets marquee treatment as the vivid
case of the receipts culture across models: a dedicated
how-it-works section ("Three models. One table. You chair." —
deliberate / you decide / receipts-still), selling the CHAIRING,
not "orchestration" (DEC-12 vocabulary rule). Lesson for future
folds: folding a pillar means relocating its story, not shrinking
it to a bullet.

### DEC-15 — Engines get credit at the point of proof; help is right-sized (2026-08-29, later same day)

The chair proposed sharing billing across attune-rag, attune-verify,
and the other bundled packages instead of attune-help's inherited
prominence. Ratified with the lead's amendment: **attribution, not
product billing** — rag and verify are bundled core deps whose
invisibility ("built in, no extra install") is itself a selling
point, so they are credited by name where their receipts appear,
never promoted to sibling products. Three parts:

1. attune-help's cross-ad inside attune-ai's marketplace description
   is cut (help keeps its own listing and card — true and real, just
   no longer piggybacking).
2. Every engine-powered proof-point names its engine ("powered by
   attune-rag", "powered by attune-verify").
3. The README Ecosystem table's information appears on the site,
   **benefit-framed** (chair's amendment): a homepage "one install"
   section — each engine as a benefit inside `pip install attune-ai`,
   with two constraints from the lead's pushback: (a) framed as
   components of ONE install, never a product grid (only attune-help
   carries a separate install line, marked optional); (b) placed low
   on the page near the install decision, not above the fold. Data
   single-sourced as `ECOSYSTEM` in features.ts, roles only, no
   versions — so it cannot go stale on a release.

Rider: executing this surfaced a README accuracy drift — the
Accuracy section claimed "0.98 mean, CI-gated at ≥ 0.97", both
halves contradicting the drift-guarded METRICS guidance ("say mean
0.97, CI-gated, never 'gated at ≥ 0.97'"); normalized to the
canonical phrasing.

### DEC-16 — Plugin-first at first contact; harness stays the architecture term (2026-08-29, closes the open item)

Grounded in a survey first: "AI Workflow-harness" appears nowhere
in public copy today — the only public "harness" uses are the
generic test-rig sense (planted-defect harness, evaluation
harness). Ruling ratifies the de facto state as policy:

- **"Plugin" is the first-contact noun** on all public surfaces —
  hero-adjacent copy, marketplace, PyPI, install sections. It
  pattern-matches to "small thing I can try", the truth of the
  two-command install and what the DEC-12 solo buyer needs.
- **Depth formula** wherever more-than-a-plugin must be signaled:
  "a Claude Code plugin that grows into a full CLI + MCP stack."
  Lead light, reveal depth; never lead heavy.
- **"AI Workflow-harness" remains the ratified
  internal/architecture term** (the 2026-07-29 ruling is
  untouched). Public use only as a defined term in
  architecture-explaining contexts (docs, the discipline article) —
  never in a hero, tagline, or install block. A supporting reason:
  the site already uses "harness" in the test-rig sense, and one
  word carrying two meanings is the overload the "one name, one
  contract" story exists to prevent.
- Counter-case recorded: "agent harness" is an emerging term of
  art and attune genuinely is one — if the term takes off
  industry-wide, revisiting costs one ruling; adopting early and
  retracting later costs credibility. Revisit trigger: the term
  becoming common buyer vocabulary.

### DEC-17 — Recommended install is the full stack, framed as both-and-free (2026-08-29)

Chair leaned toward recommending "the full platform" as the
download; ratified with the lead's two amendments: (1) the word is
**"the full stack"**, never "platform" (DEC-12 vocabulary); (2)
the recommendation is framed **"install both — still free, no API
key needed"**, defusing the #1 documented user confusion (a Claude
subscription does not include API credits) at the exact moment it
would arise: `pip install attune-ai` itself is free and most of
what it unlocks runs keyless; the key gates only direct CLI
workflow runs, which are step three, not step one. The plugin-only
path stays visible as the lighter fallback ("just want the
skills?"), preserving DEC-16's lead-light spirit. Surfaces:
README Get Started, homepage get-started section (both cards now
carry the recommended emphasis), attune-ai.dev install block.

**Watch-item (retro pushback, ratified 2026-08-29):** the
free-framing defused the billing trap but not the INSTALL trap —
recommending pip+plugin routes first contact through Python
packaging, where the setup-friction-log says people got hurt.
Measure the 2026-09-01 first-user onboarding against this; if
setup friction recurs at first contact, revisit DEC-17's
recommendation ordering.

### DEC-18 — Spec Ladders sells the engine, not just the brakes (2026-08-29)

Chair flagged that spec-driven *execution* was undersold: every
`/spec` mention was control-framed ("approve rung by rung", gates,
rulings) with nothing saying the agent executes the ladder between
approvals — workflows dispatched, native agent capabilities
driving the work. Partly this session's own doing: DEC-11 retired
the spec-first hero and nothing re-housed the execution half (the
DEC-14a fold-drops-the-story class again). Ratified with the
lead's two amendments:

- **Category vocabulary inside the receipts story, no new
  pillar/shelf**: say "spec-driven development, with receipts" —
  borrows the hot category's vocabulary (Kiro, Spec Kit made it
  searched) while differentiating inside it (they generate specs;
  attune independently verifies execution against them). Memory =
  shelf and receipts = differentiator (DEC-10) stand.
- **The three-provider execution claim ships only with a
  receipt**: Claude Code is lived daily and Codex installs the
  same plugin; `/spec` executing end-to-end under Antigravity is
  inferred, not checked — copy stays narrower ("agent" generic /
  the two receipted providers) until a live-fire probe passes.
  Chair authorized the probe same-session ("go and verify").

  **Probe receipt (2026-08-29, later same session): PASSED.** A
  minimal throwaway spec (requirements/tasks/decisions) was
  executed by Antigravity (`agy` 1.1.22, scoped workspace): the
  seat created the spec'd file, checked the ladder box, and
  appended the ruling — all three verified by the LEAD re-running
  them centrally (file prints the exact required string, exit 0;
  box checked; ruling line present), never by the seat's
  self-report. Scope honestly stated: one rung with recorded
  ruling, not the full gated /spec interview flow. This authorizes
  the three-provider execution line in copy. Environment notes for
  reproduction: agy's bundled datacloud_telemetry PreToolUse hook
  is version-skewed against agy 1.1.22 (blocks ALL tool calls;
  chair disabled it for the probe), and headless agy needs either
  a permissions allow-rule or a scoped workspace with
  auto-approval. Transcript: agy brain run d160cfba (10:54),
  rendered copy delivered to the chair in-session.

Copy: README Spec Ladders bullet, plugin README callout,
how-it-works spec-gate card, and the reliability loop's Build
stage all gain engine-framing ("the approved spec drives the
agents" / "the agent executes the spec'd tasks").

### DEC-18a — Live-fire receipts are the standing bar for cross-provider capability claims (2026-08-29, retro item 10)

Ratified from the retro: a cross-provider capability claim in
PUBLIC copy (a named provider executing an attune capability)
ships only with a **live-fire receipt, centrally re-run by the
lead** — never the seat's self-report — with the receipt's scope
stated honestly in the decision record before the claim lands.
Worked example and template: the DEC-18 Antigravity probe
(throwaway spec, scoped sandbox, central re-run of every
artifact). Recorded here rather than in the collaboration
contract deliberately: this is a marketing-claims bar, not a
governance rule, and the contract is the wrong blast radius.

## Open (not ruled)

- *(none — DEC-16 closed the review's last open item; DEC-17,
  DEC-18, and DEC-18a were ratified after closure.)*

## Evidence base (session findings, 2026-08-29)

Verified by reading the files this session, driving the execution
map below:

- `website/lib/features.ts` PRODUCTS/LIFECYCLE_STEPS/
  DIFFERENTIATORS still tell the pre-pivot help-tool story
  ("Generate, maintain, and serve help from your code") —
  contradicting the README positioning on the homepage and
  how-it-works pages. PILLARS is current but coexists with the
  stale layer.
- README count drift: top says 59 MCP tools, the collapsible
  says "61 — 50 core plus 11", the 15.0.0 section says 48,
  `features.ts` says 48; the tool list still names the retired
  `attune_get_level`/`attune_set_level`.
- README "New in" rotating slot says 15.0.0; 16.1.0 shipped
  2026-08-28.

## Execution map

Ordered; each item is a separate small PR unless noted.
**Status: all executed and merged 2026-08-29** — item 1 → #2356,
item 2 → #2357, item 3 → #2359, item 4 → #2358, plus a
chair-directed extension of item 3 to the attune-ai.dev landing
(#2361). Merge states verified via `gh pr view` at note time.

1. **README truth pass** (root `README.md`) — reconcile the MCP
   tool counts to the one registry-derived number, drop retired
   tools from the list, rotate the "New in" slot to 16.1.0.
   Receipt: the website-content-accuracy verification commands +
   `tests/unit/test_website_version_accuracy.py`.
2. **features.ts de-fiction** (`website/lib/features.ts`) —
   rewrite the attune-ai PRODUCT card's tagline/description to
   the DEC-10 story; retire or rewrite LIFECYCLE_STEPS and
   DIFFERENTIATORS (help-era content) or re-scope them to the
   attune-help product card only. Website-only PR: run the guard
   locally, CI won't.
3. **Pillar fold** (features.ts PILLARS + consuming pages) —
   execute DEC-14: merge the multi-LLM pillar's portability point
   into the memory pillar (DEC-13 copy), move
   cross-review/roundtable under receipts/verification. Homepage
   hero adopts the DEC-11 persuasion pair.
4. **Marketplace/plugin blurb pass** — align the plugin
   description surfaces with DEC-11 precision copy (and settle
   the harness-vs-plugin open question first if it blocks
   wording).
