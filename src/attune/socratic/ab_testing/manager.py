"""Experiment Manager for A/B Testing

Manages the lifecycle of A/B experiments including creation, execution,
recording metrics, and analysis of results.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from ...config import _validate_file_path
from .allocator import TrafficAllocator
from .models import (
    AllocationStrategy,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    Variant,
)
from .statistics import StatisticalAnalyzer

logger = logging.getLogger(__name__)


class ExperimentManager:
    """Manages A/B experiments lifecycle."""

    def __init__(self, storage_path: Path | str | None = None):
        """Initialize experiment manager.

        Args:
            storage_path: Path to persist experiments
        """
        if storage_path is None:
            storage_path = Path.home() / ".attune" / "socratic" / "experiments.json"
        self.storage_path = Path(storage_path)
        self._experiments: dict[str, Experiment] = {}
        self._allocators: dict[str, TrafficAllocator] = {}

        # Load existing experiments
        self._load()

    def create_experiment(
        self,
        name: str,
        description: str,
        hypothesis: str,
        control_config: dict[str, Any],
        treatment_configs: list[dict[str, Any]],
        domain_filter: str | None = None,
        allocation_strategy: AllocationStrategy = AllocationStrategy.FIXED,
        min_sample_size: int = 100,
    ) -> Experiment:
        """Create a new experiment.

        Args:
            name: Experiment name
            description: Description
            hypothesis: What we're testing
            control_config: Configuration for control group
            treatment_configs: Configurations for treatment groups
            domain_filter: Optional domain to filter
            allocation_strategy: How to allocate traffic
            min_sample_size: Minimum samples before analysis

        Returns:
            Created experiment
        """
        experiment_id = hashlib.sha256(f"{name}:{time.time()}".encode()).hexdigest()[:12]

        # Create variants
        num_variants = 1 + len(treatment_configs)
        traffic_each = 100.0 / num_variants

        variants = [
            Variant(
                variant_id=f"{experiment_id}_control",
                name="Control",
                description="Control group with existing configuration",
                config=control_config,
                is_control=True,
                traffic_percentage=traffic_each,
            )
        ]

        for i, config in enumerate(treatment_configs):
            variants.append(
                Variant(
                    variant_id=f"{experiment_id}_treatment_{i}",
                    name=config.get("name", f"Treatment {i + 1}"),
                    description=config.get("description", ""),
                    config=config.get("config", config),
                    is_control=False,
                    traffic_percentage=traffic_each,
                )
            )

        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            hypothesis=hypothesis,
            variants=variants,
            domain_filter=domain_filter,
            allocation_strategy=allocation_strategy,
            min_sample_size=min_sample_size,
        )

        self._experiments[experiment_id] = experiment
        self._save()

        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment.

        Args:
            experiment_id: ID of experiment to start

        Returns:
            True if started successfully
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False

        if experiment.status != ExperimentStatus.DRAFT:
            return False

        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.now()
        self._allocators[experiment_id] = TrafficAllocator(experiment)
        self._save()

        return True

    def stop_experiment(self, experiment_id: str) -> ExperimentResult | None:
        """Stop an experiment and analyze results.

        Args:
            experiment_id: ID of experiment to stop

        Returns:
            Experiment results with analysis
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = datetime.now()
        self._save()

        return self.analyze_experiment(experiment_id)

    def allocate_variant(
        self,
        experiment_id: str,
        user_id: str,
    ) -> Variant | None:
        """Allocate a user to a variant.

        Args:
            experiment_id: Experiment ID
            user_id: User/session ID

        Returns:
            Allocated variant or None
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None

        allocator = self._allocators.get(experiment_id)
        if not allocator:
            allocator = TrafficAllocator(experiment)
            self._allocators[experiment_id] = allocator

        return allocator.allocate(user_id)

    def record_impression(self, experiment_id: str, variant_id: str) -> None:
        """Record an impression for a variant.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        for variant in experiment.variants:
            if variant.variant_id == variant_id:
                variant.impressions += 1
                break

        self._save()

    def record_conversion(
        self,
        experiment_id: str,
        variant_id: str,
        success_score: float = 1.0,
    ) -> None:
        """Record a conversion for a variant.

        Args:
            experiment_id: Experiment ID
            variant_id: Variant ID
            success_score: Score from 0-1
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return

        for variant in experiment.variants:
            if variant.variant_id == variant_id:
                variant.conversions += 1
                variant.total_success_score += success_score
                break

        self._save()

    def analyze_experiment(self, experiment_id: str) -> ExperimentResult | None:
        """Analyze experiment results.

        Args:
            experiment_id: Experiment ID

        Returns:
            Analysis results
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None

        control = experiment.control
        if not control:
            return None

        treatments = experiment.treatments
        if not treatments:
            return None

        # Find best treatment
        best_treatment = max(treatments, key=lambda v: v.conversion_rate)

        # Statistical test
        z_score, p_value = StatisticalAnalyzer.z_test_proportions(
            control.impressions,
            control.conversions,
            best_treatment.impressions,
            best_treatment.conversions,
        )

        is_significant = p_value < (1 - experiment.confidence_level)

        # Calculate lift
        if control.conversion_rate > 0:
            lift = (
                (best_treatment.conversion_rate - control.conversion_rate) / control.conversion_rate
            ) * 100
        else:
            lift = 0.0

        # Confidence interval for treatment
        ci = StatisticalAnalyzer.confidence_interval(
            best_treatment.impressions,
            best_treatment.conversions,
            experiment.confidence_level,
        )

        # Determine winner
        winner = None
        recommendation = ""

        if is_significant:
            if best_treatment.conversion_rate > control.conversion_rate:
                winner = best_treatment
                recommendation = (
                    f"Adopt {best_treatment.name}. It shows {lift:.1f}% improvement "
                    f"over control with p-value {p_value:.4f}."
                )
            else:
                winner = control
                recommendation = "Keep control. Treatment did not show improvement."
        else:
            recommendation = (
                f"No significant difference detected (p={p_value:.4f}). "
                f"Consider running longer or increasing sample size."
            )

        return ExperimentResult(
            experiment=experiment,
            winner=winner,
            is_significant=is_significant,
            p_value=p_value,
            confidence_interval=ci,
            lift=lift,
            recommendation=recommendation,
        )

    def get_running_experiments(
        self,
        domain: str | None = None,
    ) -> list[Experiment]:
        """Get all running experiments.

        Args:
            domain: Optional domain filter

        Returns:
            List of running experiments
        """
        running = []
        for exp in self._experiments.values():
            if exp.status != ExperimentStatus.RUNNING:
                continue
            if domain and exp.domain_filter and exp.domain_filter != domain:
                continue
            running.append(exp)
        return running

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        """List all experiments."""
        return list(self._experiments.values())

    def _save(self) -> None:
        """Save experiments to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "experiments": [e.to_dict() for e in self._experiments.values()],
        }

        validated_path = _validate_file_path(str(self.storage_path))
        with validated_path.open("w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Load experiments from storage."""
        if not self.storage_path.exists():
            return

        try:
            with self.storage_path.open("r") as f:
                data = json.load(f)

            for exp_data in data.get("experiments", []):
                exp = Experiment.from_dict(exp_data)
                self._experiments[exp.experiment_id] = exp

                # Restore allocators for running experiments
                if exp.status == ExperimentStatus.RUNNING:
                    self._allocators[exp.experiment_id] = TrafficAllocator(exp)

        except Exception as e:
            logger.warning(f"Failed to load experiments: {e}")
