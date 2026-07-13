# Elicitation v3 — constructs gain handles and tense

**Status:** design draft (2026-07-13) — for Patrick's review; no
build during the release freeze (through 2026-07-27).
**Origin:** freeze-week design session (Patrick: "take widgets to
the next level", directions 1+2+3 combined).
**Owns:** the construct-response protocol and the grammar
extension. The output-surface application lives in
[analysis-workflow-output-widgets/design-v2-control-surfaces.md](../analysis-workflow-output-widgets/design-v2-control-surfaces.md).

---

## The generalization

Today's grammar members (decision, pushback, progress, report) are
utterances: they render once and the conversation moves past them.
v3 upgrades the construct to a **surface**: it holds state, carries
**handles** (actions that speak back into the conversation), and has
**tense** (final vs. live). The three "next level" directions are
the three axes of this one change:

| Direction | Axis |
|---|---|
| Round-trip widgets | handles on output constructs |
| Elicitation v2 forms | richer input constructs, same reply channel |
| Live widgets | tense (checkpoint re-render) |

## The construct-response envelope (load-bearing)

One reply shape for every handle on every construct:

```text
construct-response {board: security-audit, finding: high-1
path-traversal workflows/config.py:112, action: fix} — propose the
fix, do not commit
```

- **Prefix** `construct-response` — greppable, hook-matchable.
  **CORRECTED (2026-07-13, standards-landscape review):** the
  shipped widgets already postback via the
  `__elicitation_response__` sentinel (fenced JSON over
  `sendPrompt`, validated by `elicitation_collect_response`). The
  v3 envelope EXTENDS that existing channel — same sentinel family
  plus `action` + instance fields — rather than introducing a
  parallel prefix. One reply channel, one validator (R4). The
  braced-body example below is the human-readable rendering; the
  wire form is the sentinel JSON.
- **Braced body** — `construct`, instance id, `action`, optional
  payload. Compact key:value, not strict JSON: it must survive
  human editing in the composer (the user may modify the utterance
  before sending — that is a feature, not a parsing hazard).
- **Em-dash tail** — the human-readable intent, also the
  instruction the agent actually follows. The braced body is
  provenance and routing; the tail is the ask.

### Transport: sendPrompt, deliberately

`show_widget` handles call `sendPrompt(envelope)`. The reply lands
as a USER message in the transcript. Chosen over any hidden side
channel because:

1. **Auditability** — every widget action is readable in the
   transcript afterward; nothing moves invisibly.
2. **Safety** — envelope text is user-ROLE but must be treated as
   DATA: the receiving turn parses and validates, echoes intent,
   and destructive verbs (fix-and-commit, delete, publish) retain
   normal confirmation judgment. Constraint acknowledged: the
   PreToolUse hook layer cannot see conversation context (existing
   lesson — enforcement primitive sees only tool_name/tool_input),
   so envelope validation is IN-BAND agent discipline plus a
   UserPromptSubmit hook that can at least recognize the prefix
   and inject the parsing rule.
3. **Degradation for free** — a user on a non-widget surface can
   type the same sentence by hand; the envelope IS the API.

### Instance validation (added same-day — found by the FIRST live click)

A construct-response must resolve against a **live construct
instance** recorded at render time (id, construct type, item ids,
producing run). Rendering a construct registers the instance
(session-scoped registry — a scratch-dir JSON line is enough);
receiving an envelope looks the instance up FIRST:

- **Unknown instance** (demo card, stale board from a pruned
  session, hand-typed id) → polite refusal naming why, never
  fabricated work. The failure mode is real: the design-session
  demo's mock findings were clicked minutes after rendering, and a
  collector without validation would have "explained" a
  path-traversal that doesn't exist and proposed fixes for a
  properly-capped dependency.
- **Known instance, stale state** (workflow re-ran since render) →
  act on CURRENT state, note the drift in the reply.
- Validation failures are themselves telemetry (one event, reason
  code) — stale-click rate is a signal about widget lifetime.

### Degradation ladder

| Surface capability | Construct renders as | Reply arrives as |
|---|---|---|
| show_widget (desktop, Cowork) | interactive card + handles | sendPrompt envelope |
| AskUserQuestion only (CLI) | question + numbered options | option pick (mapped to same envelope by the agent) |
| plain text | numbered list | terse vocab (`1`, `go`) |

The construct definition is surface-independent; only the renderer
differs. This is v2 phase-0's surface fork, kept — v3 adds nothing
new here.

## Grammar extension: the fifth member

Per the communication-grammar rule ("don't extend ad-hoc — propose
deliberately"), v3 proposes ONE new member:

- **board** — a set of items, each carrying the same small verb set
  (explain / dismiss / act). Fires when a workflow's output is a
  findings-shaped collection. Distinct from `report` (prose,
  no handles) and from `decision` (one fork, one pick). The
  dismiss verb feeds the memory noise ledger — every dismissal is
  a labeled negative example the memory-as-insurance frame needs.

Existing members gain handles WITHOUT changing their identity:
decision options become buttons (already true on AskUserQuestion
surfaces); pushback's "overrule / switch" become handles; progress
gains pause / refocus / stop.

## Tense

A construct instance is `final` or `live`. Live = checkpoint
re-render: the producing workflow emits at checkpoints (section
scored, task done), and the surface re-renders the construct with
updated state. No streaming socket — re-render works on every
surface today; true streaming is a per-surface enhancement later.
The progress construct is the first live member; `board` becomes
live when a long sweep populates findings incrementally.

## Ratified design constraints (Patrick, 2026-07-13)

1. **Projector, not platform.** Any "factory" must follow the help
   single-source pattern: one construct definition, projected to N
   surfaces (show_widget HTML, AskUserQuestion fallback, MCP-native
   elicitation, agent template). It REPLACES hand-built widgets; it
   never becomes a new subsystem family. This is the only factory
   shape in scope (F4 discipline from the product-direction
   assessments).
2. **Adapters, not foundations.** Emerging agent standards (MCP
   elicitation, MCP Apps/UI, OpenAI Apps SDK, A2A, AG-UI, card
   schemas) are projection TARGETS the grammar can emit to — never
   structural dependencies. The grammar stays ours; standards get
   adapters, chosen per the standards-landscape research memo.

## Non-goals

- No savings/effectiveness claims about handles until dogfooded
  (D4 scar: real payloads, real clicks, real round-trips).
- No new MCP tools in v3 design — `elicitation_render_widget` and
  `elicitation_collect_response` are the existing seams; v3 changes
  what they carry, not the tool surface.
- No per-PR CI, no telemetry expansion beyond counting handle use
  (one event per envelope received, mirroring memory_events.jsonl).

## Sequencing

1. Stage 1 (output handles) validates the envelope on the simplest
   click — see the sibling design doc.
2. Stage 2 ships the batched multi-dimension form as a construct
   whose submit emits the same envelope.
3. Stage 3 adds tense to progress + board.

Build starts post-freeze (2026-07-28+); acceptance criteria live
with each stage in the sibling doc.
