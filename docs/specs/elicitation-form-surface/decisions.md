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

## D6 — Salvage: reuse the existing form model; the live wiring is the gap

**Date:** 2026-06-27 · **Status:** decided · see
[salvage-assessment.md](salvage-assessment.md)

A bounded salvage pass found that most of v1 **already exists** and is
proven, so v1 is even smaller than D5 implied:

- **REUSE** `meta_workflows/models.py` — `FormSchema`/`FormQuestion`/
  `QuestionType` (incl. `MULTI_SELECT`)/`FormResponse` +
  `to_ask_user_format()` + `get_question_batches(4)` + validation. This
  *is* the D3 artifact + the D5 §2 renderer mapping. Do not duplicate.
- **The gap is the live wiring.** `SocraticFormEngine`'s
  `ask_user_callback` path has **no live caller** (no `/wizard` skill /
  command / CLI handler — confirmed; only a docstring placeholder +
  test mocks). `AskUserQuestion` is an agent tool, not a Python API, so
  the engine never reaches the user; today's questioning is
  markdown-driven. v1's real new work = the model→tool bridge.
- **Florence (`Deep-Study-AI/ai-nurse-florence-v3.1`) proves D3.** The
  in-repo model was built (pre-AskUserQuestion) to support that app's
  ~20 clinical multi-step web forms — the same declarative model
  already drove a *web* surface in production. That web rendering is
  the **v2 target**; v1 just drives the same model through
  `AskUserQuestion`.

**Open — bridge nature (deferred per Patrick, decide before building):**
**A** pure-markdown skill (model unused at runtime; defers D3 to v2) vs
**B** skill + thin Python bridge (an MCP tool runs the real model →
`AskUserQuestion` → validated `FormResponse`; the true stepping stone).
Agent recommends **B**. See salvage-assessment.md.

## D7 — Option B built; two MCP tools + skill-driven mapping; §4 needs a guard relaxation

**Date:** 2026-06-27 · **Status:** decided · built in PR #1128

