# Socratic Ambiguity Calibration — Requirements

**Status:** parked (2026-07-13; reqs+design shipped #1071/#1072; #1068 = paired trigger fix, not this scope; remaining: G1–G4 impl — see
[decisions.md](decisions.md)) · **Owner:** Patrick + agent
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

## Open questions (resolved 2026-06-25 — see [decisions.md](decisions.md))

- Q1. Always-ask vs calibrated? → **calibrated** (d1).
- Q2. Reach the Python `SocraticFormEngine`? → **no — skills + rule
  only**; engine is a deferred follow-up (d2).
- Q3. How to operationalize "genuinely ambiguous"? → **shared one-line
  test (rule + template) + per-skill conditional `Scoping` table** (d3).

## Related

- Working-memory rule: `feedback_query_dont_guess_on_ambiguity`
  (the personal-discipline seed of this product spec).
- Pairs with the shipped **skill-trigger disambiguation** (#1068) —
  same surface (skill `.md` design), complementary concern (triggers =
  *which* skill fires; this = *whether/what* it asks before running).
