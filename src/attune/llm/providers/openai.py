"""OpenAI provider.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider.

    Supports GPT-4, GPT-3.5, and other OpenAI models.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4-turbo-preview", **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = model

        # Validate API key is provided
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for OpenAI provider. "
                "Provide via api_key parameter or OPENAI_API_KEY environment variable",
            )

        # Lazy import
        try:
            import openai

            self.client = openai.AsyncOpenAI(api_key=api_key)
        except ImportError as e:
            raise ImportError("openai package required. Install with: pip install openai") from e

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate response using OpenAI API"""
        # Add system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Convert to standardized format
        content = response.choices[0].message.content or ""
        usage = response.usage
        return LLMResponse(
            content=content,
            model=response.model,
            tokens_used=usage.total_tokens if usage else 0,
            finish_reason=response.choices[0].finish_reason,
            metadata={
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
                "provider": "openai",
            },
        )

    def get_model_info(self) -> dict[str, Any]:
        """Get OpenAI model information"""
        model_info = {
            "gpt-4-turbo-preview": {
                "max_tokens": 128000,
                "cost_per_1m_input": 10.00,
                "cost_per_1m_output": 30.00,
            },
            "gpt-4": {"max_tokens": 8192, "cost_per_1m_input": 30.00, "cost_per_1m_output": 60.00},
            "gpt-3.5-turbo": {
                "max_tokens": 16385,
                "cost_per_1m_input": 0.50,
                "cost_per_1m_output": 1.50,
            },
        }

        return model_info.get(
            self.model,
            {"max_tokens": 128000, "cost_per_1m_input": 10.00, "cost_per_1m_output": 30.00},
        )
