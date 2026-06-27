# Elicitation Form Surface — Requirements

**Status:** draft (2026-06-27) · **Owner:** Patrick + agent
**Born:** a post-9.0.0 chat. Patrick — tech-writing / hypertext-help
background — said he'd "missed the form-related options from working
with HTML" and wanted to explore them, multi-select first. Two live
widget mockups (a generic HTML control showcase + an attune
spec-intake form) made the experience concrete and surfaced the real
engineering question this spec exists to answer.

Direct sibling of
[socratic-ambiguity-calibration](../socratic-ambiguity-calibration/requirements.md):
that spec decides *when* to ask; this one enriches *how* the asking is
rendered and collected.

## Problem

attune's Socratic discovery and wizard flows collect user input only
through `AskUserQuestion` — a 2–4-option, one-question-per-turn
multiple-choice primitive. Two costs:

1. **Multi-field intake is N turns, not one form.** Gathering an
   outcome + approach + concerns + scope today means a stack of
   sequential button-questions. A single intake form would collect all
   of it in one pass. (Observed live: one session asked ~8 separate
   button-questions to gather less than a single form holds.)
2. **The control palette is impoverished.** HTML forms have text,
   textarea, number, range, select, multi-select, radio, checkbox,
   toggle, date, color. `AskUserQuestion` has buttons. Inputs that are
   natural as a slider (budget cap, fan-out, severity threshold), a
   multi-select (the concerns palette), or free text (spec outcome) are
   today either coerced into buttons or parsed out of prose.

Multi-select is the headline gap: it is the control Patrick reached for
first and the one buttons most obviously cannot express.

## Goals

- **G1.** Give attune an owned **elicitation/form surface** that
  collects multiple typed fields in a single pass, returning structured
  data — not N sequential button-questions.
- **G2.** Support a **richer control palette** than buttons, with
  **multi-select as the priority-1 control**; radio, range, textarea,
  toggle, number, date as the target set.
- **G3.** Route at least one real attune flow through it first
  (candidate: wizard step, `/attune` Socratic discovery, or spec/release
  intake — first target chosen in design, after Phase 0).
- **G4.** Degrade gracefully where the surface is unavailable: a flow
  must still complete (falling back to today's `AskUserQuestion`
  button turns), never dead-end.

## Non-Goals

- Replacing `AskUserQuestion` wholesale. It stays the right tool for a
  quick 2–4-way pick; this is for multi-field / rich-control intake.
- Shipping a web app or external form host. The surface must live
  inside the Claude Code / MCP interaction, not a separate URL.
- Building every HTML control. Color and other low-value inputs are
  explicitly out of the v1 target set (G2).

## Phase 0 — Research spike (gate before requirements firm up)

Chosen 2026-06-27: do not spec on unverified assumptions about the
delivery surface. Phase 0 grounds the surface decision; R-numbers below
are provisional until it lands. Verify against real docs/SDK, never
from memory (the claims in the bullets are the *questions*, not facts).

- **Q0.1 — MCP elicitation reality.** Does MCP native elicitation
  exist in the client(s) attune targets? What JSON-schema field types
  does it support — is it flat (string/number/boolean/enum) only, or
  can it express **multi-select** (array/enum-multi)? What is the
  actual client-coverage today (Claude Code desktop/CLI/web)?
- **Q0.2 — Rendered-widget surface.** What is the real availability and
  contract of an inline widget surface (the `visualize`-style path used
  in the mockups)? Confirm the return mechanism (post-JSON-back vs a
  clean tool result) and which clients render it.
- **Q0.3 — Multi-select feasibility per surface.** For each surface,
  can the priority-1 control (multi-select) actually be delivered, or
  does it need a documented fallback?
- **Q0.4 — Recommendation.** Output a surface decision (elicitation /
  widget / hybrid) with the evidence, recorded in
  [decisions.md](decisions.md). Hybrid baseline (portable elicitation +
  widget enhancement where supported) is the hypothesis to test, not a
  foregone conclusion.

## Requirements (provisional — confirm against Phase 0)

- **R1.** A single elicitation call presents multiple fields and
  returns one structured result object keyed by field id.
- **R2.** The palette covers the G2 target set, with multi-select
  working on at least one verified surface.
- **R3.** Every elicitation has a button-question fallback path (G4);
  the flow's outcome is identical whichever surface fired.
- **R4.** The collected result is validated (types/required) before the
  flow consumes it — no silent acceptance of malformed input.
- **R5.** The first integrated flow (G3) demonstrably replaces an
  N-turn button stack with one form, dogfooded end-to-end (not just
  unit-mocked) — a real round-trip is the receipt.
- **R6.** A form is defined as a **declarative, serializable artifact**
  (data, not imperative agent code). One artifact renders on any
  surface, validates the same way, and could later be human-authored or
  have fields/options bound to a data source. This is the shared spine
  that keeps the user-designed / data-bound horizon (see North star)
  open at near-zero cost now — and the one architectural choice locked
  this session (decision [D3](decisions.md)). Confirmed with Patrick
  2026-06-27.

## North star (out of scope for v1)

Where this path eventually leads — recorded so v1's architecture does
not foreclose it, **not** committed work:

- **User-designed forms** — Patrick authors a form artifact himself, not
  just the agent generating one at need.
- **Data-bound forms** — a field's options come from a query; a
  submission persists to / prefills from a store.

R6 (declarative artifact) is the only thing v1 must honour to keep this
reachable. Building the designer or the data binding is explicitly
later.

## Open questions

- **First target flow (G3)** — leaning toward the **Socratic discovery
  flow** (the `/attune` discovery surface / sibling
  [socratic-ambiguity-calibration](../socratic-ambiguity-calibration/requirements.md)),
  named by Patrick 2026-06-27 as the good example. Confirmed in design,
  after Phase 0.
- **Result-return mechanism** (tool value vs posted message, and how the
  agent reliably parses it) — **delegated to the agent's design-time
  judgement** once Phase 0 grounds the surfaces (Patrick 2026-06-27).
  Whatever the mechanism, R6 (declarative artifact) holds.
- **Interaction with `socratic-ambiguity-calibration`** — a form is the
  "ask" surface; that spec's "ask only when genuinely ambiguous" rule
  governs *whether* to render one. They compose; confirm no conflict.
  Patrick endorses that rule but is **open to revisiting it with more
  feedback** — not a v1 change, flagged for future discussion.

## Exploration record

Two interactive mockups (2026-06-27) established the desired
experience and are the reference for the palette:

1. **HTML control showcase** — text, textarea, number, range,
   dropdown, multi-select, radio, checkbox, toggle, date, color; live
   summary + post-back.
2. **attune spec-intake form** — outcome (textarea) + artifact-shape
   (radio) + concerns (multi-select) + fan-out (range) + spec-first
   (toggle), collected in one pass — the form equivalent of a Socratic
   discovery turn.
