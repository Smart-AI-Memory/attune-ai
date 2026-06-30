# Single-Source Authoring (session-as-author) — Requirements

**Status:** draft (2026-06-30) · **Owner:** Patrick + agent
**Born:** Patrick — "I think you can replace much of the code with
instructions that support your authoring polished content." Correct for
the *authoring* half (the pushback that resolved it is recorded in
[attune-author-consolidation/decisions.md](../attune-author-consolidation/decisions.md)
D1–D3). This spec is the replacement: a skill that makes the driving
session a disciplined author of single-source masters.

Sibling specs: [attune-author-consolidation](../attune-author-consolidation/)
deletes the LLM authoring machinery this skill replaces;
[feature-page-scaffolder](../feature-page-scaffolder/) automates the
*mechanical* setup/build around it. This spec owns the *judgment* in the
middle.

## Why a skill, not a generator

The LLM authoring machinery (`generator`/`polish`) is being retired
because the empirical result is in: the **driving session is a superior
polish layer to the API pass, and the only one that catches correctness
bugs** (lessons). #1188 proved it — a hand-authored, code-verified master
projected clean on the first try. The gap is that this depended on *me
knowing* the discipline (read the code, verify every symbol, run the
audits). A skill encodes that discipline so any session — or any
contributor — authors to the same standard, with no API and no credits.

## What "authoring discipline" means (the thing to encode)

The verifiable practices #1188 used, which a generator cannot do but a
guided session can:

1. **Ground every claim in live code** — grep the exports, the enum, the
   tool names *before* writing the API tables; never confabulate a symbol.
2. **Fit the projector's section contract** — the canonical headings, so
   the master projects without "missing section" surprises.
3. **Run the gates as you go** — `audit_doc_imports`, the projector
   `--dry-run`, the bundle sync — and fix at the master, not the outputs.
4. **Verify, don't trust** — a master is the single point of *failure*;
   its claims get checked against the code they describe.

## Requirements

- **R1 — A skill drives master authoring.** Triggered when a feature needs
  a single-source page (or a master needs revision), it walks the session
  through: scaffold (or locate) the master → author each section grounded
  in live code → verify → project → audit. No API, no `attune-author
  generate`.
- **R2 — Verification is the skill's spine, not an afterthought.** The
  skill makes "grep the symbol before you write it" and "run the audit
  before you commit" explicit steps, because that discipline is the only
  thing separating session-authoring from the generator's fiction.
- **R3 — Composes with the scaffolder and the projector.** The skill calls
  the [scaffolder](../feature-page-scaffolder/) for the mechanical
  setup/build and the (now in-repo, per consolidation) projector for the
  fan-out — it owns judgment, not plumbing.
- **R4 — Surface-correct.** Ships in both `plugin/skills/` and the
  `.agents/` mirror (synced via `sync_agents_skills.py`), like every other
  skill.
- **R5 — Self-demonstrating.** The skill's own acceptance is that a fresh
  session, given only the skill, can reproduce the #1188 outcome — a
  green, code-accurate feature page — without out-of-band knowledge.

## Non-goals

- **Not a generator.** It does not emit prose for the session to rubber-
  stamp; it *guides* the session to author and verify. The judgment stays
  with the model-in-the-loop, grounded in code.
- **Not the projector or the scaffolder.** Those are deterministic code
  (sibling specs); this is instructions.
- **Not auto-fact-check-on-write.** The skill *prompts* verification and
  runs the existing gates; it does not add a new gate (that's the gate
  specs' job).

## Acceptance

- A session with no prior single-source knowledge, handed the skill,
  authors a master that projects byte-clean and passes `doc-import-audit`
  + the bundle sync on the first real attempt.
- The skill references only live, in-repo machinery (post-consolidation:
  `attune.authoring.*`, the scaffolder, the audits) — no `attune-author`
  generate/polish.
- Zero API credits across the authoring flow.
