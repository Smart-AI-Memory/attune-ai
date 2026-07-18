# Agent Round Table — Decisions

## Chat-ratified foundations (2026-07-18, Patrick)

Ratified live in the originating session (the same session that
closed antigravity-adapter D3 and shipped #1445–#1447):

- **Fixed roster** (Claude + Antigravity + Codex), Patrick
  **chairs all promotions** — his exact picks when offered
  fixed-vs-per-question and chair-vs-review-after.
- **Moderator owns all I/O; members text-in/text-out** — derived
  from same-day receipts: `agy -p` auto-denies shell headlessly
  (no interactive prompt exists), so members cannot safely do
  their own Redis I/O. Monitoring is therefore structural, not
  aspirational.
- **Routines are Phase 3, not Phase 1** — a routine is a
  scheduled invocation of a table that already works
  interactively. Patrick's ask ("routines it can run") is the
  third leg of his own 2026-05-17 synthesis: bulletin = what a
  routine produces; learner = where routines come from; table =
  what runs them.
- **The cross-agent-memory-product spec folds in as Phase 0**
  (was about to be written standalone; one data model, designed
  once).

## Probe-001 — the dogfood that validated the value hypothesis

Promoted from `attune:roundtable:thread:probe-001` (Redis
short-term, 7-day TTL) on 2026-07-18, per the promotion protocol
this spec itself defines. Chair: Patrick. Moderator: Claude Code.

**Question:** Next release: auto-wire memory hydration + contract
scaffolding on plugin install, or explicit `attune memory init`?

**Positions (independent, headless, same brief):**

- **Claude** (context-free subagent): (b) explicit init with a
  hard verification receipt (preflight Redis → install → real
  stash/recall round trip → then say "done") + a non-invasive
  discovery nudge in `attune doctor`. Named risk of own
  position: opt-in ships dark for most users.
- **Antigravity** (agy 1.1.4, plan mode): (b) explicit init as
  diagnostic gatekeeper; verify Redis reachable before
  registering hooks. Named risk: feature obscurity;
  multi-workspace fragmentation.
- **Codex** (codex-cli 0.144.6): (c) hybrid — auto-wire
  *detection* via the already-consented plugin SessionStart
  hook; explicit `init` only for the repo-scaffolding trust
  boundary; "advertise memory as active only after a real
  write/hydrate/recall smoke test passes." Question back: is
  repo-level scaffolding the default init scope, with global
  agent settings behind a separate explicit flag?

**Moderator's note:** both (b) members assumed auto-wire means
silent writes to `~/.claude/settings.json`. The shipping path is
the plugin's own hook manifest, which loads because the user
installed the plugin — install is the consent moment. This
materially weakens the invasiveness objection to (a).

**Chair's ruling: (a) auto-wire on plugin install** — Patrick,
overruling both (b) members, with two amendments carried from the
dissent:

1. The hydration hook must **silent-degrade** without Redis
   (fast, quiet, zero session-start breakage) — clean-machine
   receipt required before release.
2. **Machine wiring ≠ repo writes**: hook auto-wires via the
   plugin manifest; writing `AGENTS.md`/scaffolding into a
   user's repo stays prompt-gated (Socratic consent moment).

Codex's (c) mechanics converge with these amendments from the
opposite direction — recorded as supporting design input for the
Phase 0 tasks.

**Dogfood verdict:** three models, three distinguishable
positions, and the disagreement mapped the actual design space
(trust boundaries, verification gates, adoption). The chair
overruling a unanimous member recommendation — with rationale the
members lacked (the plugin-manifest consent mechanism) — is
exactly the human-in-the-loop shape the table is designed around.

## Seating receipts (2026-07-18)

- Antigravity: contract probe answered verbatim from loaded
  context (post-#1447); headless reasoning briefs work in plan
  mode; shell auto-denied (drives R1).
- Codex: CLI installed same-day (`npm install -g @openai/codex`,
  0.144.6), reused existing `~/.codex` ChatGPT auth with no
  browser flow; probe answered. Gotcha shipped to lessons
  (#1448): arg-prompt `codex exec` blocks forever on non-TTY
  stdin — use `codex exec -` with the brief on stdin.
- Claude: context-free subagent via Agent tool (19.5s,
  independent of moderator context).

## D1–D3 resolved (2026-07-18, Patrick, batched elicitation form)

- **D1: skill first, CLI later** — `/roundtable` with the live
  session's Claude as moderator; standalone CLI after the loop
  is proven.
- **D2: spec if one owns it, else report** —
  `docs/reports/roundtable/<thread-slug>.md` as the fallback
  destination.
- **D3: RESOLVED — up to 3 rounds per question** (Patrick,
  follow-up 2026-07-18: "You and the other llm's/agents can use
  up to three rounds of questions/suggestions"). Rounds are
  available to members too (follow-up questions/suggestions per
  R9), moderator halts early on convergence, three is a hard
  ceiling without the chair. His earlier D3-slot answer ratified
  scope: members "receive OR post questions including code,
  feedback/suggestions from the other agents/llm's", and the
  moderator then creates "a spec, pr or one shot based on the
  complexity using our table with 4 types of responses" —
  bidirectional origination (R9) + promotion routed through the
  contract's four artifact tiers (R10).
