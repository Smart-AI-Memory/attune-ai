# Workflow Intake Forms — Decisions

**Status:** active (decision log; grows as the spec advances)

## D1 — Theme byte budget amended 4 KB → 6 KB (chair, 2026-07-31 ~21:20 ET, Task 3 execution)

Task 3's execution measurement: `FORM_THEME_CSS` — the full family
sheet WITH the design-mandated `var()` fallback literals — is
5,574 B raw, 5,192 B minified; the scope-prefix repetition is
~920 B, so even CSS-nesting restructuring lands ~4.3 K. The 4 KB
figure was authored before the fallbacks existed and measured a
per-widget subset, not the full concatenation.

Chair ruled (over the presented fork, lead recommendation
followed): amend the budget to 6 KB rather than cut real rules to
honor a stale number. Rationale preserved from the original
design: the latency claim (sub-millisecond against the ~100–145 ms
derivation baseline) holds identically at 6 KB, the anti-framework
ratchet remains the test itself plus the hard bans (no fonts, no
icon fonts, no images, no @import), and widgets continue shipping
per-form family subsets (~2.5–3 KB class). `test_form_theme_budget`
enforces 6,144 B; design.md amended in the same commit.

**Amendment (chair, 2026-08-30, landed 2026-08-31 with #2382):** raise
the cap from 12 KB to 16 KB — ratified for the project path-picker
family and re-confirmed the same day for attune-forms 0.11.1. The released expanded grammar theme
measures 14,926 B. The chair approved the cap raise after the
dependency compatibility receipt exposed the overage; the hard bans
and byte-budget drift guard remain unchanged, and another increase
requires another ruling.

## D2 — Phase 2a ruled and executed same night: the merge fallback, six refinements, gate override (chair, 2026-07-31 ~22:15 ET)

Roundtable `q-intake-forms-phase2-design-001` (transcript
machine-local; msgs 2–5 promoted). Convergence 3/3: shape
right-sized; cache-free v1; thin two-consumer staging; the
re-expression gate right in spirit. Split 2–1 on template-less
fallback (codex+antigravity: free-text until authored slots;
claude: demand-gated derivation with telemetry).

**Chair rulings:** (1) THE MERGE — free-text fallback in v1 plus
claude's demand-telemetry marker on every template-less ask;
derivation is a debug tool only. (2) All six refinements PROMOTED:
structural-equality gate with stubbed providers; same-PR deletion
of hand FORM-BUILDING; cache-free v1; list-without-provider
rejected at build time; prefill exact-match only; drill-down
re-entrancy design text before migration. (3) IMPLEMENT NOW —
the chair's third timing override of the evening, over the lead's
post-demo recommendation. Gate-override on record: the
rule-of-three had not fired (two consumers); the chair overrode
his own sequencing gate deliberately, and codex's warning stands
in the spec as the third consumer's test: fix and spec "may be
structurally similar enough to produce a misleadingly elegant
API."

**Executed same session:** `intake_template.py` + fix/spec
re-expression + provider registration + 12-test gate suite
(structural-equality goldens copied verbatim from the deleted
hand construction), 347 elicitation tests green, existing 20
behavioral pins untouched. The drill-down question dissolved on
inspection: `--list-dirs` is a skill-side loop between renders,
not an in-form dependency — recorded in design.md.

## D3 — Third consumer by chair fiat: 17 workflow templates registered (chair, 2026-08-01 morning)

The chair ordered the expansion directly ("create the shared
template for the standard analysis workflows and templates for the
rich form candidates don't create for Poor fits") after the
registry sweep showed the suitability tiers. This IS the third
consumer moment D2 deferred to — arrived by fiat rather than
demand telemetry, hours after the marker shipped.

**Registered:** ONE shared standard-analysis template
(path + depth ± budget) bound per-workflow across 13 workflows —
the sweep's prediction that the family is one form held, so it is
one factory, not 13 hand modules (exactly the copy-paste hazard
the shared shape implied); plus 4 individual rich templates:
deep-review (focus multi-select from the workflow's literal valid
set), discovery-sweep (source names derived LIVE from
default_sources(); the schema's `sources` field takes adapter
OBJECTS and is deliberately not asked — the `source` name filter
is), secure-release (changed-files provider), test-audit
(dual path pickers). **Deliberately absent:** the five
dict-context poor fits — they keep the free-text fallback + the
demand marker.

**Codex's D2 warning, answered early:** the API generalized to 17
consumers with zero shape changes — no new FieldSlot fields, no
generator edits; the only friction found was registration-by-
import (fixed in #1845, lazy loading). The bound-validation path
(tighten-only, list-needs-provider) now runs against 17 real
registry schemas on every suite run.

**Option provenance rule applied:** every static option value is
verified against the tree and pinned by test (depth vocabulary,
focus set, output formats); registry-derived options (sweep
sources, path candidates) come from providers so they cannot
drift. Live-fire receipt: discovery-sweep's generated form
rendered with real working-tree path candidates and all seven
adapter names.

## D4 — Substrate extracted to the standalone `attune-forms` package (chair, 2026-08-12, decision form)

The chair ruled via the decision construct (session
`dynamic-forms-library`): the elicitation substrate becomes a
**separate PyPI package in its own repo** —
`Smart-AI-Memory/attune-forms`, import name `attune_forms` — with
attune-ai as its first consumer; artifact tier "direct extraction
PR this session" (over a gated spec; the coupling surface was
measured thin: form dataclasses + `structlog` only).

**What moved:** the form models (out of `meta_workflows/models.py`),
`bridge`, `widget`, `theme`, `elicitation_schema`, `template_store`,
`reference_form`, `intake_template`, and `telemetry/form_events`.
**What stayed:** fix/spec intakes, the 17 workflow templates, MCP/CLI
wiring, and the display kernels (different substrate). Two host
seams replace the in-repo couplings: `WORKFLOW_SCHEMA_RESOLVER`
(registry lookup) and `TEMPLATE_LOADERS` (registration-by-import).

**Compatibility ruling:** legacy import paths are `sys.modules`
aliases bound to the same module objects (the `os.path` pattern) —
class identity and monkeypatching preserved, goldens untouched.
Receipts: attune-forms 358 tests green standalone + wheel packs the
template data; attune-ai full unit suite 20,625 green with the
dependency swapped in. Sequencing: the attune-ai PR merges only
after `attune-forms` 0.1.0 is live on PyPI.
