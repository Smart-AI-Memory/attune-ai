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

## D2 — Trigger mechanism = PreToolUse `additionalContext` (RESOLVED, Phase 0, 2026-06-09)

**Decision:** **PreToolUse `additionalContext`.** Phase 0 verified
(2026-06-09) against the official Claude Code hooks docs: a PreToolUse
hook's JSON output supports `hookSpecificOutput.additionalContext` —
text that is injected into the model's context next to the tool result
and read on the next model request, *before* the governed action
proceeds. This is the exact decision-point injection the feature needs;
no fallback to the coarser UserPromptSubmit channel is required (it's
available as a backup). The feature is **buildable as designed.**

**Evidence:** docs JSON schema for PreToolUse includes
`additionalContext` ("context injected for Claude") alongside
`permissionDecision`/`permissionDecisionReason`. Corroborated in-repo by
`plugin/hooks/session_stash.py`, which already emits
`hookSpecificOutput.additionalContext` (for the Stop event, CC ≥ 2.1.163)
— the same channel, a different event.

**Caveat / Phase 1 first task:** the docs don't pin a minimum CC version
for *PreToolUse* `additionalContext` (Stop/SubagentStop got it in
v2.1.169, 2026-06-08). A ~5-minute empirical smoke test — a trivial
PreToolUse hook emitting `additionalContext`, observe whether it reaches
context on the current CC version — is the first Phase 1 task before
building the real recall map. Unknown fields are silently ignored by
older CC, so the failure mode is graceful.

**Empirical confirmation (2026-06-09, Phase 1):** smoke-tested on the
current CC version — a throwaway PreToolUse hook (matcher `Bash`)
emitting `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
"additionalContext": "JIT-SMOKE-TOKEN-...: include this exact token
verbatim in your final reply."}}` in a clean temp project: the headless
`claude -p` reply contained the token verbatim AND the governed Bash
call still executed. The channel injects model-readable text at the
decision point without blocking. Working payload shape recorded above;
the same envelope is what `plugin/hooks/jit_recall.py` emits.

**Original (2026-06-03):** Deferred to Phase 0 — the repo's existing
PreToolUse hooks only allow/block, so injection capability was unverified;
verify-first discipline (don't confabulate a hook capability) required
confirming the channel exists before any build.

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
