# Elicitation Form Surface — V6 Requirements: the MCP Apps adapter

**Status:** draft (2026-07-16) — awaiting Patrick approval.
**Freeze:** design-only until 2026-07-28 (ratified with the
standards-landscape sequence); no code before the freeze lifts.
**Sequencing:** V7 (`v7-requirements.md`) was ratified 2026-07-17 and
sequences BEFORE this doc in the same post-freeze window (D20 in
[decisions.md](decisions.md)) — V7's templates supply this adapter's
round-trip payloads. This doc's own approval remains open.
**Source:** [v3-standards-landscape.md](v3-standards-landscape.md)
(2026-07-13, 26-agent verified) — this doc is its "Recommended
sequence" step 2 (+ step 1 as FR-4), phased as V6.
**Constraints (ratified 2026-07-13):** projector-not-platform;
adapters-not-foundations.

## Premise — stated, per the value gate

attune has ~0 external usage signal, and the ratified rule is
validate-infrastructure-against-user-value. V6 passes the gate on a
**distribution premise, named explicitly**: MCP Apps is the standard
co-developed by Anthropic + OpenAI, and the OpenAI Apps SDK converged
on it — so ONE adapter projects the grammar into Claude
(web/desktop/mobile/Cowork) **and** ChatGPT (app directory = a
discovery channel, plausibly the user-acquisition move). If that
premise weakens (directory access gated, host support regresses),
re-triage before building.

## What V6 adds

Projection target #4 for the existing `FormSchema` master: the
grammar's constructs (intake, decision, pushback, progress — plus
`list_style` variants) rendered as **MCP Apps widgets**:

- pre-declared MCP resources at `ui://attune/<construct>`
  (`text/html;profile=mcp-app`) on the MCP server attune already
  ships;
- tools link via `_meta.ui.resourceUri`;
- round-trip via `tools/call` from the widget iframe back into the
  one validator seam.

No new subsystem, no new family member, no new validator. The render
core is the shipped `form_to_widget_html`; V6 wraps it in one
generic, grammar-driven construct-renderer template.

## Functional requirements

- **FR-1 — resource registration.** Register `ui://attune/<construct>`
  resources for every grammar member on the existing MCP server.
  Adding a future construct must require only its existing
  `widget.py` render branch — no per-adapter fork.
- **FR-2 — one generic renderer.** A single construct-renderer
  template driven by `FormSchema`; per-construct differences stay in
  the existing `_control_html` branches.
- **FR-3 — one reply channel.** Widget postbacks flow through
  `tools/call` into `collect_form_response` (R4: never silently
  accept malformed input). No parallel response path.
- **FR-4 — envelope correction (landscape memo, step 1).** The v3
  construct-response envelope EXTENDS the shipped
  `__elicitation_response__` sentinel channel (add `action`/instance
  fields) — it does not introduce a parallel `construct-response`
  prefix. One reply channel, one validator. Free; land first.

## Acceptance criteria — receipts, not registration

- **AC-1 — Claude host round-trip.** A real construct rendered via
  `ui://` in an MCP Apps-capable Claude surface; a human submits; the
  postback validates through `collect_form_response`. Receipt =
  response id, per the D15/D16/V5 pattern.
- **AC-2 — ChatGPT host round-trip.** The SAME artifact rendered in
  ChatGPT (dev mode acceptable; directory listing not required for
  AC); human submit; validated postback. Receipt required.
  "Registered ≠ working" — AC-2 is the gate that makes the
  distribution premise real, and V6 is NOT done without it.
- **AC-3 — full-grammar coverage.** All four constructs render
  through the one template and round-trip the one validator (unit +
  one live receipt each on the Claude host; ChatGPT receipt required
  for at least `decision`).

## Non-goals

- AG-UI / A2A adapters — parked until a consumer names itself
  (landscape tiers).
- The skills projector (sequence step 3) — separate phase.
- Infographics / display-direction visuals — owned by
  `discovery-sweep-rich-surface`, not the answer-validated grammar.
- Native MCP elicitation upgrades — quarterly re-test per host
  (D10 is host behavior), not V6 work.

## Open questions (for the design pass)

1. ChatGPT dev-mode logistics: OpenAI account/app setup needed for
   AC-2, and whether dev-mode rendering matches directory rendering.
2. Host CSP/iframe constraints: does `form_to_widget_html` output
   need a sandbox-safe variant (no inline handlers) per host?
3. Resource versioning: how `ui://attune/<construct>` versions when
   the widget template changes (cache behavior per host).
