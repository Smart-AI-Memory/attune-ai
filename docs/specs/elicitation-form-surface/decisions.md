# Elicitation Form Surface — Decisions

Decision log for [requirements.md](requirements.md). Append-only;
newest at the bottom.

## D1 — Resolve the delivery-surface fork with a Phase 0 research spike

**Date:** 2026-06-27 · **Status:** decided

The central design fork is the delivery surface: MCP native elicitation
(portable, tool-native return, but possibly flat schemas / uneven
multi-select support) vs a rendered HTML widget (full palette, but
client-dependent and round-tripping via posted JSON).

Rather than spec on unverified assumptions about either surface — the
agent flagged its own elicitation claims as memory, not verified fact —
the spec opens with **Phase 0**, a research spike that grounds the
surface capabilities against real docs/SDK before requirements firm up
(see requirements §Phase 0). Hybrid baseline (portable elicitation +
widget enhancement) is the hypothesis to test, not a foregone
conclusion.

**Why:** honours verify-first — the recurring "research subagents
confabulate SDK signatures; introspect before coding" and "re-validate
a spec's premise" disciplines. Speccing the build on an unconfirmed
multi-select capability would risk a wrong foundation for exactly the
control Patrick most wants.

## D2 — Priority-1 control is multi-select

**Date:** 2026-06-27 · **Status:** decided

Multi-select is the headline target: the control Patrick reached for
first and the one buttons most obviously cannot express. The palette
also targets radio, range, textarea, toggle, number, date (G2); color
and other low-value inputs are out of v1 scope.

## D3 — A form is a declarative, serializable artifact

**Date:** 2026-06-27 · **Status:** decided

Forms are defined **as data** (a declarative, serializable artifact),
not constructed imperatively in agent code. The same artifact renders
on any surface, validates the same way, and could later be
human-authored or have fields/options bound to a data source.

**Why:** it is the shared spine for the North-star horizon (user-designed
+ data-bound forms) — Patrick's "integrating content from databases and
so on." Made declarative now, that horizon stays reachable at near-zero
extra cost; built imperatively, it would foreclose it. This is the one
architectural choice locked this session; the designer and data binding
themselves are explicitly out of v1 scope. Also makes forms
surface-agnostic, which de-risks the Phase 0 surface fork (D1).

## D4 — Phase 0 outcome: AskUserQuestion-first; elicitation rejected, widget deferred

**Date:** 2026-06-27 · **Status:** decided (Phase 0 Q0.4) · **Resolves D1**

Phase 0 research (cited findings below) **overturned the spec's
premise** and resolves the surface fork. v1 builds on the built-in
**`AskUserQuestion`** tool; MCP elicitation is rejected; the rendered
widget is deferred to a later enhancement.

**Findings (verify-first; confidence flagged):**

- **`AskUserQuestion` already supports the two priority controls.**
  `multiSelect: true` per question = choose-many; the `questions` array
  takes **up to 4 questions in one call** = multi-field in a single
  pass; the return is a clean structured dict (no message-parsing).
  *Confirmed against the live tool schema — documented.* The premise
  that "AskUserQuestion is buttons-only, one question per turn" was
  wrong: the one-question habit is **attune's own question-shape rule**
  (`feedback_question_shape` / `ask_question_format_guard`), not a
  platform limit.
- **MCP elicitation cannot express multi-select.** The 2025-06-18 spec
  restricts `requestedSchema` to flat objects of primitives
  (string/number/boolean/enum); arrays/multi-select are excluded *by
  design*. *Documented.* And Claude Code client support for elicitation
  is **unconfirmed (likely absent)** — undocumented in the CC/SDK docs.
  Either way it fails the priority-1 control, so it is rejected.
- **The rich palette (slider/textarea/date) has no portable surface.**
  Only the `visualize`-style widget renders it, and that is an
  Anthropic surface with a fragile post-JSON-back return — **not an
  MCP-server capability** attune can own. Deferred, not core.

**Decision:** v1 = a declarative form (D3) rendered onto
`AskUserQuestion` at its full extent (multi-select + ≤4 questions/pass),
plus **relaxing attune's one-question rule** where a genuinely compound
intake warrants a multi-question turn. Rich-control widget = deferred
enhancement off the *same* declarative artifact. This collapses the
build to a renderer + a rule change — no new infrastructure — and
re-fuses the spec with its sibling
[socratic-ambiguity-calibration](../socratic-ambiguity-calibration/requirements.md)
(the lever is *how we question*, not new plumbing).

**Sources:** MCP spec 2025-06-18 elicitation
(`modelcontextprotocol.io/.../client/elicitation`); Claude Code Agent
SDK user-input docs (`code.claude.com/.../agent-sdk/user-input`);
live `AskUserQuestion` tool schema.

## D5 — v1 design approved (first-target + rule relaxation)

**Date:** 2026-06-27 · **Status:** decided · see [design.md](design.md)

Patrick signed off on the v1 design as drafted:

- **First integrated flow (G3) = the `/attune` Socratic discovery
  scoping turn** (goal + scope + focus — today sequential buttons).
  Dogfooded end-to-end per R5.
- **One-question-rule relaxation (design §4) approved.** Batch 2–4
  fields into one form-turn *only when all hold*: independent
  dimensions of one decision · answers don't branch · each field is
  genuinely ambiguous per `socratic-ambiguity-calibration`; otherwise
  stay single-question. Composition: the sibling rule decides *which*
  fields are worth asking, the form decides *whether* they're batched —
  the form never adds a field the ambiguity rule wouldn't already ask.
  This is the guardrail against richer forms amplifying Socratic
  fatigue.
- **v1 artifact types** = select / multiselect / text (via the "Other"
  free-text escape). slider/date/number/color are valid artifact types
  but deferred to the widget enhancement (D4).

Build scope now fully specified: a declarative-form renderer onto
`AskUserQuestion` + the §4 batching rule. No new infrastructure.

## Open

- **Confirm CC elicitation support** — low priority (elicitation is
  rejected regardless for lacking multi-select), but worth nailing if
  the widget/enhancement phase is ever revisited.
- **Revisit the `socratic-ambiguity-calibration` "ask only when
  genuinely ambiguous" rule** — Patrick endorses it now but is open to
  changing it with more feedback. Future discussion, not a v1 change.
