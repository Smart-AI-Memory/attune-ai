---
feature: workflows
depth: reference
generated_at: 2026-04-04T02:25:50.273884+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Workflows Reference

## Classes

| Class | Description | File |

|-------|-------------|------|

| `AgentRunResult` | Data extracted from Agent SDK execution. | `src/attune/workflows/agent_sdk_adapter.py` |

| `AgentSDKResultAdapter` | Converts Agent SDK ResultMessage text into a WorkflowResult. | `src/attune/workflows/agent_sdk_adapter.py` |

| `BaseWorkflow` | Base class for multi-model workflows. | `src/attune/workflows/base.py` |

| `BatchRequest` | Single request in a batch. | `src/attune/workflows/batch_processing.py` |

| `BatchResult` | Result from batch processing. | `src/attune/workflows/batch_processing.py` |

| `BatchProcessingWorkflow` | Process multiple tasks via Anthropic Batch API (50% cost savings). | `src/attune/workflows/batch_processing.py` |

| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. | `src/attune/workflows/bug_predict.py` |

| `WorkflowBuilder` | Builder for complex workflow configuration. | `src/attune/workflows/builder.py` |

| `CachedResponse` | Cached LLM response data (retained for interface compatibility). | `src/attune/workflows/caching.py` |

| `CachingMixin` | No-op caching mixin. | `src/attune/workflows/caching.py` |

| `CodeReviewWorkflow` | SDK-native code review with four specialized subagents. | `src/attune/workflows/code_review.py` |

| `ModelTier` | DEPRECATED: Model tier for cost optimization. | `src/attune/workflows/compat.py` |

| `ModelProvider` | DEPRECATED: Supported model providers. | `src/attune/workflows/compat.py` |

| `ModelConfig` | Configuration for a specific model. | `src/attune/workflows/config.py` |

| `WorkflowConfig` | Configuration for workflow model selection and XML prompts. | `src/attune/workflows/config.py` |

| `WorkflowContext` | Container for workflow capability services. | `src/attune/workflows/context.py` |

| `ContextProxyMixin` | Proxy methods that delegate to WorkflowContext services. | `src/attune/workflows/context_proxy_mixin.py` |

| `CoordinationMixin` | Mixin providing agent coordination, adaptive routing, and heartbeat tracking. | `src/attune/workflows/coordination_mixin.py` |

| `CostTrackingMixin` | Mixin providing cost tracking capabilities for workflows. | `src/attune/workflows/cost_mixin.py` |

| `WorkflowStage` | Represents a single stage in a workflow. | `src/attune/workflows/data_classes.py` |

| `CostReport` | Cost breakdown for a workflow execution. | `src/attune/workflows/data_classes.py` |

| `StageQualityMetrics` | Quality metrics for stage output validation. | `src/attune/workflows/data_classes.py` |

| `NextAction` | Contextual suggestion for what to do next after a workflow. | `src/attune/workflows/data_classes.py` |

| `WorkflowResult` | Result of a workflow execution. | `src/attune/workflows/data_classes.py` |

| `DeepReviewAgentSDKWorkflow` | Multi-pass deep code review using Claude Agent SDK subagents. | `src/attune/workflows/deep_review.py` |

| `DependencyCheckWorkflow` | Audit dependencies with Agent SDK subagents. | `src/attune/workflows/dependency_check.py` |

| `DependencyParserMixin` | Mixin providing dependency file parsing methods. | `src/attune/workflows/dependency_check_parsers.py` |

| `CheckResult` | Result of a single documentation audit check. | `src/attune/workflows/doc_audit/checks.py` |

| `DocAuditWorkflow` | Documentation accuracy audit and gap filling workflow. | `src/attune/workflows/doc_audit/workflow.py` |

| `DocOrchFilterMixin` | Mixin providing filtering and validation for documentation orchestrator. | `src/attune/workflows/doc_orch_filters.py` |

| `DocOrchReportMixin` | Mixin providing generation phase and reporting for documentation orchestrator. | `src/attune/workflows/doc_orch_report.py` |

| `DocOrchScoutMixin` | Mixin providing scout phase for documentation orchestrator. | `src/attune/workflows/doc_orch_scout.py` |

| `APIReferenceMixin` | Mixin providing API reference extraction and generation for doc generation. | `src/attune/workflows/document_gen/api_reference.py` |

