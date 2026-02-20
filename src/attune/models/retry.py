"""Retry Policy for LLM Calls

Configures retry behavior with exponential backoff for transient
LLM failures such as rate limits, timeouts, and server errors.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field


@dataclass
class RetryPolicy:
    """Policy for retrying failed LLM calls.

    Configures how many times to retry and with what delays.
    """

    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 30000
    exponential_backoff: bool = True
    backoff_multiplier: float = 2.0
    retry_on_errors: list[str] = field(
        default_factory=lambda: [
            "rate_limit",
            "timeout",
            "server_error",
            "connection_error",
        ],
    )

    def get_delay_ms(self, attempt: int) -> int:
        """Get delay before retry attempt.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in milliseconds

        """
        if not self.exponential_backoff:
            return self.initial_delay_ms

        delay = self.initial_delay_ms * (self.backoff_multiplier ** (attempt - 1))
        return min(int(delay), self.max_delay_ms)

    def should_retry(self, error_type: str, attempt: int) -> bool:
        """Check if should retry for this error.

        Args:
            error_type: Type of error encountered
            attempt: Current attempt number

        Returns:
            True if should retry

        """
        if attempt >= self.max_retries:
            return False

        return error_type in self.retry_on_errors
