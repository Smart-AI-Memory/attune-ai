"""Feedback Loop for Continuous Improvement

Analyzes success metrics from workflow executions to improve
future agent generation. This creates a learning system that:

1. Tracks which agent configurations succeed
2. Identifies patterns in successful workflows
3. Adjusts agent recommendations based on historical data
4. Provides insights for manual tuning

This module is a facade that re-exports all public APIs from
the underlying focused modules:

- feedback_models: AgentPerformance, WorkflowPattern
- feedback_collector: FeedbackCollector
- adaptive_generator: AdaptiveAgentGenerator, FeedbackLoop

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .adaptive_generator import AdaptiveAgentGenerator, FeedbackLoop
from .feedback_collector import FeedbackCollector
from .feedback_models import AgentPerformance, WorkflowPattern

__all__ = [
    "AgentPerformance",
    "WorkflowPattern",
    "FeedbackCollector",
    "AdaptiveAgentGenerator",
    "FeedbackLoop",
]
