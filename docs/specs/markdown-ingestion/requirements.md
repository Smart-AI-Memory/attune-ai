# Tolerant Markdown Ingestion — requirements

**Status:** draft (2026-08-14) — awaiting chair review of the task
ladder; intake rulings in [decisions.md](decisions.md) D1.
**Slug:** `markdown-ingestion` · **Repo:** attune-forms.
**Provenance:** round table `q-forms-grammar-expansion-001` — all
three seats independently flagged rendering-without-ingestion as the
S4 surface's missing half ("documentation, not a surface"); chair
ruled it "spec next" (receipt `resp-20260814-211025`). Intake ruled
via decision form (receipt `resp-20260814-213951`).

## Outcome

Replies on the markdown surface (Codex CLI, Antigravity, plain chat)
parse into validated answers without demanding perfect JSON. The S4
surface becomes a full round-trip: render (`form_to_markdown`, shipped
attune-forms #14) → user types a reply → parse → validate → re-ask
only what failed.

## Done when (intake, verbatim)

markdown_to_answers merged to attune-forms main with CI green:
shorthand + JSON-block parsing round-trips the full reference form,
malformed replies produce named per-field re-asks rendered back as
markdown (error echo loop), skill text teaches the free-text lane, and
one live receipt of a typed shorthand reply validating end-to-end is
recorded.

## Ruled constraints (D1 — re-open only by new ruling)

- **Hybrid normalization** (intake fork 1): the library ships a
  DETERMINISTIC parser for the shorthand grammar; free-text replies
  are the HOST AGENT's lane (skill-taught proposal). Validation truth
  is `collect_form_response` for both — the parser proposes raw
  answers, never a validated response.
- **Minimal shorthand grammar** (intake fork 2): `field_id: value`
  lines, `N: value` lines (1-based field position), dotted triage ids
  (`field.item: disposition`), and a filled JSON answer block. Option
  matching is EXACT — a miss is a named re-ask, never a guess.
  Case-insensitive/prefix matching is out of scope until real
  transcripts justify its ambiguity rules.
- **No silent guesses**: every unparseable line and every unknown id
  is a named problem in the result — the parser's honesty mirrors the
  validator's.

## Requirements

- **R1 — `markdown_to_answers(form, reply)`.** Pure function returning
  `(answers, problems)`. Accepts, in precedence order: (1) the last
  fenced JSON block in the reply (either the full sentinel payload or
  a bare answers object); (2) shorthand lines — `field_id: value`,
  `N: value` (1-based), `field_id.item_key: disposition` for triage.
  Type-aware value handling: exact option membership for select-likes,
  Yes/No for boolean, numeric parse for number, comma-separated exact
  options for multi_select. Lines that parse nowhere and ids that
  match no field become problems; nothing is guessed or dropped
  silently.
- **R2 — error echo loop.** `problems_to_markdown(form, problems)`
  renders the offending fields ONLY, as markdown (reusing the S4 field
  renderer), headed by the named problems — the re-ask a text-only
  host relays verbatim. Fields that validated are never re-asked
  (mirrors the widget discipline).
- **R3 — free-text lane (skill).** The skill teaches the host agent:
  try `markdown_to_answers` first; for free text, propose a mapping
  and validate it through `elicitation_collect_response`; when a value
  is uncertain, re-ask that field rather than guess. The
  `form_to_markdown` reply footer documents the shorthand so users
  discover it without reading docs.
- **R4 — validator untouched.** No changes to
  `collect_form_response` semantics; the parser and echo loop are
  pure additions.
- **R5 — drift guard.** A conformance test types a shorthand reply
  covering EVERY QuestionType (the reference form) and round-trips it
  to a validated `FormResponse`; the reference answers stay the single
  fixture.

## Out of scope

- Prefix/fuzzy option matching (named v2 lane, needs its own ruling).
- Any new MCP tool (the D3 four-tool mirror holds; parser is reachable
  through the library and, later, convergence work).
- Localization of the shorthand keywords.

## Acceptance criteria

- **AC-1** Shorthand round-trip: a typed reply using id lines, an N
  line, a dotted triage line, and a comma-separated multi-select
  parses and validates for the full reference form.
- **AC-2** JSON-block round-trip: the S4 skeleton, filled and pasted
  back, parses identically (payload or bare-answers form).
- **AC-3** Echo loop: a reply with one bad option and one unknown id
  yields problems naming both, and `problems_to_markdown` re-renders
  exactly the offending fields.
- **AC-4** Live receipt: one real typed shorthand reply validated
  end-to-end in a session, recorded in decisions.md.
- **AC-5** Full suite + lint green on CI.

## Tasks

1. **Parser core** (R1, AC-1, AC-2): `markdown_ingestion.py` [[?markdown-ingestion]]
   (not yet built — this spec's deliverable): JSON-block extraction +
   shorthand lines + type-aware values; exhaustive unit tests
   including the no-silent-guess cases.
2. **Error echo loop** (R2, AC-3): `problems_to_markdown` reusing the
   S4 field renderer; problem-to-field attribution; tests.
3. **Skill + footer + guards** (R3, R5): shorthand documented in the
   `form_to_markdown` reply footer; skill free-text lane; reference
   conformance test; CHANGELOG.
4. **Receipt + PR** (AC-4, AC-5): live typed-reply receipt, full
   suite, PR with the spec linked.
