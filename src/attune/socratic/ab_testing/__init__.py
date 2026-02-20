"""A/B Testing for Workflow Optimization

Enables controlled experiments to compare different workflow configurations
and determine which performs better for specific goals or domains.

Key Features:
- Experiment definition with control and variant groups
- Statistical significance testing
- Automatic traffic allocation
- Multi-armed bandit for adaptive optimization
- Integration with feedback loop

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .allocator import TrafficAllocator
from .manager import ExperimentManager
from .models import (
    AllocationStrategy,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    Variant,
)
from .statistics import StatisticalAnalyzer
from .workflow_tester import WorkflowABTester

__all__ = [
    "AllocationStrategy",
    "Experiment",
    "ExperimentManager",
    "ExperimentResult",
    "ExperimentStatus",
    "StatisticalAnalyzer",
    "TrafficAllocator",
    "Variant",
    "WorkflowABTester",
]
