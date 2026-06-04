# Spec: Ops Dashboard Workflows Page Refinement — Decisions

**Status:** approved (2026-06-01)

> Pre-committed decisions per the existing CLAUDE.md lesson
> "Pre-committed decision matrices survive contact with data." Each
> decision was ratified in the 2026-06-01 in-session conversation
> that produced [requirements.md](requirements.md). Patrick stepped
> through them with `chips` / `y` / `no` / `By concern` / etc. and
> the kebab + v1 scope advice was ratified separately. Edits to
> this file after v1 ships require a follow-up PR with rationale.

---

## Decision matrix

| Decision | Choice | Rationale |
|---|---|---|
| **D1 — Bucket dimension** | **By concern** (review / test / docs / refactor / audit / meta / other) | Maps to "which workflow do I want?" — the load-bearing decision users face. Static derivation (mirror `spec_lifecycle.py`), no telemetry dependency, no usage data required. Alternatives rejected: by-cost-tier (less directly answer-shaped); by-last-used (telemetry-dependent, page-load cost); combination (visual weight, more state to manage). Bucket assignment is **canonical** per workflow — one workflow lives in exactly one bucket. |
| **D2 — Filter widget shape** | **Chip row above table, one chip per concern** | Mirrors the just-shipped Specs page pattern (PRs #533-#539). One-click toggle, inline counts double as population indicator, fits the existing dashboard visual language. Alternatives rejected: dropdown (hides state behind click), segmented control (overkill for 7 buckets), none (defeats the point). |
| **D3 — Search input** | **Yes — plain text, filters within active buckets** | At 20 workflows the volume case for search is weaker than for 45 specs, but workflow names are MORE cryptic (`secure-release` vs `release-prep`, `orchestrated-health-check` vs `health-check`) so keystroke-level disambiguation matters more. Search input lives in the chip toolbar (mirrors Specs A3a layout). Filter is substring-match against workflow `name` only — description matching adds noise (descriptions contain "code review" in 5+ workflows). |
| **D4 — Cost-estimate column** | **No** | Vetoed in conversation. Would require a telemetry-derived estimate (lookup of `~/.attune/telemetry/usage.jsonl` per workflow) which (a) adds page-load cost, (b) is empty for never-run workflows, and (c) gives a misleading number for workflows whose cost varies by depth/path. Phase 5+'s improved SDK error messages already address the silent-failure aspect of cost surprises (real cause now surfaces). Revisit in v2 if usage data accumulates and users want a budgeting affordance. |
| **D5 — Kebab action menu** | **3 actions: View recent runs / Copy run command / View docs** | Distinct from the Specs page kebab — Workflows is about run-management, not spec-metadata navigation. Each action is non-destructive and unique-to-row. Skipped: "View source" alone (better as sub-action of docs); "View typical cost" (telemetry-dependent per D4); "Edit scope" (already addressed by per-row scope picker). |
| **D6 — URL params for state** | **Yes — `?bucket=…&q=…`** | Mirrors the Specs A3c pattern (PR #539). Shareable links for "show me all `audit` workflows" or "find any workflow matching `release`". Default URL (no params) = all buckets active, no search, alphabetical-by-name sort. |
| **D7 — Sort dimension** | **Alphabetical-by-name** | Workflows have a stable namespace; alphabetical is the lookup-friendly default. v2 may add "by last-run-date" if usage data accumulates and users surface a real need. No tier-based sort (D1's concern grouping already clusters cost-similar workflows). |
| **D8 — Implementation pattern** | **4-5 small PRs mirroring Specs A1→A3c** | Pattern shipped clean for Specs page. Drift-guard tests on the bucket-derivation module + source-grep tests on the JS + TestClient tests on the route. |

---

## Concern bucket assignment

Authoritative mapping (codified in the implementation module
`src/attune/ops/workflow_concern.py`, mirroring `spec_lifecycle.py`):

| Concern | Workflows |
|---|---|
| `review` | `code-review`, `deep-review`, `security-audit`, `bug-predict` |
| `test` | `test-gen`, `test-audit` |
| `docs` | `doc-gen`, `doc-audit`, `doc-orchestrator` |
| `refactor` | `simplify-code`, `refactor-plan` |
| `audit` | `discovery-sweep`, `perf-audit`, `dependency-check` |
| `meta` | `release-prep`, `secure-release`, `orchestrated-health-check`, `health-check` |
| `other` | `rag-code-gen`, `research-synthesis` |

**Trade-offs ratified:**

- **`bug-predict` lives in `review`** (not `audit`) because its UX
  intent matches the review-class workflows: "tell me what's wrong
  with this code." `audit` is for codebase-wide health surveys.
- **`security-audit` lives in `review`** for the same reason —
  it's a focused review of one file/dir. The big-picture audit
  workflows live in `audit`.
- **`doc-orchestrator` lives in `docs`** even though it's a
  meta-workflow (composes other docs workflows). `meta` is
  reserved for release/health ops; `doc-orchestrator` is a
  domain-specific composer.
- **Naming consistency**: `audit` is BOTH a concern name AND a
  workflow-name suffix (`test-audit`, `doc-audit`, `perf-audit`).
  These are routed by purpose, not name pattern — `test-audit`
  is `test` concern, `doc-audit` is `docs`, `perf-audit` is
  `audit`. (Concern is about *what the user wants to do*, not
  the workflow's filename.)

---

## Filter widget behavioral details (D2)

- **Default chip state**: all 7 chips ACTIVE on first paint. Unlike
  the Specs page (where Complete defaults OFF because completed
  specs are visual noise), Workflows are all relevant by default —
  no concern is structurally "noise."
- **All-off state**: if all chips are toggled off, render
  "All concerns filtered out — re-enable at least one chip."
  (Mirrors Specs page empty-state pattern.)
- **Search**: filters the *already-bucket-filtered* set.
  0-result state: "No workflows in active concerns match
  '<query>'."
- **Persistence**: chip selections + search live in URL query
  params (`?bucket=review,audit&q=security`).

## Kebab menu behavioral details (D5)

- **Menu items (v1)**: `View recent runs`, `Copy run command`,
  `View docs`.
- **Close behavior**: click outside, Escape, or selecting an item
  closes the menu. One menu open at a time per page. (Mirrors
  Specs page kebab.)
- **`View recent runs` target**: scrolls to / opens the per-row
  recent-runs strip that's hidden by default. Existing
  `data-recent-runs="<name>"` element gets `hidden=false` toggle.
- **`Copy run command` action**: copies
  `attune workflow run <name>` to clipboard. If the workflow has
  a non-empty scope-picker selection, includes
  ` --path <selected-scope>`. Toast confirmation (mirrors
  Specs page Copy slug toast).
- **`View docs` target**: opens
  `/help/<workflow-name>` in a new tab. The dashboard's `/help`
  page (PR #482-#484) renders the `.help/templates/<workflow>/`
  content. Fallback to `/help` index if no per-workflow page
  exists yet.
- **Disabled state**: works in read-only mode (all 3 actions are
  non-mutating). No `allow_run` gating needed.
- **Keyboard**: arrow keys focus row, `M` (or `.`) opens menu on
  focused row, arrows in menu, Enter to fire. (Mirrors Specs
  page keyboard pattern.)

---

## Out of scope (parking lot)

- **Cost-estimate column** — D4 vetoed for v1. v2 trigger
  conditions: users surface a real budgeting pain AND telemetry
  accumulates enough per-workflow runs that the estimate is
  meaningful (≥10 runs per workflow).
- **`by last-used` sort** — D7 deferred. v2 trigger: D1 grouping
  proves insufficient AND users ask for recency-based prioritization.
- **`Edit scope` row action** — already addressed by per-row scope
  picker. No kebab duplication.
- **Per-row cost preview tooltip** — same blocker as D4.
- **Multi-select / bulk-run** — explicit non-goal. Each workflow
  run is a deliberate decision.
- **Custom concern grouping per-user** — v2 if requested. v1 is the
  authoritative mapping above.

---

## Carryover

- **2026-06-01** — All 8 decisions ratified in conversation. Patrick
  approved the kebab actions (View recent runs / Copy run command
  / View docs) and the v1 scope (H1+H4 closure via chips + search
  + bucket grouping + kebab) as my recommendation; the rest he
  ratified directly with `y` / `chips` / `By concern` shorthand
  per [feedback_response_shorthand](../../../../.claude/memory/feedback_response_shorthand.md).
- **Spec progresses to Phase 3 (wireframe)** for visual review.
  Per the existing CLAUDE.md "wireframes surface design gaps"
  lesson, expect at least one decision to need revision when the
  wireframe lands. Capture revisions here, not in requirements.md.
