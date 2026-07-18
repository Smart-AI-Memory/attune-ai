# Agent Round Table — Requirements

**Status: requirements APPROVED-pending-review (2026-07-18)** —
foundations chat-ratified by Patrick same day; D1/D2 picked, D3
provisional (see [decisions.md](decisions.md), including the
promoted probe-001 transcript).

## Vision

An orchestrated, strictly monitored deliberation surface where a
fixed team of heterogeneous LLMs — not N copies of one model —
debates questions, goals, and feature requests Patrick poses, and
where he chairs what gets promoted from deliberation into durable
artifacts. Evolution of the 2026-05-17 bulletin-board concept
(same collaboration loop; see the
`project_bulletin_and_pipeline_learner` memory — do not silo this
spec from the pipeline-learner concept it bridges to in Phase 3).

The value hypothesis was dogfooded before this spec was written:
probe-001 put one real product question to all three members and
got three distinguishable positions that mapped the design space
(transcript in decisions.md). Diversity is real; the spec's job is
to make convening it cheap, monitored, and recorded.

## Ratified foundations (chat, 2026-07-18 — do not re-open)

- **Fixed roster**: Claude + Antigravity + Codex. Claude also
  moderates. Patrick **chairs all promotions**.
- **Moderator owns ALL Redis I/O; members are stateless
  text-in/text-out.** Not a style choice — forced by verified
  headless permission walls (`agy -p` auto-denies shell; `codex
  exec` sandboxed). Every message physically passes through the
  moderator: "strictly monitored" is structural.
- **Substrate**: Redis short-term keyspace `attune:roundtable:*`
  (TTL'd working state, distinct from the derived
  `attune:memory:*` which is never written directly), with board
  operations as server-side Redis Functions (the `recall_digest`
  precedent): atomic, schema-validated writes.
- **Board → record**: suggestions/code sketches park in short-term
  memory pending chair-approved promotion to a spec or report.
  Deliberation is TTL'd; only promoted content is durable.
- **Phasing**: P0 substrate → P1 moderated round-trip → P2
  promotion gates → P3 routines. The cross-agent-memory-product
  work folds in as P0 (one data model, designed once).

## Phases

- **P0 — substrate.** Message schema (thread, author =
  provider+session, ts, reply_to, kind ∈ question | position |
  synthesis | ruling | suggestion | halt, body); Redis Functions
  `rt_post_message` / `rt_read_thread` / `rt_promote`; default
  thread TTL 7 days.
- **P1 — moderated round-trip.** One question → moderator briefs
  each member (headless recipes below) → collects replies →
  posts validated messages → synthesizes → presents to chair.
  Bounded rounds.
- **P2 — promotion gates.** Chair reviews thread; per-item
  approve/decline; approved items written to the destination
  (D2) and the thread marked promoted. Includes the
  lesson-candidate lint (chair ruling, lessons-flow-001): drafted
  lesson candidates are checked for format + curation bar before
  presentation; no receipt AND no chair-waiver tag → blocked.
- **P3 — routines.** Scheduled table runs (weekly §12
  Clean-Run-Check is the first candidate), budget-capped,
  results posted as a board digest; bridge to pipeline-learner
  (routines are canonicalized sequences).

## Roster invocation recipes (verified live 2026-07-18)

- Claude: context-free subagent (Agent tool) or `claude -p`.
- Antigravity: `agy --add-dir <ws> -p <brief> --mode plan` —
  reasoning-only headless; shell auto-denied.
- Codex: `codex exec --skip-git-repo-check -` with the brief on
  stdin (arg-prompt form blocks forever on non-TTY stdin —
  lessons corpus, 2026-07-18). codex-cli ≥0.144.6, shares
  `~/.codex` ChatGPT auth.

## Design forks (RESOLVED 2026-07-18, Patrick)

- **D1 — v1 intake surface: skill first, CLI later.**
  `/roundtable` in a Claude Code session; the live session's
  Claude is the moderator. A standalone CLI follows once the
  deliberation loop is proven.
- **D2 — promotion destination: spec if one owns it, else
  report.** Promoted items land in the owning spec's
  `decisions.md` when a spec exists (probe-001 set the
  precedent); otherwise `docs/reports/roundtable/<thread-slug>.md`.
