# Output widgets v2 — control surfaces (stages 1 and 3)

**Status:** design draft (2026-07-13) — for Patrick's review; build
post-freeze (2026-07-28+).
**Depends on:** the construct-response envelope defined in
[elicitation-form-surface/v3-construct-protocol.md](../elicitation-form-surface/v3-construct-protocol.md)
(that doc owns the protocol; this one applies it to the shipped
report panel and triage board).

---

## Stage 1 — handles on the existing findings surfaces

The universal report panel and the discovery-sweep triage board
render findings today; v2 gives each finding item three handles:

| Handle | Envelope action | What the agent does |
|---|---|---|
| explain | `action: explain` | deepen on that one finding — file read, context, severity rationale |
| dismiss | `action: dismiss` | record to the noise ledger (memory event with reason), strike the item on re-render |
| fix | `action: fix` | PROPOSE the change (diff in reply); committing stays a separate explicit go |

Per-tier mapping (the three-tier table from D4/the section-shape
map is unchanged — handles attach at render time):

- **Deterministic-structured** (discovery-sweep): items are real
  `Finding` objects — envelope ids are finding ids. Full handle
  set.
- **LLM-schema structured** (security-audit, code-review): items
  are severity cards with file:line — envelope id is
  `<severity>-<n> <slug> <file:line>` (self-describing; survives
  reordering).
- **Text-tier category bullets** (perf-audit, bug-predict, etc.):
  bullets lack file:line reliably — ship explain + dismiss only;
  no fix handle on unstructured items (a fix button on a vague
  bullet invites hallucinated patches).

### Implementation seams

- `findings_widget` / `report_to_panel_html` gain an
  `actions=True` render mode emitting the buttons; the envelope is
  built at render time from the section item. OFF by default —
  the `*_html` fields stay byte-compatible until the flag flips
  (hard rule (a): every new response field breaks exact-dict
  tests — pop/extend deliberately, keep legacy keys exact).
- Skill/docs edits follow hard rule (b): `sync_agents_skills.py`
  + commit the mirror.
- The dismiss path writes one telemetry event
  (`construct_response`, action, construct id) beside
  memory_events.jsonl — same fire-only discipline.

### Acceptance (stage 1)

- One REAL workflow run (security-audit, live payload) rendered
  with handles; explain, dismiss, and fix each clicked once; all
  three round-trips visible in the transcript and correctly
  parsed. (D4 scar: no hand-built demo payloads count.)
- Dismiss produces the ledger event AND the re-rendered board
  shows the item struck.
- Text-tier render shows NO fix handle.
- Exact-dict legacy tests still green with the flag off.

## Stage 3 — tense (checkpoint re-render)

Live constructs re-render at producer checkpoints:

- **Producer side:** long workflows (discovery-sweep, deep-review)
  already have per-section/per-audit boundaries; each boundary
  writes a checkpoint row (JSON line: construct id, state delta)
  to the session scratch dir.
- **Surface side:** the agent re-renders the construct from the
  latest checkpoint state at natural turn boundaries. No sockets,
  no polling loops in the widget itself — a live widget may show
  a "refresh ↗" handle that asks the agent to re-render (same
  envelope, `action: refresh`).
- **Progress construct** is the first live member: sections
  scored / total, current section, cost so far, plus pause and
  stop handles (stop = graceful: finish current section, render
  final board).

### Acceptance (stage 3)

- One real discovery-sweep run rendered live: at least two
  checkpoint re-renders visible, one refresh handle round-trip,
  and the final render identical to what a cold render of the
  finished result produces (tense must not fork the format).

## Sequencing and non-goals

Stage 1 → (v3 stage 2, sibling spec) → stage 3. Nothing here adds
MCP tools, changes workflow output schemas, or touches the three
render tiers' classification. The markdown-inline polish nit
(raw `**bold**` in text-tier bullets) rides stage 1 as a warm-up
change.
