# Phase 3 triage — HIGH fact-drift remainder (2026-05-30)

Scout pass for `doc-fiction-cleanup` Phase 3. Classifies the
remaining HIGH fact-drift tracked docs after Phase 1 (3 rewrites)
and Phase 2 (8 retire/archive + 8 mechanical + 1 rewrite) shipped,
plus the two MEDIUM `webhook-event-integration.md` example docs
that were flagged in `decisions.md` "Open questions" as Phase 2
follow-up.

Method per doc: `wc -l` → `head -10` → `grep -nE` for the
fiction markers `decisions.md` flagged + adjacent fictions →
spot-check the critical symbols against `src/attune/` to
confirm whether the renamed class actually exists at the
implied path. Classification follows the same four buckets as
`phase-2-triage.md`.

`docs/how-to/agent-factory.md` was already in the candidate
list but has already been rewritten on the in-flight PR #509
(commit `4b696f8c` on branch `docs/fiction-cleanup-phase-2-rewrite`
in this worktree). Treated as DONE; not classified below.

## Counts

- MECHANICAL: 4
- RETIRE-CANDIDATE: 4
- REWRITE: 3
- UNCLEAR: 0
- **Total**: 11

The cohort splits roughly evenly between mechanical renames and
retires. The retire-leaning weight comes from a coordination
subsystem (`attune.coordination`) that was REMOVED in v6.8.0 —
three docs in this cohort describe deleted classes
(`AgentCoordinator`, `AgentTask`, `TeamSession`,
`ConflictResolver`) and the shim at `src/attune/coordination.py`
now raises `ImportError` with a "removed in v6.8.0" message.
Those docs are not rewritable against a current API; the API
they describe was intentionally deleted. The CLI-shaped fictions
(`attune orchestrate`, `python -m attune.cli`) are the other
notable cluster — those are rewritable because the underlying
features (orchestration templates, the `attune` CLI itself)
exist, just not at the entry points the docs claim.

## Triage

