# Library Health Report — 2026-07-14

Deterministic signals measured live this session (git, `gh`, Codecov
API, pip-audit, radon, repo gate scripts) plus a discovery-sweep
pass. Interactive version:
[claude.ai artifact](https://claude.ai/code/artifact/afc2b043-5f96-40c6-86f0-5c3f3a2f57f2).
Repo state: v10.4.1, main at the FG1 Phase 1 merge (#1370).

## Scoreboard

| Signal | Value | Read |
|--------|-------|------|
| Coverage (Codecov, main) | 94.1% | good |
| Main CI (today's runs) | all green | good |
| Known dependency vulns (pip-audit) | 0 | good |
| Avg cyclomatic complexity (radon, 5,155 blocks) | A (4.00) | good |
| D-or-worse blocks | 30 (incl. 3 F-grade) — CORRECTED at refresh; the first measurement was a truncated listing | watch |
| Open issues / open PRs | 0 / 2 | good |
| Source | 170k LOC · 654 files | — |
| Tests | 330k LOC · 993 files · 2,061 test fns | 1.94:1 ratio |
| TODO/FIXME/XXX in src | 1 real (27 grep hits are scanner-regex/prompt-text/scaffold data — triaged in #1375) | good |
| Bare `except:` in src | 0 | good |
| Real dynamic-code (eval/exec) uses | 0 (16 string-literal prompt examples) | good |

## Docs & single-source gates

| Gate | Result |
|------|--------|
| doc-import audit | clean (1 documented migration skip) |
| docs wiring audit | clean |
| help completeness | 27 features × 11 kinds, no orphans |
| projection drift (new, #1372) | 0 findings |
| spec corpus | 22 active dirs, 106 archived; audit #49: 97 scanned / 1 drifted (by design) |

## Hotspots (churn × size × complexity)

| File | LOC | Changes/90d | Signal |
|------|-----|-------------|--------|
| `ops/data.py` | 1,583 | 29 | 2 of 3 D-grade fns (`spend_alarm` D23, `read_telemetry_summary` D22) |
| `workflows/agent_sdk_adapter.py` | 1,748 | 19 | largest file in src |
| `ops/routes/dashboard.py` | — | 34 | highest-churn Python file |
| `mcp/server.py` | 1,446 | 23 | size + churn |
| `telemetry/feedback_loop.py` | — | — | `recommend_tier` D23 |
| `elicitation/bridge.py` / `widget.py` | — | — | `form_from_dict` F87, `_control_html` F84 — the true worst blocks, surfaced at refresh |
| `project_index/dependency_analysis.py` | — | — | `_build_summary` F48 |

The `ops/` subsystem is the concentration: top churn, top size, and
two of the three worst-complexity blocks.

## Findings

1. **Product bug (found live):** `discovery_sweep` reported
   `success: true` while 6 of 7 audit sources silently returned
   `success=False` ($0 spent, 6.2 s) — a failed sweep renders as a
   clean one. Same class as the #1152 security-audit fix; the source
   failures match the known nested-SDK-workflow limitation.
2. **Medium:** broad `except Exception:` at
   `ops/sweep_results.py:187` (the sweep's one queue finding).
3. **Caveat:** the LLM half of this report degraded to pattern-scan
   only because of finding 1 — re-run from a non-nested context for
   full LLM findings.

## Improvement plan (ranked)

Execution status (2026-07-14, same day): items 1+3 shipped in
PR #1374 (merged); items 6+7 shipped in PR #1375 (merged); items
2+5 refactors in PR #1376 (D23/D23/D22 → C13/C19/C15) (which also lands the
characterization pins for items 2 and 5); item 4's seam map is at
[agent-sdk-adapter-seam-map-2026-07-14.md](agent-sdk-adapter-seam-map-2026-07-14.md).

1. **Surface discovery-sweep source failures** — act now. When N of
   7 sources fail, the result must say so, not "Here's what I
   found." Extend the #1152 pattern to the sweep envelope (failed
   sources named, `success=false` above a failure threshold,
   regression test), then root-cause the nested-SDK source failures
   so in-session audits actually run.
2. **Decompose `ops/data.py`** — structural. 1,583 LOC, 29
   changes/90d, 2 of the repo's 3 D-grade functions. Split
   `spend_alarm` and `read_telemetry_summary`; pin behavior with
   tests first; target grade C or better.
3. **Fix the broad except at `ops/sweep_results.py:187`** — quick
   win. Narrow the exception types, log before handling.
4. **Split `workflows/agent_sdk_adapter.py`** — structural. Largest
   file in src with sustained churn; extract seams before it grows.
5. **Refactor `FeedbackLoop.recommend_tier` (D23)** — scoped.
   Table-drive the tier rules; property tests.
6. **Triage the 28 TODOs** — hygiene. Delete, do inline, or promote
   to an issue/chip; a TODO that survives triage gets an owner.
7. **Spec-status headers for the 22 active specs** — hygiene.
   CORRECTED at execution (#1375): 20/22 already had correct status
   lines (the 07-13/14 truth-sweep PRs); the two gaps
   (elicitation-form-surface design.md, windows-exit139-segfault
   README-only dir) are fixed. The real remaining gap: the
   "(unknown)" orientation noise is `spec_audit.py`'s *staleness*
   column — no spec declares `## Deliverables`, so the drift
   classifier is toothless repo-wide. Follow-up candidate.

## Corrections (refresh, 2026-07-14 evening)

- **D-count was wrong in the first pass**: "3 D-grade blocks" came
  from reading a radon listing through `| tail -8` — the truncation
  ate 27 rows. True count on main: 30 blocks at D or worse,
  including 3 F-grade (`form_from_dict` F87, `_control_html` F84,
  `_build_summary` F48). Average complexity A is unaffected
  (30/5,155 = 0.6%). Count with `grep -c`, never a truncated view.
- TODO metric settled at 0 real markers after #1375's deletion.

## Method notes

- Coverage from the Codecov API, not the badge.
- pip-audit run against the project venv (a first `uvx pip-audit`
  audited the wrong environment — discarded).
- The 16 grep hits for dynamic-code calls were individually
  inspected: all are string literals inside prompt/docstring
  examples that teach the scanner.
- Churn window: 90 days, `src/` only, merge commits excluded by
  `--pretty=format:`.
