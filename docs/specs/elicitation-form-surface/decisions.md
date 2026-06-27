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

## Open (to be decided in design, after Phase 0)

- **First integrated flow (G3)** — leaning Socratic discovery flow
  (Patrick 2026-06-27); confirmed in design.
- **Result-return mechanism + parsing** — delegated to the agent's
  design-time judgement after Phase 0 grounds the surfaces (Patrick
  2026-06-27); R6/D3 (declarative artifact) holds regardless.
- **Final surface decision** (Phase 0 Q0.4).
- **Revisit the `socratic-ambiguity-calibration` "ask only when
  genuinely ambiguous" rule** — Patrick endorses it now but is open to
  changing it with more feedback. Future discussion, not a v1 change.