| `ChunkedGenerationMixin` | Mixin providing chunked generation and display utilities for doc generation. | `src/attune/workflows/document_gen/chunked_generation.py` |

| `DocGenCostMixin` | Mixin providing cost management for document generation. | `src/attune/workflows/document_gen/cost_management.py` |

| `OutlineStageMixin` | Mixin providing the outline generation stage. | `src/attune/workflows/document_gen/outline_stage.py` |

| `PolishStageMixin` | Mixin providing the polish (final review) stage. | `src/attune/workflows/document_gen/polish_stage.py` |

| `DocumentGenerationWorkflow` | Generate new documentation from source code (creation). | `src/attune/workflows/document_gen/workflow.py` |

| `WriteStageMixin` | Mixin providing the write (content generation) stage. | `src/attune/workflows/document_gen/write_stage.py` |

| `DocumentManagerWorkflow` | You are an expert in the creating wide many types of documents. You use program libraries, systems, style guide, and industry best practices, to efficiently create and update documentation for the attune-ai framework. | `src/attune/workflows/document_manager.py` |

| `DocumentationItem` | A single item that needs documentation work. | `src/attune/workflows/documentation_orchestrator.py` |

| `OrchestratorResult` | Result from DocumentationOrchestrator execution. | `src/attune/workflows/documentation_orchestrator.py` |

| `DocumentationOrchestrator` | End-to-end documentation management orchestrator. | `src/attune/workflows/documentation_orchestrator.py` |

| `EscalationChain` | Retry-with-feedback escalation across model tiers. | `src/attune/workflows/escalation/chain.py` |

| `Evaluator` | Base class for LLM-based semantic evaluation. | `src/attune/workflows/escalation/evaluator.py` |

| `SemanticEvaluator` | Uses a lightweight LLM to judge response quality. | `src/attune/workflows/escalation/evaluator.py` |

| `FeedbackType` | What kind of feedback triggered a retry or escalation. | `src/attune/workflows/escalation/models.py` |

| `ValidationFeedback` | Structured feedback from a single validation step. | `src/attune/workflows/escalation/models.py` |

| `AttemptResult` | Result of a single LLM call within the chain. | `src/attune/workflows/escalation/models.py` |

| `EscalationResult` | Final result of running the EscalationChain. | `src/attune/workflows/escalation/models.py` |

| `Validator` | Protocol for rule-based response validators. | `src/attune/workflows/escalation/validators.py` |

| `StructureValidator` | Check that all required fields are present in the response dict. | `src/attune/workflows/escalation/validators.py` |

| `ConfidenceValidator` | Check that the response confidence meets a minimum threshold. | `src/attune/workflows/escalation/validators.py` |

| `ExecutionMixin` | Mixin providing the main workflow execution method. | `src/attune/workflows/execution_mixin.py` |

| `ExecutorMixin` | Mixin providing LLMExecutor integration methods. | `src/attune/workflows/executor_mixin.py` |

| `CategoryScore` | Individual category health score. | `src/attune/workflows/health_check_models.py` |

| `HealthCheckReport` | Comprehensive health check report. | `src/attune/workflows/health_check_models.py` |

| `HelpMaintenanceWorkflow` | Maintain the help knowledge base automatically. | `src/attune/workflows/help_maintenance.py` |

| `WorkflowHistoryStore` | SQLite-backed workflow history with migrations. | `src/attune/workflows/history.py` |

| `LLMMixin` | Mixin providing LLM calling, output validation, and complexity assessment. | `src/attune/workflows/llm_mixin.py` |

| `MigrationConfig` | Configuration for workflow migration behavior. | `src/attune/workflows/migration.py` |

| `MultiAgentStageMixin` | Mixin enabling workflow stages to delegate to multi-agent teams. | `src/attune/workflows/multi_agent_mixin.py` |

| `OrchestratedHealthCheckWorkflow` | Health check workflow using meta-orchestration. | `src/attune/workflows/orchestrated_health_check.py` |

| `QualityGate` | Quality gate threshold for release readiness. | `src/attune/workflows/orchestrated_release_prep.py` |

| `ReleaseReadinessReport` | Consolidated release readiness assessment. | `src/attune/workflows/orchestrated_release_prep.py` |

| `OrchestratedReleasePrepWorkflow` | Release preparation workflow using meta-orchestration. | `src/attune/workflows/orchestrated_release_prep.py` |

