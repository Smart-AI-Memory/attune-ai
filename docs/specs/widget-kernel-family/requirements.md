# Widget Kernel Family — requirements

**Status:** draft (2026-08-05) — awaiting chair review.
**Owner:** Patrick + agent (lead-authored — D11 different-model
review lane required before the chair reads this).
**Intake receipts:** session contract `resp-20260805-130002`
(outcome + done-when + effort cap), spec-intake form
`resp-20260805-131112` (four design forks), pushback form
`resp-20260805-131610` (infographic v1 scope — Patrick switched to
the agent's alternative). All three collected through the live
elicitation grammar, validated via `collect_form_response`.

## Outcome (from the session contract)

The chart, form, and infographic widget types work with low
latency. Charts already do (chartkit, PR #1941); this spec extends
the same pattern to the other two and makes the latency claim
measurable and honest.

## The ratified pattern (intake fork 1)

**Sealed kernel + declarative spec + RFC 7386 patch**, chartkit's
worked instance generalized into a family:

- The model authors only a small JSON spec (create) or a merge
  patch (update) — never renderer code.
- A sealed, size-budgeted JS kernel renders the spec; kernel
  source imports nothing outside itself, nothing imports kernel
  internals.
- One kernel per widget type: `chartkit` (shipped), `formkit`
  (R1), `infokit` (R2).

## The latency model (names the residual honestly)

Three delivery levels; this spec wins level 1 and explicitly does
NOT claim level 2:

| Level | Model authors | Model re-emits | Widget bytes in context |
|---|---|---|---|
| L0 streamed HTML (forms today) | full HTML | full HTML | twice/render |
| L1 kernel on `show_widget` (this spec) | spec/patch | full HTML | twice/render |
| L2 kernel via MCP Apps `ui://` (V6) | spec/patch | nothing | zero |

The L1 residual — the model mechanically re-emitting returned HTML
into `show_widget` (~2–3k output tokens per render) — is a property
of the surface, not the kernel. Its eliminator is the elicitation
spec's V6 MCP Apps adapter (`ui://attune/<construct>` pre-declared
resources, host-side fetch), which stays sequenced in THAT spec.
Mitigations meanwhile: prompt-cache reads on re-emitted HTML and
D21 collapse-on-submit.

## Requirements

- **R1 — formkit.** A sealed kernel that renders a `FormSchema`
  spec (the existing declarative dict — no new spec grammar) with
  the full construct family (intake controls, decision, pushback,
  progress, `list_style`) and the `sendPrompt` postback. The
  server-side seams are unchanged: `form_from_dict` validates the
  definition, `collect_form_response` validates answers. The
  existing `form_to_widget_html` string-builder becomes the
  fallback; the kernel path is the default widget renderer.

  **Identity + patch lifecycle (D2/F2 — normative by reference):**
  formkit implements the mechanism `chart_widget_tool` already
  ships, not a new design — a stable `form_id`
  (`[A-Za-z0-9_-]`, max 64) keys the canonical stored spec in
  session memory; updates are RFC 7386 merge patches against the
  stored spec; when persistence is unreachable the result SAYS so
  and requires a full spec (legible degradation, chartkit D5). The
  stored spec is canonical — the rendered widget is a projection,
  never the source of truth for a patch.
- **R2 — infokit, tiles preset only (pushback ruling).** One
  infographic kernel whose v1 ships a single preset: **stat tiles /
  metric cards** (counts, scores, deltas — live consumers today:
  `spec_progress`-class summaries, health/ops counts). The
  discovery-sweep **triage board is phase-gated**: it lands as this
  kernel's first preset amendment only after
  `discovery-sweep-rich-surface` ratifies its flow — no preset
  ships without a live consumer.
- **R3 — the seal generalized.** One boundary gate covers every
  kernel: source imports nothing outside its kernel dir, nothing in
  attune imports kernel internals, built artifact within its size
  budget. Generalize `scripts/check_chartkit_boundary.py` rather
  than copying it per kernel; chartkit's ≤20,480-byte budget is the
  default, per-kernel overrides recorded here when ruled.

  **formkit override (D2/F4 — ruled up front, not at gate time):**
  formkit's built budget is **≤ 40,960 bytes minified** (2× the
  default) — it carries the full construct family plus the postback
  script, and chartkit's kernel is already 11.3KB *unminified* for
  charts alone. chartkit and infokit stay at the 20,480 default.
  If formkit lands comfortably under 20,480 the override is
  retired in decisions.md rather than kept as slack.
