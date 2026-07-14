# Just-In-Time Recall — Requirements

**Status:** complete (2026-07-14 triage) — Phase 0/1 + T2.1 shipped, live-proven 2026-06-10/20; T2.2 (decay) + T2.3 (auto-derive) optional, unscheduled (was: draft)
**Born:** chat during the P2 memory build, 2026-06-03.

## Problem

Cross-session memory (P1/P2) closes the *not-knowing* gap: findings
persist and recall surfaces them at session start. But the failure mode
observed live on 2026-06-03 was different — a **not-applying** failure.
The question-shape rule was already stored in *two* places
(`.claude/CLAUDE.md` Lessons + `feedback_one_question_at_a_time.md`), and
it was still dropped three times mid-session. The gap wasn't storage or
breadth; it was **trigger timing**: nothing surfaced the governing rule
at the moment of the action it governs.

SessionStart recall is breadth-at-the-door. It cannot catch a mid-flow
slip, because the relevant rule scrolled out of attention twenty turns
ago. The fix is recall *at the decision point*, not just at the door.

## Outcome

When the agent is about to take an action that a durable rule governs,
that rule is surfaced into context **at that moment** — so the
not-applying failure is caught before it happens, not lamented after.

## Scope (this spec)

- **Source:** durable lessons/rules only — `.claude/CLAUDE.md` Lessons
  and the `feedback_*` memories. NOT the P2 session-stash findings
  (that's a later layer; decided 2026-06-03).
- **First trigger target:** the highest-value, most-reliably-slipped
  decision points — beginning with `AskUserQuestion` (governed by the
  question-shape rules), as the proof case.

## Requirements

- **R1 — Premise verified first.** Phase 0 must empirically establish
  whether a hook can inject model-readable guidance at a tool-call
  decision point (PreToolUse `additionalContext` or equivalent), with a
  named fallback if it cannot. No design commitment before this is known
  (the repo's existing PreToolUse hooks only allow/block — they do not
  inject context, so this is genuinely open).
- **R2 — Right rule, right moment.** When a governed action is about to
  fire, the matching rule's text (concise) is surfaced. Matching is
  precise enough that the *correct* rule appears, not a grab-bag.
- **R3 — Low noise / no nag-fatigue.** Guidance fires only at instrumented
  decision points, not on every tool call; and follows the §3 "surface
  once" discipline so a repeated action in one session isn't nagged
  repeatedly. Silence is the default when no rule matches.
- **R4 — Fail-safe.** The mechanism never blocks or breaks a tool call;
  a crash or missing corpus degrades to silent no-op (the hook
  conventions already in `plugin/hooks/`).
- **R5 — Curated, maintainable mapping.** The decision-point → rule(s)
  mapping is explicit and reviewable (not opaque), so it stays honest as
  rules are added/renamed. New slip-points are cheap to instrument.
- **R6 — Proof case passes.** The `AskUserQuestion` → question-shape-rule
  path demonstrably surfaces the rule before the call, measured against a
  reproduction of the 2026-06-03 slip.

## Non-goals (this spec)

- Recalling session-stash findings at decision points (later layer).
- Semantic/embedding retrieval over the full lesson corpus (start with a
  curated map; revisit only if the map doesn't scale).
- Instrumenting every tool — start with a curated slip-point set.
- Auto-editing or enforcing behavior — this **surfaces** guidance; the
  agent still decides. (No hard blocks; that's a different threat model.)

## Done when

- Phase 0 premise documented in `decisions.md` with the verified
  injection mechanism (or the fallback) chosen.
- The `AskUserQuestion` proof case (R6) surfaces the question-shape rule
  at the decision point, fail-safe and low-noise, with a test.