| `Finding` | Individual finding from a workflow. | `src/attune/workflows/output.py` |

| `ReportSection` | Individual section of a workflow report. | `src/attune/workflows/output.py` |

| `WorkflowReport` | Main workflow report container. | `src/attune/workflows/output.py` |

| `FindingsTable` | Render a list of Finding objects as a Rich Table or plain text. | `src/attune/workflows/output.py` |

| `MetricsPanel` | Display score with color-coded indicator. | `src/attune/workflows/output.py` |

| `ResponseParsingMixin` | Mixin providing response parsing capabilities for workflows. | `src/attune/workflows/parsing_mixin.py` |

| `PerformanceAuditWorkflow` | SDK-native performance audit with three specialized subagents. | `src/attune/workflows/perf_audit.py` |

| `PostSimplificationMixin` | Mixin providing optional post-execution code simplification. | `src/attune/workflows/post_simplification_mixin.py` |

| `ProgressTracker` | Tracks and broadcasts workflow progress. | `src/attune/workflows/progress.py` |

| `ProgressStatus` | Status of a workflow or stage. | `src/attune/workflows/progress_models.py` |

| `StageProgress` | Progress information for a single stage. | `src/attune/workflows/progress_models.py` |

| `ProgressUpdate` | A progress update to be broadcast. | `src/attune/workflows/progress_models.py` |

| `ProgressReporter` | Protocol for progress reporting implementations. | `src/attune/workflows/progress_reporters.py` |

| `ConsoleProgressReporter` | Console-based progress reporter optimized for IDE environments. | `src/attune/workflows/progress_reporters.py` |

| `JsonLinesProgressReporter` | JSON Lines progress reporter for machine parsing. | `src/attune/workflows/progress_reporters.py` |

| `RichProgressReporter` | Rich-based live progress display with spinner, progress bar, and metrics. | `src/attune/workflows/progress_reporters.py` |

| `ProgressServerConfig` | Configuration for the progress WebSocket server. | `src/attune/workflows/progress_server.py` |

| `ProgressServer` | WebSocket server for broadcasting workflow progress. | `src/attune/workflows/progress_server.py` |

| `Tier` | Model tier levels for progressive escalation. | `src/attune/workflows/progressive/core.py` |

| `FailureAnalysis` | Multi-signal failure detection and quality analysis. | `src/attune/workflows/progressive/core.py` |

| `TierResult` | Results from a single tier execution attempt. | `src/attune/workflows/progressive/core.py` |

| `ProgressiveWorkflowResult` | Complete results from a progressive workflow execution. | `src/attune/workflows/progressive/core.py` |

| `EscalationConfig` | Configuration for progressive tier escalation. | `src/attune/workflows/progressive/core.py` |

| `MetaOrchestrator` | Meta-agent that orchestrates progressive tier decisions. | `src/attune/workflows/progressive/orchestrator.py` |

| `TierPromptMixin` | Mixin providing tier-specific prompt building methods. | `src/attune/workflows/progressive/orchestrator_prompts.py` |

| `ProgressiveTelemetry` | Telemetry tracker for progressive workflows. | `src/attune/workflows/progressive/telemetry.py` |

| `ProgressiveTestGenWorkflow` | Test generation workflow with progressive tier escalation. | `src/attune/workflows/progressive/test_gen.py` |

| `BudgetExceededError` | Raised when execution cost exceeds configured budget. | `src/attune/workflows/progressive/workflow.py` |

| `UserCancelledError` | Raised when user cancels execution during approval prompt. | `src/attune/workflows/progressive/workflow.py` |

| `ProgressiveWorkflow` | Base class for workflows with progressive tier escalation. | `src/attune/workflows/progressive/workflow.py` |

| `PromptMixin` | Mixin providing prompt building and rendering methods. | `src/attune/workflows/prompt_mixin.py` |

| `RefactorPlanWorkflow` | Prioritize tech debt with Agent SDK subagents. | `src/attune/workflows/refactor_plan.py` |

| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents. | `src/attune/workflows/release_prep.py` |

| `ResearchSynthesisWorkflow` | Multi-source research synthesis with Agent SDK subagents. | `src/attune/workflows/research_synthesis.py` |

| `RoutingContext` | Context information for routing decisions. | `src/attune/workflows/routing.py` |

