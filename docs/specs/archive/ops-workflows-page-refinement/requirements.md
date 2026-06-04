# Spec: Ops Dashboard Workflows Page Refinement

> The Workflows tab in attune-ops lets a user with 20+ registered
> workflows find the right one and run it without scrolling/scanning
> the whole table. Mirror of the Specs-page refinement pattern
> (PRs #533-#536, #539) for the next pain-point area.

**Status:** complete (2026-06-02; A1-A3c shipped in v7.3.0 + v7.3.1 — PRs #552, #557, #554, #555, #556)
**Created:** 2026-06-01
**Owner:** Patrick
**Related:**
- `docs/specs/ops-specs-page-refinement/` — pattern this spec
  mirrors. Same shape of pain points (volume, interpretation,
  actionability) and same artifact progression (Phase 1 →
  wireframe → implementation).

---

## Ratified scope (2026-06-01 conversation)

**Pain points addressed in v1:**
- **H1 — Volume + lack of grouping** (closes via lifecycle/grouping buckets + chips + search)
- **H4 — Similar-named pairs indistinguishable** (closes via grouping — pairs like `health-check`/`orchestrated-health-check` land in same bucket, making the relationship visible)

**Pain points deferred to v2 or separate work:**
- H2 (run-cost preview) — vetoed for v1 (no cost-estimate column)
- H3 (have-I-run-this) — wait for richer usage data
- H5 (bulletin strip discoverability) — separate small concern, not bundled

**Design choices ratified:**
- **Filter shape:** chip row above table (mirrors Specs page)
- **Search input:** yes
- **Cost-estimate column:** no
- **Lifecycle bucket type:** **by concern** — `review / test / docs / refactor / audit / meta / other`
  - `review`: code-review, deep-review, security-audit, bug-predict
  - `test`: test-gen, test-audit
  - `docs`: doc-gen, doc-audit, doc-orchestrator
  - `refactor`: simplify-code, refactor-plan
  - `audit`: discovery-sweep, perf-audit, dependency-check
  - `meta`: release-prep, secure-release, orchestrated-health-check, health-check
  - `other`: rag-code-gen, research-synthesis
- **URL params:** yes (`?bucket=…&q=…`), mirrors Specs A3c
- **Kebab action menu:** yes, 3 actions:
  1. View recent runs
  2. Copy run command (`attune workflow run <name>`)
  3. View docs/template (opens `.help/templates/<workflow>/concept.md`)

**Implementation pattern:** Specs-page parity — derive concern from a static
Python module (mirrors `spec_lifecycle.py` from PR #533), 4-5 small PRs
mirroring Specs A1 → A3c.

---

## Current state — what `/workflows` renders today

`GET /workflows` returns a single flat table with one row per
workflow. As of 2026-06-01, `list_workflows()` returns **20
registered workflows**:

```
code-review, discovery-sweep, doc-audit, doc-gen, doc-orchestrator,
bug-predict, security-audit, rag-code-gen, perf-audit, test-audit,
test-gen, refactor-plan, dependency-check, simplify-code,
secure-release, orchestrated-health-check, release-prep,
research-synthesis, deep-review, health-check
```

Columns (current):

| Column | What it shows |
|---|---|
| **Name** | Workflow slug as `<code>` |
| **Tier map** | Per-stage tier chips (Standard/Cheap/Premium) plus tooltip showing the Claude model class |
| **Description** | Free-text + a per-row recent-runs strip + a log pane (hidden until expanded) |
| **Scope** | Per-row scope picker (dropdown of features + custom path) — `n/a` for workflows without `PATH_ARG_REGISTRY` entry |
| **Action** | Single `Run` button (hidden in `--read-only` mode) |

Plus: above the table, a bulletin strip showing "Now running across
actors" (hidden when zero in-flight runs). The `discovery-sweep` row
gets special treatment — inline chips for `queue / questions /
rejected` counts that link to scope-keyed detail pages.

The page mixes **all 20 workflows in one flat list** with no
grouping, filtering, search, or sort.

---

## Pain-point hypotheses (TO BE RATIFIED)

These are my hypotheses based on (a) the Specs-page parallel, (b)
reading the current `workflows.html`, and (c) the existing CLAUDE.md
lessons about workflow-cost surprises and silent failures. Patrick
should ratify/veto/extend each before they become requirements.

### H1 — Volume + lack of grouping

**Hypothesis:** 20 workflows in a flat alphabetical list make it
hard to answer "which workflow do I want right now?" without
scanning every row.

**Evidence (weak):** Same pattern that motivated the Specs page
refinement at 45 specs. Workflows is at 20 today, but the list
is growing (new workflows shipped routinely in this codebase) and
each row carries more visual weight than a spec row (multiple chips,
description, scope picker, run button) — so the per-row cognitive
cost is higher than per-spec.

**Possible groupings** (need ratification):
- **By concern** — review (code-review, deep-review, security-audit,
  bug-predict), test (test-gen, test-audit), docs (doc-gen,
  doc-audit, doc-orchestrator), refactor (simplify-code,
  refactor-plan), audit (discovery-sweep, perf-audit,
  dependency-check), meta (release-prep, secure-release,
  orchestrated-health-check, health-check), other (rag-code-gen,
  research-synthesis).
- **By cost tier** — single-agent (cheap, ~$0.10-0.50/run),
  multi-subagent (expensive, ~$1-10/run) — per the existing
  CLAUDE.md lesson "Single-agent SDK workflows fit under $1.50.
  Multi-subagent need ≥$5 even on tiny inputs."
- **By last-used** — frequently-used at top, never-used at bottom
  (data exists in telemetry).

### H2 — Run-cost is invisible until after the fact

**Hypothesis:** The per-stage tier chips show Standard/Cheap/
Premium **per stage** but not "what will this entire run cost." A
user clicking Run on `security-audit` doesn't know that the
default-budget cap is $2 and the workflow needs ≥$5 to complete
(per CLAUDE.md lesson on multi-subagent budget caps). They find
out via a silent failure with $0.00 / 0.0s output (per the
existing SDK error fidelity work).

**Evidence (strong):** The SDK error fidelity spec (#526, #531)
explicitly ships the side-channel infrastructure to surface
budget-cap failures. But that's after-the-fact diagnostics. A
"this workflow typically costs $X" estimate BEFORE clicking Run
would prevent the failure entirely. Telemetry has the data.

### H3 — No visibility into "have I run this before"

**Hypothesis:** The recent-runs strip is per-workflow and hidden by
default. A user can't tell at-a-glance which workflows they've
exercised vs which are unfamiliar. Could lead to anchoring on a
small set of familiar workflows and never trying the others.

**Evidence (medium):** No data on actual usage patterns. Worth
asking Patrick if this matches his experience.

### H4 — `health-check` vs `orchestrated-health-check` are
indistinguishable from the list

**Hypothesis:** Two workflows with similar names but different
implementations sit adjacent in the list with no visual cue about
which is "newer / preferred." Same problem with potential
overlaps: `code-review` vs `deep-review`, `doc-gen` vs
`doc-orchestrator`, `test-gen` vs `test-audit`.

**Evidence (strong):** The list literally has these pairs.
Picking the wrong one wastes a run.

### H5 — The bulletin strip's "in-flight from other actors" is
hidden when zero — so users don't know it exists

**Hypothesis:** The bulletin strip is well-designed when populated
(shows other Claude sessions' active workflows) but is `hidden`
when empty. A user new to the dashboard may never realize the
multi-actor coordination affordance exists.

**Evidence (medium):** Defensible UX choice (don't add noise when
empty) but trades discoverability for cleanliness. Worth deciding
explicitly.

---

## Non-hypotheses (likely OUT of scope)

- **Scope picker UX** — already addressed in PRs #324/#344/#358's
  scope picker work; not revisiting unless Patrick flags new pain.
- **Run-cost telemetry collection** — already exists; this spec
  consumes it, doesn't extend it.
- **Workflow registration** — not a UX problem; not on this page.
- **Workflow-result viewing** — that's `/runs/<id>/view` — separate
  surface, separate concerns.

---

## Open design questions (for Patrick)

1. **Which hypotheses are real?** Rate H1–H5. Any I missed?

2. **Lifecycle/state buckets — do workflows have lifecycle?**
   The Specs page's 6-bucket lifecycle (Active / Approved /
   Complete / Paused / Stale / Draft) was load-bearing for that
   spec. Workflows don't have a comparable "lifecycle" in the
   same sense — they're all just registered or not. But there
   may be analogous useful buckets:
   - **Recently-used (last 7 days) / familiar (≥1 run lifetime) /
     unused (zero runs)?**
   - **By cost tier (cheap / standard / expensive)?**
   - **By concern (review / test / docs / refactor / audit /
     meta)?**
   - **Combination of the above?**
   - **None — just sort by last-used desc?**

3. **Filter widget shape** — chips above the table (matching
   Specs page), dropdown, segmented control, or none?

4. **Search** — does the page need a search input? Specs page
   v1 didn't add one (URL `?q=` only); Workflows is smaller (20
   vs 45) but workflow names are more cryptic to scan than spec
   slugs.

5. **Cost-estimate column** — should each row show a "typical
   cost" estimate derived from telemetry? Or only show after
   the user has run it themselves (so the estimate is
   self-calibrated)? Or not at all?

6. **Action menu** — Specs page added a kebab `⋯` with 3
   actions. Workflows already has a Run button. Does it need
   additional actions (view recent runs, view typical cost,
   open scope picker in dedicated UI, view source)?

7. **Scope for v1** — small focused PRs landing one slice at a
   time (like Specs page A1/A2/A3a/A3b/A3c). What's the v1
   slice — H1 only (grouping/filtering)? H1 + H2 (add cost
   estimate)? Something else?

---

## Acceptance criteria (sketch — will firm up after ratification)

Whatever the v1 scope ends up being, success looks like:

- **Sub-second page load** (no new heavy data fetches).
- **No regression in existing Workflows-tab features** — the
  scope picker, Run button, recent-runs strip, bulletin strip,
  discovery-sweep chips all continue to work.
- **Drift-guard tests** — any new derivation logic (lifecycle
  buckets, cost estimates) gets a pure unit-test layer testable
  in isolation (mirror `spec_lifecycle.py` pattern from PR
  #533).
- **URL state** — filter / sort / search state lives in URL
  params so links are shareable (mirror Specs page's `?bucket=…`
  pattern from PR #539).

---

## Next steps (post-conversation)

After Patrick ratifies the hypotheses + open questions:

1. Update this requirements.md with the ratified pain points
   and remove the open-questions section (move them to
   decisions.md as ratified or to non-goals).
2. Draft decisions.md with the ratified design choices.
3. Build a standalone HTML wireframe (mirror Specs page's
   `wireframe.html`) and review it together — expect the
   wireframe to surface gaps the conversation didn't (per the
   wireframes-surface-gaps lesson).
4. Update decisions.md with any gaps the wireframe surfaced.
5. Implementation in small focused PRs.
