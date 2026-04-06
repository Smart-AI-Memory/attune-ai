---
feature: workflows
depth: reference
generated_at: 2026-04-06T02:39:14.545548+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Workflows reference

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
| `CacheService` | No-op cache service. | `src/attune/workflows/services/cache_