| `TierRoutingStrategy` | Abstract base class for tier routing strategies. | `src/attune/workflows/routing.py` |

| `CostOptimizedRouting` | Route to cheapest tier that can handle the task. | `src/attune/workflows/routing.py` |

| `PerformanceOptimizedRouting` | Route to fastest tier regardless of cost. | `src/attune/workflows/routing.py` |

| `BalancedRouting` | Balance cost and performance with budget awareness. | `src/attune/workflows/routing.py` |

| `SecureReleaseResult` | Result from SecureReleasePipeline execution. | `src/attune/workflows/secure_release.py` |

| `SecureReleasePipeline` | Comprehensive security pipeline for release preparation. | `src/attune/workflows/secure_release.py` |

| `SecurityAuditWorkflow` | SDK-native security audit with four specialized subagents. | `src/attune/workflows/security_audit.py` |

| `CacheService` | No-op cache service. | `src/attune/workflows/services/cache_service.py` |

| `CoordinationService` | Service for inter-agent coordination. | `src/attune/workflows/services/coordination_service.py` |

| `CostService` | Service for calculating and reporting workflow costs. | `src/attune/workflows/services/cost_service.py` |

| `ParsingService` | Service for parsing structured data from LLM responses. | `src/attune/workflows/services/parsing_service.py` |

| `PromptService` | Service for building and rendering prompts. | `src/attune/workflows/services/prompt_service.py` |

| `TelemetryService` | Service for tracking workflow telemetry. | `src/attune/workflows/services/telemetry_service.py` |

| `TierService` | Service for selecting model tiers for workflow stages. | `src/attune/workflows/services/tier_service.py` |

| `SimplifyCodeWorkflow` | Simplify over-engineered code with Agent SDK subagents. | `src/attune/workflows/simplify_code.py` |

| `StatePersistenceMixin` | Mixin providing state persistence for workflow execution. | `src/attune/workflows/state_mixin.py` |

| `WorkflowStepConfig` | Configuration for a single workflow step. | `src/attune/workflows/step_config.py` |

| `TelemetryMixin` | Mixin that provides telemetry tracking for workflow LLM calls. | `src/attune/workflows/telemetry_mixin.py` |

| `ModuleCoverage` | Coverage data for a single module. | `src/attune/workflows/test_audit/coverage_parser.py` |

| `TestAuditWorkflow` | Autonomous test coverage audit with Agent SDK subagents. | `src/attune/workflows/test_audit/workflow.py` |

| `ASTFunctionAnalyzer` | AST-based function analyzer for accurate test generation. | `src/attune/workflows/test_gen/ast_analyzer.py` |

| `FunctionSignature` | Detailed function analysis for test generation. | `src/attune/workflows/test_gen/data_models.py` |

| `ClassSignature` | Detailed class analysis for test generation. | `src/attune/workflows/test_gen/data_models.py` |

| `TestGenerationWorkflow` | SDK-native test generation with three specialized subagents. | `src/attune/workflows/test_gen/workflow.py` |

| `TestGenerationTask` | Tracks the state of a single test generation task. | `src/attune/workflows/test_gen_parallel.py` |

| `ParallelTestGenerationWorkflow` | Generate and complete behavioral tests in parallel using multi-tier LLMs. | `src/attune/workflows/test_gen_parallel.py` |

| `TestTask` | A queued test management task. | `src/attune/workflows/test_lifecycle.py` |

| `TestLifecycleManager` | Manages the lifecycle of tests based on source file events. | `src/attune/workflows/test_lifecycle.py` |

| `TestAction` | Actions that can be taken for test management. | `src/attune/workflows/test_maintenance.py` |

| `TestPriority` | Priority levels for test actions. | `src/attune/workflows/test_maintenance.py` |

| `TestPlanItem` | A single item in a test maintenance plan. | `src/attune/workflows/test_maintenance.py` |

| `TestMaintenancePlan` | Complete test maintenance plan for a project. | `src/attune/workflows/test_maintenance.py` |

| `TestMaintenanceWorkflow` | Workflow for automatic test lifecycle management. | `src/attune/workflows/test_maintenance.py` |

| `TierRoutingMixin` | Mixin providing tier routing logic for workflow stages. | `src/attune/workflows/tier_routing_mixin.py` |

