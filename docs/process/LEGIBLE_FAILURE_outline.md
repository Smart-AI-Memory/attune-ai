# Article outline — "Too Graceful: When Your Fallbacks Lie to You"

**Status:** outline seed (2026-06-11) — Patrick to shape; structure
and case material captured same-day while receipts were fresh.
**Relationship to the Discipline article:** standalone companion
piece, per the "article is generative — synergies tied to the
discipline, not new sections" decision. Cross-link both ways.
**Working titles:** "Too Graceful" / "Make Failure Legible" /
"Every Fallback Borrows Observability From Your Future Self"

## Thesis

Graceful degradation is taught as an unalloyed good. It isn't.
A fallback so smooth that nobody notices the primary is dead is a
failure mode wearing a feature's clothes. The fix is not to make
failure loud (loud breaks the user's flow) — it's to make failure
**legible**: the system stays graceful, the human stays informed.

One-line design rule: **any change that adds a fallback path must
ship the "you are degraded" signal in the same change.**
Design-review question: *"when this falls back, who knows, and how
fast?"*

## The spine: one true story (2026-06-11 recall-loop triage)

Narrative arc, all receipts real
(docs/specs/just-in-time-recall/recall-loop-triage-2026-06-11.md):

1. The innocent question: "are the memory enhancements helping yet?"
2. The dogfood: `/recall` on a topic with rich history → `[]`.
3. Layer 1: the semantic-memory server had been dead for a WEEK
   (died on a reboot; nohup). Nothing surfaced it — the resolver's
   connectivity gate politely degraded to a file tier.
4. Layer 2: the file tier held 2 entries — both test fixtures. The
   store had NEVER held a real finding.
5. Layer 3: 19 "done" sentinels said the capture hook had run.
   Three silent mechanisms compounded: a miscalibrated threshold
   gate (most sessions never captured), a hook interpreter missing
   an optional dependency (captures went to the wrong tier), and a
   capture step that returned 0 on failure while the "done" marker
   was written anyway.
6. The kicker: every individual component WORKED. 100+ tests green.
   The extraction quality, tested live, was genuinely good. Only
   the live loop, walked end-to-end with receipts demanded at each
   step, exposed that the system had been performing the motions of
   memory without remembering anything.

## The pattern, generalized — three instances, one shape

Each previously named separately; the article unifies them:

- **"Registered ≠ working"** — a hook/skill/integration that's
  wired up and exits 0 is not evidence it does anything. The
  receipt is a non-mocked round-trip.
- **"Mocked-green / live-broken"** — 100+ passing tests where the
  mocks encode the developer's belief about the dependency, not
  the dependency's behavior (the AMS dedup/ordering/limit traps).
- **"Degraded-silently"** — this article's headline case: the
  fallback works so well it conceals the outage.

Unifying claim: all three are the system being *polite about
failure*, and the politeness is what makes the failure expensive.
`except Exception: return fallback` borrows observability from
your future self — with interest.

## The fix pattern — legible, not loud

Three concrete mechanisms (each maps to a fix that shipped in #769):

1. **A status function** — `backend_status()`-style: cheap,
   queryable, names the unreachable tier rather than summarizing
   "ok/not ok".
2. **A health line at a natural attention point** — session start,
   CLI output footer — that prints **even when there are zero
   results**. Silence is exactly what hides the outage; "no results
   (file tier; semantic tier unreachable)" is a different fact than
   "no results".
3. **A forensic file trail** — when a process's stdout is
   structurally invisible (Stop hooks, daemons, cron), a one-line
   append-only log beside its state files turns the next hour-long
   triage into a 30-second grep.

Counterpoint to address honestly: why not just crash / alert?
Because the degraded mode IS valuable (the file tier kept working;
the session must not break). Loudness taxes the user every time;
legibility taxes them only when they look — but guarantees there's
something true to see.

## The epistemics tie-in (closing section)

This is the receipts discipline pointed inward. Receipts make the
*agent's* claims legible to the human; legible failure makes the
*system's* state legible to both. Same principle at both layers:
trust is built by making it cheap to verify and impossible to be
silently wrong. (Cross-link: Discipline article §7,
verification beats taste.)

## Material inventory (for drafting)

- Triage doc with full command-level receipts (link above)
- attune-ai #769 — the three fixes + tests, diff-able
- CLAUDE.md lesson (2026-06-11) — the compact three-rule form
- Global memory `feedback_legible_failure_principle` — the
  ratified one-liner
- Prior-instance sources: AMS four-behaviors lesson, P2-hooks
  "registered ≠ working" lesson

## Open questions for Patrick

- Audience: the Discipline article's audience (practitioners
  working with AI agents), or broader (anyone shipping fallback
  paths)? The story works for both; the framing differs.
- Venue: attune-ai.dev alongside /discipline, or external first?
- How much of the AI-collaboration angle to foreground — the
  triage was agent-driven dogfooding, which is itself a point.
