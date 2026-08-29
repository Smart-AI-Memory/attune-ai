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

## Open (not ruled)

- **Harness vs. plugin first-contact framing.** "AI
  Workflow-harness" is the ratified internal/architecture term;
  whether first-contact copy should say "plugin" (try-me light)
  instead was discussed, not ruled.

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
