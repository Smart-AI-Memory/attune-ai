"""Workflow A/B Testing Integration

High-level API for A/B testing workflow configurations, integrating
with the Socratic workflow builder to test different configurations
and optimize over time.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .manager import ExperimentManager
from .models import AllocationStrategy, ExperimentStatus


class WorkflowABTester:
    """High-level API for A/B testing workflow configurations.

    Integrates with the Socratic workflow builder to test different
    configurations and optimize over time.
    """

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize the tester.

        Args:
            storage_path: Path to persist data
        """
        self.manager = ExperimentManager(storage_path)

    def create_workflow_experiment(
        self,
        name: str,
        hypothesis: str,
        control_agents: list[str],
        treatment_agents_list: list[list[str]],
        domain: str | None = None,
    ) -> str:
        """Create an experiment comparing workflow agent configurations.

        Args:
            name: Experiment name
            hypothesis: What we're testing
            control_agents: Agent list for control
            treatment_agents_list: Agent lists for treatments
            domain: Domain filter

        Returns:
            Experiment ID
        """
        control_config = {"agents": control_agents}
        treatment_configs = [
            {
                "name": f"Treatment {i + 1}",
                "config": {"agents": agents},
            }
            for i, agents in enumerate(treatment_agents_list)
        ]

        experiment = self.manager.create_experiment(
            name=name,
            description=f"Testing different agent configurations for {domain or 'general'} workflows",
            hypothesis=hypothesis,
            control_config=control_config,
            treatment_configs=treatment_configs,
            domain_filter=domain,
            allocation_strategy=AllocationStrategy.THOMPSON_SAMPLING,
        )

        return experiment.experiment_id

    def get_workflow_config(
        self,
        session_id: str,
        domain: str | None = None,
    ) -> tuple[dict[str, Any], str | None, str | None]:
        """Get workflow configuration for a session.

        Returns control config or allocates to an experiment.

        Args:
            session_id: Session ID for allocation
            domain: Optional domain filter

        Returns:
            (config, experiment_id, variant_id) or (default_config, None, None)
        """
        # Check for running experiments
        experiments = self.manager.get_running_experiments(domain)

        for exp in experiments:
            variant = self.manager.allocate_variant(exp.experiment_id, session_id)
            if variant:
                self.manager.record_impression(exp.experiment_id, variant.variant_id)
                return (variant.config, exp.experiment_id, variant.variant_id)

        # No experiment, return default
        return ({}, None, None)

    def record_workflow_result(
        self,
        experiment_id: str,
        variant_id: str,
        success: bool,
        success_score: float = 0.0,
    ) -> None:
        """Record the result of a workflow execution.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
            success: Whether workflow succeeded
            success_score: Success score (0-1)
        """
        if success:
            self.manager.record_conversion(
                experiment_id,
                variant_id,
                success_score,
            )

    def get_best_config(self, domain: str | None = None) -> dict[str, Any]:
        """Get the best known configuration for a domain.

        Args:
            domain: Domain filter

        Returns:
            Best configuration based on completed experiments
        """
        best_config: dict[str, Any] = {}
        best_score = 0.0

        for exp in self.manager.list_experiments():
            if exp.status != ExperimentStatus.COMPLETED:
                continue
            if domain and exp.domain_filter != domain:
                continue

            result = self.manager.analyze_experiment(exp.experiment_id)
            if result and result.winner:
                if result.winner.avg_success_score > best_score:
                    best_score = result.winner.avg_success_score
                    best_config = result.winner.config

        return best_config