The bridge-nature fork (open at the end of D6) is resolved as **B**, and
Option B is built ([PR #1128](https://github.com/Smart-AI-Memory/attune-ai/pull/1128)).
Shape of the build:

- **Two MCP tools, pure reuse of the bridge's three functions** — no new
  surface-specific translation to retest: `elicitation_render_form`
  (validate definition + batched payloads) and
  `elicitation_collect_response` (validate answers, R4). The bridge core
  (`attune.elicitation`, 26 tests, 100% line+branch) is the locked spine.
- **The surface mapping lives in the skill, not Python (D6).**
  `AskUserQuestion` is an agent tool, not a Python API, so the new
  `elicit` skill carries the mapping rules (type→`multiSelect`,
  recommendation-first, "Other" free-text escape, ≤4 batching, two-tier
  picker for >4 options). attune-hub routes to it.

**The dogfood (R5) caught a real conflict — the §4 enforcement, not just
the habit.** A live, **global** PreToolUse guard
(`~/.claude/hooks/ask_question_format_guard.py`) hard-blocks any
`AskUserQuestion` with >1 question. Consequences:

- **Multi-select itself (D2, priority-1) is unaffected** — `multiSelect:
  true` is one question and ships today.
- **§4 multi-*field* batching was blocked** until the guard was relaxed.
  Patrick approved §4 and the relaxation: the guard now permits a
  **deliberate** batched form — opt-in via `metadata.source` containing
  "form" (the `elicit` skill sets `"elicit-form"`), still capped at 4 —
  while the one-question default holds for everything else; multi-select
  questions are exempted from the recommendation-first requirement. The
  relaxed guard + the real batched round-trip were dogfooded green. (The
  guard is personal config, not in the repo.)

## D8 — v2 surface: MCP elicitation leads; show_widget is the escape hatch

**Date:** 2026-06-27 · **Status:** decided (Patrick ratified) · see
[v2-phase0-requirements.md](v2-phase0-requirements.md) +
[v2-phase0-findings.md](v2-phase0-findings.md)

The V2.0 surface-grounding spike (research + thin PoC) settles the v2
rendering surface and **partially overturns D4**.

- **D4's elicitation rejection is STALE.** The MCP spec 2025-11-25 adds
  multi-select to elicitation (`type:array` + `items.enum`,
  `minItems`/`maxItems`) with a **structured, keyed** return
  (`action` accept/decline/cancel + `content`). The disqualifier that
  sent v1 to `AskUserQuestion` (no multi-select) is gone.
- **PoC evidence (task v2.0-3).** S2: the artifact maps to a valid
  elicitation `requestedSchema` and the keyed `content` flows straight
  into `collect_form_response` with zero parsing (round-trip green). S1:
  a live `show_widget` form rendered the same artifact and posted answers
  back via the free-text `sendPrompt` — workable, but exactly the
  "round-trip via posted JSON" D4 named (confirmed for S1 only).

**Decision:**

- **Lead surface = S2 (MCP native elicitation).** Best return path
  (structured/keyed), native + portable (Claude Code/Desktop/web, with
  `capabilities.elicitation` negotiation), reuses the v1 validation seam
  (`collect_form_response`) behind one artifact→schema transform.
- **Escape hatch = S1 (`show_widget`).** For controls elicitation can't
  express (true slider, color, rich layout), accepting the free-text
  `sendPrompt` postback.
- **S3 (standalone web)** stays the **V2.3 / North-star** horizon (user-
  designed, data-bound), not a v2 build target.

D4 verdict: **(a) elicitation-lacks-multi-select OVERTURNED;
(b) widget-return-fragile CONFIRMED for S1 only, N/A for the chosen S2
lead.** V2.1 (rich controls on the artifact) and V2.2 (the elicitation
renderer + live round-trip) inherit this.

## D9 — V2.2 renderer shipped; live round-trip pending a server restart

**Date:** 2026-06-27 · **Status:** decided · see
[v2-2-requirements.md](v2-2-requirements.md)

V2.2 productionizes the elicitation renderer on the lead surface (D8).
Grounded against the installed MCP SDK (verify-first):
``ServerSession.elicit_form(message, requestedSchema, related_request_id)
-> ElicitResult{action, content}``, reachable from a tool handler via
``Server.request_context`` (`.session`, `.request_id`).

Shipped:

- **`form_to_elicitation_schema(form)`** (`attune.elicitation`) — the
  artifact → elicitation ``requestedSchema`` transform for all 7
  controls; 100% line+branch.
- **`elicitation_ask` MCP tool** — the full server-side round-trip: build
  the schema, ``await session.elicit_form(...)``, and on ``accept``
  validate the structured ``content`` through ``collect_form_response``
  (R4). ``decline``/``cancel`` return cleanly; a missing/incapable
  session returns ``action: "unsupported"``/``"error"`` so the caller
  falls back to ``elicitation_render_form`` (AskUserQuestion). Validated
  with a mocked session across every path.

**R5 caveat (as in V2.0):** the *true* live round-trip needs an
elicitation-capable client AND the MCP server running V2.2 code (the
session's server is started per-session; new tools appear only after a
restart). The mocked-session test proves the transform + emit + collect
path end to end; the live dogfood is deferred to the next session that
boots the updated server. This is the v2 build's renderer — V2.0–V2.2
(the three build phases) are now complete; V2.3 (designer/data-binding)
stays held.

## D10 — live R5 dogfood: native form rendering NOT supported by the CC client

**Date:** 2026-06-27 · **Status:** decided (Patrick observed the live run)

The deferred R5 receipt from D9 finally ran: a fresh session booted the
MCP server on V2.2 code, so `mcp__attune-ai__elicitation_ask` was live.
Two declarative forms were sent through it.

**Result — the lead surface (D8) does NOT render on Claude Code today.**
The client advertises an elicitation session (so the handler did *not*
short-circuit to `unsupported` — `session is not None`), `elicit_form`
was sent, and the client returned `action: "decline"` with **no dialog
shown** (Patrick confirmed nothing appeared on screen). So:

- Server-side mechanics are proven live: artifact → `requestedSchema`
  → `elicit_form` → structured `ElicitResult` → clean non-accept
  handling, no crash. The emit + decline path round-trips end to end.
- Native form **rendering** is unproven — this CC build auto-declines
  form elicitation instead of presenting it. D8's "MCP elicitation
  leads" bet is **not validated on this client**; the AskUserQuestion
  fallback (v1's choice) remains the only working surface here.
- **Design gap:** `elicitation_ask` only self-falls-back when
  `session is None` (→ `unsupported`). An unrendered auto-`decline`
  is indistinguishable from a real user "no", so the caller never
  falls back to `elicitation_render_form`. The lead surface silently
  no-ops as a decline. (server.py:810–831.)

**Bug found — rich controls unreachable through the MCP front door.**
A form with a `date`/`number` field is rejected at input validation:
`'date' is not one of ['text_input','single_select','multi_select',
'boolean']`. `elicitation_ask` reuses the v1 `field_schema`
(tool_schemas.py:389–409, shared with the AskUserQuestion bridge),
whose `type` enum was never widened — even though V2.1 added
number/date/textarea to the artifact, V2.2's
`form_to_elicitation_schema` handles all 7, and the tool's own
description advertises them. Fix is NOT a global enum widen (v1
`render_form`/`collect_response` intentionally support 4 — AskUser
Question has no native number/date); `elicitation_ask` needs its own
7-type field schema.

This closes the "registered ≠ working" gap for v2 honestly: the
plumbing works, the lead-surface premise does not hold on CC, and the
front door rejects the very controls V2.1 added.

## D11 — S1 (`show_widget`) built as the rich surface; D10 enum fix shipped with it

**Date:** 2026-06-27 · **Status:** decided (Patrick chose "build S1,
existing 7 first")

D10 showed native elicitation does not render on Claude Code, which
promotes S1 (`show_widget`) from "escape hatch" to the **working rich
surface**. Scope chosen: render the existing **7** controls; the new
`slider`/`color` types stay deferred (they'd touch the locked D3 model
— a clean follow-up).

Shipped:

- **`form_to_widget_html(form, message)`** (`attune.elicitation.widget`)
  — the pure `FormSchema → HTML` transform. Self-contained (scoped
  CDS-token styles, transparent bg, no `position:fixed`), one control
  per type (number spinner / date picker / multi-line textarea /
  multi-select checkboxes / Yes-No select). Injection-safe: all
  form text is `html.escape`d and the submit script reads the DOM by
  `data-*` attributes — no form data is interpolated into executable JS.
- **Postback shape (S1, per D4/D8):** on submit the widget calls the
  global `sendPrompt` with a sentinel-marked fenced JSON block
  (`__elicitation_response__`, `WIDGET_RESPONSE_MARKER`); number →
  number, multi-select → list, date → `YYYY-MM-DD`, boolean →
  `Yes`/`No`. The agent parses it and validates through the EXISTING
  `collect_form_response` (R4) — no new collection logic.
- **`elicitation_render_widget` MCP tool** — returns `{html, title,
  field_ids}`; agent passes `html` to `mcp__visualize__show_widget`.
- **`elicit` skill** — added the "Choosing a surface" widget bullet +
  a "Widget surface" round-trip section, and the D10 caveat (a CC
  `decline` you didn't see the user make = surface unavailable, fall
  back; don't read it as the user saying no).

**D10 finding #2 fixed as a prerequisite.** `elicitation_render_widget`
(and `elicitation_ask`) now use a **`rich_form_schema`** whose `type`
enum lists all 7 controls + `minimum`/`maximum`/`max_length`; v1
`render_form`/`collect_response` stay on the 4-type schema
(AskUserQuestion has no native number/date). Without this the rich
controls
were rejected at the MCP boundary for the widget tool too, so the fix
had to land here. Guarded by `test_tool_schemas` (v2 = 7, v1 = 4).

**Live S1 dogfood — DONE (2026-06-28).** The round-trip that was
deferred at write-time is now proven end to end against the released
9.1.0 server (the per-session-server constraint cleared once 9.1.0 was
on main). Receipt:

1. `elicitation_render_widget` on a 3-field form (`number` 1–5,
   `date`, `multi_select`) → `success: true`, valid HTML.
2. `show_widget` rendered all three rich controls (number spinner,
   native date picker, multi-select checkboxes).
3. Submit fired `sendPrompt` with the sentinel
   `__elicitation_response__` JSON block; it arrived intact.
4. `elicitation_collect_response` validated it → `success: true`,
   `response_id: resp-20260628-010916`.

Type fidelity across the JSON hop held: number came back as typed `1`
(not `"1"`), date as ISO `2026-06-29`, multi_select as a 3-element
array — all passed R4 required + option-membership validation. The
"registered ≠ working" gap for the S1 surface is closed.

## D12 — adoption gap: the enhanced form is consumed by ONE path, and most features are not fits

**Date:** 2026-06-27 · **Status:** finding (recorded at Patrick's
request) · grounded by grep, not assumed

The v1/v2 elicitation surface is built and validated standalone, but a
grep of `plugin/skills` + `plugin/commands` for consumers shows
**adoption = one path**: the `elicit` skill itself, reachable only via
the `attune-hub` routing table (`"scope this" → elicit`). **No feature
workflow has adopted it**, and the design's named first integration —
`/attune` discovery (design.md §5, G3, "for sign-off") — was never
wired. Classic "registered ≠ working" adoption gap.

But "wire it everywhere" is the wrong conclusion — the §4 batching rule
itself says stay single-question when only one dimension is unknown.
The features split:

- **Genuine fits (multi-dimension intake) — the real adoption targets:**
  - `/spec` — does the heaviest interactive scoping of any feature, all
    **raw one-at-a-time `AskUserQuestion`** (mode / plan-approval /
    between-stage gates). Its kickoff (goal + scope + focus) is
    *literally* the elicit worked example, yet unconverted. Highest
    payoff.
  - `/attune` discovery — goal + scope + concerns; design's named first
    target.
  - `/planning` — feature/tdd/architecture + scope (maybe).
- **Not fits (single-arg / path-scoped) — should stay one-question:**
  `/code-quality`, `/security-audit`, `/bug-predict`, `/smart-test`,
  `/release-prep` each take one `argument-hint` (a path/version). At
  most one genuine question; a multi-field form there is the
  "bureaucratic intake" the rule warns against.

**Takeaway:** the gap is ~2–3 genuinely multi-dimension flows (not 22),
and the highest-value one (`/spec`) is the design's own showcase still
running the old way. A real first-consumer integration — not another
surface — is the next move that would prove the form earns its keep.
Needs its own scoping (which flow, behind the §4 rule); not started.

## D13 — first-consumer adoption: S1 widget surface wired into the 3 D12-fit flows

**Date:** 2026-06-28 · **Status:** decided (Patrick chose "Follow D12:
attune + planning", after an initial "analysis skills" pick was
reconciled against D12)

D12 named the genuine multi-dimension fits (`/spec`, `/attune`
discovery, `/planning`) and explicitly ruled the path-scoped analysis
skills (`code-quality`/`security-audit`/`smart-test`/`bug-predict`/
`release-prep`) **out** — a multi-field form there is the "bureaucratic
intake" the §4 rule warns against. When the adoption work was scoped,
the first instinct was to add forms to the analysis skills; reading D12
overturned that. We wire the **S1 `show_widget` rich surface** (the
only one that renders on Claude Code — D10) into exactly the three D12
fits, no further:

- **`spec`** — kickoff (`outcome`/`scope` textareas + `concerns`
  multi-select) now **prefers** `elicitation_render_widget` →
  `show_widget`, falling back to the AskUserQuestion-portable mapping
  when the widget surface is unavailable (and per D10, an unseen
  `decline` = surface unavailable, not a user "no").
- **`attune-hub`** — the existing "2–4 open dimensions → one form" note
  now prefers the widget surface (textareas + multi-select) with the
  AskUserQuestion fallback.
- **`planning`** — the **Subject** phrasing branches on **Type**, so it
  is NOT a clean 3-field batch: ask **Type** first (or take it from the
  argument), then gather the independent **Subject** + **Scope** as one
  widget form. Faithful to §4; D12 flagged planning "(maybe)" for this
  reason.

Native MCP elicitation (`elicitation_ask`) stays a non-option until a
CC client renders it (D10). The analysis skills stay single-question.
Surface-only change (skill markdown) — the engine (D11) is unchanged.

## D14 — V3: the decision construct (communication grammar)

**Date:** 2026-06-29 · **Status:** decided (Patrick chose "fold") ·
see [v3-requirements.md](v3-requirements.md)

A session exploring "dynamic conversations to enhance agent-user
communication" produced a live decision form (recommendation +
rationale + ranked alternatives) Patrick flagged as a breakthrough.
Grounding it against this spec showed it is not greenfield — it is the
next member of THIS spec's declarative-form family. Folded in as
**V3**.

Reconciles three premises from the exploratory draft:

- schema home → already `FormSchema` / `attune.elicitation`; extend,
  do not invent.
- renderer → the S1 widget (D11), not MCP elicitation (D10).
- "second construct = scope form" → the scope/intake form already
  ships and is adopted (D13); the genuinely new construct is the
  **decision** (opening-shape) itself.

Design: a decision is a presentation-enriched `SINGLE_SELECT` — the
answer path (round-trip + `collect_form_response`) is unchanged; V3
adds a model field-set + a widget card renderer + the grammar doc.
The widget surface makes no Anthropic API call, so V3 is fully
buildable and dogfoodable without API credits.

## D15 — AC3 receipt: live MCP round-trip for the decision construct

**Date:** 2026-06-30 · **Status:** done (live receipt)

AC3 was blocked at the V3 handoff only because the running MCP server
had booted before #1174 merged, so its `elicitation_render_widget`
enum lacked `decision` (the D10/D11 "registered ≠ working until the
server reboots" pattern). A fresh session rebooted the server on
merged-main code and the live round-trip went through end to end:

1. **Enum confirmed** — live
   `mcp__attune-ai__elicitation_render_widget` schema now advertises 8
   types including `decision` (was 7).
2. **render_widget** — a real `decision` form (recommended option +
   rationale + per-option tradeoffs) returned `success: true` with the
   V3 card markup (`ae-card-rec`, `ae-rec-badge`, `ae-rationale`).
3. **show_widget** — rendered the card; user picked an option and
   submitted via the `__elicitation_response__` sentinel.
4. **collect_response** — `success: true`,
   `{construct_3: "pushback construct"}`, `response_id`
   `resp-20260630-010914` (R4 validation against the live tool).

The dogfood doubled as the parked construct-#3 product question
(below): Patrick chose the **pushback construct**. No Anthropic API
call on any step — the entire receipt cost zero credits.

## D16 — V4: the pushback construct (grammar member #3)

**Date:** 2026-06-30 · **Status:** built · see
[v4-requirements.md](v4-requirements.md)

Construct #3 is the **pushback** construct: agent-to-user, surfaces a
disagreement with the user's stated approach + a concrete alternative
and rationale. Two product choices Patrick made (2026-06-30, both via
the live decision construct — dogfooding the grammar to extend it):

- **#3 = pushback**, not a status/progress construct. Pushback reuses
  the V3 substrate almost verbatim and encodes the standing
  "pushback welcomed" working agreement.
- **A new `QuestionType.PUSHBACK`**, not composing `decision`. The
  value of pushback over decision is the *dissent framing* (the user's
  approach shown as the status quo, the alternative badged "I'd suggest
  instead", a "Why I'd push back" rationale). Composing `decision`
  would be a doc convention, not a visible construct —
  `communication-grammar.md` step 1 ("a new type is justified when
  rendering OR answer-meaning genuinely differ") is cleared on the
  rendering axis.
- **Scope = substrate + one consumer.** Mirrors V3's footprint (model
  + widget + round-trip + tests + dogfood) AND wires one real
  consumer — the `/spec` Stage 2 review gate — so the construct proves
  end-to-end value, the way `decision` got its consumer in #1176.

Design parallels V3 exactly: the answer is one selected option, so
`SINGLE_SELECT` validation and the round-trip are reused — V4 adds one
optional field (`user_position`), a widget branch, and the consumer
wiring. No Anthropic API call on any surface.

**Build note — reuse gap caught by the dogfood discipline:**
`_validate_answer` (`bridge.py`) listed only `SINGLE_SELECT`/`DECISION`
for option-membership, so a PUSHBACK answer initially skipped
validation. The unit test `test_collect_rejects_out_of_option` caught
it; fixed by adding `PUSHBACK` to that tuple. "Reuse the answer path"
needed one explicit line, not zero.

**AC3 receipt status — CLOSED 2026-06-30.** Proven on both surfaces
with **real human submits**:

- **`show_widget` / function level** (build session): real
  `form_to_widget_html` output rendered via `show_widget`, dissent
  framing intact, Patrick picked the alternative (a "switch"), the
  `__elicitation_response__` sentinel posted back, and
  `collect_form_response` validated it (`resp-20260630-013130`); it also
  rejects out-of-option picks.
- **Full MCP-tool path** (next session, after #1178 merged
  `1cd7707be` and the server rebooted on main): the live
  `mcp__attune-ai__elicitation_render_widget` schema enum now carries
  `"pushback"` (9 types) + `user_position`/`recommended`/`rationale`/
  `option_notes`. Rendered a real pushback form through that tool →
  `show_widget` → Patrick submitted → `elicitation_collect_response`
  validated it: `success: true`, `resp-20260630-015652`. This submit
  was an **overrule** (Patrick kept his own approach — "Build construct
  #4"), the complementary arm to the build session's "switch", so both
  pushback outcomes are now exercised end-to-end. The D10/D11 / D15
  "registered ≠ working until the server reboots" pattern held exactly.

## D17 — forms-by-default with on-demand keyboard mode (product direction)

**Date:** 2026-06-30 · **Status:** direction (not built) · **owner:**
patrick

Forward-looking call on how the grammar surfaces to different users.
Reached via a live **pushback** form (`resp-20260630-021445`) — Patrick
proposed a 30-day unlock, I pushed back on the timer, he **switched**
to the alternative.

- **Default = forms.** The elicitation forms (intake / decision /
  pushback) are the default surface — built for beginners and
  mouse-preferring users.
- **Keyboard-centric mode = on-demand opt-in from day one.** A more
  keyboard-driven interaction style is an opt-in setting available
  immediately. **No 30-day timer and no per-user tenure state** — the
  rejected arm. The timer added nothing once the mode is available on
  demand; it only delayed the power users who want it fastest.
- **Discovery = usage-triggered, not calendar.** Surface a one-time
  hint about keyboard mode after N form submissions, so people who'd
  benefit find it without gating access behind tenure.

Not built. "Keyboard mode" is a design direction, not a live feature;
the terse-reply vocab (`y` / `go` / `1`,
[feedback_response_shorthand]) is the closest thing shipping today.
Promote to its own spec when ready to build.

## D18 — V5: the progress construct (grammar member #4)

**Date:** 2026-06-30 · **Status:** built · see
[v5-requirements.md](v5-requirements.md)

Construct #4 is the **progress** construct: agent-to-user, reports a set
of items by status (`done` / `in_flight` / `blocked`) and surfaces the
blocked items as a single-select picker. It is the first member that is a
*report* rather than a fork. Three product choices Patrick made
(2026-06-30, all via the live decision construct — dogfooding the grammar
to extend it):

- **Build construct #4**, not stop the grammar. (The "Build construct #4"
  click in the D16 AC3 dogfood was a throwaway receipt, per the
  next-session starter; this is the real directive made via a fresh
  decision form.)
- **Answer path = report + blocked-item picker**, not a pure display or a
  bare acknowledge. This keeps the construct answer-validated: the
  blocked items become the `options` of a `SINGLE_SELECT`, so the answer
  is one selected blocker, validated by membership — the V3/V4 answer
  path reused untouched. A pure display would never run the validator
  (markdown-in-a-form, the weakest substrate fit). A consequence falls
  out cleanly: when **nothing is blocked**, `options` is empty and the
  construct degrades to a pure status display — so "pure display" is a
  sub-state of one construct, not a separate member.
- **First consumer = the `/spec` execute gate**, not session-start
  orientation or the workflow sweep. The execute loop already has the
  done/in_flight/blocked shape natively (completed tasks, the current
  task, tasks that fail a quality gate), and the blocked-item picker maps
  exactly onto "which blocked task to fix/retry". Tightest, most
  dogfoodable wiring — mirrors how V4 wired into the Stage 2 review gate.

A new `QuestionType.PROGRESS` is justified on the rendering axis
(`communication-grammar.md` step 1): the three-bucket status board with
static done/in_flight rows + a blocked radiogroup is genuinely new
rendering, even though the answer-meaning is a single-select. V5 adds one
optional field (`progress_items`), a widget branch, the enum
(`tool_schemas` 9→10), and the consumer wiring. No Anthropic API call on
any surface.

**Build note — invariant caught at design, not after.** Because
`options` carries only the *answerable* (blocked) subset while
`progress_items` carries *all* items, the two can disagree. The bridge
enforces `set(blocked labels) == set(options)` in `form_from_dict`, and a
unit test (`test_blocked_subset_must_equal_options`) guards it — the
picker can never offer a non-existent blocker or omit a real one.

**AC3 receipt status — MCP render + collect PROVEN LIVE on 9.3.0
(2026-06-30); human pixel-click still surface-gated.** Function-level
render was dogfooded at build time: real `form_to_widget_html` output
(8 tasks: 6 done, 1 in-flight, 1 blocked) via `show_widget` — three
buckets, "suggested next" badge, "Summary" callout intact; plus unit
coverage (85 tests) for `collect_form_response` + the empty-blocked
degrade. After v9.3.0 published and the MCP server reconnected on 9.3.0,
the **full MCP-tool path** was exercised — verified first (the D15/D16
"registered ≠ working until reboot" gate) that the live
`mcp__attune-ai__elicitation_render_widget` schema enum carries
`"progress"` (10 types) + `progress_items`. A real progress form
(4 done / 1 in_flight / 3 blocked) rendered through that tool →
`success: true` with the correct three-bucket HTML; the postback then
validated live through `mcp__attune-ai__elicitation_collect_response` →
`success: true`, `next_action` membership-checked,
**`resp-20260630-055649`**. Honest gap vs. V3/V4: those receipts include
a real **rendered-widget human click**; this session ran in a terminal
where `mcp__visualize__show_widget` was NOT connected, so the literal
pixel-render + mouse-click atom is still owed — it needs a widget-capable
surface (claude.ai/code or Cowork). Render-logic + validation are proven
end-to-end live on 9.3.0; only the human click on a rendered widget
remains.

## Open

- **Confirm CC elicitation support** — low priority (elicitation is
  rejected regardless for lacking multi-select), but worth nailing if
  the widget/enhancement phase is ever revisited.
- **Revisit the `socratic-ambiguity-calibration` "ask only when
  genuinely ambiguous" rule** — Patrick endorses it now but is open to
  changing it with more feedback. Future discussion, not a v1 change.
