"""Anthropic Batch API provider for cost-optimized bulk processing.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class AnthropicBatchProvider:
    """Provider for Anthropic Batch API (50% cost reduction).

    The Batch API processes requests asynchronously within 24 hours
    at 50% of the standard API cost. Ideal for non-urgent, bulk tasks.

    Example:
        >>> provider = AnthropicBatchProvider(api_key="sk-ant-...")
        >>> requests = [
        ...     {
        ...         "custom_id": "task_1",
        ...         "model": "claude-sonnet-4-5",
        ...         "messages": [{"role": "user", "content": "Analyze X"}],
        ...         "max_tokens": 1024
        ...     }
        ... ]
        >>> batch_id = provider.create_batch(requests)
        >>> # Wait for processing (up to 24 hours)
        >>> results = await provider.wait_for_batch(batch_id)

    """

    def __init__(self, api_key: str | None = None):
        """Initialize batch provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

        """
        if not api_key or not api_key.strip():
            raise ValueError(
                "API key is required for Anthropic Batch API. "
                "Provide via api_key parameter or ANTHROPIC_API_KEY environment variable",
            )

        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
            self._batch_jobs: dict[str, Any] = {}
        except ImportError as e:
            raise ImportError(
                "anthropic package required for Batch API. Install with: pip install anthropic",
            ) from e

    def create_batch(self, requests: list[dict[str, Any]], job_id: str | None = None) -> str:
        """Create a batch job.

        Args:
            requests: List of request dicts with 'custom_id' and 'params' containing message creation parameters.
                Format: [{"custom_id": "id1", "params": {"model": "...", "messages": [...], "max_tokens": 1024}}]
            job_id: Optional job identifier for tracking (unused, for API compatibility)

        Returns:
            Batch job ID for polling status

        Raises:
            ValueError: If requests is empty or invalid
            RuntimeError: If API call fails

        Example:
            >>> requests = [
            ...     {
            ...         "custom_id": "task_1",
            ...         "params": {
            ...             "model": "claude-sonnet-5",
            ...             "messages": [{"role": "user", "content": "Test"}],
            ...             "max_tokens": 1024
            ...         }
            ...     }
            ... ]
            >>> batch_id = provider.create_batch(requests)
            >>> print(f"Batch created: {batch_id}")
            Batch created: msgbatch_abc123

        """
        if not requests:
            raise ValueError("requests cannot be empty")

        # Validate and convert old format to new format if needed
        formatted_requests = []
        for req in requests:
            if "params" not in req:
                # Old format: convert to new format with params wrapper
                formatted_req = {
                    "custom_id": req.get("custom_id", f"req_{id(req)}"),
                    "params": {
                        "model": req.get("model", "claude-sonnet-5"),
                        "messages": req.get("messages", []),
                        "max_tokens": req.get("max_tokens", 4096),
                    },
                }
                # Copy other optional params
                for key in ["temperature", "system", "stop_sequences"]:
                    if key in req:
                        formatted_req["params"][key] = req[key]
                formatted_requests.append(formatted_req)
            else:
                formatted_requests.append(req)

        # Drop params newer models (Opus 4.7+) reject from every request's
        # params — same root cause as the non-batch provider; an Opus 4.8
        # batch request carrying temperature would otherwise 400 per-item.
        from .anthropic import _normalize_api_kwargs_for_model

        for formatted in formatted_requests:
            params = formatted.get("params")
            if isinstance(params, dict):
                _normalize_api_kwargs_for_model(params)

        try:
            # Use correct Message Batches API endpoint
            batch = self.client.messages.batches.create(requests=formatted_requests)
            self._batch_jobs[batch.id] = batch
            logger.info(f"Created batch {batch.id} with {len(formatted_requests)} requests")
            return batch.id
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to create batch: {e}")
            raise RuntimeError(f"Batch creation failed: {e}") from e

    def get_batch_status(self, batch_id: str) -> Any:
        """Get status of batch job.

        Args:
            batch_id: Batch job ID

        Returns:
            MessageBatch object with processing_status field:
            - "in_progress": Batch is being processed
            - "canceling": Cancellation initiated
            - "ended": Batch processing ended (check request_counts for success/errors)

        Example:
            >>> status = provider.get_batch_status("msgbatch_abc123")
            >>> print(status.processing_status)
            in_progress
            >>> print(f"Succeeded: {status.request_counts.succeeded}")

        """
        try:
            # Use correct Message Batches API endpoint
            batch = self.client.messages.batches.retrieve(batch_id)
            self._batch_jobs[batch_id] = batch
            return batch
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to get batch status for {batch_id}: {e}")
            raise RuntimeError(f"Failed to get batch status: {e}") from e

    def get_batch_results(self, batch_id: str) -> list[dict[str, Any]]:
        """Get results from completed batch.

        Args:
            batch_id: Batch job ID

        Returns:
            List of result dicts. Each dict contains:
            - custom_id: Request identifier
            - result: Either {"type": "succeeded", "message": {...}} or {"type": "errored", "error": {...}}

        Raises:
            ValueError: If batch has not ended processing
            RuntimeError: If API call fails

        Example:
            >>> results = provider.get_batch_results("msgbatch_abc123")
            >>> for result in results:
            ...     if result['result']['type'] == 'succeeded':
            ...         message = result['result']['message']
            ...         print(f"{result['custom_id']}: {message.content[0].text}")
            ...     else:
            ...         error = result['result']['error']
            ...         print(f"{result['custom_id']}: Error {error['type']}")

        """
        status = self.get_batch_status(batch_id)

        # Check processing_status instead of status
        if status.processing_status != "ended":
            raise ValueError(
                f"Batch {batch_id} has not ended processing (status: {status.processing_status})",
            )

        try:
            # Use correct Message Batches API endpoint
            # results() returns an iterator, convert to list
            results_iterator = self.client.messages.batches.results(batch_id)
            return list(results_iterator)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to get batch results for {batch_id}: {e}")
            raise RuntimeError(f"Failed to get batch results: {e}") from e

    async def wait_for_batch(
        self,
        batch_id: str,
        poll_interval: int = 60,
        timeout: int = 86400,  # 24 hours
    ) -> list[dict[str, Any]]:
        """Wait for batch to complete with polling.

        Args:
            batch_id: Batch job ID
            poll_interval: Seconds between status checks (default: 60)
            timeout: Maximum wait time in seconds (default: 86400 = 24 hours)

        Returns:
            Batch results when processing ends

        Raises:
            TimeoutError: If batch doesn't complete within timeout
            RuntimeError: If batch had errors during processing

        Example:
            >>> results = await provider.wait_for_batch(
            ...     "msgbatch_abc123",
            ...     poll_interval=300,  # Check every 5 minutes
            ... )
            >>> print(f"Batch completed: {len(results)} results")

        """
        start_time = datetime.now()

        while True:
            status = self.get_batch_status(batch_id)

            # Check if batch processing has ended
            if status.processing_status == "ended":
                # Check request counts to see if there were errors
                counts = status.request_counts
                logger.info(
                    f"Batch {batch_id} ended: "
                    f"{counts.succeeded} succeeded, {counts.errored} errored, "
                    f"{counts.canceled} canceled, {counts.expired} expired",
                )

                # Return results even if some requests failed
                # The caller can inspect individual results for errors
                return self.get_batch_results(batch_id)

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(f"Batch {batch_id} did not complete within {timeout}s")

            # Log progress with request counts
            try:
                counts = status.request_counts
                logger.debug(
                    f"Batch {batch_id} status: {status.processing_status} "
                    f"(processing: {counts.processing}, elapsed: {elapsed:.0f}s)",
                )
            except AttributeError:
                logger.debug(
                    f"Batch {batch_id} status: {status.processing_status} (elapsed: {elapsed:.0f}s)",
                )

            # Wait before next poll
            await asyncio.sleep(poll_interval)
