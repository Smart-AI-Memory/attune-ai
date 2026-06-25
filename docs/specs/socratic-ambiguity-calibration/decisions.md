# Socratic Ambiguity Calibration — Decisions

Design-phase decisions for [requirements.md](requirements.md).
Sequencing unchanged: implementation queued **behind 9.0.0**.

---

## d1 — Calibrated, not reflexive "always ask" (Q1)

**Decided:** 2026-06-25 · **By:** Patrick

The Socratic Interaction Rule moves from reflexive *"ALWAYS ask,
NEVER skip to execution"* to the **calibrated** three-arm form:

1. **Ask on genuine ambiguity** — a decision the workflow must make
   has ≥2 plausible answers with materially different outcomes, and
   the user hasn't already specified it.
2. **Proceed when clear** — if scope/target/focus is given, don't
   re-ask; proceed and state the assumption in one line.
3. **Never guess on genuine ambiguity** — the safeguard against
   under-asking; a wrong guess builds real work on a wrong premise.

**Why:** reflexive "always ask" has its own failure mode — re-asking
for scope the user already gave (`audit src/ for secrets` →
"which path?"). Over-asking erodes trust as much as guessing does and
makes questioning feel like a form, not intelligence. Calibrated keeps
the safeguard (arm 3) while removing the fatigue, and is the stronger
differentiator: attune asks only when it sharpens the user's intent.

**Rejected:** keep always-ask (brand stance); hybrid-by-surface
(always-ask for `/attune` entry, calibrated for workflow skills) —
more copy to maintain for marginal gain.

---

## d2 — Scope to skills + rule; form engine out of scope (Q2)

**Decided:** 2026-06-25 · **By:** Patrick

Calibration scope is the **rule + 16 `SKILL.md` Scoping sections +
the skill template**. The Python `SocraticFormEngine`
(`src/attune/meta_workflows/form_engine.py`) is **out of scope**,
noted as a possible follow-up.

**Why:** the engine is schema-driven — `ask_questions()` asks whatever
a `FormSchema` defines; it does not reflexively over-ask the way the
"always ask" rule does. Calibrating it would mean adding
conditional/skip-if-already-known logic to the engine + schema format
— a separable, heavier code change, ill-timed against the 9.0.0
removal churn. The reflexive over-asking this spec targets lives in
skill copy + the rule, so that is where the win is.

**Follow-up (deferred):** if form schemas later need
ask-only-what's-open behavior, add a `skip_if` predicate to
`FormQuestion` and have `ask_questions()` honor already-known inputs.

---

## d3 — Shared test + per-skill table (Q3)

**Decided:** 2026-06-25 · **By:** Patrick

"Genuinely ambiguous" is operationalized **at author time**, not via
a runtime detector, with two layers:

1. **Shared one-line test**, stated once in the rule + skill template:
   > Ask about an input only if it has ≥2 plausible values that lead
   > to materially different outcomes **and** the user didn't already
   > specify it. Otherwise proceed and state the assumption.
2. **Per-skill conditional `Scoping` table** in each `SKILL.md` that
   instantiates the test for that skill's actual inputs
   (Input | Ask only if… | If the user gave it).

**Why:** the shared test keeps the definition DRY and consistent
across skills (no drift); the per-skill table makes it concrete for
each workflow so the agent has less to interpret. Rejected:
per-skill-table-only (duplication, drift) and shared-test-only (too
abstract per workflow).

---

## Status

All three design-phase open questions (Q1–Q3) resolved. Spec moves
**draft → approved**. Implementation remains queued **behind 9.0.0**.
