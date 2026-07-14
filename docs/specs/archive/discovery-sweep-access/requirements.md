# Discovery-Sweep Access — Requirements

**Status:** killed (2026-07-14) — triage decision (matrix-2026-07-14): MCP tool + skill already exist; unclear residual scope
**Owner:** Patrick + agent
**Scope:** surface layer only — the engine already exists at
`src/attune/workflows/discovery_sweep/`.

---

## Problem

`discovery-sweep` is a fully-built, registered workflow with **zero
user-facing entry points**. An accessibility audit (2026-06-25) found it
is the only one of 22 registry workflows with no MCP tool, no skill, no
slash command, and no catalog listing. A Claude Code plugin user cannot
discover or trigger it; the sole path is the raw
`attune workflow run discovery-sweep` CLI invocation.

Every other workflow is reachable via at least one user-facing surface.
This spec closes that gap.

---

## What discovery-sweep does (context)

A deterministic triage meta-workflow. It fans out across seven audit
sources (`PatternScan` non-LLM + `bug-predict`, `security-audit`,
`dependency-check`, `perf-audit`, `doc-audit`, `test-audit`), dedups by
location, and routes findings — with LLM-free logic — into three buckets:

- `queue` — act on (high confidence, located, severity ≥ threshold)
- `questions` — needs human judgment (no location, low confidence,
  conflicting severity, or the source crashed)
- `rejected` — filtered noise (below threshold, duplicate)

It is budget-capped (`DEFAULT_BUDGET_USD = $10`) and fault-tolerant (a
crashing source becomes one `questions` entry, never a failed sweep).

---

## Use cases

1. **Pre-PR "what did I break"** — one call runs the full audit panel
   over changed code, returning a prioritized queue with noise stripped.
2. **Inherited / unfamiliar codebase triage** — first-pass landmine map
   across bugs, security, deps, perf, docs, and test gaps.
3. **Tech-debt backlog intake** — the three buckets are a grooming
   pipeline (queue→tickets, questions→review, rejected→documented noise).
4. **Noise-filtered aggregation** — dedup + severity + confidence
   routing extracts signal from six overlapping scanners.
5. **Broad pre-release scan** — wide quality sweep, complementary to the
   deterministic CLI-only `release-gate`.

(The scheduled-daemon / `event_sink` use case is a separate Phase-2 ops
integration and is explicitly **out of scope** here.)

---

## Functional requirements

- **FR-1** A `discovery_sweep` MCP tool exists and appears in
  `get_workflow_tools()`, so Claude can invoke the workflow directly.
- **FR-2** The tool accepts: `path` (string, **required**, scope to
  sweep), `budget_usd` (number, optional, default `$10.00`), `no_llm`
  (boolean, optional, fast non-LLM-only sweep).
- **FR-3** The handler validates `path` with `_validate_file_path(...,
  allowed_dir=self._workspace_root)` (same guard as every sibling tool).
- **FR-4** The handler forces `output_format="json"` so the response
  carries all three buckets as structured data (not rendered markdown).
- **FR-5** A `discovery-sweep` skill exists under `plugin/skills/` with a
  description whose auto-triggers are **disambiguated** from
  `security-audit`, `bug-predict`, `deep-review`, and
  `workflow-orchestration` (see NFR-2).
- **FR-6** The skill routes to the `discovery_sweep` MCP tool, not a raw
  CLI shell-out.

## Non-functional requirements

- **NFR-1** No change to the engine (`workflow.py`, `verification.py`,
  `sources/`). Surface-only — the spec adds adapters, not behavior.
- **NFR-2** Auto-trigger phrases must fire for "run all audits / full
  sweep / what should I fix / triage findings / audit everything" and
  must **not** shadow the single-purpose audit skills (the #1068
  disambiguation discipline).
- **NFR-3** All reference-validation invariants hold: the skill names
  only real MCP tools; the tool count test and any README MCP-tool-count
  claim are updated in lockstep (`doc-audit` checks the README claim).

---

## Acceptance criteria (Done when)

- [ ] `discovery_sweep` appears in `EmpathyMCPServer._build_dispatch_table()`
  and the live tool list (count 41→42 base, 46→47 with redis plugin).
- [ ] Invoking the tool on a path returns `{queue, questions, rejected}`
  structured buckets; a crashing source degrades to a `questions` entry.
- [ ] `plugin/skills/discovery-sweep/SKILL.md` exists, lints clean, and
  references only real tool names; `test_plugin_reference_validation`
  passes.
- [ ] Tool-count tests and README MCP-tool-count claim updated; full MCP
  test suite green.
- [ ] No edits under `workflows/discovery_sweep/` except, if needed, a
  one-line registry/exposure note.

---

## Out of scope

- The `event_sink` / ops-dashboard daemon path (separate Phase-2 spec
  `discovery-sweep-ops-integration`).
- A dedicated `attune discovery-sweep` CLI command (the generic
  `attune workflow run discovery-sweep` already works).
- Website `features.ts` / marketing surfaces.
