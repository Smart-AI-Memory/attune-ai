# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Guard: no NEW ``except Exception`` / ``except BaseException`` in shipped code.

Broad exception handlers are the soil silent failures grow in. The
Critical Rules already forbid *bare* ``except:``, but ``except Exception``
with a swallow is functionally equivalent and was unpoliced.

**This guard freezes debt; it does not force conversion.** The per-file
baseline below is SHRINK-ONLY: a new or raised count anywhere fails, and
converting a file means lowering (or deleting) its entry. Legitimate
sites — evidence collectors, must-not-crash hook paths — stay in the
baseline indefinitely. The baseline is the escape hatch, not
pattern-matching cleverness (spec R3/R4).

Ratified rulings this implements (``docs/specs/broad-except-ratchet``,
D1 2026-08-06):

- **R5 — ``# noqa: BLE001`` sites are COUNTED.** The annotation is not
  an exemption: at approval, 580 of 586 ``src/attune`` sites carried it,
  so excluding them would have policed 6 sites out of 586. It records
  that ruff was satisfied, not that a contract was documented.
- **R6 — scope is ``src/attune`` + ``attune_redis`` + ``backend``.**
  ``attune_redis`` ships bundled in the wheel; ``backend`` holds auth
  and subscription code where a swallow costs most.
- **R4 — the scan is mechanical.** A handler that logs and re-raises is
  still counted; correctness is judged by humans, not by this test.

Detection is AST-based, not textual: this repo's prose, lessons corpus,
and docstrings mention ``except Exception`` constantly, and a regex would
count those. One ``ExceptHandler`` catching either type counts once,
however many names its tuple carries.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

#: Trees in scope (R6), relative to the repo root.
SCOPED_TREES = ("src/attune", "attune_redis", "backend")

_BROAD = frozenset({"Exception", "BaseException"})

_HINT = (
    "Catch the SPECIFIC exception(s) you can handle and log before "
    "handling. If the broad catch is genuinely required (evidence "
    "collector, must-not-crash hook path), the baseline in this file is "
    "the escape hatch — add a comment saying WHY at the call site and "
    "raise the entry in the same commit, with the reason in the PR."
)

