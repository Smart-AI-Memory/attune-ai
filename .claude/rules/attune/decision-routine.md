# Decision Routine — Choosing the Right Shape of Work

**Created:** 2026-05-19
**Source:** Session conversation; codifies the lead-with-
recommendation + concerns-palette discipline.

---

## Purpose

This routine enhances focus, accuracy, and proactive surfacing of
options the user can redirect. It is not a compliance flowchart — it
is a discipline that produces sharper proposals.

The default failure mode it counteracts: presenting balanced options
without a preference, jumping into execution without proposing the
right artifact shape, or proposing artifacts whose composition
(impl-only, no regression guard, etc.) silently encourages padding
or omission.

---

## When this routine fires

Any request that meets at least one of:

- Touches 3+ files
- Involves a design decision with more than one defensible answer
- Could be executed multiple ways with materially different cost
  or scope
- References a premise that should be measured before
  implementation

For trivial work (single-file edits, bug fixes, config tweaks per
`xml-enhanced-prompts.md`'s "Do NOT use" list), this routine does
NOT fire. Just do the work.

---

## Decision tree

```text
Is this trivial per xml-enhanced-prompts.md?
├─ YES → Just do it. No artifact.
└─ NO  → continue

Does this need decision recording, premise validation,
or multi-session coordination?
├─ YES, and NO spec exists for it → Spec via /spec
│        Within the spec, individual tasks use XML-enhanced
│        prompts per xml-enhanced-prompts.md criteria.
├─ YES, and a spec ALREADY exists (docs/specs/<x>/) → amend it;
│   name the choice out loud (don't silently pick):
│   ├─ originating or advancing a PHASE (new requirements/
│   │   design/tasks, or a phase gate) → OFFER /spec (re-enter
│   │   the approval loop + Socratic scoping)
│   └─ recording a decision / logging evidence / status fix
│       (decisions.md, a targeted task) → direct edit is
│       correct; mention /spec is available but don't force it
└─ NO  → continue

Does this meet xml-enhanced-prompts.md's "When to Use" criteria?
├─ YES → Single (or several) XML-enhanced prompts
└─ NO  → Just do it inline
```

XML-enhanced prompt criteria are canonical in
`xml-enhanced-prompts.md`. This file does not duplicate them. If
you find yourself listing them here, stop and reference the
canonical file instead.

---

## Concerns palette

When recommending one or more XML-enhanced prompts, also propose
which **concerns** the work needs. Each concern maps to one prompt
block. Don't pad with concerns that don't apply.

| Concern | When to include |
|---|---|
| `impl` | The production change itself. Always present. |
| `test` | New tests covering new behavior. Skip when impl includes test changes inline. |
| `regression-guard` | Drift-protection test that fails CI if the bug returns. Use on bug fixes; skip on feature adds. |
| `docs` | User-facing docs that aren't release artifacts: mkdocs pages, in-code docstrings, README structural content (not badges/version). Skip when the change is invisible to users. |
| `migration` | Backward-compat shims, deprecation timers. Use on breaking changes; skip on additive ones. |
| `release-notes` | CHANGELOG entry, README badges/version refs, decisions.md log when unblocking a spec, plus version-bump files per CLAUDE.md's "Version bumps touch 7+ files" lesson when shipping a release. Use when the change ships externally or unblocks a spec. |
| `preflight` | Lint / format / typecheck pass before staging. Use when the change touches files known to trip pre-commit (mixed formats, generated files, sibling-package boundaries). |

Don't extend this palette ad-hoc. If a new concern emerges, propose
it in a session and add it deliberately — additions here drift into
"checklist of every possible thing" if uncurated.

---

## Visible output pattern

When the routine fires, produce output in this shape:

> **Recommended: X.** *(one sentence — what and why)*
>
> *Rationale: 2-3 lines.*
>
> **Concerns:** `impl` + `regression-guard` + `release-notes`
> *(only when XML prompts are recommended)*
>
> *Inline XML prompt(s) here if XML is the recommendation.*
>
> **Alternatives:**
>
> - Option B — one-line tradeoff
> - Option C — one-line tradeoff
>
> **Open questions** *(only if real ambiguity exists)*

Lead with the recommendation. Render the XML prompt inline when XML
is the answer — don't make the user approve-then-see. List
alternatives ranked, briefly. Surface open questions only when they
genuinely matter; don't manufacture ambiguity.

---

## Pushback discipline

When a user-stated preference looks weaker than an alternative I
see, push back — but only if I can render the alternative
concretely (XML prompt body, file list, measurement plan). Pushback
without a concrete artifact is hedging, creates friction, and
carries no value. If I can't render the alternative, execute the
user's plan and learn the boundary later.

The concrete artifact this discipline requires has a first-class
shape: the **pushback construct** (communication grammar member #3 —
see [communication-grammar.md](communication-grammar.md)). When the
surface can render it, present the disagreement AS a `pushback` (the
user's approach tagged "your approach", my alternative badged "I'd
suggest instead", a "Why I'd push back" rationale) rather than as
prose — the user overrules or switches with one pick. `/spec`'s
Stage 2 review is the worked consumer.

---

## Acting on a terse "go"

Two gates fire before executing a `go` / `do it` / `y` (full rule in
the `feedback_go_referent_and_spend_gates` memory):

- **Referent gate (A).** Execute only when exactly one action is the
  obvious referent from my immediately-prior turn. If that turn listed
  multiple options or open items, the referent is unresolved — resolve
  it first (one line or `AskUserQuestion`) before acting. The precision
  burden is mine, not the user's shorthand.
- **Spend gate (B).** Before the first billable API call of a task,
  state what + a rough cost estimate and get an explicit go for the
  spend — even when a spec pre-authorizes the work. Then it's
  session-durable. Free/local actions never trip this.

An ambiguous referent that resolves to a paid action trips both →
hard stop.

---

## Cross-references

- `feedback_go_referent_and_spend_gates` memory — the two gates above
  in full, with the origin and how-to-apply
- `.claude/rules/attune/xml-enhanced-prompts.md` — canonical for
  XML prompt criteria and schema
- `.claude/CLAUDE.md` — Critical Rules section names when to use
  XML format; Lessons Learned section has the "Version bumps touch
  7+ files" checklist that `release-notes` references
- `docs/implementation/TASK_PROMPTS.md` — 10 executed XML prompt
  examples showing the spec → tasks → XML-prompts nesting
- `/spec` command — spec-driven workflow with approval loop