| Doc | Class | Reason / fiction markers | Phase 3 action |
|---|---|---|---|
| `docs/how-to/short-term-memory-implementation.md` | RETIRE-CANDIDATE | 555-line how-to whose central premise is the deleted coordination API: `from attune import AgentCoordinator, AgentTask` (line 109), `TeamSession` (219), `StagedPattern` (260, real but minor), plus end-to-end "team review" example (429–457) built on `AgentCoordinator`+`AgentTask`+`TeamSession`. All three classes confirmed REMOVED in v6.8.0 per `src/attune/coordination.py` (now an `ImportError` shim listing exactly these names). `EmpathyOS`/`get_redis_memory`/`check_redis_connection` ARE real top-level exports per `src/attune/__init__.py`, but they're not the spine of the doc — the deleted coordination API is. | Retire. The "implementing short-term memory" how-to needs to be re-authored against the remaining Redis primitives (`get_redis_memory`, `EmpathyOS` integration, `StagedPattern`); that's a separate spec, not a Phase-1-style rewrite of this fictional surface. Remove from nav, `.help/features.yaml`, inbound links. |
| `docs/reference/SHORT_TERM_MEMORY.md` | RETIRE-CANDIDATE | 408-line API reference centered on the same deleted classes: `### AgentCoordinator` (218), `### TeamSession` (252), full constructor + method signatures for both, end-to-end example at 363–385. Same v6.8.0 removal applies. Plus: doc reframes itself as "file-first architecture with optional Redis" — both halves of which need fresh verification against current source if a replacement is ever written. | Retire. A real `SHORT_TERM_MEMORY.md` belongs as a spec deliverable after the redis-decoupling work (referenced in coordination.py shim) is stable. Same nav/`features.yaml`/inbound-link cleanup as the how-to. |
| `docs/how-to/learning-and-patterns.md` | MECHANICAL | 241-line how-to. Three method renames: `extractor.extract(...)` → `extract_patterns` (verified at `src/attune/learning/extractor.py:143`); `storage.search(...)` → `search_patterns` (verified at `src/attune/learning/storage.py:263`); `storage.get_most_used(...)` (line 196) GONE — no `get_most_used` anywhere in `src/attune/learning/`. Imports all resolve at `attune.learning.*`. | Two method renames + delete-or-replace the `get_most_used` block (one option: `get_all_patterns` exists; another: drop the snippet). grep+replace + smoke-test imports. |
| `docs/reference/pattern-library.md` | MECHANICAL | 433-line reference. `library.find_patterns(...)` appears at lines 91, 179, 401 — real method is `query_patterns` (verified at `src/attune/pattern_library.py:186`; docstrings inside the source confirm the rename ("Reduces query_patterns from O(n) to O(k)" at line 122)). `library.remove_pattern(pattern.id)` at line 359 — no such method on `PatternLibrary` (its method list: `contribute_pattern`, `query_patterns`, `get_pattern`, `get_patterns_by_tag`, `get_patterns_by_type`, `record_pattern_outcome`, `link_patterns`, `get_related_patterns`, `get_agent_patterns`, `get_top_patterns`, `get_library_stats`, `reset`). Also: line 277 imports `from attune.persistence import PatternPersistence` — real path is `attune.pattern_persistence.PatternPersistence` (`src/attune/persistence.py` and `src/attune/pattern_persistence.py` are different modules). | grep+replace `find_patterns` → `query_patterns` (3 sites); delete the `remove_pattern` example block (or substitute with `reset` or removed-from-public-API note); fix `attune.persistence` → `attune.pattern_persistence` import. Mechanical but multi-site. |
| `docs/how-to/multi-agent-coordination.md` | RETIRE-CANDIDATE | 525-line how-to. Mixed surface: `PatternLibrary`/`Pattern` from `attune.pattern_library` are real, BUT the doc's coordination story rests on `ConflictResolver()` at line 447 (REMOVED in v6.8.0 per `coordination.py` shim) and `AgentMonitor` from `attune.monitoring` (line 463) — `AgentMonitor` is real but lives at `attune.agent_monitoring`, NOT `attune.monitoring` (which is a separate alerts/metrics package). Once the `ConflictResolver` example is stripped, what remains is a thin pattern-library demo that overlaps with the existing pattern-library reference doc. | Retire. The conflict-resolution narrative is the doc's reason to exist as a separate "multi-agent coordination" how-to, and that API is deleted. Surviving content (pattern-sharing, agent monitoring) belongs as smaller examples in the existing pattern-library and (future) agent_monitoring docs. |
| `docs/tutorials/META_ORCHESTRATION_TUTORIAL.md` | REWRITE | 931-line tutorial. Real underlying surface verified: `MetaOrchestrator` at `src/attune/orchestration/meta_orchestrator.py:120`; `get_template`/`get_all_templates` at `src/attune/orchestration/agent_templates/registry.py:41,62`; all six execution strategies (`Sequential`/`Parallel`/`Debate`/`Teaching`/`Refinement`/`Adaptive`) live at `src/attune/orchestration/execution_strategies.py` and are exported. Fictions to strip: (a) `attune orchestrate` CLI subcommand appears ~7 times (122, 125, 131, 171, 174, 177, 222, 225, 228, 231) — no such subcommand in `cli_minimal.py` (real subparsers: `workflow`/`telemetry`/`costs`/`provider`/...); (b) `AGENT_REGISTRY` import at lines 724–725 — real symbol is `_TEMPLATE_REGISTRY` (private) with public `get_registry()` accessor; (c) "7 agent templates" claim — `builtin_templates.py` declares 14 `AgentTemplate(` constructions. Six real strategy blocks (317–423) appear to use correct class names; need per-snippet verification. | Phase-1-style rewrite against `src/attune/orchestration/`. Strip the `attune orchestrate` CLI sections entirely (or replace with the real Python entry-point pattern), fix the `AGENT_REGISTRY` example to use `get_registry()` / `register_custom_template`, correct the count, verify each strategy snippet. Large but coherent. |
| `docs/how-to/agent-factory.md` | DONE | Rewritten on PR #509 (commit `4b696f8c`). Skipped per scout instructions. | n/a |
| `docs/how-to/smart-router.md` | MECHANICAL | 310-line how-to. Every example uses `wizard`/`primary_wizard`/`secondary_wizards`/`list_wizards()` etc. Real `SmartRouter` at `src/attune/routing/smart_router.py:33` uses `workflow` everywhere: `primary_workflow`, `secondary_workflows`, `get_workflow_info`, `WorkflowRegistry`, `WorkflowInfo`. The wizard→workflow rename is system-wide in source. `ChainExecutor` at `src/attune/routing/chain_executor.py:66` is real. The "17+ wizards" claim (line 35) becomes "17+ workflows" — verify the actual registry size after rename. Pure mechanical replace once the wizard→workflow direction is set; no fictional surface beyond the rename. | grep+replace `wizard`→`workflow` (case-preserved) across the doc, plus the field renames (`primary_wizard`→`primary_workflow`, etc.). Verify registry size by inspecting `WorkflowRegistry` or running `python -c "from attune.routing import SmartRouter; print(len(SmartRouter().list_workflows()))"`. Largest mechanical of the cohort by churn but still mechanical. |
| `docs/reference/cli-reference.md` | REWRITE | 885-line reference. Real surface: `attune workflow/telemetry/costs/provider/...` subcommands all verified in `cli_minimal.py`. Fictions: (a) `python -m attune.cli` (lines 866–868) — no `src/attune/cli.py` exists (only `cli_minimal.py`, `cli_router.py`, and per-subpackage `cli.py` files); the "30+ commands" claim for that nonexistent entry point is doubly false. (b) `python -m attune.socratic` (line 878) — `src/attune/socratic/` exists as a package but has no `__main__.py`, so `python -m attune.socratic` fails. Other `python -m` entries DO resolve (`attune.telemetry`, `attune.test_generator`, `attune.project_index`, `attune.models` all have `__main__.py` per `find`). (c) `attune.cli_unified` Deprecated entry — needs source confirmation (likely fossil). Doc body for workflow/telemetry/costs commands appears largely real but needs per-flag verification. | Phase-1-style rewrite, scoped to the "All CLI Entry Points" section primarily: delete the fictional `python -m attune.cli` row, delete or replace the fictional `python -m attune.socratic` row with a note that socratic is a subpackage CLI not a runnable module, verify per-command flags against `cli_minimal.py` subparsers. Most of the body is salvageable; the entry-point matrix is the load-bearing fiction. |
| `docs/how-to/project-analysis-and-metrics.md` | MECHANICAL | 235-line how-to. Imports resolve: `attune.project_index.ProjectIndex` real (`index.py:25`), `attune.project_index.models.FileCategory` real. But `ProjectSummary` fields were renamed wholesale per `decisions.md`: doc uses `summary.python_files` / `health_score` / `test_coverage_ratio` / `documented_ratio` / `high_risk_files`. Real fields per `src/attune/project_index/models.py:172–214` are `source_files` (no `python_files`), no `health_score` at all, `test_coverage_avg`, `files_with_docstrings_pct`, `high_impact_files`. Every `summary.*` access in the doc is broken. | Mechanical but multi-site (≈10 field references). grep+replace each field to its real name. Verify by running the snippets against a small test repo OR by walking through `to_dict()` field list. The `health_score` field has no direct replacement — drop that line or compute it from real fields. |
| `docs/examples/webhook-event-integration.md` | RETIRE-CANDIDATE | 846-line example doc. Imports `attune.events.EventBus, Event` and `attune.webhooks.WebhookManager` — neither module exists in `src/attune/` (only `src/attune/memory/security/events.py` which is unrelated). `pip install attune-ai[webhooks]` extra also doesn't exist in `pyproject.toml`. Same as the already-retired `docs/how-to/webhook-integration.md` situation: entire example built on a fictional package. | Retire. Remove from nav, inbound refs, any `index.md` listings. |
| `docs/tutorials/examples/webhook-event-integration.md` | RETIRE-CANDIDATE | Identical file (`diff -q` reports no difference) — same retire reasoning. Two copies of the same fictional example doc in different locations. | Retire alongside the `docs/examples/` copy. Single PR. |

