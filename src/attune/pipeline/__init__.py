"""Pipeline orchestrator for spec-driven development.

Reads XML task specs from plan files and executes them
with agent teams, quality gates, and automated testing.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from attune.pipeline.models import PipelineResult, TaskResult
from attune.pipeline.orchestrator import PipelineOrchestrator
from attune.pipeline.spec_reader import read_spec

__all__ = [
    "PipelineOrchestrator",
    "PipelineResult",
    "TaskResult",
    "read_spec",
]
