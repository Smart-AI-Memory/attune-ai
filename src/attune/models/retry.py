"""Retry Policy for LLM Calls

Configures retry behavior with exponential backoff for transient
LLM failures such as rate limits, timeouts, and server errors.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import random
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
    #: Randomize each delay within [base/2, base] ("equal jitter").
    #: Without it, concurrent callers that failed together retry in
    #: lockstep and re-trigger shared rate limits (#2242). Set False
    #: for deterministic delays (tests, reproductions).
    jitter: bool = True
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
            base = self.initial_delay_ms
        else:
            raw = self.initial_delay_ms * (self.backoff_multiplier ** (attempt - 1))
            base = min(int(raw), self.max_delay_ms)
        if not self.jitter:
            return base
        # Equal jitter: uniform in [base/2, base]. random is fine here —
        # this is herd-spreading, not cryptography.
        return int(base / 2 + random.random() * base / 2)  # noqa: S311

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
