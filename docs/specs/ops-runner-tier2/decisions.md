# Decisions — Ops Runner Tier 2

**Status:** draft
**Owner:** Patrick
**Opened:** 2026-05-11
**Predecessors:**
- PR #247 — Tier 1 rich rendering (workflow output gets parsed links, file chips, workflow pills, headers)
- PR #251 — Full-page run view (output survives browser refresh; full viewport instead of cramped table-row pane)

---

## Amendment (2026-05-11, post-#251)

The original Tier 2 spec assumed the **inline log pane** in the workflows table as the output surface for Phases 3–5. PR #251 replaced that with a dedicated `/runs/{run_id}/view` page. The spec's intent is unchanged — same phases, same outcomes — but the **rendering surface for Phases 3 (recent-runs history), 4 (pill-clicks chain runs), and 5 (recommendation cards) is now the run-view page, not the workflows-table row.**

Phase 2 (the scope picker — your idea) remains on the Workflows tab. That's the launcher; scope belongs with the Run button. Once a run starts, the user navigates to `/runs/{run_id}/view` and that's where chains, history, and recommendations render.

The recent-runs strip (Phase 3) appears on BOTH the workflows table (as a per-workflow history chip strip) AND the run-view page (as a "switch to another run for this workflow" navigator). Same data, two locations.

See `design.md` "Run-view page integration" and `tasks.md` Phases 3–5 for the updated surfaces.

---

## Problem

The current `/workflows` tab on the ops dashboard runs each workflow against the **whole project** with no path scoping. On a real codebase (attune-ai itself has 15k+ tests) this means:

- **Slow runs.** A `code-review` over `src/attune/` takes 5–10 minutes of LLM time when the user really wanted to check `src/attune/memory/`.
- **Diluted output.** Recommendations sprawl across unrelated areas. The "useful follow-along advice" Patrick called out (workflow X recommends running workflow Y next) gets lost in noise.
- **Dashboard-vs-terminal habit gap.** Developers iterating on one feature run `attune workflow run code-review --path src/foo` in the terminal because the dashboard can't scope. They never come back to the dashboard for that workflow.

PR #247 makes the output *prettier* — links, file chips, workflow-name pills, section headers — but the pills are inert. Clicking a recommended workflow doesn't do anything yet. The whole pattern was holding still until we knew where it should go.

This spec is where it should go.

---

## Decision

**Tier 2 turns the dashboard from a viewer into a workflow conductor.** Four headline capabilities, sequenced so each is independently shippable and reversible:

1. **Scope picker per workflow row** — a feature/path dropdown sourced from `.help/features.yaml`, with a free-form `--path` fallback. Runs become *fast and focused*.
2. **Workflow-name pills become buttons** — Tier 1's inert pills become "Run this workflow with the same scope" actions. Recommendations turn into clicks.
3. **Output persistence** — last N runs stored per workflow, browsable inline. Returning users see prior context.
4. **Structured recommendation channel** — workflows can emit JSON like `{"kind": "next-workflow", "name": "bug-predict", "args": {"path": "src/foo"}}` alongside their text stream; the UI renders these as proper action cards.

Headline UX:

```
[ src/attune/memory/  ▼ ]  [ Run ]
  ├─ All of project
  ├─ specs           docs/specs/
  ├─ ops             src/attune/ops/
  ├─ memory          src/attune/memory/   ← selected
  ├─ workflows       src/attune/workflows/
  └─ Custom path…    (text input)
```

Plus a runs-history strip per workflow:

```
Recent runs:  [success • 2m ago • ops]  [failed • 1h ago • all]  [success • yesterday • memory]
```

---

## Why now

