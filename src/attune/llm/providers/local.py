"""Local model provider (Ollama, LM Studio, etc.).

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .base import BaseLLMProvider, LLMResponse


class LocalProvider(BaseLLMProvider):
    """Local model provider (Ollama, LM Studio, etc.).

    For running models locally.
    """

    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama2", **kwargs):
        super().__init__(api_key=None, **kwargs)
        self.endpoint = endpoint
        self.model = model

    async def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs,
    ) -> LLMResponse:
        """Generate response using local model"""
        import aiohttp

        # Format for Ollama-style API
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.endpoint}/api/chat", json=payload) as response:
                result = await response.json()

                return LLMResponse(
                    content=result.get("message", {}).get("content", ""),
                    model=self.model,
                    tokens_used=result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                    finish_reason="stop",
                    metadata={"provider": "local", "endpoint": self.endpoint},
                )

    def get_model_info(self) -> dict[str, Any]:
        """Get local model information"""
        return {
            "max_tokens": 4096,  # Depends on model
            "cost_per_1m_input": 0.0,  # Free (local)
            "cost_per_1m_output": 0.0,
            "endpoint": self.endpoint,
        }