| `TierAttempt` | Record of a single tier attempt. | `src/attune/workflows/tier_tracking.py` |

| `WorkflowTierProgression` | Track tier progression for a workflow run. | `src/attune/workflows/tier_tracking.py` |

| `WorkflowTierTracker` | Automatically track tier progression for workflow runs. | `src/attune/workflows/tier_tracking.py` |

| `WorkflowValidationError` | Raised when workflow input or stage output fails validation. | `src/attune/workflows/validation.py` |

| `InputSchema` | Schema for validating workflow input kwargs. | `src/attune/workflows/validation.py` |

| `StageContract` | Schema for validating stage output. | `src/attune/workflows/validation.py` |

| `WorkflowSpec` | Specification for a single workflow in a batch. | `src/attune/workflows/workflow_batch_runner.py` |

| `WorkflowBatchResult` | Result from a single workflow execution in a batch. | `src/attune/workflows/workflow_batch_runner.py` |

| `BatchRunReport` | Aggregated report from a batch run. | `src/attune/workflows/workflow_batch_runner.py` |

| `WorkflowBatchRunner` | Orchestrates multiple workflow executions with cost tracking. | `src/attune/workflows/workflow_batch_runner.py` |


## Functions

| Function | Description | File |

|----------|-------------|------|

| `discover_workflows()` | Discover workflows via entry points and config. | `src/attune/workflows/__init__.py` |

| `refresh_workflow_registry()` | Refresh the global WORKFLOW_REGISTRY by re-discovering all workflows. | `src/attune/workflows/__init__.py` |

| `get_opt_in_workflows()` | Get the list of opt-in workflows that require explicit enabling. | `src/attune/workflows/__init__.py` |

| `get_workflow()` | Get a workflow class by name, routing to SDK variant automatically. | `src/attune/workflows/__init__.py` |

| `list_workflows()` | List available workflows with descriptions. | `src/attune/workflows/__init__.py` |

| `collect_agent_output()` | Extract text and metadata from a single SDK message. | `src/attune/workflows/agent_sdk_adapter.py` |

| `build_result_text()` | Combine collected text into the final result string. | `src/attune/workflows/agent_sdk_adapter.py` |

| `get_max_budget_usd()` | Get budget cap for a workflow depth. | `src/attune/workflows/agent_sdk_adapter.py` |

| `get_subagent_model()` | Get model for a subagent based on role keywords. | `src/attune/workflows/agent_sdk_adapter.py` |

| `estimate_tokens()` | Rough token estimate: ~4 characters per token. | `src/attune/workflows/base.py` |

| `format_bug_predict_report()` | Format bug prediction output as a human-readable report. | `src/attune/workflows/bug_predict_report.py` |

| `main()` | CLI entry point for bug prediction workflow. | `src/attune/workflows/bug_predict_report.py` |

| `workflow_builder()` | Factory function for creating workflow builders. | `src/attune/workflows/builder.py` |

| `get_model()` | Get the model name for a provider/tier combination. | `src/attune/workflows/config.py` |

| `create_example_config()` | Generate an example configuration file content. | `src/attune/workflows/config.py` |

| `format_dependency_check_report()` | Format dependency check output as a human-readable report. | `src/attune/workflows/dependency_check_report.py` |

| `main()` | CLI entry point for dependency check workflow. | `src/attune/workflows/dependency_check_report.py` |

| `check_test_count()` | Verify test count badge in README matches actual pytest count. | `src/attune/workflows/doc_audit/checks.py` |

| `check_workflow_count()` | Verify workflow count in docs matches registered workflows. | `src/attune/workflows/doc_audit/checks.py` |

| `check_skill_count()` | Verify skill count in docs matches .claude/commands/ files. | `src/attune/workflows/doc_audit/checks.py` |

| `check_mcp_tool_count()` | Verify MCP tool count in docs matches actual registered tools. | `src/attune/workflows/doc_audit/checks.py` |

| `check_file_line_limits()` | Verify no Python file in src/ exceeds 1000 lines. | `src/attune/workflows/doc_audit/checks.py` |

| `check_install_extras()` | Verify install extras match between pyproject.toml and README. | `src/attune/workflows/doc_audit/checks.py` |

| `check_stale_references()` | Detect references to removed or deprecated features in docs. | `src/attune/workflows/doc_audit/checks.py` |

