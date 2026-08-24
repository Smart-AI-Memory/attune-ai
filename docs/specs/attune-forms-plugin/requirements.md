# attune-forms Plugin & Beta — Requirements

**Status:** active (2026-08-14) — Phase 4 (chair go, D5); P1–P3 executed (D2–D4); D1 announcement gate satisfied 2026-08-13. The
sequencing and announcement gate are already chair-ratified
(decisions.md D1, ruled in-discussion the same day); this document
phases that ruling into gated, executable scope. No phase executes
before its chair go.
**Slug:** `attune-forms-plugin`
**Provenance:** chair discussion 2026-08-12, hours after the
attune-forms extraction shipped (attune-ai #2058, PyPI 0.1.0). The
chair named the goal ("I want the library to be a plugin that I can
submit to different distribution networks like anthropic's
marketplace"), accepted the lead's timing pushback (beta announcement
waits for the story and the install path), and ratified the build
order. Memory: `project_attune_forms_plugin_roadmap`.

## Position against the existing stack

- **Engine (exists):** the `attune-forms` PyPI package
  ([Smart-AI-Memory/attune-forms](https://github.com/Smart-AI-Memory/attune-forms))
  — `FormSchema` + the communication-grammar constructs
  (decision/pushback/progress), `form_from_dict` validation,
  three renderers (widget HTML, AskUserQuestion, MCP elicitation),
  surface routing, intake templates, 384 tests (was 358 at drafting; recount 2026-08-14), 7 required CI checks.
- **Host wiring (exists, attune-ai-only):** the elicitation MCP tools
  live inside attune-ai's MCP server; the `elicit` skill lives in
  attune-ai's plugin. Nothing installable exists for a repo that
  isn't running attune-ai.
- **This spec adds:** a standalone MCP server in the library, a thin
  distributable plugin wrapping it, the de-attuning of the config
  surface a public artifact requires, and the gated announcement.

## Problem

The communication grammar demonstrably improves agent↔user
communication (one validated form replaces N question turns; the
2026-08-12 session ran its entire scoping, design, and pushback flow
through it). Today it is only reachable by installing the full
attune-ai workflow harness. Distribution networks (the Anthropic
plugin marketplace, community directories) distribute skills + MCP
servers, not Python libraries — so reaching users who want ONLY the
forms grammar requires a plugin-shaped artifact that does not exist,
and the library still leaks attune-ai branding (`attune.config.json`,
`ATTUNE_*` env vars, `~/.attune` telemetry paths) that a public
artifact must not impose on strangers.

## Ruled constraints (D1 — not re-openable without a new ruling)

- **Announcement gate:** the beta is announced only after BOTH the
  communication-grammar article publishes AND the plugin ships.
  Nothing in this spec authorizes an announcement.
- **Build order:** de-attune first, then MCP server, then plugin
  wrapper, then submission. Rationale: nothing public may ever see
  the attune-branded config surface; genericizing before outside
  installs exist is strictly cheaper (attune-ai absorbs the change
  through its `<1.0` cap).
- **Overlap boundary:** attune-forms ships the GENERIC skill;
  attune-ai's plugin keeps only its attune-specific intakes
  (fix/spec/workflow templates) layered on top — mirroring the code
  split. Both installed together must not fight over trigger phrases.

## Phase 1 — De-attune the config surface (attune-forms 0.2.0)

**R1.1** Every user-facing name the library reads or writes is
genericized with a back-compat shim: config file (`attune.config.json`
→ a generic name, e.g. `forms.config.json`, old name still read),
env vars (`ATTUNE_KEYBOARD_MODE`, `ATTUNE_FORM_TELEMETRY`,
`ATTUNE_HOME` → generic equivalents, old names still honored), and
the telemetry path (`~/.attune/telemetry/form_events.jsonl` → a
generic default, old path used when it already exists).
**R1.2** Precedence is pinned by test: new name > old name > default;
a repo with only the old config keeps working byte-identically.
**R1.3** attune-ai keeps working with ZERO changes at 0.2.0 (its
existing env vars and config flow through the shims) — receipt:
attune-ai's full elicitation + MCP suites green against 0.2.0.
**R1.4** No new dependency; the library stays structlog-only.

**Gate:** chair reviews the naming choices (the generic names are a
brand decision) before implementation.

## Phase 2 — Standalone MCP server (`attune-forms[mcp]`)

**R2.1** `attune_forms.mcp` module behind an `[mcp]` extra exposing,
at minimum: `render_form` (dict → validated form + surface decision),
`render_widget` (dict → self-contained widget HTML), and
`collect_response` (form + raw answers → validated FormResponse or
field-level problems). Tool names/schemas may follow attune-ai's
existing elicitation tools where that eases later convergence.
**R2.2** Launchable as `uvx --from 'attune-forms[mcp]' attune-forms-mcp`
(console script) — the exact command a plugin `.mcp.json` will carry.
**R2.3** attune-ai's server keeps its own tools unchanged this phase
(convergence to thin delegation is follow-up work, not a blocker).
**R2.4** Receipts: non-mocked stdio round-trip test (spawn the
server, call each tool, validate replies) + a live-fire render from
a real Claude Code session.

**Gate:** chair go on the tool surface before implementation.

## Phase 3 — The plugin wrapper

**R3.1** Plugin scaffold in the attune-forms repo:
`.claude-plugin/marketplace.json` + `plugin.json`, one generic
elicit-style skill (the forms discipline, no attune workflow
references), and `.mcp.json` launching the Phase 2 server via `uvx`.
**R3.2** The skill's trigger phrases are disjoint from attune-ai's
`elicit`/`fix`/`spec` skills (overlap boundary, D1) — verified by
installing both plugins in one session and exercising each trigger.
**R3.3** Degradation is first-class and documented: widget surface
where the host renders HTML, AskUserQuestion fallback in terminal
sessions, native MCP elicitation where supported — the skill teaches
the model to consult the library's surface router, never to assume.
**R3.4** Local install receipt: `claude --plugin-dir` session in a
non-attune repo builds, renders, and validates a form end-to-end.

**Gate:** chair reviews the skill text (public-facing voice) before
the plugin lands.

## Phase 4 — Submission + beta (announcement-gated)

**R4.1** Submit to the Anthropic plugin marketplace and the community
directories the chair names (prior art: the attune-ai submission,
memory `project_marketplace_directory_submission`).
**R4.2** README/PyPI page rewritten for a zero-attune-context reader
before submission.
**R4.3** The beta announcement executes ONLY after the
communication-grammar article is published (its own thread, not this
spec) — the D1 gate, checked at this phase's chair go.

## Phase 5 — Template-bound forms (chair-placed 2026-08-24; executes after Phase 4's submission clears)

Forms authored in advance that look and work exactly like
live-composed dynamic forms — closing the two costs measured live
2026-08-24 (agent-side schema orientation; form HTML transiting the
agent's context) and the adoption gap on the existing V7
`template_store` ("sculpt once, cast per fork" exists; nothing binds
it to the places forms fire from).

**R5.1 Binding convention.** A skill/command that elicits ships its
form template alongside it (per-skill `form.json` or a named
`template_store` entry); the Socratic rule's instruction becomes
"cast the named template, fill the slots" — composing a form dict
from scratch is the fallback, not the default.
**R5.2 Fused server call.** `elicitation_render_widget` accepts
`template: <name>` + `slots: {...}` and performs
load → cast → validate → render server-side in ONE call; the form
schema and HTML never transit the agent's context.
**R5.3 Authoring gate.** A CI drift test validates every shipped
template through `form_from_dict` at authoring time — a template
edit cannot ship a form the validator would reject at cast time.
**R5.4 Authoring preview.** A standalone HTML preview page
exercising the production renderer (the ratified preview
discipline), so a template edit is seen as users will see it.

**Measurement dependency:** the form-events stage instrumentation
(form_id + build/rendered/submitted stamps, chipped 2026-08-24)
lands first, so R5.2's latency win is measured, not asserted.

## Out of scope

- The display substrate (chartkit / widget kernels) — different
  substrate, stays in attune-ai (boundary reaffirmed 2026-08-12).
- The communication-grammar article itself (writing thread; only its
  publication is a GATE here).
- Converging attune-ai's MCP server onto the standalone one (noted as
  follow-up in R2.3).
- Any auto-firing hooks in the plugin — v1 is skill + MCP tools only.

## Risks

- **Two-plugin conflict** (medium): users with both plugins get
  competing forms guidance — mitigated by R3.2's disjoint triggers
  and the D1 boundary; residual risk recorded for the Phase 3 gate.
- **Back-compat shim drift** (medium): the old-name shims in Phase 1
  quietly diverging from the new path — mitigated by R1.2's
  precedence tests running both paths every CI.
- **uvx cold-start latency** (low): first MCP-server launch downloads
  the package; document it, measure at Phase 2, escalate only on a
  measured problem (the workflow-intake-forms latency discipline).
- **Marketplace review friction** (unknown): requirements may force
  packaging changes; Phase 4 absorbs them rather than pre-engineering.
