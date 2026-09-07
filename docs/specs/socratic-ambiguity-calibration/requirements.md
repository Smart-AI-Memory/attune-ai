# Socratic Ambiguity Calibration — Requirements

**Status:** parked (2026-09-07; reqs+design shipped #1071/#1072; #1068 =
paired trigger fix, not this scope; G1's rule text SHIPPED 2026-09-07 via
host-surface-parity D16 + #2459, outside this spec; G2–G4 open; the
per-session measure is a CANDIDATE, Q4 unruled — see
[decisions.md](decisions.md)) · Resume-Trigger: chair ruling on Q4 ·
**Owner:** Patrick + agent
**Sequencing:** queued **behind 9.0.0** (the Empathy framework removal).
**Born:** the 8.10.0-ship session (2026-06-25). After a compound reply
I'd *guessed* at, Patrick's feedback was "always query me on an
ambiguous reply — guessing isn't ideal; it can usher in missteps and
hallucinations," then the deeper point: "it will also help me learn."
He then asked: **"will end users benefit from this insight?"** — which
is the seed of this spec: elevate the private working-rule into the
product's Socratic design so every user gets it, not just our sessions.

## Problem

attune-ai's headline differentiator is **Socratic discovery** — ask
before executing. But the rule as written is reflexive: *"ALWAYS use
AskUserQuestion … NEVER skip straight to execution."* Two gaps:

1. **No calibration → Socratic fatigue.** "Always ask" means the agent
   can re-ask for scope the user already gave ("audit src/ for
   secrets" → "which path?"). Over-asking on clear input erodes trust
   as much as guessing does, and makes the questioning feel like a
   form, not intelligence.
2. **The questioning isn't framed as a *learning* act.** A good
   clarifying question forces the user to articulate intent — which
   sharpens *their* thinking, not just the agent's inputs. The product
   treats questions as gates ("I need info"), not as a sharpening tool
   ("to target this well, which …?"). That frame is a differentiator:
   most coding tools guess and apologize; attune could ask and make the
   user smarter for it.

The unifying principle (from the session's working-memory rule
`feedback_query_dont_guess_on_ambiguity`): **ask when the request is
genuinely ambiguous; proceed when it's clear; never guess on genuine
ambiguity — and frame the question as clarifying the user's own
intent.**

## Goals

- G1. Refine the **Socratic Interaction Rule** (`.claude/CLAUDE.md`)
  from "always ask" to "ask when it matters," with three explicit
  arms: ask-on-genuine-ambiguity, proceed-when-clear (state the
  assumption), never-guess-on-ambiguity.
- G2. Make per-skill **`Scoping`** sections *conditional* — ask only
  the inputs the user left genuinely open; honor anything specified.
- G3. Bake the **learning frame** into the question copy guidance
  (question as intent-sharpening, not info-gathering).
- G4. Propagate to the **skill template** so new skills inherit it.
- G5 (candidate, unruled — Q4). Measure the calibration per session:
  `asked` / `inferred` / `corrected` / `confirmed_untouched` counts and
  the two rates they yield, so arms 2 and 3 of d1 can be read from data
  instead of argued. See "Per-session calibration measure" below.

## Non-goals

- Not removing Socratic discovery — this *sharpens* it, doesn't weaken
  it. The "never guess on genuine ambiguity" arm is the safeguard
  against under-asking.
- Not a runtime ML ambiguity-detector — this is prompt/design guidance
  the agent applies, consistent with how skills already work.

## Draft artifacts (carried from the session, to refine in design)

### Refined Socratic Interaction Rule (draft)

```markdown
## Socratic Interaction Rule

Guide users with questions — but ask when it *matters*, not
reflexively. The goal is to clarify intent, not to gate every action.

### Ask when the request is genuinely ambiguous
Ask before executing when a decision the workflow must make has ≥2
plausible answers that lead to materially different outcomes, and the
user hasn't already specified it (scope unstated; request maps to >1
skill; choice changes cost/blast-radius/output; premise should be
measured first). Frame the question as clarifying the *user's* intent.

### Proceed (don't ask) when intent is clear
If the user already specified scope/target/focus, DON'T re-ask —
proceed and state the assumption in one line so they can redirect.
Over-asking on clear input is its own failure mode (Socratic fatigue).

### Never guess on genuine ambiguity
When input is genuinely ambiguous, ASK — never guess and proceed. A
right guess is luck; a wrong one builds real work on a wrong premise.
The seconds a question costs are cheaper than a misstep — and
answering sharpens the user's own thinking.
```

### Per-skill conditional `Scoping` (draft)

```markdown
## Scoping (ask only what's genuinely open)
Check each input the workflow needs. Ask ONLY the ones the user left
ambiguous; honor anything they already specified.

| Input | Ask only if… | If the user gave it |
|-------|--------------|---------------------|
| Target path | no path given | use it — don't re-ask |
| Focus | request is generic ("review this") | honor the stated focus |
| Depth/budget | costly multi-agent run + unstated | use the default, state it |
```

## Scope / blast radius

- `.claude/CLAUDE.md` — the Socratic Interaction Rule (core change).
- All **16** `plugin/skills/*/SKILL.md` `Scoping` sections.
- The skill template / authoring guidance (so new skills inherit it).
- Possibly the meta-workflow Socratic form engine
  (`src/attune/meta_workflows/form_engine.py`) if the calibration
  should reach the code-level questioning path too — design decision.

## Per-session calibration measure (candidate, unruled — Q4)

Added 2026-09-07 at the chair's direction (thread 3 of that session's
ranking). Host-surface-parity **D16** (2026-09-07) ruled the
confirm-on-trigger calibration for this repository's dev sessions and
named this spec as "the place for the product-level version and its
measurement". This section is the measurement half. It is a candidate:
nothing below is built, and Q4 records the ruling still owed.

