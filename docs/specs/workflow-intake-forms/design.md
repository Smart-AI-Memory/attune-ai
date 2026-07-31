# Workflow Intake Forms — Design

**Status:** draft (2026-07-31) — authored on the approved
requirements; implementation authority still arrives per-phase via
chair gates.

## Layer map

```text
contracts        InputSchema on each workflow (validation.py) —
                 what a workflow takes; already validated at run
templates        FormTemplate: field slots + provider names —
                 how to ASK for those inputs
providers        named derivations (git-changed paths, test-shaped
                 files, package areas, taken slugs) — the options
generation       intake_form(workflow) -> FormSchema
surfaces         widget (claude.ai) · AskUserQuestion fallback ·
                 ops dashboard — all owned by elicitation-form-surface
theme            ONE tracked CSS source, projected into every
                 surface — the shared look (this spec's addition)
```

Everything above `generation` exists today; this spec adds the
template/provider layer and the theme, and completes the contracts
layer's coverage (requirements Phase 1).

## Contracts layer (Phase 1)

`InputSchema` (`attune/workflows/validation.py`: required keys +
key types, opt-in via `LLMWorkflowMixin.input_schema`) is the
single source. Design rules:

- Workflows declare WHAT they take, never how to ask —
  presentation metadata (labels, help text, provider hints) lives
  on the template layer, so the contracts stay UI-free and the
  ops runner / `workflow run` validation reuse them unchanged.
- The execution scope for the sweep is grep-derived at task time
  (`input_schema` absence across the live registry), not a list
  frozen in this document — the code is the contract.
- `PATH_ARG_REGISTRY` consumers migrate onto `input_schema`
  lookups where the change is mechanical; the registry is deleted
  only when its last consumer is gone.

## Template + provider layer (Phase 2, rule-of-three gated)

```python
@dataclass
class FormTemplate:
    workflow: str                 # registry name
    fields: list[FieldSlot]       # ordered

@dataclass
class FieldSlot:
    key: str                      # matches an InputSchema key
    text: str                     # question text
    provider: str | None = None   # candidate provider name
    control: str | None = None    # override; else derived from type
    help_text: str | None = None
    required: bool | None = None  # TIGHTEN-only override, see below
```

- **Slot overrides may TIGHTEN, never LOOSEN (codex lane,
  2026-07-31):** a slot can require a schema-optional field for the
  interactive flow, but a schema-REQUIRED field can never be
  rendered optional — the generator rejects such a template at
  build time, so the UI contract cannot diverge from the execution
  contract in the dangerous direction.
- Providers are plain callables in a module-level dict:
  `PROVIDERS: dict[str, Callable[[ProviderContext], list[str]]]`.
  `ProviderContext` carries `repo_root`, the invocation text, and
  the already-answered fields. No entry points, no plugins — a
  dict (H3-no-parallel-framework).
- Control derivation uses ONLY what `InputSchema` actually
  carries — the declared python type — plus the slot's explicit
  `control` override (codex lane, 2026-07-31: the schema has no
  `max_length` or enum metadata, so nothing may pretend to derive
  from them): `str` → `text_input` (a slot opts into `textarea`),
  `list` + provider → `multi_select`, `int`/`float` → `number`,
  `bool` → `boolean`. Richer derivation arrives only if
  `InputSchema` itself grows the metadata.
- A field whose value is already present in the invocation text
  or context is PREFILLED, rendered as inferred (the existing
  `inferred_from` path) — never re-asked blind.
- Proof obligation: the fix and spec intakes re-expressed as
  templates render byte-identical `FormSchema`s to the shipped
  hand modules, pinned by test, before any third consumer ships.

## Generation flow

```text
intake_form(workflow_name, invocation_text) ->
  1. registry lookup -> workflow_cls.input_schema  (fail: no form,
     fall back to free-text ask — never block)
  2. template lookup (in-tree dict; missing -> derive a minimal
     template from the schema alone)
  3. run providers (bounded; see latency)
  4. build FormSchema via form_from_dict  (validation unchanged)
  5. surface via select_form_surface      (unchanged)
```

