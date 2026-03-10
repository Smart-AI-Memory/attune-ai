"""Workflow-to-Agent adapter for DynamicTeam composition.

Wraps a ``BaseWorkflow`` subclass so that it can participate in
``DynamicTeam`` orchestration alongside ``SDKAgent`` instances.

``process()`` bridges the async/sync boundary using ``asyncio.run()``
in a thread -- the same pattern used by ``DynamicTeam._execute_parallel()``.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
from typing import Any
from uuid import uuid4

from attune.agents.sdk.sdk_models import SDKAgentResult

logger = logging.getLogger(__name__)


class WorkflowAgentAdapter:
    """Adapts a BaseWorkflow to the ``SDKAgent.process()`` interface.

    Allows workflows to participate in ``DynamicTeam`` compositions.
    ``process()`` calls ``workflow.execute()`` and converts
    ``WorkflowResult`` to ``SDKAgentResult``.

    Args:
        workflow_class: BaseWorkflow subclass to wrap.
        workflow_kwargs: Keyword arguments forwarded to the workflow constructor.
        agent_id: Optional agent identifier. Auto-generated if ``None``.
        role: Human-readable role name. Defaults to the workflow's ``name``.
        state_store: Optional ``AgentStateStore`` forwarded to the workflow.

    """

    def __init__(
        self,
        workflow_class: type,
        workflow_kwargs: dict[str, Any] | None = None,
        agent_id: str | None = None,
        role: str | None = None,
        state_store: Any | None = None,
    ) -> None:
        """Initialize WorkflowAgentAdapter wrapping a BaseWorkflow class.

        Args:
            workflow_class: The BaseWorkflow subclass to wrap.
            workflow_kwargs: Optional kwargs for the workflow constructor.
            agent_id: Optional agent identifier. Auto-generated if None.
            role: Human-readable role name. Defaults to the workflow's name.
            state_store: Optional AgentStateStore forwarded to the workflow.

        """
        self.workflow_class = workflow_class
        self.workflow_kwargs = workflow_kwargs or {}
        self.agent_id = agent_id or f"wf-adapter-{uuid4().hex[:8]}"
        self.role: str = role or getattr(workflow_class, "name", "workflow")
        self.state_store = state_store

    def process(self, input_data: dict[str, Any]) -> SDKAgentResult:
        """Execute the wrapped workflow and return an ``SDKAgentResult``.

        Bridges async/sync boundary using ``asyncio.run()`` -- identical
        to the pattern in ``DynamicTeam._execute_parallel()``.

        Args:
            input_data: Structured input forwarded to ``workflow.execute()``.

        Returns:
            ``SDKAgentResult`` with workflow findings and metadata.

        """
        start = time.time()

        # Build workflow instance with forwarded kwargs + state_store
        kwargs = dict(self.workflow_kwargs)
        if self.state_store is not None:
            kwargs["state_store"] = self.state_store

        workflow = self.workflow_class(**kwargs)

        # Execute the async workflow in a sync context.
        # When called from DynamicTeam._execute_sequential() an event loop
        # is already running, so asyncio.run() would fail.  In that case
        # we offload to a thread (same pattern as _execute_parallel).
        try:
            try:
                asyncio.get_running_loop()
                # Already inside a loop - run in a separate thread
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    result = pool.submit(asyncio.run, workflow.execute(**input_data)).result()
            except RuntimeError:
                # No running loop - safe to call asyncio.run() directly
                result = asyncio.run(workflow.execute(**input_data))
        except Exception as e:  # noqa: BLE001
            logger.error("WorkflowAgentAdapter: %s failed: %s", self.role, e)
            return SDKAgentResult(
                agent_id=self.agent_id,
                role=self.role,
                success=False,
                findings={"error": str(e)},
                score=0.0,
                cost=0.0,
                execution_time_ms=(time.time() - start) * 1000,
                error=str(e),
            )

        execution_time_ms = (time.time() - start) * 1000

        # Convert WorkflowResult -> SDKAgentResult
        total_cost = result.cost_report.total_cost if result.cost_report else 0.0
        findings = self._extract_findings(result)

        return SDKAgentResult(
            agent_id=self.agent_id,
            role=self.role,
            success=result.success,
            findings=findings,
            score=self._calculate_score(result),
            cost=total_cost,
            execution_time_ms=execution_time_ms,
            error=result.error,
        )

    def _extract_findings(self, result: Any) -> dict[str, Any]:
        """Extract structured findings from a WorkflowResult.

        Args:
            result: WorkflowResult from workflow execution.

        Returns:
            Dict of findings suitable for SDKAgentResult.

        """
        findings: dict[str, Any] = {
            "workflow_name": getattr(self.workflow_class, "name", "unknown"),
            "success": result.success,
            "stage_count": len(result.stages),
            "total_duration_ms": result.total_duration_ms,
        }

        if result.final_output is not None:
            findings["final_output"] = result.final_output

        if result.stages:
            findings["stages"] = [
                {
                    "name": s.name,
                    "tier": s.tier.value if hasattr(s.tier, "value") else str(s.tier),
                    "cost": s.cost,
                    "duration_ms": s.duration_ms,
                    "skipped": s.skipped,
                }
                for s in result.stages
            ]

        if result.error:
            findings["error"] = result.error

        return findings

    def _calculate_score(self, result: Any) -> float:
        """Calculate a quality score from a WorkflowResult.

        Args:
            result: WorkflowResult from workflow execution.

        Returns:
            Quality score (0-100).

        """
        if not result.success:
            return 0.0

        # Base score for successful completion
        score = 80.0

        # Bonus for completing all stages without skips
        if result.stages:
            completed = sum(1 for s in result.stages if not s.skipped)
            completion_ratio = completed / len(result.stages) if result.stages else 0
            score += completion_ratio * 20.0

        return min(score, 100.0)