### Why a measure

d1's three arms name two opposite failures — guessing where an ask was
owed (arm 3) and asking where an assumption would have done (arm 2).
Each is argued from anecdotes today. Two per-session rates make both
visible at once, and they pull in opposite directions, so neither can
be optimized alone:

- a high **correction rate** after inference means under-asking;
- a high **confirm-without-change rate** means ceremony.

The framing carried from the 2026-09-07 planning session: one week of
that data would settle more than another round table.

### Unit and counts

The unit is one agent session on one host. Four counts per session:

| Count | Definition | Arm |
| --- | --- | --- |
| `asked` | asks put to the user before acting: native `AskUserQuestion` calls (questions counted, not calls), Attune forms rendered, typed fallback questions | 1 |
| `inferred` | decisions taken by assume-and-disclose instead of an ask: assumptions disclosed in the report, `assumption_review` items surfaced, form questions carrying a `default` with `inferred_from`, `suggested` values on ranking or triage | 2 |
| `corrected` | inferred decisions the user reversed afterwards: `assumption_review` reject or edit rulings, a `suggested` value changed at submit, a user message redirecting an assumed reading | 3 (violated) |
| `confirmed_untouched` | asks answered by accepting the proposal as offered: the " (Recommended)" option picked, a form submitted with a `suggested` value untouched, a `[No preference]` answer | 2 (violated) |

Two rates: **correction rate** = `corrected / inferred`;
**ceremony rate** = `confirmed_untouched / asked`. Read together, never
one alone. No target band is proposed — the first week of counts is
what a band would be set from.

### Sources (existing stores first, per ASI-6)

| Signal | Store today | Gap |
| --- | --- | --- |
| Form asks and answers | `~/.attune/telemetry/form_events.jsonl` — `form_rendered` / `form_submitted` joined on `instance_id` | no per-field accepted-untouched flag; that is attune-forms#90 option 3 |
| Native asks and answers | none — a hand-written `AskUserQuestion` turn never enters Python (the attune-forms `form_events` module docstring says so) | a PostToolUse hook on `AskUserQuestion` appending local rows: question count, whether the picked label carries " (Recommended)", `[No preference]`, dismissal; same consent model as `form_events` — local, default-on, `DO_NOT_TRACK` honored, nothing leaves the machine |
| Surfaced inferences | `assumption_review` rulings, `default` + `inferred_from`, `suggested` — all in the validated response | not aggregated anywhere |
| Inferences and corrections in prose | transcript only | `/retro` self-report: the close-out already asks which claims carried no stated basis; add the two counts to that ask |

### Boundaries

- **Not the ASI T4 protocol.** T4 records `Corrections`,
  `Clarification turns` and `Override` per occurrence of ONE consumer
  (the `spec` review choice) under a frozen preregistration. This
  measure is per session across every ask and does not amend T4; a T4
  occurrence's clarification turns are a subset of `asked`.
- **Not a runtime ambiguity detector** (the non-goal above holds). The
  counts observe the calibration; they do not decide it.
- **No provider calls, no phone-home.** Every source is local.
- **Nothing counted is authority.** A low ceremony rate does not
  license skipping D16's trigger list.

## Open questions (Q1–Q3 resolved 2026-06-25; Q4 open)

Rulings live in [decisions.md](decisions.md).

- Q1. Always-ask vs calibrated? → **calibrated** (d1).
- Q2. Reach the Python `SocraticFormEngine`? → **no — skills + rule
  only**; engine is a deferred follow-up (d2).
- Q3. How to operationalize "genuinely ambiguous"? → **shared one-line
  test (rule + template) + per-skill conditional `Scoping` table** (d3).
- Q4. Adopt the per-session calibration measure (G5)? → **open**
  (raised 2026-09-07; options and the lead's recommendation are in
  decisions.md; not ruled).

## Related

- Working-memory rule: `feedback_query_dont_guess_on_ambiguity`
  (the personal-discipline seed of this product spec).
- Pairs with the shipped **skill-trigger disambiguation** (#1068) —
  same surface (skill `.md` design), complementary concern (triggers =
  *which* skill fires; this = *whether/what* it asks before running).
- Host-surface-parity **D16** (2026-09-07): ruled the dev-session
  calibration and delegated the product-level version and its
  measurement here; **#2459** shipped the `elicit` / `planning` Claude
  host default that carries G1's rule text.
- adaptive-session-interactions **ASI-6** and the frozen
  [T4 protocol](../adaptive-session-interactions/t4-protocol.md):
  per-occurrence counts for one consumer; this measure composes with,
  never amends, that protocol.
- attune-forms#90: the accepted-untouched flag (option 3) is this
  measure's form-side source.
