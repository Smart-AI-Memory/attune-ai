"""Google Gemini provider with cost tracking integration.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import Any

from .base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider with cost tracking integration.

    Supports Gemini models:
    - gemini-2.0-flash-exp: Fast, cheap tier (1M context)
    - gemini-1.5-pro: Balanced, capable tier (2M context)
    - gemini-2.5-pro: Premium reasoning tier
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-pro",
        **kwargs,
    ):
        super().__init__(api_key, **kwargs)
        self.model = model

        # Validate API key is provided
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for Gemini provider. "
                "Provide via api_key parameter or GOOGLE_API_KEY environment variable",
            )

        # Lazy import to avoid requiring google-generativeai if not used
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self.genai = genai
            self.client = genai.GenerativeModel(model)
        except ImportError as e:
            raise ImportError(
                "google-generativeai package required. Install with: pip install google-generativeai",
            ) from e

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate response using Google Gemini API.

        Gemini-specific features:
        - Large context windows (1M-2M tokens)
        - Multimodal support
        - Grounding with Google Search
        """
        import asyncio

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        # Build generation config
        generation_config = self.genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # Create model with system instruction if provided
        if system_prompt:
            model = self.genai.GenerativeModel(
                self.model,
                system_instruction=system_prompt,
            )
        else:
            model = self.client

        # Call Gemini API (run sync in thread pool for async compatibility)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(
                gemini_messages,  # type: ignore[arg-type]
                generation_config=generation_config,
            ),
        )

        # Extract token counts from usage metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata"):
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)

        # Log to cost tracker
        try:
            from attune.cost_tracker import log_request

            tier = self._get_tier()
            log_request(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                task_type=kwargs.get("task_type", "gemini_generate"),
                tier=tier,
            )
        except ImportError:
            pass  # Cost tracking not available

        # Convert to standardized format
        content = ""
        if response.candidates:
            content = response.candidates[0].content.parts[0].text

        finish_reason = "stop"
        if response.candidates and hasattr(response.candidates[0], "finish_reason"):
            finish_reason = str(response.candidates[0].finish_reason.name).lower()

        return LLMResponse(
            content=content,
            model=self.model,
            tokens_used=input_tokens + output_tokens,
            finish_reason=finish_reason,
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": "google",
                "model_family": "gemini",
            },
        )

    def _get_tier(self) -> str:
        """Determine tier from model name."""
        if "flash" in self.model.lower():
            return "cheap"
        if "2.5" in self.model or "ultra" in self.model.lower():
            return "premium"
        return "capable"

    def get_model_info(self) -> dict[str, Any]:
        """Get Gemini model information"""
        model_info = {
            "gemini-2.0-flash-exp": {
                "max_tokens": 1000000,
                "cost_per_1m_input": 0.075,
                "cost_per_1m_output": 0.30,
                "supports_vision": True,
                "ideal_for": "Fast responses, simple tasks, large context",
            },
            "gemini-1.5-pro": {
                "max_tokens": 2000000,
                "cost_per_1m_input": 1.25,
                "cost_per_1m_output": 5.00,
                "supports_vision": True,
                "ideal_for": "Complex reasoning, large codebases",
            },
            "gemini-2.5-pro": {
                "max_tokens": 1000000,
                "cost_per_1m_input": 2.50,
                "cost_per_1m_output": 10.00,
                "supports_vision": True,
                "ideal_for": "Advanced reasoning, complex tasks",
            },
        }

        return model_info.get(
            self.model,
            {
                "max_tokens": 1000000,
                "cost_per_1m_input": 1.25,
                "cost_per_1m_output": 5.00,
                "supports_vision": True,
            },
        )