- PR #247 just landed visual cues that signal "this should be clickable." Leaving the pills inert beyond a brief Tier-1 trial window erodes trust.
- `.help/features.yaml` already exists; the data is there.
- The ops-specs-features work (#236/#239/#240) proved out the same pattern (config-driven listing + per-row actions + read-only-aware mutation). The scaffolding is reusable.
- We just established the spec-first/tar-pit discipline in CLAUDE.md. Big UX work without a spec is exactly what that rule is for.

---

## Working hypotheses

### H1 — `.help/features.yaml` is the right scope source

The file already maps feature names to source globs (consumed by `attune-author`, `attune-help`, the doc-staleness check, etc.). Reusing it means:

- Zero new metadata for users who already maintain `.help/features.yaml`
- Graceful degradation: no `features.yaml` → only "All of project" + "Custom path…" are offered (still strictly better than today)
- Future-proof: any improvement to the feature list flows automatically into the picker

Risk: `features.yaml` is project-specific. Patrick maintains one for attune-ai but most ops users haven't. Mitigation: the dashboard's empty state explicitly tells them how to bootstrap one (`attune-author init`).

### H2 — Workflow `--path` support is unevenly implemented

Some workflows take `--path` (`code-review`, `bug-predict`, `simplify-code`, `perf-audit`, `test-gen`). Some don't (`release-prep`, `health-check`, `dependency-check`). The runner needs per-workflow knowledge of which arg is accepted.

Investigation task: enumerate which workflows support `--path` and which don't. Disable the picker on the latter; surface a tooltip explaining the workflow runs project-wide by design.

### H3 — Persistence belongs in the runner service, not a separate "Runs" tab

The current `RunnerService` keeps runs in memory (last 20). Persistence means writing run metadata + truncated log to disk under `~/.attune/ops/runs/<id>.json`. The "Runs" tab idea from earlier conversation gets folded into per-workflow row history (chips next to the Run button) — simpler navigation, no extra page.

### H4 — Structured recommendations should be opt-in per workflow, not retrofitted everywhere

A workflow opts in by emitting an SSE event with type `recommendation` carrying a small JSON payload. The UI renders these as action cards. Workflows that don't opt in fall back to the Tier 1 regex parser — no regression. This is much safer than rewriting every workflow's output format at once.

---

## Out of scope

- **Multi-project ops.** The dashboard scopes to one project at a time. Switching projects = restart `attune ops --project-root <other>`.
- **Editor integration for file-path chips.** Tier 2 keeps those as visual chips. A file-path "click to open in editor" capability requires a protocol-handler or attune-gui bridge — separate spec if/when needed.
- **Run cancellation.** The current runner doesn't support cancel; Tier 2 doesn't change that. If wanted, separate task.
- **Sharing runs across users.** Persistence is per-user under `~/.attune/ops/`. No multi-user/server-side storage.
- **Reorganizing the nav.** The Specs tab + Workflows tab + Telemetry tab structure stays. Tier 2 adds depth within Workflows, not breadth across tabs.

---

## Alternatives considered

### Alternative A — Free-form path input only (no `.help/features.yaml`)

Skip the feature-list integration; just give every Run button a `--path` text field. Simpler. But it loses the "menu of named scopes" UX that makes scoping discoverable. Users would have to know what paths exist in their project.

Verdict: rejected. The dropdown is the discoverability story. Free-form stays as the fallback for edge cases.

### Alternative B — Make Tier 1 pills clickable now, defer the scope picker

Smaller scope. But clicking a pill without a scope just re-runs the same project-wide pattern that's already slow. Scope is the lever that makes the action valuable. Doing pills first means users get a "click-to-do-the-slow-thing" experience and learn to ignore the pills.

Verdict: rejected. The scope picker is the prerequisite.

### Alternative C — A separate "Run with scope" wizard page

Dedicated multi-step page: pick workflow → pick scope → pick args → run. Maximally guided. But it shifts the dashboard from "two-click execute" to "five-click wizard" and the current users aren't asking for that — they're asking for *less* friction, not more.

Verdict: rejected. Inline picker per row.

---

## Resolution criteria

Tier 2 closes when:

1. Every workflow row has a scope picker (or a tooltip explaining why it doesn't)
2. Workflow-name pills in output trigger a follow-on run with the same scope
3. Per-workflow recent-runs history visible inline
4. At least one workflow demonstrates the structured-recommendation channel end-to-end
5. PR #247's drift-guard tests + new Tier 2 tests stay green on all 12 platform lanes (windows-memory-detection spec resolved by then)
6. Patrick has used the new dashboard for at least one real feature scope (e.g. `src/attune/memory/`) and confirmed the UX feels right
