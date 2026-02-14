"""Base LLM provider and response dataclass.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""

    content: str
    model: str
    tokens_used: int
    finish_reason: str
    metadata: dict[str, Any]


class BaseLLMProvider(ABC):
    """Base class for all LLM providers.

    Provides unified interface regardless of backend.
    """

    def __init__(self, api_key: str | None = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate response from LLM.

        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific options

        Returns:
            LLMResponse with standardized format

        """

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the model being used"""

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Rough approximation: ~4 chars per token
        """
        return len(text) // 4
