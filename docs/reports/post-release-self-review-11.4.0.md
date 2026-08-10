# Post-release self-review triage — 11.4.0 shipped tree (2026-08-08)

Dashboard-recorded runs (release-execute step 16): code-review `1f5af4455671` (score 82/100, $3.93, 250s) + bug-predict `feeb1194ee31` (risk 47/100, $2.46, 223s). Every finding claim-verified against the tree before classification.

## Act-now — FIXED in PR #1982

1. [High/perf, CONFIRMED] N+1 Redis round-trips — sessions.py:253, facade.py:417, conflicts.py:265, patterns.py:183, working.py clear(). Verify: per-key `_get`/`_delete` loops read directly. Fixed via new `BaseOperations._mget`/`_delete_many`.
2. [High/doc-fiction, CONFIRMED] coverage_agent.py:29 docstring claims LLM gap analysis; `_execute_tier` only runs pytest+parse. Ties to chip task_bc331bf3. Docstring corrected.
3. [Medium, CONFIRMED] dashboard.py:74 sync `fetch_summary` (network on cache-miss) inside async handler. Wrapped in `run_in_threadpool`.
4. [Medium, CONFIRMED] specs_data.py decisions.md double-read per spec. Single-read restructure.
5. [Medium, CONFIRMED] security_agent.py:177 `critical_issues` = CRITICAL+HIGH feeding `max_critical_issues: 0`. Behavior conservative and correct; naming misleads. Intent documented at producer; rename deferred (consumers: health_check_scoring/tracking, gate configs).

## Needs-a-look (unscheduled)

6. [High/arch, CONFIRMED — 5 sites, report said 6] ModelTier defined in registry.py, workflows/compat.py (marked for v4.0 removal, still live at 11.4.0), routing/model_router.py, config/agent_config.py, telemetry/feedback_models.py. Consolidation is spec-worthy, cross-cutting.
7. [Systemic, CONFIRMED] mypy configured (dev dep, "run separately" comment) but present in ZERO CI jobs — type/None/signature drift undefended. Enabling is a project (expect a large initial error surface); candidate for a ratchet-style introduction.
8. [Medium, PLAUSIBLE] base_agent.py:236 tier escalation re-runs deterministic tools for 3 of 4 release agents — verify then short-circuit.
9. [Medium, PLAUSIBLE] `_execute_tier` try/except boilerplate duplicated across 4 release agents, already drifted — hoist as template method.
10. [Medium, CONFIRMED] BaseWorkflow = 14-mixin aggregate, ~20-param constructor — long-horizon SRP/ISP debt.
11. [Medium, CONFIRMED] refactor_wizard.py:142 binds concrete RefactorPlanWorkflow instead of get_workflow() registry.
12. [Medium, PLAUSIBLE] /specs route rescans filesystem uncached per load — short-TTL cache candidate (partially mitigated by the double-read fix).
13. [Low/sec, CONFIRMED] executor.py:150 `format(**context)` before `shlex.split` can smuggle argv tokens into allowlisted binaries (no shell). Validate/escape context values.
14. [Low/sec, CONFIRMED] health_snapshot.py:111 codecov path from shape-checked repo_slug — quote path segments.
15. [Watch-list] bug-predict hotspots: agent_sdk_adapter.py, redis_bootstrap.py, mcp/workflow_handlers.py (high LOC × subprocess/async × fan-in).

## Dismissed / downgraded (with reasons)

16. [Downgraded] single_turn.py:499 "layering inversion" — the lazy import carries an explicit comment documenting the deliberate mitigation; known tradeoff, not new debt.
17. [Dismiss-lean] workflows/__init__.py stale `__all__` (cmd_ship etc.) — deliberate deprecation surface per module comment ("Deliberately NOT bound at module level"); revisit when stubs retire.
18. [Low, unverified] release_models.py to_dict/format_console_output legacy — deletion candidate pending usage check.
