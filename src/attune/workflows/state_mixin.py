"""State Persistence Mixin for BaseWorkflow.

Extracted as a mixin for maintainability.  Integrates
``AgentStateStore`` into the workflow execution loop to record
stage-level lifecycle events and save checkpoints for recovery.

When ``self._state_store`` is ``None`` every method is a no-op,
making the mixin completely backwards-compatible.

Expected attributes on the host class:
    name (str): Workflow name
    _state_store (AgentStateStore | None): State store instance
    _agent_id (str | None): Agent identifier (set during execute())
    _run_id (str): Execution run ID (set during execute())

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class StatePersistenceMixin:
    """Mixin providing state persistence for workflow execution.

    All public methods silently no-op when ``_state_store`` is ``None``.
    All state store calls are wrapped in ``try/except`` so that a
    persistence error never crashes the host workflow.
    """

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    _state_store: Any  # AgentStateStore | None
    _agent_id: str | None
    _run_id: str

    # Internal tracking set per-execution
    _state_exec_id: str | None
    _state_completed_stages: list[str]
    _state_stage_costs: dict[str, float]
    _state_last_output: Any

    # ------------------------------------------------------------------
    # Workflow lifecycle
    # ------------------------------------------------------------------

    def _state_record_workflow_start(self) -> str | None:
        """Record workflow execution start in the state store.

        Returns:
            execution_id for later completion/failure recording, or
            ``None`` when persistence is disabled.

        """
        if self._state_store is None:
            return None

        try:
            exec_id = self._state_store.record_start(
                agent_id=self._agent_id or f"{self.name}-unknown",
                role=f"workflow:{self.name}",
                input_summary=f"run_id={self._run_id}",
            )
            self._state_exec_id = exec_id
            self._state_completed_stages = []
            self._state_stage_costs = {}
            self._state_last_output = None
            return exec_id
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: State persistence is best-effort; must not crash workflow
            logger.debug("State persistence: failed to record workflow start: %s", e)
            return None

    def _state_record_workflow_complete(
        self,
        success: bool,
        total_cost: float,
        execution_time_ms: float,
        error: str | None = None,
    ) -> None:
        """Record workflow completion or failure in the state store.

        Args:
            success: Whether the workflow succeeded.
            total_cost: Total LLM cost in USD.
            execution_time_ms: Wall-clock time for the full run.
            error: Error message if the workflow failed.

        """
        if self._state_store is None:
            return

        exec_id = getattr(self, "_state_exec_id", None)
        agent_id = self._agent_id or f"{self.name}-unknown"

        try:
            if exec_id is not None:
                if success:
                    self._state_store.record_completion(
                        agent_id=agent_id,
                        execution_id=exec_id,
                        success=True,
                        findings={
                            "completed_stages": getattr(self, "_state_completed_stages", []),
                        },
                        score=100.0 if success else 0.0,
                        cost=total_cost,
                        execution_time_ms=execution_time_ms,
                    )
                else:
                    self._state_store.record_failure(
                        agent_id=agent_id,
                        execution_id=exec_id,
                        error=error or "Unknown workflow error",
                    )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Best-effort persistence
            logger.debug("State persistence: failed to record workflow completion: %s", e)

    # ------------------------------------------------------------------
    # Stage lifecycle
    # ------------------------------------------------------------------

    def _state_record_stage_start(self, stage_name: str) -> None:
        """Save a checkpoint before a stage runs.

        The checkpoint records which stages have already completed so
        that a future recovery can skip them.

        Args:
            stage_name: Name of the stage about to start.

        """
        if self._state_store is None:
            return

        agent_id = self._agent_id or f"{self.name}-unknown"

        try:
            checkpoint = {
                "workflow_name": self.name,
                "run_id": self._run_id,
                "current_stage": stage_name,
                "completed_stages": list(getattr(self, "_state_completed_stages", [])),
                "stage_costs": dict(getattr(self, "_state_stage_costs", {})),
                "started_at": datetime.now().isoformat(),
            }
            self._state_store.save_checkpoint(agent_id, checkpoint)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Best-effort persistence
            logger.debug(
                "State persistence: failed to save stage-start checkpoint for %s: %s",
                stage_name,
                e,
            )

    def _state_record_stage_complete(
        self,
        stage_name: str,
        cost: float,
        duration_ms: float,
        tier: str,
    ) -> None:
        """Update the checkpoint after a stage completes successfully.

        Args:
            stage_name: Name of the completed stage.
            cost: LLM cost for this stage in USD.
            duration_ms: Wall-clock time for this stage.
            tier: Model tier used (e.g. ``"cheap"``, ``"capable"``).

        """
        if self._state_store is None:
            return

        # Track internally
        completed = getattr(self, "_state_completed_stages", [])
        completed.append(stage_name)
        self._state_completed_stages = completed

        stage_costs = getattr(self, "_state_stage_costs", {})
        stage_costs[stage_name] = cost
        self._state_stage_costs = stage_costs

        agent_id = self._agent_id or f"{self.name}-unknown"

        try:
            checkpoint = {
                "workflow_name": self.name,
                "run_id": self._run_id,
                "current_stage": stage_name,
                "completed_stages": list(self._state_completed_stages),
                "stage_costs": dict(self._state_stage_costs),
                "last_tier": tier,
                "last_duration_ms": duration_ms,
                "updated_at": datetime.now().isoformat(),
            }
            self._state_store.save_checkpoint(agent_id, checkpoint)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Best-effort persistence
            logger.debug(
                "State persistence: failed to save stage-complete checkpoint for %s: %s",
                stage_name,
                e,
            )

    # ------------------------------------------------------------------
    # Recovery helpers
    # ------------------------------------------------------------------

    def _state_get_recovery_checkpoint(self) -> dict[str, Any] | None:
        """Get the last saved checkpoint for this workflow agent.

        Returns:
            Checkpoint dict or ``None`` if no checkpoint exists or
            persistence is disabled.

        """
        if self._state_store is None:
            return None

        agent_id = self._agent_id or f"{self.name}-unknown"

        try:
            return self._state_store.get_last_checkpoint(agent_id)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Best-effort persistence
            logger.debug("State persistence: failed to get recovery checkpoint: %s", e)
            return None
