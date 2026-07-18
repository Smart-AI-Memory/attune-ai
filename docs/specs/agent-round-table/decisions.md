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

## P0 substrate — SHIPPED (2026-07-18)

`src/attune/roundtable/` (`board.py`): message schema
(`BoardMessage`, `KINDS`), the `attune_roundtable` Redis Function
library (`rt_post_message` / `rt_read_thread` / `rt_promote` —
distinct library name from the hydration hook's `attune_memory`,
so `FUNCTION LOAD REPLACE` never clobbers it), and the
moderator-side `Board` client. Validation lives SERVER-SIDE in
Lua per R2/AC-1.

Receipts: 16 tests, run parallel AND serial against a REAL local
Redis with the library loaded by the suite itself — AC-1 (five
malformed shapes each rejected with `rt_post_message:` errors and
ZERO partial writes: thread + meta keys both absent after), AC-6
(TTL set on post), full post→read→promote round trip, promote
marks meta + returns messages, missing-thread and
missing-destination rejections. Keyless-CI lane covered by
boundary-double tests (no Redis required).

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

## P1 moderated round-trip — SHIPPED (2026-07-18)

The `/roundtable` skill (`plugin/skills/roundtable/SKILL.md`,
mirrored to `.agents/skills/` by the sync projector): intake +
spend gate, thread open, member briefs via the verified headless
recipes, positions posted with R7 receipts, R6 absent-seat
degradation, R9 origination as `question`/`suggestion` messages,
bounded rounds with early-halt (D3), synthesis, and chair-gated
promotion with R10 tier recommendation and D2 destination routing.

**AC-2 receipt — live dogfood, thread `lessons-flow-001`** (board
`attune:roundtable:thread:lessons-flow-001`, TTL 7d from
2026-07-18): question ("how do deliberations flow into the shared
learning corpus?") → all 3 seats answered (claude 17s via
subagent; antigravity 5s via `agy --mode plan`; codex 10s via
`codex exec -`) → 3 `position` + 3 member-originated `question`
messages + 1 `synthesis`, all server-side schema-validated, thread
read back via `rt_read_thread`. Moderator halted after round 1 of
3 on unanimous convergence: all seats picked (b) — a distinct
lesson-promotion lane — and all three independently named
review-fatigue/dilution as the risk. Open items triaged to the
chair (unruled as of this writing): the evidence bar for lesson
candidates (codex + claude convergent follow-up) and a pre-chair
lint guardrail (antigravity). Promotion of the thread itself:
chair's call, pending (R4).