- **D3 — budget: RESOLVED — up to 3 rounds per question**
  (Patrick, 2026-07-18: "You and the other llm's/agents can use
  up to three rounds of questions/suggestions"). The moderator
  and members may use rounds as the deliberation needs them —
  including member-originated follow-up questions (R9) — and the
  moderator halts early when positions have converged or new
  rounds stop adding information. Three rounds is a hard
  ceiling: invocation past it requires the chair.

## Ratified scope additions (Patrick, D3 answer 2026-07-18)

- **Bidirectional board**: members and agent sessions may
  ORIGINATE items — questions, code suggestions, feedback — not
  only respond. All originations flow through the moderator like
  every write (R1/R2 unchanged); the moderator triages
  member-originated items to the chair.
- **Tier-routed outcomes**: when the chair promotes, the
  moderator recommends an artifact tier using the contract's
  artifact-selection table — **inline edit / structured one-shot
  / XML task / spec** — based on the complexity of what the
  table produced; the chair ratifies the tier; the artifact is
  then created (spec dir, PR, or executed one-shot). The
  deliberation loop feeds the same discipline the repo already
  ships.

## Requirements

- **R1** Members are invoked headlessly, text-in/text-out; no
  member performs Redis I/O, file writes, or shell actions in a
  deliberation.
- **R2** Every board write passes moderator validation against
  the message schema; the stored procedure rejects malformed
  messages (missing author/kind/thread) atomically.
- **R3** Board state lives only under `attune:roundtable:*` with
  TTLs; the derived `attune:memory:*` keyspace is never written
  (contract rule, #1447).
- **R4** Nothing reaches a tracked artifact without the chair's
  explicit per-item approval (P2). No auto-promotion in any
  phase, including routines.
- **R5** A per-question budget cap is enforced by the moderator:
  member invocation halts at the cap and a `halt` message is
  posted to the thread naming the reason.
- **R6** An unavailable member (CLI missing, auth expired,
  timeout) is marked absent in the thread and deliberation
  proceeds — a seat failure never blocks the table. Degrades to
  a single-member table (contract: works with one provider).
- **R7** Every member invocation is receipted in the thread:
  provider, duration, token/cost figures where the CLI reports
  them.
- **R8** Routine runs (P3) carry the same caps and gates as
  interactive runs; a routine that surfaces a promotion
  candidate queues it for the chair, never self-promotes.
- **R9** Member-originated items (kind `question` or
  `suggestion`, any member as author) are first-class board
  messages: schema-validated, moderator-posted, triaged to the
  chair. Origination grants no execution rights — R1 holds.
- **R10** Promotion includes tier selection: the moderator
  recommends inline edit / structured one-shot / XML task /
  spec per the contract's artifact-selection criteria; the
  chair's approval names the tier; the created artifact records
  the thread id it came from.

## Acceptance criteria (failure-sensitive)

- **AC-1** `rt_post_message` with a missing `kind` or `author`
  field is rejected by the Redis Function (error, no partial
  write) — verified against the real Redis, not a mock.
- **AC-2** A full P1 round trip runs against the real member
  CLIs: question in → ≥3 messages of kind `position` (or seats
  marked absent per R6) → one `synthesis` → thread readable via
  `rt_read_thread`. The probe-001 class, automated.
- **AC-3** Promotion: chair approves an item → destination
  artifact exists with the content and the thread is marked
  promoted; chair declines → no file change (`git status`
  clean).
- **AC-4** With one member CLI made unavailable, the run
  completes, the thread shows the absent seat, and exit is
  success.
- **AC-5** With a cap of N invocations, invocation N+1 is not
  made and the thread carries a `halt` message.
- **AC-6** After thread TTL expiry, promoted content survives in
  git; unpromoted board state is gone (this is the designed
  behavior, verified — not a bug report waiting to happen).

## Out of scope

- Resident member processes, streaming member-to-member traffic,
  or members writing anywhere directly (moderator-owns-I/O is
  ratified).
- Auto-promotion of any kind.
- Per-question roster composition (fixed roster is ratified for
  v1; revisit only with field evidence).
- The memory-product auto-wire implementation itself (probe-001
  ruling (a) + amendments): recorded in decisions.md here, but
  its hydration-hook/plugin work ships under its own tasks — this
  spec consumes the substrate, it does not implement the plugin
  hook.
- Gemini CLI membership (product sunset — see gemini-projector
  spec, PARKED).