#: Per-file frozen baseline (repo-relative posix). SHRINK-ONLY: ratchet
#: DOWN as sites are converted; never raise an entry without a stated
#: reason. Seeded 2026-08-07 from the tree at the seeding commit.
_BASELINE: dict[str, int] = {
    # mcp_tools.py raised 12 -> 13 for rct-3 (PR #1987): the doctor
    # diagnostic's classifier guard — the effective-config section must
    # never flip an otherwise-healthy health-tool response to failure.
    "attune_redis/mcp_tools.py": 13,
    # memory.py raised 13 -> 14 for the retrieve_many batch extension
    # (PR #1991): the batched working-memory read degrades AMS errors to
    # all-None instead of raising, matching retrieve()'s must-not-crash
    # memory-layer contract (collaboration principle 15).
    "attune_redis/memory.py": 14,
    "attune_redis/plugin.py": 1,
    "attune_redis/signals.py": 2,
    "attune_redis/tests/test_integration.py": 1,
    "attune_redis/vector_db_int8.py": 1,
    "backend/api/analysis.py": 3,
    "backend/services/analyzers/multi_layer_analyzer.py": 1,
    "backend/services/auth_service.py": 1,
    "backend/services/database/auth_db.py": 1,
    "src/attune/__init__.py": 1,
    "src/attune/agent_factory/adapters/autogen_adapter.py": 2,
    "src/attune/agent_factory/adapters/haystack_adapter.py": 2,
    "src/attune/agent_factory/adapters/langchain_adapter.py": 3,
    "src/attune/agent_factory/adapters/langgraph_adapter.py": 2,
    "src/attune/agent_factory/decorators.py": 3,
    "src/attune/agent_factory/resilient.py": 3,
    "src/attune/agents/release/base_agent.py": 3,
    "src/attune/agents/release/coverage_agent.py": 1,
    "src/attune/agents/release/documentation_agent.py": 1,
    "src/attune/agents/release/quality_agent.py": 1,
    "src/attune/agents/release/release_prep_team.py": 2,
    "src/attune/agents/release/security_agent.py": 1,
    "src/attune/agents/state/store.py": 1,
    "src/attune/agents/team.py": 1,
    "src/attune/agents_md/loader.py": 1,
    "src/attune/authoring/fact_check/cli_refs.py": 1,
    "src/attune/authoring/fact_check/doc_examples.py": 1,
    "src/attune/authoring/fact_check/import_repair.py": 1,
    "src/attune/authoring/fact_check/imports.py": 4,
    "src/attune/authoring/fact_check/numeric_refs.py": 1,
    "src/attune/authoring/faithfulness/__init__.py": 1,
    "src/attune/authoring/generator.py": 3,
    "src/attune/authoring/polish.py": 1,
    "src/attune/authoring/projector.py": 1,
    "src/attune/authoring/rag_hook.py": 1,
    "src/attune/authoring/source_introspection.py": 1,
    "src/attune/authoring/spec_runner.py": 1,
    "src/attune/authoring/spec_workflow.py": 1,
    "src/attune/cli_commands/_exit_codes.py": 2,
    "src/attune/cli_commands/diagnosis_commands.py": 1,
    "src/attune/cli_commands/fix_commands.py": 1,
    "src/attune/cli_commands/memory_agent.py": 2,
    "src/attune/cli_commands/provider_commands.py": 2,
    "src/attune/cli_commands/telemetry_commands.py": 12,
    "src/attune/cli_commands/utility_commands.py": 6,
    "src/attune/cli_commands/workflow_commands.py": 1,
    "src/attune/cli_minimal.py": 3,
    "src/attune/cli_router.py": 1,
    "src/attune/commands/context.py": 2,
    "src/attune/commands/parser.py": 2,
    "src/attune/config/legacy.py": 1,
    "src/attune/config/xml_config.py": 1,
    "src/attune/cost_tracker.py": 1,
    "src/attune/curator/core.py": 3,
    "src/attune/curator/sources/bulletin.py": 2,
    "src/attune/curator/sources/diagnoses.py": 1,
    "src/attune/curator/sources/spec_drift.py": 1,
    "src/attune/curator/sources/specs.py": 2,
    "src/attune/diagnosis/priors.py": 1,
    "src/attune/diagnosis/triage.py": 1,
    "src/attune/discovery.py": 1,
    "src/attune/handoff/memory_link.py": 5,
    "src/attune/help/feedback.py": 1,
    "src/attune/help/polish.py": 1,
    "src/attune/hooks/executor.py": 2,
    "src/attune/hooks/registry.py": 1,
    "src/attune/hooks/scripts/evaluate_session.py": 3,
    "src/attune/hooks/scripts/help_freshness_nudge.py": 1,
    "src/attune/hooks/scripts/lessons_reminder.py": 1,
    "src/attune/hooks/scripts/pre_compact.py": 1,
    "src/attune/hooks/scripts/starter_prompt_nudge.py": 1,
    "src/attune/hooks/scripts/starter_reconciler.py": 3,
    "src/attune/hooks/scripts/worktree_path_guard.py": 1,
    "src/attune/llm/fable_call.py": 2,
    "src/attune/llm/interaction.py": 1,
    "src/attune/llm/providers/anthropic_batch.py": 3,
    "src/attune/mcp/memory_handlers.py": 12,
    "src/attune/mcp/server.py": 8,
    "src/attune/mcp/version_check.py": 2,
    "src/attune/mcp/workflow_handlers.py": 2,
    "src/attune/memory/claude_memory.py": 2,
    "src/attune/memory/config.py": 1,
    "src/attune/memory/control_panel.py": 4,
    "src/attune/memory/cross_session/service.py": 1,
    # features.py raised 1 -> 2 for rct-2 (PR #1985): classify_redis_health's
    # probe is a P15 never-block path — ANY unexpected exception must degrade
    # to degraded_connectivity, pinned by TestNeverBlock's RuntimeError case.
    "src/attune/memory/features.py": 2,
    "src/attune/memory/file_stash.py": 1,
    "src/attune/memory/lessons.py": 2,
    "src/attune/memory/long_term_integration.py": 2,
    "src/attune/memory/long_term_operations.py": 2,
    "src/attune/memory/memory_tool.py": 2,
    "src/attune/memory/mixins/backend_init_mixin.py": 5,
    "src/attune/memory/mixins/long_term_mixin.py": 4,
    "src/attune/memory/mixins/short_term_mixin.py": 2,
    "src/attune/memory/personal.py": 5,
    "src/attune/memory/redis_auto_detect.py": 1,
    "src/attune/memory/redis_bootstrap.py": 8,
    "src/attune/memory/security/audit_logger.py": 4,
    "src/attune/memory/security/query.py": 1,
    "src/attune/memory/session_stash.py": 14,
    # verdict_log.propagate_verdict is a P15 never-block path: redis
    # import/connect/delete failures of ANY shape must degrade to False —
    # the verdict loop is never blocked on the memory layer (P2 task 6).
    "src/attune/memory/verdict_log.py": 1,
    # serve_telemetry.log_curated_recall mirrors the hook-side writer's
    # posture (same sink, same contract): telemetry about a recall must
    # never cost the caller the recall — ANY failure degrades to False
    # (memory-status-integrity P3 task 2).
    "src/attune/memory/serve_telemetry.py": 1,
    "src/attune/memory/short_term/base.py": 1,
    "src/attune/memory/short_term/pubsub.py": 6,
    "src/attune/memory/short_term/transactions.py": 1,
    "src/attune/memory/storage_backend.py": 1,
    "src/attune/meta_workflows/cli_commands/analytics_commands.py": 8,
    "src/attune/meta_workflows/cli_commands/config_commands.py": 1,
    "src/attune/meta_workflows/cli_commands/memory_commands.py": 2,
    "src/attune/meta_workflows/cli_commands/template_commands.py": 3,
    "src/attune/meta_workflows/cli_commands/workflow_commands.py": 4,
    "src/attune/meta_workflows/form_engine.py": 1,
    "src/attune/meta_workflows/llm_execution.py": 3,
    "src/attune/meta_workflows/pattern_learner.py": 2,
    "src/attune/meta_workflows/pattern_memory.py": 4,
    "src/attune/meta_workflows/session_context.py": 8,
    "src/attune/meta_workflows/workflow.py": 2,
    "src/attune/metrics/prompt_metrics.py": 1,
    "src/attune/models/auth_cli.py": 4,
    "src/attune/models/auth_strategy.py": 3,
    "src/attune/models/empathy_executor.py": 2,
    "src/attune/models/provider_config.py": 2,
    "src/attune/models/resilient_executor.py": 2,
    "src/attune/models/single_turn.py": 2,
    "src/attune/models/telemetry/__init__.py": 1,
    "src/attune/models/token_estimator.py": 2,
    "src/attune/monitoring/multi_backend.py": 5,
    "src/attune/monitoring/notifications.py": 1,
    "src/attune/monitoring/otel_backend.py": 4,
    "src/attune/monitoring/validators.py": 2,
    "src/attune/ops/cli.py": 1,
    "src/attune/ops/collab_data.py": 5,
    "src/attune/ops/data.py": 3,
    "src/attune/ops/health_snapshot.py": 3,
    "src/attune/ops/help_data.py": 2,
    "src/attune/ops/memory_data.py": 6,
    "src/attune/ops/routes/bulletin.py": 1,
    "src/attune/ops/routes/dashboard.py": 5,
    "src/attune/ops/routes/specs.py": 2,
    "src/attune/ops/runner.py": 3,
    "src/attune/ops/session_summarizer.py": 2,
    "src/attune/ops/sweep_results.py": 1,
    "src/attune/ops/sweep_results_watcher.py": 2,
    "src/attune/orchestration/_strategies/advanced_strategies.py": 5,
    "src/attune/orchestration/_strategies/base.py": 1,
    "src/attune/orchestration/_strategies/conditions.py": 1,
    "src/attune/orchestration/_strategies/core_strategies.py": 2,
    "src/attune/orchestration/ghosts/runner.py": 1,
    "src/attune/orchestration/pattern_learner.py": 1,
    "src/attune/orchestration/tools/quality.py": 4,
    "src/attune/orchestration/tools/security.py": 1,
    "src/attune/orchestration/tools/test_generation.py": 5,
    "src/attune/orchestration/tools/testing.py": 7,
    "src/attune/patterns/confidence.py": 1,
    "src/attune/patterns/contextual.py": 1,
    "src/attune/patterns/git_extractor.py": 4,
    "src/attune/patterns/resolver.py": 1,
    "src/attune/pipeline/orchestrator.py": 3,
    "src/attune/plugins/registry.py": 3,
    "src/attune/project_index/index.py": 1,
    "src/attune/redis_config.py": 1,
    "src/attune/redis_memory_storage.py": 1,
    "src/attune/resilience/circuit_breaker.py": 2,
    "src/attune/resilience/fallback.py": 5,
    "src/attune/resilience/health.py": 4,
    "src/attune/roundtable/producing.py": 1,
    "src/attune/roundtable/review.py": 1,
    "src/attune/roundtable/solutions.py": 1,
    "src/attune/roundtable/triage_appendix.py": 2,
    "src/attune/routing/classifier.py": 1,
    "src/attune/telemetry/agent_coordination.py": 7,
    "src/attune/telemetry/agent_tracking.py": 5,
    "src/attune/telemetry/approval_gates.py": 8,
    "src/attune/telemetry/cli_analysis.py": 1,
    "src/attune/telemetry/cli_automation.py": 4,
    "src/attune/telemetry/event_streaming.py": 6,
    "src/attune/telemetry/feedback_loop.py": 6,
    "src/attune/telemetry/lessons/__init__.py": 1,
    "src/attune/telemetry/memory_events.py": 1,
    "src/attune/telemetry/usage_ping.py": 4,
    "src/attune/telemetry/usage_tracker.py": 3,
    "src/attune/tools.py": 1,
    "src/attune/utils/tokens.py": 4,
    "src/attune/validation/xml_validator.py": 2,
    "src/attune/verification/mixin.py": 3,
    "src/attune/voice/formatter.py": 2,
    "src/attune/voice/next_steps.py": 2,
    "src/attune/voice/report_renderer.py": 1,
    "src/attune/widgets/chart_widget_tool.py": 3,
    "src/attune/wizards/base.py": 1,
    "src/attune/wizards/builtin/refactor_wizard.py": 2,
    "src/attune/wizards/builtin/security_wizard.py": 3,
    "src/attune/wizards/decomposer.py": 1,
    "src/attune/wizards/registry.py": 3,
    "src/attune/workflows/__init__.py": 2,
    "src/attune/workflows/agent_sdk_adapter.py": 4,
    "src/attune/workflows/base.py": 1,
    "src/attune/workflows/bug_predict.py": 1,
    "src/attune/workflows/code_review.py": 1,
    "src/attune/workflows/coordination_mixin.py": 5,
    "src/attune/workflows/deep_review.py": 1,
    "src/attune/workflows/dependency_check.py": 1,
    "src/attune/workflows/dependency_check_audit.py": 4,
    "src/attune/workflows/dependency_check_parsers.py": 4,
    "src/attune/workflows/discovery_sweep/sources/bug_predict.py": 1,
    "src/attune/workflows/discovery_sweep/sources/dependency_check.py": 1,
    "src/attune/workflows/discovery_sweep/sources/doc_audit.py": 1,
    "src/attune/workflows/discovery_sweep/sources/perf_audit.py": 1,
    "src/attune/workflows/discovery_sweep/sources/security_audit.py": 1,
    "src/attune/workflows/discovery_sweep/sources/test_audit.py": 1,
    "src/attune/workflows/discovery_sweep/workflow.py": 2,
    "src/attune/workflows/doc_audit/workflow.py": 1,
    "src/attune/workflows/doc_orch_report.py": 2,
    "src/attune/workflows/doc_orch_scout.py": 1,
    "src/attune/workflows/document_gen/api_reference.py": 1,
    "src/attune/workflows/document_gen/chunked_generation.py": 2,
    "src/attune/workflows/document_gen/outline_stage.py": 2,
    "src/attune/workflows/document_gen/polish_stage.py": 1,
    "src/attune/workflows/document_gen/workflow.py": 1,
    "src/attune/workflows/document_manager.py": 2,
    "src/attune/workflows/documentation_orchestrator.py": 2,
    "src/attune/workflows/escalation/chain.py": 1,
    "src/attune/workflows/escalation/evaluator.py": 1,
    "src/attune/workflows/execution_mixin.py": 13,
    "src/attune/workflows/health_check_tracking.py": 1,
    "src/attune/workflows/help_maintenance.py": 1,
    "src/attune/workflows/llm_mixin.py": 1,
    "src/attune/workflows/perf_audit.py": 1,
    "src/attune/workflows/post_simplification_mixin.py": 1,
    "src/attune/workflows/progress.py": 1,
    "src/attune/workflows/progress_reporters.py": 1,
    "src/attune/workflows/progressive/telemetry.py": 5,
    "src/attune/workflows/progressive/workflow.py": 2,
    "src/attune/workflows/prompt_mixin.py": 1,
    "src/attune/workflows/rag_code_gen.py": 2,
    "src/attune/workflows/refactor_plan.py": 1,
    "src/attune/workflows/release_prep.py": 1,
    "src/attune/workflows/research_synthesis.py": 1,
    "src/attune/workflows/secure_release.py": 1,
    "src/attune/workflows/security_audit.py": 1,
    "src/attune/workflows/services/coordination_service.py": 5,
    "src/attune/workflows/services/telemetry_service.py": 2,
    "src/attune/workflows/simplify_code.py": 1,
    "src/attune/workflows/state_mixin.py": 5,
    "src/attune/workflows/suggestions.py": 5,
    "src/attune/workflows/telemetry_mixin.py": 2,
    "src/attune/workflows/test_audit/workflow.py": 1,
    "src/attune/workflows/test_gen/ast_analyzer.py": 1,
    "src/attune/workflows/test_gen/workflow.py": 1,
    "src/attune/workflows/test_gen_parallel.py": 2,
    "src/attune/workflows/test_maintenance.py": 1,
    "src/attune/workflows/test_runner.py": 4,
    "src/attune/workflows/test_runner_helpers.py": 2,
    "src/attune/workflows/tier_tracking.py": 2,
    "src/attune/workflows/workflow_batch_runner.py": 1,
}


