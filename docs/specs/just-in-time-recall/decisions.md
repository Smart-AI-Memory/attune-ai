# Just-In-Time Recall — Decisions

Irreversible / load-bearing choices, timestamped. The timestamp is the
arbiter when a later session wants to relitigate.

## D1 — Source = durable lessons/rules, not session findings (2026-06-03)

**Decision:** Just-in-time recall surfaces durable rules
(`.claude/CLAUDE.md` Lessons + `feedback_*` memories), not the P2
session-stash findings.

**Why:** The failure this targets is *not-applying* (the rule existed,
unfired), not *not-knowing*. Rules are the right corpus for "remind me of
the governing constraint at the moment of the action." Findings-at-
decision-points is a valid later layer but a different problem (and a
bigger retrieval surface). Keeps the first cut focused and low-noise.

**Chosen by:** Patrick, via AskUserQuestion, over "session-stash findings"
and "both unified."

## D2 — Trigger mechanism = PENDING Phase 0 (2026-06-03)

**Decision:** Deferred to Phase 0 measurement. The repo's existing
PreToolUse hooks only allow/block (no context injection), so whether a
hook can inject model-readable guidance at a tool-call is unverified.
Phase 0 verifies PreToolUse `additionalContext` first, then
UserPromptSubmit injection as fallback. No build past Phase 0 until the
chosen mechanism is logged here.

**Why:** Verify-first discipline — do not confabulate a hook capability;
an entire build hangs on whether the injection channel exists.

## D3 — Matching = one explicit curated map, not semantic retrieval (2026-06-03)

**Decision:** A single reviewable decision-point → rule(s) map (one
file), keyed by tool name, valued by short `{rule_id, one_liner}` lists.
Not embedding/semantic retrieval; not per-file frontmatter tags (yet).

**Why:** A handful of known slip-points don't justify semantic retrieval
in the hot path of every tool call (cost + false-match noise →
nag-fatigue, violating R3). An explicit map is precise, diff-reviewable,
honest, and cheap to extend. Re-evaluate only if the map outgrows a
single file (then the frontmatter-tag approach).

## D4 — Surface text = distilled one-liner, not full lesson body (2026-06-03)

**Decision:** The map stores a one-line nudge per rule, not the full
lesson text.

**Why:** The goal is an at-the-moment nudge, not a wall — and surfacing a
paragraph would itself violate the concision discipline this feature
exists to enforce. The full lesson stays in CLAUDE.md / the memory as the
source of truth.

## D5 — Surface-once cadence = once per (session, rule), revisit (2026-06-03)

**Decision:** Start with a per-session sentinel keyed by
`(session_id, rule_id)` (reusing the `_state` sentinel pattern). Open
question carried into implementation: whether once-per-session is too
sparse (the reminder may scroll out before the slip-prone window ends) —
a turn/time decay is the candidate refinement, deferred until the proof
case shows whether it's needed.

**Why:** R3 (no nag-fatigue) is the binding constraint; start conservative
(quiet) and loosen only with evidence from the proof case.
