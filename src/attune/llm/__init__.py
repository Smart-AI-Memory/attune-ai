"""Attune AI LLM Integration.

Core LLM wrapper with empathy levels, provider adapters, and state tracking.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .core import EmpathyLLM
from .levels import EmpathyLevel
from .providers import (
    AnthropicBatchProvider,
    AnthropicProvider,
    BaseLLMProvider,
    GeminiProvider,
    LLMResponse,
    LocalProvider,
    OpenAIProvider,
)
from .state import CollaborationState, PatternType, UserPattern

__all__ = [
    # Core
    "EmpathyLLM",
    # Levels
    "EmpathyLevel",
    # Providers
    "AnthropicBatchProvider",
    "AnthropicProvider",
    "BaseLLMProvider",
    "GeminiProvider",
    "LLMResponse",
    "LocalProvider",
    "OpenAIProvider",
    # State
    "CollaborationState",
    "PatternType",
    "UserPattern",
]