## The shared look — form theme (chair requirement)

**Problem.** Every widget currently inlines its own ~2.4 KB style
block (measured 2026-07-31: 2,462 B of 6,542 B total), authored
inside `form_to_widget_html`. Styling drifts per generator, and a
family of intake forms should read as ONE surface.

**Design: single source, projected — never fetched.**

- `attune/elicitation/theme.py` exports `FORM_THEME_CSS`: design
  tokens as CSS custom properties plus the component classes
  (`.ae-field`, `.ae-label`, `.ae-input`, `.ae-submit`, …).
  Tokens default to the HOST's variables with literal fallbacks —
  `var(--surface-1, #f7f6f3)`, `var(--text-primary, #2c2c2a)` —
  so one stylesheet renders native on claude.ai widgets
  (light/dark follows the host automatically), in the ops
  dashboard, and standalone.
- **Widgets: inline injection is the design, not a compromise.**
  The widget sandbox's CSP forbids external stylesheet fetches,
  so "shared" cannot mean shared-by-URL there. It means
  shared-by-SOURCE: `form_to_widget_html` injects `FORM_THEME_CSS`
  once per widget, keeping the per-instance scoping wrapper
  (`#attune-elicit-form-<id>`) for isolation.
- **Ops dashboard: same constant, served once.** The dashboard
  serves the identical string as a static `/static/form-theme.css`
  (one cacheable fetch); a drift test asserts the served file is
  byte-equal to the constant — one source, two projections.

**Latency analysis (the chair's constraint).**

- Zero added round trips anywhere: widgets were already inline;
  the dashboard file is cached after first load.
- Byte budget: `FORM_THEME_CSS` ≤ 4 KB raw, enforced by a
  residency-style drift test (`test_form_theme_budget`) so the
  theme cannot quietly grow into a framework. At ≤4 KB the
  render-time cost is sub-millisecond against the ~100–145 ms
  derivation baseline — styling is not on the latency path, and
  the budget test keeps it that way.
- No external fonts, no icon fonts, no images: system font stack
  and host tokens only. (An @import or webfont would be the first
  real latency regression this section exists to forbid.)

## Latency mechanics (Phase 3, measurement-gated)

- Instrument `intake_form` end-to-end (derive/build/render marks)
  behind the existing telemetry surface — no new store.
- Cache: providers are declared either REPO-STATE-PURE (read
  only the tree/git — cacheable) or CONTEXT-DEPENDENT (read
  invocation text or earlier answers — never cached in v1; codex
  lane, 2026-07-31: a context-blind key would replay one
  invocation's candidates into an unrelated one). Pure providers
  key on `(repo_root, HEAD, sha256(sorted dirty set))` — the key
  IS the state, so invalidation is structural. In-process dict
  first; the existing memory backend second.
- The Redis Function (chair's stored procedure): `FCALL
  intake_form_digest` assembling cached candidate fragments
  server-side for surfaces already holding a connection (MCP, ops
  dashboard) — read-side only, hydrated from the tracked tree
  (principle 12), and Redis-absent falls back to inline
  derivation (principle 15). Ships only with a measured
  before/after showing a budget miss it closes.

## Receipts design

- Phase 1: registry coverage sweep test + a malformed-input CLI
  run showing named-field errors (behavioral).
- Phase 2: byte-identical re-expression pins for fix/spec intakes
  (behavioral); provider unit tests on real tmp trees (suite).
- Theme: budget drift test, widget/dashboard byte-equality drift
  test, and a rendered-form screenshot on both surfaces in the
  PR (evidence of the user-visible behavior, per the
  verification-receipts contract).
- Phase 3: the latency numbers re-measured from the instrument,
  never quoted from this document (metric).
