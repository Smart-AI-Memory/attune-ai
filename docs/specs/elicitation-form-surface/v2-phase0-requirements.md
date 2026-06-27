# Elicitation v2 — Phase 0 (V2.0): ground the surface fork

Requirements for the v2 surface-grounding spike. v1 (Option B) shipped
the declarative artifact + the `AskUserQuestion` bridge
([requirements.md](requirements.md), [design.md](design.md),
[decisions.md](decisions.md) D1–D7). v2 renders the **same** artifact on
a rich interactive surface. This phase decides **which** surface and
**proves the return path** before any renderer is built.

## Context

- The form artifact is declarative and surface-agnostic (D3/R6) — v2
  reuses it unchanged, along with `form_from_dict` and
  `collect_form_response` (the R4 validation seam).
- v1 deliberately drove the artifact through `AskUserQuestion` because
  it natively supports multi-select (D4); the widget surface was
  deferred because its return path looked fragile (D4 — "client-
  dependent, round-tripping via posted JSON").
- That deferral predates the `show_widget`/Cowork `sendPrompt(text)`
  postback, so the "fragile return path" premise may be stale. We
  verify, not assert (the v1 Phase 0 discipline — D1).

## Problem

Before committing the v2 renderer (V2.2), we do not actually know
(a) which surface can render the full control palette (multi-select +
the V2.1 rich controls), and (b) whether any of them offers a **clean,
validated return path** from rendered form to `collect_form_response`.
D4's return-path worry is the crux and is currently unverified.

## Goals

- **G1** Evaluate three candidate surfaces against a fixed rubric
  (below), grounded in real docs/SDK/behaviour — not memory.
- **G2** Empirically prove a single **render → submit → validated
  response** round-trip on the leading surface (a thin PoC), so the
  return-path risk is retired with evidence.
- **G3** Record the surface decision (**D8**) and re-validate (confirm
  or overturn) D4's return-path premise.

## Surfaces in scope (Patrick, 2026-06-27)

- **S1 — `show_widget` / Cowork preview pane.** Renders HTML inline;
  has a `sendPrompt(text)` postback to chat. Leading candidate.
- **S2 — MCP native elicitation.** Re-check whether multi-select
  support changed since v1 rejected it.
- **S3 — Standalone web app (Florence-style).** A separate web surface
  like `ai-nurse-florence`; heaviest, closest to the North-star horizon.

Excluded: the `attune-gui` FastAPI sidecar (Patrick deprioritized it
for this evaluation).

## Evaluation rubric (criteria each surface is scored on)

- **C1 Control coverage** — can it render multi-select **and** the V2.1
  rich controls (slider, number, date, textarea, toggle)?
- **C2 Return path** — is there a clean path from a submitted form to a
  `{field_id: value}` map that `collect_form_response` validates? (the
  crux — the thing D4 worried about).
- **C3 Portability** — client-independent? works in Claude Code /
  Cowork without bespoke setup?
- **C4 Reuse** — plugs into the existing artifact +
  `collect_form_response` with no new infrastructure?
- **C5 North-star fit** — keeps the `options_source` seam reachable
  (V2.3 horizon) without building it.

## End state (acceptance)

- A **findings doc** scoring S1–S3 on C1–C5, each claim backed by a
  verification (doc link, SDK introspection, or observed behaviour).
- A **thin PoC** on the leading surface: renders a real declarative
  form (via `form_from_dict`) and returns answers that pass
  `collect_form_response` — a genuine round-trip (R5), not a mock.
- **D8 recorded** in `decisions.md`: chosen surface + rationale, and an
  explicit confirm/overturn verdict on D4's return-path premise.

## Out of scope

- V2.1 rich-control **implementation** (this phase only checks each
  surface *can* host them; building them is V2.1).
- V2.2 full renderer.
- V2.3 designer / data-bound options (HELD per the 2026-06-27 scope
  decision — a documented horizon + the `options_source` seam only; any
  designer/data-binding needs its own spec with a named consumer).

## Tasks

<task id="v2.0-1" name="surface-inventory">
  <objective>
    Score S1–S3 against the C1–C5 rubric, grounding every claim in real
    docs/SDK/behaviour (verify-first — no assertions from memory).
  </objective>
  <context>
    <surfaces>S1 show_widget/Cowork (sendPrompt postback), S2 MCP
    elicitation, S3 standalone web (Florence-style).</surfaces>
    <rubric>C1 control coverage, C2 return path, C3 portability,
    C4 reuse, C5 north-star fit.</rubric>
  </context>
  <files-to-create>
    <file path="docs/specs/elicitation-form-surface/v2-phase0-findings.md">
      A surface×criteria table; each cell cites its evidence.
    </file>
  </files-to-create>
  <validation>
    <check>Every C-score links a doc, an introspection, or an observed
    behaviour — not a memory claim.</check>
    <check>C2 (return path) is answered concretely for each surface.</check>
  </validation>
  <risks>
    <risk severity="medium">Confabulating SDK/surface capabilities from
    memory — the exact failure D1 guards against. Introspect/read first.</risk>
  </risks>
</task>

<task id="v2.0-2" name="revalidate-d4-return-path">
  <objective>
    Resolve D4's premise specifically: can the leading surface's postback
    (e.g. show_widget `sendPrompt`) carry a structured form submission
    back as a clean {field_id: value} map?
  </objective>
  <validation>
    <check>A concrete yes/no with evidence on whether the postback
    delivers structured answers (not just free text).</check>
  </validation>
  <risks>
    <risk severity="high">If NO clean return path exists on any surface,
    V2.2 is blocked — surface that finding loudly rather than papering
    over it.</risk>
  </risks>
</task>

<task id="v2.0-3" name="thin-postback-poc">
  <objective>
    On the leading surface, render a real declarative form and round-trip
    its answers through collect_form_response — a genuine R5 receipt that
    the return path works end to end.
  </objective>
  <context>
    <reuse>form_from_dict + collect_form_response (attune.elicitation) —
    no new validation logic.</reuse>
  </context>
  <validation>
    <check>A real (non-mocked) render → submit → validated-response
    round-trip is demonstrated.</check>
    <check>Malformed answers are rejected by collect_form_response (R4),
    not silently accepted.</check>
  </validation>
  <risks>
    <risk severity="medium">Scope creep into V2.2 — keep the PoC thin
    (one form, prove the path), do not build the general renderer.</risk>
  </risks>
</task>

<task id="v2.0-4" name="record-d8-decision">
  <objective>
    Record D8 in decisions.md: the chosen surface + rationale, and an
    explicit confirm/overturn verdict on D4's return-path premise. Note
    what V2.1/V2.2 inherit.
  </objective>
  <files-to-modify>
    <file path="docs/specs/elicitation-form-surface/decisions.md">
      <change location="append after D7">Add the D8 decision block.</change>
    </file>
  </files-to-modify>
  <validation>
    <check>D8 names the surface, cites the PoC evidence, and states
    whether D4 is confirmed or overturned.</check>
  </validation>
</task>