- **R4 — latency receipts (intake fork 2).** The gate is
  **model-authored tokens per render and per update**, measured per
  kernel (chartkit's numbers are the baseline). Wall-clock time to
  first render is recorded as informational, never gating. The
  receipt must count what the model AUTHORS (spec/patch), stated
  separately from the L1 re-emission residual so the numbers cannot
  be read as an L2 claim.

  **Counting method (D2/F1 — the gate must be reproducible):**
  authored size is the byte length of the canonical compact JSON
  of the spec or patch (`json.dumps(x, separators=(",", ":"),
  sort_keys=True)`, UTF-8), with tokens *estimated* at bytes / 4.
  Deterministic and tokenizer-free; the task-4 harness measures it
  and records per-kernel baselines in decisions.md. Budgets
  (lead-proposed under the D2 adoption; standing unless the chair
  adjusts, re-ruled once the harness records real baselines):

  | Kernel | Render spec (bytes) | Update patch (bytes) |
  |---|---|---|
  | chartkit | ≤ 1,600 | ≤ 400 |
  | formkit | ≤ 4,096 | ≤ 512 |
  | infokit (tiles) | ≤ 1,024 | ≤ 256 |
- **R5 — ownership (intake fork 4).** This umbrella spec owns the
  pattern, the seal rules, and the latency budgets. The owning
  feature specs — chartkit's plan, `elicitation-form-surface`,
  `discovery-sweep-rich-surface` — get cross-links, not competing
  text. Widget-family changes that alter a feature's behavior are
  still ruled in the feature's own decisions.md.

## Out of scope

- The V6 MCP Apps adapter (owned + sequenced by
  `elicitation-form-surface`; this spec only names it as the L1
  residual's eliminator).
- The triage-board preset (phase-gated per R2 — not v1).
- New grammar constructs, validator changes, or chartkit behavior
  changes beyond the R3 boundary-script generalization.
- Form/infographic spec grammars beyond what exists (`FormSchema`
  is already the form spec; the tiles spec is new but minimal).

## Acceptance criteria — receipts, not registration

- **AC-1 — formkit round-trip.** A live form rendered by the
  kernel from a `FormSchema` spec, answered by a human, validated
  through `collect_form_response`; authored-token count recorded
  and within budget. (D15/D16 receipt pattern.)
- **AC-2 — formkit patch update.** An already-rendered form
  updated via a merge patch (e.g. option list swap) with the
  authored patch measured in tens of tokens, not a re-authored
  spec.
- **AC-3 — infokit tiles live.** The tiles preset rendered from a
  spec by a real consumer flow (not a demo fixture), with the same
  authored-token receipt. **The consumer is bound (D2/F3):** first
  consumer is the ops **Health tab metric cards** (live today, no
  new flow needed); `spec_progress`-class summaries are the named
  second. Before wiring either, the behavior change is ruled in the
  OWNING feature's decisions.md (R5) — the wiring PR links that
  ruling, and AC-3 is not satisfiable without it.
- **AC-4 — the seal holds in CI.** The generalized boundary gate
  passes for all kernels and FAILS on a seeded violation (import
  leak or size breach) — the gate is proven able to fail.

## Tasks (for review — XML prompts at execution time)

1. Generalize the boundary script + CI wiring (R3, AC-4).
2. formkit kernel: controls + constructs + postback; route the
   widget path through it; fallback retained (R1, AC-1, AC-2).
3. infokit kernel: tiles preset + minimal spec; first real
   consumer wired (R2, AC-3).
4. Latency receipt harness: authored-token measurement per kernel,
   recorded in this spec's decisions.md (R4).
