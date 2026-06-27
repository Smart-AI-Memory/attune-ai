# Elicitation Form Surface — Salvage Assessment

A bounded "does it exist / does it work" pass (per
`.claude/rules/attune/removing-dead-code.md`) before building v1.
Outcome: **most of v1 already exists as a proven, surface-agnostic form
model; only the live AskUserQuestion wiring is missing.** Feeds
[decisions.md](decisions.md) D6.

## What exists in-repo

`src/attune/meta_workflows/` + `src/attune/wizards/`:

- **`models.py`** — `FormSchema`, `FormQuestion`, `QuestionType`
  (`TEXT_INPUT` / `SINGLE_SELECT` / `MULTI_SELECT` / boolean→Yes-No),
  `FormResponse`, plus `to_ask_user_format()`, `get_question_batches(4)`,
  and validation (required + multi-select membership).
- **`form_engine.py`** — `SocraticFormEngine.ask_questions(schema, …)`:
  batch ≤4 → `to_ask_user_format` → `_ask_batch` via an
  `ask_user_callback` (or defaults).
- **`wizards/base.py`** + builtin wizards (debug/security/refactor/
  release_prep) consume `FormQuestion`/`FormSchema`.

## Verdict — reuse / fix / discard

**REUSE (high value, proven):** the form **data model** in `models.py`
— `FormSchema`/`FormQuestion`/`QuestionType` (incl. `MULTI_SELECT`),
`FormResponse`, `to_ask_user_format()`, `get_question_batches(4)`,
validation. This *is* the declarative artifact (D3) and the renderer
mapping (D5 §2) the design called for — already multi-select-capable,
already ≤4-batching, already validated. v1 builds on it; do **not**
duplicate it.

**FIX — the genuine gap: the live wiring is absent.** The
`ask_user_callback` interactive path has **no live caller** — only a
docstring placeholder (`wizards/__init__.py:16` `my_callback`) and test
mocks. The `/wizard` check confirmed it: **no `plugin/skills/wizard/`,
no `plugin/commands/wizard.md`, no CLI handler** wiring a real callback
(`cli_minimal.py:682` `/wizard run` is help text only). Expected:
`AskUserQuestion` is an **agent tool**, not a Python-callable API, so a
Python "engine + callback" cannot reach the user. Today's live
questioning is **markdown-driven** (e.g. `attune-hub`/`/attune` calls
`AskUserQuestion` from the skill), not engine-driven. v1's real new
work is the bridge from the model to the live tool.

**DISCARD / irrelevant:** the wizard-run + agent-team orchestration
already removed (#1093); the XML task-decomposition (repaired #1097) is
a separate concern from form collection.

## Florence — the v2 precedent (external)

`Deep-Study-AI/ai-nurse-florence-v3.1` (Patrick's separately-built
healthcare app; the in-repo form model was built to support it,
**before** AskUserQuestion — `form_engine.py` header: "v4.3.0 — Real
AskUserQuestion integration", a later adapter). It contains ~20 working
clinical-form wizards (`src/routers/wizards/`: SBAR, SOAP, nursing
assessment, discharge summary, care plan, medication reconciliation,
…). Pattern: server-driven **multi-step forms** — per-step field
definitions, session state, progress %, validation — rendered as **web
forms** by the frontend.

Significance:

- **D3 is proven, not hypothetical.** The same kind of declarative form
  model already drove a *non-AskUserQuestion* surface (web) in
  production. The artifact is genuinely surface-agnostic by birth.
- **Florence's web rendering is the v2 target.** The rich HTML palette
  Patrick misses is not new to invent — the same model drove it once.
  v2 = bring that renderer back; v1 = drive the same model through
  `AskUserQuestion`.

## v1 implication + the open fork

v1 shrinks to **wiring the existing model to the live tool** for the
`/attune` discovery flow (D5 §5). The model + validation carry
multi-select for free; v2's richer types already exist in
`QuestionType`'s space.

**Open — bridge nature (decide before building):**

- **A — pure-markdown skill.** Agent assembles compound
  `AskUserQuestion` calls from skill guidance; the Python model is
  unused at runtime. Fast; defers all D3 reuse to v2; model stays
  unproven.
- **B — skill + thin Python bridge.** A small MCP tool drives the real
  `FormSchema` (`to_ask_user_format` + validation) →
  `AskUserQuestion` → validated `FormResponse`. Runs the salvaged model
  in v1; v2 swaps only the render adapter. More work; the true stepping
  stone.

Agent recommends **B** (aligns with v1-as-stepping-stone + makes D3
load-bearing now); decision deferred per Patrick 2026-06-27.
