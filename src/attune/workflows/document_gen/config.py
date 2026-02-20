"""Document Generation Configuration.

Token costs and step configurations for documentation generation workflow.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from ..base import ModelTier
from ..step_config import WorkflowStepConfig

# Approximate cost per 1K tokens (USD) - used for cost estimation
# These are estimates and should be updated as pricing changes
TOKEN_COSTS = {
    ModelTier.CHEAP: {"input": 0.00025, "output": 0.00125},  # Haiku
    ModelTier.CAPABLE: {"input": 0.003, "output": 0.015},  # Sonnet
    ModelTier.PREMIUM: {"input": 0.015, "output": 0.075},  # Opus
}

# Define step configurations for executor-based execution
# Note: max_tokens for polish is dynamically set based on input size
DOC_GEN_STEPS = {
    "polish": WorkflowStepConfig(
        name="polish",
        task_type="final_review",  # Premium tier task
        tier_hint="premium",
        description="Polish and improve documentation for consistency and quality",
        max_tokens=20000,  # Increased to handle large chunked documents
    ),
}
