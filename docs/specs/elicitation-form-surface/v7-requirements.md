# Elicitation Form Surface — V7 Requirements: form-template library

**Status:** draft (2026-07-16) — awaiting Patrick approval.
**Freeze:** design-only until 2026-07-28; no code before the freeze
lifts. V6 (MCP Apps adapter, `v6-requirements.md`) is queued for the
same window — see Sequencing below.
**Source:** Patrick's idea, discussed 2026-07-16 ("sculpt a form
once, cast per fork") — the sculptor clause applied to the grammar's
own artifacts.

## The idea — sculpt once, cast per fork

Every form today is hand-built per invocation: a skill or session
assembles a dict and calls `form_from_dict`. Recurring fork classes —
release-gate sign-off, session contract, triage matrix — get
re-sculpted from scratch each time, with drift between castings.

V7 adds a **template library**: a recurring form is persisted once as
a named JSON template, and later invocations load it with per-use
slot values. The value frame is **comparability**: reused forms make
answers comparable across sessions — a sign-off form asked from the
same template turns its responses into a time series, a dataset.

## What already exists — reuse, do not rebuild

- `form_from_dict` (`bridge.py:366`) — validates a plain-dict form
  definition and returns a `FormSchema`. The template loader is a
  thin wrapper over this; validation stays in the one seam.
- `FormSchema` / `FormQuestion` (`meta_workflows/models.py`) — plain
  dataclasses, already round-trippable through serializable dicts.
- `FormResponse` (`models.py`) — carries `template_id`, so responses
  already have the join key the comparability frame needs.
- The four constructs (intake / decision / pushback / progress) and
  their render paths — templates are instances of the existing
  grammar, not a new member.

## The gap — code-verified 2026-07-16

No form-template persistence exists anywhere in `src/attune`:
`grep -rn "form_from_template"` → zero hits; every `FormSchema` is
built ad hoc via `form_from_dict` or direct construction. There is no
store, no loader, no catalog.

## Requirements

- **R1 — template store.** A directory of JSON template files, one
  per recurring fork class (e.g. `release-gate-signoff.json`,
  `session-contract.json`, `triage-matrix.json`). Each file is
  exactly the dict shape `form_from_dict` already accepts, plus a
  `slots` declaration for per-use substitution points.
- **R2 — loader.** `form_from_template(name, slots)` (~10 lines):
  read the JSON, substitute slot values, delegate to `form_from_dict`.
  No new QuestionType, no validator changes — malformed templates
  fail through the existing `FormValidationError` path (R4 upheld).
- **R3 — slot substitution.** Slots are named placeholders in string
  fields (title, question text, options). Missing or extra slot
  values are definition errors, reported through the same
  every-problem-listed error style `form_from_dict` uses.
- **R4 — catalog surface.** The `elicit` skill documents the
  available templates (name, construct, purpose, slots) so a session
  reaches for a template before hand-building.
- **R5 — promote-on-repeat discipline.** A form earns templatehood on
  its SECOND recurrence — same rule as lessons. No speculative
  templates; the library ships with only templates whose fork class
  has already recurred (candidates at draft time: release-gate
  sign-off, session contract — confirm recurrence before seeding).

## Acceptance criteria — receipts, not registration

- **AC-1 — round-trip receipt.** A template loaded via
  `form_from_template`, rendered on a live surface, answered by a
  human, validated through `collect_form_response`. Receipt =
  response id (D15/D16/V5 pattern).
- **AC-2 — comparability receipt.** The same template asked in two
  distinct sessions, with the two `FormResponse` records joinable on
  `template_id` — the time-series claim demonstrated, not asserted.
- **AC-3 — validation parity.** A deliberately malformed template
  (bad type, duplicate id, missing slot) fails with the same
  every-problem-listed `FormValidationError` a hand-built dict gets.

## Out of scope

- New QuestionTypes, validator changes, or render changes — zero.
- Template versioning/migration — revisit when a template actually
  changes shape after collecting responses.
- Auto-promotion tooling (detecting the second recurrence
  mechanically) — the discipline is manual until the library proves
  itself.

## Sequencing vs V6 (same post-freeze window)

Recommend **V7 before V6**: V7 is pure-local plumbing (no API, no
host dependency, dogfoodable same-day) and its templates give V6's
MCP Apps round-trip receipts (AC-1/AC-2 there) realistic payloads to
render. V6's ChatGPT-host receipt has external dependencies (host
support, dev-mode access) that can slip without blocking V7 value.

## Tasks (for review)

1. Template store directory + 1-2 seed templates (recurrence
   confirmed per R5).
2. `form_from_template` loader + slot substitution + tests
   (including AC-3 malformed-template cases).
3. `elicit` skill catalog section (R4).
4. Dogfood: live round-trip for AC-1, second-session ask for AC-2.