def _handler_is_broad(handler: ast.ExceptHandler) -> bool:
    """True when this handler catches Exception or BaseException."""
    node = handler.type
    if node is None:
        return False  # bare `except:` — forbidden elsewhere, not this gate
    candidates = node.elts if isinstance(node, ast.Tuple) else [node]
    for item in candidates:
        if isinstance(item, ast.Name) and item.id in _BROAD:
            return True
        # `builtins.Exception` / `bltns.Exception` — attribute form.
        if isinstance(item, ast.Attribute) and item.attr in _BROAD:
            return True
    return False


def _count_in_file(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        # Unparseable/unreadable files cannot be audited; skip rather than
        # fail the gate on something that is not a broad-except problem.
        return 0
    return sum(
        1 for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler) and _handler_is_broad(n)
    )


def current_counts() -> dict[str, int]:
    """Broad-except handler count per in-scope file with at least one."""
    counts: dict[str, int] = {}
    for tree_name in SCOPED_TREES:
        root = REPO_ROOT / tree_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            n = _count_in_file(path)
            if n:
                counts[path.relative_to(REPO_ROOT).as_posix()] = n
    return counts


def test_no_new_broad_except_sites():
    """Fail if any in-scope file introduces or increases broad excepts."""
    current = current_counts()

    new_files = sorted(set(current) - set(_BASELINE))
    assert not new_files, (
        "New file(s) use `except Exception` / `except BaseException`:\n  "
        + "\n  ".join(f"{f} ({current[f]})" for f in new_files)
        + f"\n\n{_HINT}"
    )

    grew = sorted(
        f"{f}: {current[f]} > baseline {_BASELINE[f]}"
        for f in current
        if f in _BASELINE and current[f] > _BASELINE[f]
    )
    assert not grew, "Broad-except usage increased:\n  " + "\n  ".join(grew) + f"\n\n{_HINT}"


def test_broad_except_baseline_is_not_stale():
    """A converted file must have its entry lowered or removed.

    This is the half that makes the ratchet actually ratchet: without it,
    the baseline drifts upward in effect as code shrinks around it, and a
    later regression hides inside stale headroom.
    """
    current = current_counts()
    stale = sorted(
        f"{f}: baseline {count} but now {current.get(f, 0)} — lower it"
        for f, count in _BASELINE.items()
        if current.get(f, 0) < count
    )
    assert not stale, (
        "Baseline entries are stale (the debt shrank — record it):\n  "
        + "\n  ".join(stale)
        + "\n\nEdit _BASELINE in this file to the new counts."
    )


def test_baseline_covers_only_in_scope_files():
    """Every baseline key must live under a scoped tree (R6 drift guard)."""
    off_scope = sorted(f for f in _BASELINE if not f.startswith(SCOPED_TREES))
    assert (
        not off_scope
    ), "Baseline names file(s) outside the ratified scope " f"{SCOPED_TREES}:\n  " + "\n  ".join(
        off_scope
    )