## Notes from spot-checks against `src/`

Symbols VERIFIED present at the expected path:

- `attune.learning.extractor.PatternExtractor.extract_patterns` (`extractor.py:143`)
- `attune.learning.storage.LearnedSkillsStorage.search_patterns` (`storage.py:263`)
- `attune.pattern_library.PatternLibrary.query_patterns` (`pattern_library.py:186`)
- `attune.pattern_library.{Pattern, PatternMatch, PatternLibrary}` (same file, lines 18/69/77)
- `attune.routing.smart_router.SmartRouter` (`smart_router.py:33`) — uses `workflow` terminology end-to-end
- `attune.routing.chain_executor.ChainExecutor` (`chain_executor.py:66`)
- `attune.routing.workflow_registry.{WorkflowRegistry, WorkflowInfo}` (referenced from smart_router.py)
- `attune.orchestration.MetaOrchestrator` (`meta_orchestrator.py:120`)
- `attune.orchestration.agent_templates.registry.{get_template, get_all_templates, register_custom_template, unregister_template, get_registry}` (`registry.py:41–159`)
- `attune.orchestration.execution_strategies.{Sequential, Parallel, Debate, Teaching, Refinement, Adaptive}Strategy` (verified in module `__all__`)
- `attune.project_index.{ProjectIndex, models.FileCategory, models.ProjectSummary}` (`index.py:25`, `models.py:15,172`)
- `attune.pattern_persistence.PatternPersistence` (path differs from doc's `attune.persistence`)
- `attune.agent_monitoring.{AgentMetrics, TeamMetrics, AgentMonitor}` (`agent_monitoring.py:25/62/91`) — NOT at `attune.monitoring`

Symbols CONFIRMED REMOVED (v6.8.0 deletion):

- `attune.coordination.AgentCoordinator`
- `attune.coordination.AgentTask`
- `attune.coordination.TeamSession`
- `attune.coordination.ConflictResolver`
- `attune.coordination.ResolutionResult`
- `attune.coordination.ResolutionStrategy`
- `attune.coordination.TeamPriorities`

All seven are listed in the `_REMOVED_NAMES` frozenset of
`src/attune/coordination.py` and now raise `ImportError`
on access. Per the shim docstring, the rationale was "no
internal callers in attune-ai itself, were tightly coupled to
Redis, and were preventing pip install attune-ai from being
truly Redis-free." See `docs/specs/redis-decoupling/`.

Symbols CONFIRMED missing (fiction or not yet built):

- `attune.events.EventBus`, `attune.events.Event` — no `attune.events` module
- `attune.webhooks.WebhookManager` — no `attune.webhooks` module
- `attune-ai[webhooks]` install extra — not in `pyproject.toml`
- `attune.cli` (module / `python -m attune.cli`) — no `src/attune/cli.py`
- `attune.socratic.__main__` — `attune.socratic/` exists as a package but has no `__main__.py`
- `attune orchestrate` CLI subcommand — not in `cli_minimal.py` subparsers
- `AGENT_REGISTRY` — real is `_TEMPLATE_REGISTRY` (private) + `get_registry()` (public)
- `library.find_patterns(...)`, `library.remove_pattern(...)` — neither exists on `PatternLibrary`
- `storage.get_most_used(...)` — not in `LearnedSkillsStorage`
- `summary.python_files`, `summary.health_score`, `summary.test_coverage_ratio`, `summary.documented_ratio`, `summary.high_risk_files` — fields renamed; current names use `source_files`, `test_coverage_avg`, `files_with_docstrings_pct`, `high_impact_files`, no `health_score`

## Suggested batching for Phase 3 execution

Order maximizes per-PR coherence and minimizes risk:

1. **RETIRE batch (lowest risk; closes deleted-API exposure).**
   Single PR retires:
   - `short-term-memory-implementation.md`
   - `SHORT_TERM_MEMORY.md`
   - `multi-agent-coordination.md`
   - Both `webhook-event-integration.md` copies
     (`docs/examples/` and `docs/tutorials/examples/`)

   Total: 5 docs, all centered on either v6.8.0-removed
   coordination classes or a fictional `attune.webhooks`
   package. Nav + `.help/features.yaml` + inbound-link
   cleanup. Note coordination removal in commit body so the
   PR cross-references `docs/specs/redis-decoupling/`.

2. **MECHANICAL batch.** Single PR for the four mechanical
   docs:
   - `learning-and-patterns.md` (2 renames + 1 deletion)
   - `pattern-library.md` (`find_patterns`→`query_patterns`,
     delete `remove_pattern` example, fix
     `attune.persistence`→`attune.pattern_persistence`)
   - `smart-router.md` (`wizard`→`workflow` sweep; biggest
     churn of the cohort but still mechanical)
   - `project-analysis-and-metrics.md` (`ProjectSummary`
     field renames across ~10 sites)

   Risk: medium for `smart-router.md` only (large case-
   preserved find/replace; verify each call site after).
   Smoke-test each doc's importable snippets.

3. **REWRITE batch (per session contract, ≤1 REWRITE per
   session).** Each its own ship unit:
   - `cli-reference.md` first (smallest scope: the entry-
     point matrix is the fiction, body is mostly real)
   - `META_ORCHESTRATION_TUTORIAL.md` second (931 lines but
     the underlying API is large, real, and well-mapped; the
     CLI fiction and the `AGENT_REGISTRY` symbol fiction are
     the load-bearing strips)

After the RETIRE + MECHANICAL batches ship, the doc surface
of the 16 HIGH cohort is down to those two rewrites plus
whatever Phase 4 follow-ups land (`TROUBLESHOOTING.md`
deferred from Phase 2 — confirm whether it's in scope here
or stays Phase-4).

## Open questions for Patrick

1. **Are the short-term-memory + multi-agent-coordination
   docs strictly retire, or rewrite-against-what-remains?**
   The deleted coordination API was the spine of all three.
   `EmpathyOS`/`get_redis_memory`/`StagedPattern`/`PatternLibrary`
   remain and could support a slimmer "team coordination on
   shared Redis memory" how-to, but that's a separate spec.
   Recommend retire-without-replacement-this-PR and spawn a
   follow-up spec; mirrors the `USER_GUIDE.md` decision in
   Phase 2.
2. **In `META_ORCHESTRATION_TUTORIAL.md`, do you want the
   rewrite to include or omit a CLI section?** No
   `attune orchestrate` CLI exists. Two options: (a) omit
   the CLI sections entirely, mirroring the agent-factory
   rewrite decision; (b) note "orchestration is Python-API-
   only today" and link to the agent-templates registry. The
   tutorial loses some of its punch without invocable shell
   examples, but inventing CLI commands is exactly the
   fiction we're trying to stop.
3. **In `cli-reference.md`, what's the call on
   `python -m attune.socratic`?** The socratic package is
   real and has its own internal CLIs (`cli.py`,
   `cli_console.py`) but no `__main__.py`. Either (a) add
   a `__main__.py` (code change, out of scope for docs),
   (b) document the real invocation path (whatever it is —
   needs source spelunking), or (c) drop the row entirely.
   Pure-doc fix is (c); the cleanest user experience is (a)
   but that's a feature task.
4. **`pattern-library.md` line 359 — drop the `remove_pattern`
   example or substitute?** `PatternLibrary` has no
   pattern-removal method in its public surface. The closest
   is `reset()` (wipes all). If pattern-removal is desired,
   that's a feature ask; if not, drop the example.
5. **`project-analysis-and-metrics.md` `health_score` —
   compute or drop?** Real `ProjectSummary` has no
   `health_score` field. Either (a) drop the line (cleanest),
   (b) compute one from `test_coverage_avg` +
   `files_with_docstrings_pct` + complexity in the doc
   itself (overpromising), or (c) confirm whether there's a
   `health_score` calculation living somewhere outside
   `ProjectSummary`.
6. **`TROUBLESHOOTING.md` — Phase 3 or deferred to Phase 4?**
   Deferred from Phase 2 PR-C per `decisions.md` "Phase 2
   status" line. Not in this scout's brief (the 10 HIGH
   docs explicitly listed), so not classified above. If
   you want it in Phase 3, a separate triage pass is needed
   — its mix of real-troubleshooting-content + `coach_wizards`
   fiction puts it firmly in the REWRITE bucket.
