# Just-In-Time Recall — Design

**Status:** complete (2026-07-14 triage) — Phase 0/1 + T2.1 shipped, live-proven 2026-06-10/20; T2.2/T2.3 optional, unscheduled (was: draft)

## The core problem: match a rule to a moment

Two sub-problems: (1) a **trigger** that fires at the decision point and
can inject text the model reads; (2) a **match** from the action context
to the governing rule(s). Phase 0 settles (1); the design below settles
(2) and the surrounding control flow.

## Phase 0 — verify the injection mechanism (premise)

The repo's existing PreToolUse hooks (`security_guard.py`) only
allow (exit 0) / block (exit 2, reason to stderr) — they do **not**
inject context. So whether a hook can surface *model-readable guidance
without blocking* is unverified. Phase 0 measures, in order:

1. **PreToolUse `additionalContext`** — does a PreToolUse hook returning
   JSON `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
   "additionalContext": "..."}}` (or the current-version equivalent)
   inject text the model sees, while still allowing the call? Verify by
   instrumenting a throwaway hook and observing whether the text reaches
   context.
2. **Fallbacks if (1) fails:**
   - **UserPromptSubmit `additionalContext`** — inject on the user turn
     *before* the likely action. Less precise (turn-granular, not
     call-granular) but reliably injects.
   - **Degraded "advisory block"** — PreToolUse exit-2 with the rule as
     the reason, then immediately allow on retry. Rejected unless nothing
     else works: it interrupts the call (violates R4's spirit) and trains
     the agent to treat guidance as an error.

Phase 0 output → `decisions.md`: the chosen mechanism + why. No build
past Phase 0 until this is logged.

## Matching: a curated decision-point → rule map (chosen)

Rejected alternatives first:

- **Semantic retrieval** over the whole lesson corpus per tool call —
  heavy (attune-rag in the hot path of every call), and high false-match
  risk (noise → nag-fatigue → R3 violation). Overkill for a handful of
  known slip-points.
- **Tag-in-frontmatter** (`triggers: [AskUserQuestion]` on each memory) —
  cleaner long-term, but spreads the mapping across N files and needs a
  loader; defer until the curated map outgrows a single file.

**Chosen: one explicit, reviewable map.** A single small data structure
(e.g. `plugin/hooks/_recall_map.py` or a JSON sidecar) keyed by the
tool/decision-point name → a short list of `{rule_id, one_line_text}`.
Precise, low-noise, honest (diff-reviewable), and cheap to extend. The
rule text is a *distilled one-liner*, not the full lesson body — the goal
is a nudge at the moment, not a wall (mirrors the §3 "one paragraph"
discipline and the very rule it surfaces).

Seed entries (proof + obvious neighbors):

| Decision point | Surfaced rule (one-liner) |
|---|---|
| `AskUserQuestion` | "Lead with your recommendation; make options selectable and concise — no `and/or`, no buried prose." |
| (later) `Bash` git push to shared branch | "fetch before assuming up-to-date; verify the right worktree+branch." |

Only `AskUserQuestion` is in scope for R6; the rest are illustrative of
how the map grows.

## Control flow (the hook)

A new `plugin/hooks/jit_recall.py`, registered for the chosen event:

1. Read the hook payload; get the tool name (or, for UserPromptSubmit,
   the imminent-action heuristic).
2. Look up the tool in the curated map. No entry → silent no-op (R3).
3. **Surface-once gate:** per-session sentinel keyed by
   `(session_id, rule_id)` so the same rule isn't re-injected every time
   the action repeats in a session (reuses the `_state` sentinel dir
   pattern from the Stop-hook lesson). First fire surfaces; subsequent
   same-rule fires in the session stay silent.
4. Emit the one-liner via the verified injection channel; allow the call.
5. Wrapped in try/except → exit 0 on any error (R4).

## Noise budget & the surface-once tension

R3 is the hardest constraint. Two dials: the *map* (only instrument
genuine slip-points — keep it small) and the *surface-once gate* (once
per rule per session). Open question for `decisions.md`: is once-per-
session too sparse (the slip can recur after the reminder scrolls away)?
A middle option is a **decay** — re-surface a rule if the action recurs
after N turns / M minutes. Start with once-per-session; revisit if the
proof case shows the reminder fades before the slip-prone window ends.

## Relationship to the rest of the system

- **Distinct from P2.** P2 recalls *findings* at the *door*; this recalls
  *rules* at the *decision point*. Same backend philosophy (hooks, fail-
  safe, sentinels), different corpus + trigger. They compose; neither
  depends on the other.
- **Corpus source:** the rule one-liners are authored in the map, *derived
  from* the durable lessons (CLAUDE.md / `feedback_*`). The map is the
  curated index; the lessons remain the source of truth. (A future
  layer could auto-derive map entries from lesson frontmatter — the
  tag-in-frontmatter alternative above.)

## Prior art (verified 2026-06-03, not reinventing memory)

A web check of Anthropic's memory features confirms this spec's *trigger*
layer is distinct from existing prior art — all of which is door-layer or
consolidation-layer, none decision-point-triggered:

- **Claude Code Memory (Mar 2026)** + **CLAUDE.md** — auto-accumulated,
  file-based, loaded at session start. *Door layer.*
- **API Memory Tool** — developer-managed file store
  (view/create/str_replace/insert/delete/rename). Storage, not triggering.
- **MCP "memory" server** — local knowledge-graph persisted as JSON; the
  closest "local store for superior recall" prior art. If this spec's
  storage ever outgrows the curated map, lean here rather than reinvent.
- **Managed Agents memory + "Dreaming" (research preview, Managed Agents
  only, access-gated)** — a scheduled *between-sessions* pass that reviews
  past sessions, extracts patterns, and curates memory. This is the
  *consolidation* layer (≈ §5 consolidate-memory). Our trigger layer is
  upstream of it and complementary.

**Takeaway:** the just-in-time *trigger at the decision point* is the novel
piece. Storage and consolidation have prior art we can adopt later;
neither obviates this spec.