| `check_version_consistency()` | Verify version is consistent across pyproject.toml, __init__.py, CHANGELOG.md. | `src/attune/workflows/doc_audit/checks.py` |

| `check_cross_doc_numbers()` | Detect contradictory numeric claims across documentation. | `src/attune/workflows/doc_audit/checks.py` |

| `check_documentation_links()` | Verify local links in markdown files resolve to existing files. | `src/attune/workflows/doc_audit/checks.py` |

| `run_all_checks()` | Run all 10 documentation audit checks in sequence. | `src/attune/workflows/doc_audit/checks.py` |

| `format_doc_gen_report()` | Format document generation output as a human-readable report. | `src/attune/workflows/document_gen/report_formatter.py` |

| `calculate_category_scores()` | Calculate health scores for each category. | `src/attune/workflows/health_check_scoring.py` |

| `calculate_overall_score()` | Calculate weighted overall health score. | `src/attune/workflows/health_check_scoring.py` |

| `assign_grade()` | Assign letter grade based on score. | `src/attune/workflows/health_check_scoring.py` |

| `generate_recommendations()` | Generate actionable recommendations with specific commands. | `src/attune/workflows/health_check_scoring.py` |

| `get_trend_comparison()` | Compare current score with last check. | `src/attune/workflows/health_check_tracking.py` |

| `save_tracking_history()` | Save health check report to tracking history. | `src/attune/workflows/health_check_tracking.py` |

| `save_health_json()` | Save health check report to .attune/health.json. | `src/attune/workflows/health_check_tracking.py` |

| `get_workflow_stats()` | Get workflow statistics. | `src/attune/workflows/history_utils.py` |

| `is_interactive()` | Check if we're running in an interactive terminal. | `src/attune/workflows/migration.py` |

| `show_migration_dialog()` | Show interactive migration dialog to user. | `src/attune/workflows/migration.py` |

| `show_removed_workflow_error()` | Show error for removed workflows with migration guidance. | `src/attune/workflows/migration.py` |

| `show_deprecation_warning()` | Show deprecation warning via logger (non-blocking). | `src/attune/workflows/migration.py` |

| `resolve_workflow_migration()` | Resolve a workflow name, handling migrations as needed. | `src/attune/workflows/migration.py` |

| `show_migration_tip()` | Show a migration tip after workflow completion. | `src/attune/workflows/migration.py` |

| `get_canonical_workflow_name()` | Get the canonical (new) name for a workflow. | `src/attune/workflows/migration.py` |

| `list_migrations()` | List all workflow migrations for documentation. | `src/attune/workflows/migration.py` |

| `format_workflow_result()` | Create a standardized workflow report. | `src/attune/workflows/output.py` |

| `get_console()` | Get Rich Console if available. | `src/attune/workflows/output.py` |

| `main()` | CLI entry point for performance audit workflow. | `src/attune/workflows/perf_audit.py` |

| `create_progress_tracker()` | Factory function to create a progress tracker with optional reporter. | `src/attune/workflows/progress.py` |

| `live_progress()` | Context manager for live progress display during workflow execution. | `src/attune/workflows/progress_reporters.py` |

| `get_progress_server()` | Get or create the global progress server instance. | `src/attune/workflows/progress_server.py` |

| `cmd_list_results()` | List all saved progressive workflow results. | `src/attune/workflows/progressive/cli.py` |

| `cmd_show_report()` | Show detailed report for a specific task. | `src/attune/workflows/progressive/cli.py` |

| `cmd_analytics()` | Show cost optimization analytics. | `src/attune/workflows/progressive/cli.py` |

| `cmd_cleanup()` | Clean up old progressive workflow results. | `src/attune/workflows/progressive/cli.py` |

| `create_parser()` | Create argument parser for progressive CLI. | `src/attune/workflows/progressive/cli.py` |

| `main()` | Main entry point for progressive CLI. | `src/attune/workflows/progressive/cli.py` |

| `generate_progression_report()` | Generate human-readable progression report. | `src/attune/workflows/progressive/reports.py` |

| `save_results_to_disk()` | Save detailed results to disk. | `src/attune/workflows/progressive/reports.py` |

| `load_result_from_disk()` | Load saved result from disk. | `src/attune/workflows/progressive/reports.py` |

| `list_saved_results()` | List all saved progressive results. | `src/attune/workflows/progressive/reports.py` |

