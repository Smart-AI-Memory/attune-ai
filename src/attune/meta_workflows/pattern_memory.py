"""Memory integration mixin for pattern learner.

Provides enhanced querying via UnifiedMemory storage,
enabling semantic search across historical executions.

Created: 2026-01-17
"""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from attune.meta_workflows.workflow import list_execution_results, load_execution_result

if TYPE_CHECKING:
    from attune.meta_workflows.models import FormResponse
    from attune.meta_workflows.workflow import MetaWorkflowResult

logger = logging.getLogger(__name__)


class PatternMemoryMixin:
    """Memory integration for the pattern learner.

    Provides methods for storing and querying executions
    via UnifiedMemory for rich semantic search.

    Requires the host class to provide:
    - ``self.memory``: UnifiedMemory | None
    - ``self.executions_dir``: Path
    - ``self.get_recommendations()``: base recommendations method
    """

    def store_execution_in_memory(self, result: "MetaWorkflowResult") -> str | None:
        """Store execution result in memory for semantic querying.

        This stores execution insights in long-term memory IN ADDITION to
        file-based storage. Memory enables rich semantic queries like:
        - "Find workflows that succeeded with test coverage >80%"
        - "Show me all workflows that used progressive tier escalation"

        Args:
            result: MetaWorkflowResult to store

        Returns:
            Pattern ID if stored successfully, None otherwise

        """
        if not self.memory:
            logger.debug("Memory not available, skipping memory storage")
            return None

        try:
            tier_counts: dict[str, int] = defaultdict(int)
            for agent_result in result.agent_results:
                tier_counts[agent_result.tier_used] += 1

            metadata = {
                "run_id": result.run_id,
                "template_id": result.template_id,
                "success": result.success,
                "total_cost": result.total_cost,
                "total_duration": result.total_duration,
                "agents_created": len(result.agents_created),
                "agents_succeeded": sum(1 for a in result.agent_results if a.success),
                "tier_distribution": dict(tier_counts),
                "form_responses": result.form_responses.responses,
                "timestamp": result.timestamp,
                "error": result.error,
            }

            content = f"""Meta-workflow execution: {result.template_id}
Run ID: {result.run_id}
Status: {"SUCCESS" if result.success else "FAILED"}
Agents created: {len(result.agents_created)}
Total cost: ${result.total_cost:.2f}
Duration: {result.total_duration:.1f}s

Agents:
{self._format_agents_for_content(result)}

Form Responses:
{self._format_responses_for_content(result.form_responses.responses)}
"""

            storage_result = self.memory.persist_pattern(
                content=content,
                pattern_type="meta_workflow_execution",
                classification="INTERNAL",
                auto_classify=False,
                metadata=metadata,
            )

            if storage_result:
                pattern_id = storage_result.get("pattern_id")
                logger.info(
                    f"Execution stored in memory: {pattern_id}",
                    extra={
                        "run_id": result.run_id,
                        "template_id": result.template_id,
                    },
                )
                return pattern_id

            return None

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to store execution in memory: {e}")
            return None

    def _format_agents_for_content(self, result: "MetaWorkflowResult") -> str:
        """Format agents for searchable content."""
        lines = []
        for agent_result in result.agent_results:
            status = "ok" if agent_result.success else "fail"
            lines.append(
                f"- {status} {agent_result.role} (tier: {agent_result.tier_used}, "
                f"cost: ${agent_result.cost:.2f})",
            )
        return "\n".join(lines)

    def _format_responses_for_content(self, responses: dict) -> str:
        """Format form responses for searchable content."""
        lines = []
        for key, value in responses.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def search_executions_by_context(
        self,
        query: str,
        template_id: str | None = None,
        limit: int = 10,
    ) -> list["MetaWorkflowResult"]:
        """Search executions using semantic memory queries.

        This provides richer querying than file-based search:
        - Natural language queries
        - Semantic similarity matching
        - Cross-template pattern recognition

        Args:
            query: Natural language search query
            template_id: Optional filter by template
            limit: Maximum results to return

        Returns:
            List of matching MetaWorkflowResult objects

        """
        if not self.memory:
            logger.warning("Memory not available, falling back to file-based search")
            return self._search_executions_files(query, template_id, limit)

        try:
            patterns = self.memory.search_patterns(
                query=query,
                pattern_type="meta_workflow_execution",
                limit=limit,
            )

            results = []
            for pattern in patterns:
                metadata = pattern.get("metadata", {})
                run_id = metadata.get("run_id")

                if run_id:
                    if template_id and metadata.get("template_id") != template_id:
                        continue

                    try:
                        result = load_execution_result(run_id, storage_dir=str(self.executions_dir))
                        results.append(result)
                    except FileNotFoundError:
                        logger.warning(f"Result file not found for run_id: {run_id}")
                        continue

            return results

        except Exception as e:  # noqa: BLE001
            logger.error(f"Memory search failed: {e}")
            return self._search_executions_files(query, template_id, limit)

    def _search_executions_files(
        self,
        query: str,
        template_id: str | None,
        limit: int,
    ) -> list["MetaWorkflowResult"]:
        """Fallback file-based search when memory is unavailable."""
        results = []
        run_ids = list_execution_results(storage_dir=str(self.executions_dir))

        for run_id in run_ids[:limit]:
            try:
                result = load_execution_result(run_id, storage_dir=str(self.executions_dir))

                if template_id and result.template_id != template_id:
                    continue

                result_json = result.to_json().lower()
                if query.lower() in result_json:
                    results.append(result)

            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to load result {run_id}: {e}")
                continue

        return results[:limit]

    def get_smart_recommendations(
        self,
        template_id: str,
        form_response: "FormResponse | None" = None,
        min_confidence: float = 0.7,
    ) -> list[str]:
        """Get context-aware recommendations enhanced by memory.

        Combines statistical pattern analysis with semantic memory queries
        to provide more intelligent recommendations.

        Args:
            template_id: Template ID to get recommendations for
            form_response: Optional form responses for context-aware suggestions
            min_confidence: Minimum confidence threshold

        Returns:
            List of recommendation strings

        """
        base_recs = self.get_recommendations(template_id, min_confidence)

        if not self.memory or not form_response:
            return base_recs

        try:
            query = f"Successful workflows for {template_id}"
            if form_response:
                key_responses = []
                for key, value in form_response.responses.items():
                    key_responses.append(f"{key}={value}")
                query += f" with {', '.join(key_responses[:3])}"

            similar_executions = self.search_executions_by_context(
                query=query,
                template_id=template_id,
                limit=5,
            )

            if similar_executions:
                success_rate = sum(1 for e in similar_executions if e.success) / len(
                    similar_executions,
                )

                if success_rate >= 0.8:
                    base_recs.insert(
                        0,
                        f"{len(similar_executions)} similar workflows found "
                        f"with {success_rate:.0%} success rate",
                    )

                tier_usage: dict[str, int] = defaultdict(int)
                for execution in similar_executions:
                    for agent_result in execution.agent_results:
                        tier_usage[agent_result.tier_used] += 1

                if tier_usage:
                    most_common_tier = max(tier_usage.items(), key=lambda x: x[1])[0]
                    base_recs.append(f"Similar workflows typically use '{most_common_tier}' tier")

        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to enhance recommendations with memory: {e}")

        return base_recs