| `cleanup_old_results()` | Clean up old progressive workflow results. | `src/attune/workflows/progressive/reports.py` |

| `generate_cost_analytics()` | Generate cost optimization analytics from saved results. | `src/attune/workflows/progressive/reports.py` |

| `format_cost_analytics_report()` | Format cost analytics as human-readable report. | `src/attune/workflows/progressive/reports.py` |

| `execute_test_file()` | Execute a test file using pytest. | `src/attune/workflows/progressive/test_gen.py` |

| `calculate_coverage()` | Calculate code coverage for a test file. | `src/attune/workflows/progressive/test_gen.py` |

| `format_refactor_plan_report()` | Format refactor plan output as a human-readable report. | `src/attune/workflows/refactor_plan_report.py` |

| `main()` | CLI entry point for refactor planning workflow. | `src/attune/workflows/refactor_plan_report.py` |

| `format_secure_release_report()` | Format secure release result as a human-readable report. | `src/attune/workflows/secure_release.py` |

| `validate_step_config()` | Validate a step configuration. | `src/attune/workflows/step_config.py` |

| `steps_from_tier_map()` | Convert legacy stages/tier_map to WorkflowStepConfig list. | `src/attune/workflows/step_config.py` |

| `record_suggestions_shown()` | Record that suggestions were shown to avoid repeats. | `src/attune/workflows/suggestions.py` |

| `generate_suggestions()` | Generate contextual next-step suggestions after workflow completion. | `src/attune/workflows/suggestions.py` |

| `format_suggestions_markdown()` | Format suggestions as markdown for Claude Code skill output. | `src/attune/workflows/suggestions.py` |

| `suggestions_to_options()` | Convert suggestions to AskUserQuestion option format. | `src/attune/workflows/suggestions.py` |

| `parse_coverage_json()` | Parse pytest-cov's coverage.json output. | `src/attune/workflows/test_audit/coverage_parser.py` |

| `prioritize_modules()` | Sort modules by priority and filter below threshold. | `src/attune/workflows/test_audit/coverage_parser.py` |

| `group_into_batches()` | Group modules into batches by subsystem (package path). | `src/attune/workflows/test_audit/coverage_parser.py` |

| `format_test_gen_report()` | Format test generation output as a human-readable report. | `src/attune/workflows/test_gen/report_formatter.py` |

| `generate_test_for_function()` | Generate executable tests for a function based on AST analysis. | `src/attune/workflows/test_gen/test_templates.py` |

| `generate_test_cases_for_params()` | Generate test cases based on parameter types. | `src/attune/workflows/test_gen/test_templates.py` |

| `get_type_assertion()` | Generate assertion for return type checking. | `src/attune/workflows/test_gen/test_templates.py` |

| `get_param_test_values()` | Get test values for a single parameter based on its type. | `src/attune/workflows/test_gen/test_templates.py` |

| `generate_test_for_class()` | Generate executable test class based on AST analysis. | `src/attune/workflows/test_gen/test_templates.py` |

| `main()` | CLI entry point for test generation workflow. | `src/attune/workflows/test_gen/workflow.py` |

| `main()` | Main CLI entry point. | `src/attune/workflows/test_maintenance_cli.py` |

| `run_tests_with_tracking()` | Run tests with explicit tracking (opt-in for Tier 1 monitoring). | `src/attune/workflows/test_runner.py` |

| `track_coverage()` | Track test coverage from coverage.xml file (opt-in for Tier 1 monitoring). | `src/attune/workflows/test_runner.py` |

| `track_file_tests()` | Track test execution for a specific source file. | `src/attune/workflows/test_runner.py` |

| `get_file_test_status()` | Get the latest test status for a specific file. | `src/attune/workflows/test_runner.py` |

| `get_files_needing_tests()` | Get files that need test attention. | `src/attune/workflows/test_runner.py` |

| `auto_recommend_tier()` | Quick helper to get tier recommendation without tracker. | `src/attune/workflows/tier_tracking.py` |

| `validate_against_input_schema()` | Validate a data dict against an InputSchema. | `src/attune/workflows/validation.py` |

| `validate_against_contract()` | Validate a stage output dict against a StageContract. | `src/attune/workflows/validation.py` |


## Source Files

- `src/attune/workflows/**`


## Tags

`workflows`, `ai`, `analysis`
