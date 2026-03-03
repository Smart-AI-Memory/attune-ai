---
description: Anthropic Stack Optimization Plan - Attune AI: **Version:** 1.0 **Created:** January 16, 2026 **Owner:** Engineering Team **Status:** Planning Phase **T
---

# Anthropic Stack Optimization Plan - Attune AI

**Version:** 1.0
**Created:** January 16, 2026
**Owner:** Engineering Team
**Status:** Planning Phase
**Timeline:** 3-4 weeks (estimated)

---

## 🎯 Executive Summary

This plan outlines optimizations to fully leverage Anthropic's capabilities in the Attune AI. While the framework already uses Anthropic as the default provider, several advanced features remain underutilized.

**Current State:**
- ✅ Anthropic is default provider
- ✅ Latest Claude models (Sonnet 4.5, Opus 4.5, Haiku 3.5)
- ✅ Official Anthropic SDK integrated
- ✅ Task-based tier routing

**Goals:**
- 💰 Reduce API costs by 30-50% through Batch API and prompt caching
- ⚡ Improve response quality with Thinking mode
- 🎨 Enable vision-based workflows
- 📊 Achieve precise cost tracking with accurate token counting
- 🔄 Add real-time streaming for better UX

**Expected Impact:**
- **Cost Reduction:** 30-50% for batch-eligible tasks
- **Quality Improvement:** 15-20% better reasoning on complex tasks
- **New Capabilities:** Vision analysis, real-time streaming
- **Operational Excellence:** Precise cost attribution per workflow

---

## 📊 Optimization Tracks Overview

| Track | Priority | Effort | Impact | Timeline |
|-------|----------|--------|--------|----------|
| 1. Batch API Integration | HIGH | Medium | 50% cost reduction | Week 1-2 |
| 2. Prompt Caching | HIGH | Low | 20-30% cost reduction | Week 1 |
| 3. Thinking Mode | MEDIUM | Low | Quality improvement | Week 2 |
| 4. Precise Token Counting | HIGH | Low | Better tracking | Week 1 |
| 5. Vision Workflows | MEDIUM | High | New capability | Week 3-4 |
| 6. Streaming Support | MEDIUM | Medium | Better UX | Week 2-3 |
| 7. Max Tokens Optimization | LOW | Low | Minor savings | Week 4 |

---

## 🚀 Track 1: Batch API Integration

### Objective
Enable Anthropic's Batch API for non-urgent tasks to achieve 50% cost reduction.

### Background
Anthropic's Batch API (announced 2024) processes requests asynchronously with:
- **50% cost reduction** compared to real-time API
- **24-hour processing window** (not suitable for interactive workflows)
- **Same model quality** as real-time API
- **Bulk processing** for analytics, data processing, batch evaluations

### Implementation Steps

#### 1.1 Add Batch API Client

**File:** `attune_llm/providers.py`

**Add new class:**
```python
from anthropic import Anthropic
from anthropic.types import BatchCreateParams, BatchStatus
from typing import List, Dict, Any
import asyncio
from datetime import datetime, timedelta

class AnthropicBatchProvider:
    """Provider for Anthropic Batch API (50% cost reduction)."""

    def __init__(self, api_key: str | None = None):
        """Initialize batch provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.client = Anthropic(api_key=api_key)
        self._batch_jobs: Dict[str, BatchStatus] = {}

    def create_batch(
        self,
        requests: List[Dict[str, Any]],
        job_id: str | None = None
    ) -> str:
        """Create a batch job.

        Args:
            requests: List of request dicts with 'model', 'messages', etc.
            job_id: Optional job identifier for tracking

        Returns:
            Batch job ID for polling status

        Example:
            >>> requests = [
            ...     {
            ...         "model": "claude-sonnet-4-5",
            ...         "messages": [{"role": "user", "content": "Analyze X"}],
            ...         "max_tokens": 1024
            ...     }
            ... ]
            >>> job_id = provider.create_batch(requests)
        """
        batch = self.client.batches.create(
            requests=requests
        )

        self._batch_jobs[batch.id] = batch
        return batch.id

    def get_batch_status(self, batch_id: str) -> BatchStatus:
        """Get status of batch job.

        Returns:
            BatchStatus with status in ['processing', 'completed', 'failed']
        """
        batch = self.client.batches.retrieve(batch_id)
        self._batch_jobs[batch_id] = batch
        return batch

    def get_batch_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get results from completed batch.

        Args:
            batch_id: Batch job ID

        Returns:
            List of result dicts matching input order

        Raises:
            ValueError: If batch is not completed
        """
        status = self.get_batch_status(batch_id)

        if status.status != "completed":
            raise ValueError(
                f"Batch {batch_id} not completed (status: {status.status})"
            )

        results = self.client.batches.results(batch_id)
        return list(results)

    async def wait_for_batch(
        self,
        batch_id: str,
        poll_interval: int = 60,
        timeout: int = 86400  # 24 hours
    ) -> List[Dict[str, Any]]:
        """Wait for batch to complete with polling.

        Args:
            batch_id: Batch job ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds

        Returns:
            Batch results when completed

        Raises:
            TimeoutError: If batch doesn't complete within timeout
        """
        start_time = datetime.now()

        while True:
            status = self.get_batch_status(batch_id)

            if status.status == "completed":
                return self.get_batch_results(batch_id)

            if status.status == "failed":
                raise RuntimeError(f"Batch {batch_id} failed: {status.error}")

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(
                    f"Batch {batch_id} did not complete within {timeout}s"
                )

            # Wait before next poll
            await asyncio.sleep(poll_interval)
```

**Add to existing `AnthropicProvider` class:**
```python
class AnthropicProvider:
    # ... existing code ...

    def __init__(self, api_key: str | None = None, use_batch: bool = False):
        """Initialize provider.

        Args:
            api_key: Anthropic API key
            use_batch: If True, use batch API for non-urgent requests
        """
        self.client = Anthropic(api_key=api_key)
        self.use_batch = use_batch

        if use_batch:
            self.batch_provider = AnthropicBatchProvider(api_key=api_key)
        else:
            self.batch_provider = None
```

#### 1.2 Add Batch-Eligible Task Identification

**File:** `src/attune/models/tasks.py`

**Add new constant:**
```python
# Tasks eligible for batch processing (non-interactive, non-urgent)
BATCH_ELIGIBLE_TASKS = {
    # Analytics & Reporting
    "analyze_logs",
    "generate_report",
    "compute_metrics",
    "aggregate_stats",

    # Data Processing
    "classify_bulk",
    "extract_bulk",
    "transform_bulk",
    "validate_bulk",

    # Code Analysis
    "analyze_codebase",
    "detect_patterns",
    "compute_complexity",
    "find_vulnerabilities",

    # Content Generation (non-urgent)
    "generate_docs",
    "generate_tests",
    "generate_comments",
    "translate_bulk",

    # Evaluation & Testing
    "evaluate_responses",
    "run_test_suite",
    "validate_outputs",
}

# Tasks requiring real-time response
REALTIME_REQUIRED_TASKS = {
    "chat",
    "interactive_debug",
    "live_coding",
    "user_query",
    "wizard_step",
}
```

#### 1.3 Create Batch Workflow

**File:** `src/attune/workflows/batch_processing.py` (NEW)

```python
"""Batch processing workflow using Anthropic Batch API."""

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from attune.workflows.base import BaseWorkflow
from attune_llm.providers import AnthropicBatchProvider
from attune.models import get_model

logger = logging.getLogger(__name__)


@dataclass
class BatchRequest:
    """Single request in a batch."""
    task_id: str
    task_type: str
    input_data: Dict[str, Any]
    model_tier: str = "capable"  # cheap, capable, premium


@dataclass
class BatchResult:
    """Result from batch processing."""
    task_id: str
    success: bool
    output: Dict[str, Any] | None = None
    error: str | None = None


class BatchProcessingWorkflow(BaseWorkflow):
    """Process multiple tasks via Anthropic Batch API (50% cost savings)."""

    def __init__(self, api_key: str | None = None):
        """Initialize batch workflow.

        Args:
            api_key: Anthropic API key (optional, uses env var)
        """
        super().__init__()
        self.batch_provider = AnthropicBatchProvider(api_key=api_key)

    async def execute_batch(
        self,
        requests: List[BatchRequest],
        poll_interval: int = 300,  # 5 minutes
        timeout: int = 86400  # 24 hours
    ) -> List[BatchResult]:
        """Execute batch of requests.

        Args:
            requests: List of batch requests
            poll_interval: Seconds between status checks
            timeout: Maximum wait time

        Returns:
            List of results matching input order

        Example:
            >>> workflow = BatchProcessingWorkflow()
            >>> requests = [
            ...     BatchRequest(
            ...         task_id="task_1",
            ...         task_type="analyze_logs",
            ...         input_data={"logs": "..."}
            ...     )
            ... ]
            >>> results = await workflow.execute_batch(requests)
        """
        # Convert to Anthropic batch format
        api_requests = []
        for req in requests:
            model = get_model("anthropic", req.model_tier)

            api_requests.append({
                "custom_id": req.task_id,
                "model": model.id,
                "messages": self._format_messages(req),
                "max_tokens": 4096,
            })

        # Submit batch
        logger.info(f"Submitting batch of {len(requests)} requests")
        batch_id = self.batch_provider.create_batch(api_requests)

        logger.info(f"Batch {batch_id} created, waiting for completion...")

        # Wait for completion
        try:
            raw_results = await self.batch_provider.wait_for_batch(
                batch_id,
                poll_interval=poll_interval,
                timeout=timeout
            )
        except TimeoutError:
            logger.error(f"Batch {batch_id} timed out after {timeout}s")
            return [
                BatchResult(
                    task_id=req.task_id,
                    success=False,
                    error="Batch processing timed out"
                )
                for req in requests
            ]

        # Parse results
        results = []
        for raw in raw_results:
            task_id = raw["custom_id"]

            if "error" in raw:
                results.append(BatchResult(
                    task_id=task_id,
                    success=False,
                    error=raw["error"]["message"]
                ))
            else:
                results.append(BatchResult(
                    task_id=task_id,
                    success=True,
                    output=raw["response"]
                ))

        logger.info(
            f"Batch {batch_id} completed: "
            f"{sum(r.success for r in results)}/{len(results)} successful"
        )

        return results

    def _format_messages(self, request: BatchRequest) -> List[Dict[str, str]]:
        """Format request into Anthropic messages format."""
        # Task-specific formatting
        task_prompts = {
            "analyze_logs": "Analyze the following logs and identify issues:\n\n{logs}",
            "generate_report": "Generate a report based on:\n\n{data}",
            "classify_bulk": "Classify the following items:\n\n{items}",
            # ... more task types
        }

        prompt = task_prompts.get(
            request.task_type,
            "Process the following:\n\n{input}"
        )

        # Format with input data
        content = prompt.format(**request.input_data)

        return [{"role": "user", "content": content}]
```

#### 1.4 Add CLI Command

**File:** `src/attune/cli.py`

**Add new command:**
```python
@app.command()
def batch(
    task_type: str = typer.Option(..., help="Task type (analyze_logs, generate_docs, etc.)"),
    input_file: str = typer.Option(..., help="JSON file with input data"),
    output_file: str = typer.Option("batch_results.json", help="Output file"),
    model_tier: str = typer.Option("capable", help="Model tier (cheap/capable/premium)"),
    poll_interval: int = typer.Option(300, help="Status check interval (seconds)"),
):
    """Process tasks via Anthropic Batch API (50% cost savings).

    Input file format:
    [
        {"task_id": "1", "input_data": {"logs": "..."}},
        {"task_id": "2", "input_data": {"logs": "..."}}
    ]
    """
    import json
    import asyncio
    from attune.workflows.batch_processing import (
        BatchProcessingWorkflow,
        BatchRequest,
    )

    # Load input
    with open(input_file) as f:
        inputs = json.load(f)

    # Create requests
    requests = [
        BatchRequest(
            task_id=item["task_id"],
            task_type=task_type,
            input_data=item["input_data"],
            model_tier=model_tier,
        )
        for item in inputs
    ]

    console.print(f"[cyan]Submitting {len(requests)} tasks to batch API...[/cyan]")
    console.print(f"[yellow]Note: Batch API processes within 24 hours (50% cost savings)[/yellow]")

    # Execute
    workflow = BatchProcessingWorkflow()
    results = asyncio.run(workflow.execute_batch(requests, poll_interval=poll_interval))

    # Save results
    output_data = [
        {
            "task_id": r.task_id,
            "success": r.success,
            "output": r.output,
            "error": r.error,
        }
        for r in results
    ]

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    # Summary
    successes = sum(r.success for r in results)
    console.print(f"\n[green]✓ Batch complete: {successes}/{len(results)} successful[/green]")
    console.print(f"[cyan]Results saved to: {output_file}[/cyan]")
```

#### 1.5 Testing Strategy

**File:** `tests/unit/providers/test_batch_api.py` (NEW)

```python
"""Tests for Anthropic Batch API integration."""

import pytest
from unittest.mock import Mock, patch
from attune_llm.providers import AnthropicBatchProvider


class TestBatchProvider:
    """Test suite for batch API provider."""

    @patch("anthropic.Anthropic")
    def test_create_batch(self, mock_anthropic):
        """Test creating a batch job."""
        # Mock response
        mock_batch = Mock()
        mock_batch.id = "batch_123"
        mock_anthropic.return_value.batches.create.return_value = mock_batch

        provider = AnthropicBatchProvider(api_key="test-key")

        requests = [
            {
                "model": "claude-sonnet-4-5",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 1024
            }
        ]

        batch_id = provider.create_batch(requests)

        assert batch_id == "batch_123"
        mock_anthropic.return_value.batches.create.assert_called_once()

    @patch("anthropic.Anthropic")
    def test_get_batch_status(self, mock_anthropic):
        """Test checking batch status."""
        mock_batch = Mock()
        mock_batch.status = "completed"
        mock_anthropic.return_value.batches.retrieve.return_value = mock_batch

        provider = AnthropicBatchProvider(api_key="test-key")
        status = provider.get_batch_status("batch_123")

        assert status.status == "completed"

    @patch("anthropic.Anthropic")
    def test_get_batch_results_completed(self, mock_anthropic):
        """Test getting results from completed batch."""
        mock_batch = Mock()
        mock_batch.status = "completed"
        mock_anthropic.return_value.batches.retrieve.return_value = mock_batch
        mock_anthropic.return_value.batches.results.return_value = [
            {"custom_id": "1", "response": {"content": "Result 1"}}
        ]

        provider = AnthropicBatchProvider(api_key="test-key")
        results = provider.get_batch_results("batch_123")

        assert len(results) == 1
        assert results[0]["custom_id"] == "1"

    @patch("anthropic.Anthropic")
    def test_get_batch_results_not_completed_raises(self, mock_anthropic):
        """Test that getting results from incomplete batch raises error."""
        mock_batch = Mock()
        mock_batch.status = "processing"
        mock_anthropic.return_value.batches.retrieve.return_value = mock_batch

        provider = AnthropicBatchProvider(api_key="test-key")

        with pytest.raises(ValueError, match="not completed"):
            provider.get_batch_results("batch_123")
```

#### 1.6 Documentation

**Add to README.md:**
```markdown
### Batch Processing (50% Cost Savings)

For non-urgent tasks, use the Batch API to save 50% on API costs:

```bash
# Create input file
cat > batch_input.json <<EOF
[
  {"task_id": "log_1", "input_data": {"logs": "ERROR: Connection failed..."}},
  {"task_id": "log_2", "input_data": {"logs": "WARNING: High memory usage..."}}
]
EOF

# Submit batch job
attune batch \
  --task-type analyze_logs \
  --input-file batch_input.json \
  --output-file results.json \
  --model-tier capable
```

**Note:** Batch API processes within 24 hours. Not suitable for interactive workflows.
```

### Success Criteria
- [ ] Batch API client implemented and tested
- [ ] Batch workflow created with async polling
- [ ] CLI command added for batch processing
- [ ] Unit tests achieve 80%+ coverage
- [ ] Documentation with usage examples
- [ ] Successfully process 100+ task batch
- [ ] Verify 50% cost reduction via telemetry

### Estimated Impact
- **Cost Reduction:** 50% for batch-eligible tasks
- **Throughput:** 100x for bulk operations
- **Use Cases:** Log analysis, bulk docs generation, codebase scans

---

## 💾 Track 2: Enable Prompt Caching by Default

### Objective
Reduce API costs by 20-30% for workflows with repeated context through prompt caching.

### Background
Anthropic's Prompt Caching (2024):
- **Cache frequently used context** (system prompts, documents, code)
- **90% cost reduction** on cached tokens (read)
- **25% markup** on cache writes
- **5-minute TTL** before cache expires
- **Break-even:** ~3 requests with same context

### Implementation Steps

#### 2.1 Update Provider to Enable Caching

**File:** `attune_llm/providers.py`

**Modify `AnthropicProvider.__init__`:**
```python
class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        use_prompt_caching: bool = True,  # CHANGED: Default to True
        use_batch: bool = False,
        enable_thinking: bool = False,
    ):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            use_prompt_caching: Enable prompt caching (default: True)
            use_batch: Use batch API for non-urgent requests
            enable_thinking: Enable extended thinking mode for complex tasks
        """
        self.client = Anthropic(api_key=api_key)
        self.use_prompt_caching = use_prompt_caching
        self.use_batch = use_batch
        self.enable_thinking = enable_thinking

        if use_batch:
            self.batch_provider = AnthropicBatchProvider(api_key=api_key)
```

**Add caching logic to `complete()` method:**
```python
def complete(
    self,
    messages: List[Dict[str, str]],
    model: str = "claude-sonnet-4-5",
    system_prompt: str | None = None,
    **kwargs
) -> Dict[str, Any]:
    """Complete a prompt with optional caching.

    Args:
        messages: Conversation messages
        model: Model ID
        system_prompt: System prompt (will be cached if caching enabled)
        **kwargs: Additional API parameters

    Returns:
        API response with usage stats
    """
    # Build request
    request_params = {
        "model": model,
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 4096),
    }

    # Add system prompt with cache control
    if system_prompt:
        if self.use_prompt_caching:
            # Mark system prompt for caching
            request_params["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        else:
            request_params["system"] = system_prompt

    # Make API call
    response = self.client.messages.create(**request_params)

    # Track cache performance
    usage = response.usage
    if hasattr(usage, "cache_creation_input_tokens"):
        cache_stats = {
            "cache_creation_tokens": usage.cache_creation_input_tokens,
            "cache_read_tokens": usage.cache_read_input_tokens,
            "cache_hit": usage.cache_read_input_tokens > 0,
        }
        logger.info(f"Cache stats: {cache_stats}")

    return response.model_dump()
```

#### 2.2 Add Cache-Aware System Prompts

**File:** `src/attune/workflows/base.py`

**Add method to identify cacheable content:**
```python
class BaseWorkflow:
    # ... existing code ...

    def _build_cached_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt optimized for caching.

        Prompt caching works best with:
        - Static content (docs, code, guidelines)
        - Frequent reuse (>3 requests within 5 min)
        - Large context (>1024 tokens)

        Returns:
            System prompt with static content first (for caching)
        """
        parts = []

        # 1. Static content (CACHEABLE - goes first)
        if self.coding_standards:
            parts.append("# Coding Standards\n" + self.coding_standards)

        if self.style_guide:
            parts.append("# Style Guide\n" + self.style_guide)

        if context.get("documentation"):
            parts.append("# Documentation\n" + context["documentation"])

        if context.get("codebase_context"):
            parts.append("# Codebase Context\n" + context["codebase_context"])

        # 2. Dynamic content (NOT CACHEABLE - goes after cache boundary)
        # This will be in the user message, not system prompt

        return "\n\n".join(parts)
```

#### 2.3 Track Cache Performance

**File:** `src/attune/telemetry/usage_tracker.py`

**Add cache metrics:**
```python
@dataclass
class TokenUsage:
    """Token usage with cache metrics."""
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0  # NEW
    cache_read_tokens: int = 0      # NEW

    @property
    def total_tokens(self) -> int:
        """Total tokens including cache."""
        return (
            self.input_tokens +
            self.output_tokens +
            self.cache_creation_tokens +
            self.cache_read_tokens
        )

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of input tokens served from cache."""
        total_input = self.input_tokens + self.cache_read_tokens
        if total_input == 0:
            return 0.0
        return self.cache_read_tokens / total_input

    @property
    def estimated_cost_savings(self) -> float:
        """Estimated cost savings from caching (USD).

        Assumptions:
        - Cache reads: 90% discount vs full price
        - Cache writes: 25% markup vs full price
        - Using Sonnet 4.5 pricing ($3/M input tokens)
        """
        # Cost without caching
        full_price_per_token = 3.0 / 1_000_000
        cost_without_cache = (
            (self.input_tokens + self.cache_read_tokens) * full_price_per_token
        )

        # Cost with caching
        cache_read_price = full_price_per_token * 0.1  # 90% discount
        cache_write_price = full_price_per_token * 1.25  # 25% markup
        cost_with_cache = (
            (self.input_tokens * full_price_per_token) +
            (self.cache_creation_tokens * cache_write_price) +
            (self.cache_read_tokens * cache_read_price)
        )

        return cost_without_cache - cost_with_cache
```

#### 2.4 Add Cache Monitoring Dashboard

**File:** `src/attune/telemetry/cli.py`

**Add command:**
```python
@app.command()
def cache_stats(
    days: int = typer.Option(7, help="Days of history to analyze"),
    output_format: str = typer.Option("table", help="Output format (table/json)"),
):
    """Show prompt caching performance statistics.

    Displays:
    - Cache hit rate over time
    - Cost savings from caching
    - Top workflows benefiting from cache
    - Recommendations for optimization
    """
    from attune.telemetry import get_usage_tracker
    from rich.table import Table

    tracker = get_usage_tracker()
    stats = tracker.get_cache_stats(days=days)

    if output_format == "json":
        console.print_json(data=stats)
        return

    # Table format
    table = Table(title=f"Prompt Caching Stats (Last {days} Days)")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Cache Hit Rate", f"{stats['hit_rate']:.1%}")
    table.add_row("Total Cache Reads", f"{stats['total_reads']:,} tokens")
    table.add_row("Total Cache Writes", f"{stats['total_writes']:,} tokens")
    table.add_row("Estimated Savings", f"${stats['savings']:.2f}")
    table.add_row("Requests with Cache Hits", f"{stats['hit_count']:,}")
    table.add_row("Total Requests", f"{stats['total_requests']:,}")

    console.print(table)

    # Recommendations
    if stats['hit_rate'] < 0.3:
        console.print("\n[yellow]⚠ Cache hit rate is low (<30%)[/yellow]")
        console.print("Recommendations:")
        console.print("  - Increase reuse of system prompts across requests")
        console.print("  - Group similar requests together (5-min cache TTL)")
        console.print("  - Consider using workflow batching")
```

### Success Criteria
- [ ] Prompt caching enabled by default in provider
- [ ] Cache-aware system prompt builder
- [ ] Cache metrics tracked in telemetry
- [ ] Cache monitoring dashboard in CLI
- [ ] Documentation on optimizing for cache hits
- [ ] Achieve >50% cache hit rate in test workflows
- [ ] Verify 20-30% cost reduction for cached workflows

### Estimated Impact
- **Cost Reduction:** 20-30% for workflows with repeated context
- **Break-even:** After 3 requests with same context
- **Best Use Cases:** Code review, repeated analysis, iterative workflows

---

## 🧠 Track 3: Thinking Mode for Complex Tasks

### Objective
Enable Anthropic's extended thinking mode for premium tier tasks to improve reasoning quality.

### Background
Extended Thinking (announced Dec 2024):
- **Extended reasoning** before generating response
- **Up to 1M thinking tokens** (not billed to user)
- **Better performance** on complex logical/analytical tasks
- **Available on:** Sonnet 4.5 and Opus 4.5
- **Use cases:** Mathematical reasoning, code architecture, complex analysis

### Implementation Steps

#### 3.1 Add Thinking Mode to Model Registry

**File:** `src/attune/models/registry.py`

**Update model definitions:**
```python
# Capable tier - Sonnet 4.5 with thinking support
ModelInfo(
    provider="anthropic",
    id="claude-sonnet-4-6",
    tier="capable",
    input_price=3.00,
    output_price=15.00,
    max_tokens=8192,
    supports_tools=True,
    supports_vision=True,
    supports_thinking=True,  # NEW
    thinking_enabled_by_default=False,  # NEW: Only for premium tasks
),

# Premium tier - Opus 4.5 with thinking support
ModelInfo(
    provider="anthropic",
    id="claude-opus-4-5-20251101",
    tier="premium",
    input_price=15.00,
    output_price=75.00,
    max_tokens=8192,
    supports_tools=True,
    supports_vision=True,
    supports_thinking=True,  # NEW
    thinking_enabled_by_default=True,  # NEW: Always use for premium
),
```

#### 3.2 Update Provider to Support Thinking Mode

**File:** `attune_llm/providers.py`

**Add thinking support:**
```python
def complete(
    self,
    messages: List[Dict[str, str]],
    model: str = "claude-sonnet-4-5",
    system_prompt: str | None = None,
    enable_thinking: bool | None = None,  # NEW
    **kwargs
) -> Dict[str, Any]:
    """Complete a prompt with optional extended thinking.

    Args:
        messages: Conversation messages
        model: Model ID
        system_prompt: System prompt
        enable_thinking: Override thinking mode (None uses model default)
        **kwargs: Additional API parameters

    Returns:
        API response with thinking blocks (if enabled)
    """
    # Determine if thinking should be enabled
    use_thinking = enable_thinking if enable_thinking is not None else self.enable_thinking

    # Build request
    request_params = {
        "model": model,
        "messages": messages,
        "max_tokens": kwargs.get("max_tokens", 4096),
    }

    if system_prompt:
        request_params["system"] = system_prompt

    # Enable thinking mode
    if use_thinking:
        request_params["thinking"] = {
            "type": "enabled",
            "budget_tokens": kwargs.get("thinking_budget", 10000)
        }

    response = self.client.messages.create(**request_params)

    # Extract thinking content if present
    result = response.model_dump()
    if use_thinking and response.content:
        thinking_blocks = [
            block for block in response.content
            if block.get("type") == "thinking"
        ]
        result["thinking"] = thinking_blocks

    return result
```

#### 3.3 Auto-Enable for Complex Tasks

**File:** `src/attune/models/tasks.py`

**Add thinking-required tasks:**
```python
# Tasks that benefit from extended thinking
THINKING_REQUIRED_TASKS = {
    # Architecture & Design
    "architectural_decision",
    "design_system",
    "design_api",
    "design_database",

    # Complex Analysis
    "analyze_security",
    "analyze_performance",
    "root_cause_analysis",
    "impact_analysis",

    # Strategic Planning
    "coordinate",
    "synthesis",
    "strategic_planning",
    "technical_strategy",

    # Complex Problem Solving
    "debug_complex",
    "optimize_algorithm",
    "solve_mathematical",
    "prove_correctness",
}
```

**Update ModelRouter:**
```python
class ModelRouter:
    def route(
        self,
        task_type: str,
        context: Dict[str, Any] | None = None
    ) -> Tuple[ModelInfo, bool]:
        """Route task to appropriate model.

        Returns:
            Tuple of (model_info, enable_thinking)
        """
        # Determine tier
        if task_type in CHEAP_TASKS:
            tier = "cheap"
        elif task_type in PREMIUM_TASKS or task_type in THINKING_REQUIRED_TASKS:
            tier = "premium"
        else:
            tier = "capable"

        model = self.get_model("anthropic", tier)

        # Enable thinking for complex tasks
        enable_thinking = (
            task_type in THINKING_REQUIRED_TASKS and
            model.supports_thinking
        )

        return model, enable_thinking
```

#### 3.4 Add CLI Support

**File:** `src/attune/cli.py`

**Add option to workflow commands:**
```python
@app.command()
def workflow_run(
    workflow_id: str,
    input_data: str = typer.Option(None, help="JSON input data"),
    enable_thinking: bool = typer.Option(False, help="Enable extended thinking mode"),
):
    """Run a workflow with optional thinking mode.

    Example:
        attune workflow run code-review --enable-thinking --input '{"file": "foo.py"}'
    """
    # ... existing code ...

    # Pass thinking flag to workflow
    result = workflow.execute(
        input_data=data,
        enable_thinking=enable_thinking
    )
```

#### 3.5 Display Thinking Process

**File:** `src/attune/workflows/base.py`

**Add method to display thinking:**
```python
def _display_thinking(self, response: Dict[str, Any]):
    """Display thinking process if available."""
    if "thinking" not in response:
        return

    from rich.panel import Panel

    for block in response["thinking"]:
        thinking_text = block.get("thinking", "")

        console.print(Panel(
            thinking_text,
            title="🧠 Extended Thinking",
            border_style="cyan",
            padding=(1, 2)
        ))
```

### Success Criteria
- [ ] Thinking mode integrated in model registry
- [ ] Provider supports thinking API parameter
- [ ] Auto-enabled for THINKING_REQUIRED_TASKS
- [ ] CLI option to manually enable thinking
- [ ] Display thinking process in output
- [ ] Quality improvement measured on test set
- [ ] Documentation on when to use thinking

### Estimated Impact
- **Quality Improvement:** 15-20% on complex reasoning tasks
- **Use Cases:** Architecture decisions, security analysis, debugging
- **Cost:** Free (thinking tokens not billed)

---

## 📊 Track 4: Precise Token Counting

### Objective
Replace rough token estimates with Anthropic's official token counter for accurate cost tracking.

### Background
Current implementation uses rough estimate (4 chars per token). Anthropic provides:
- **Accurate token counting** via SDK
- **Model-specific tokenization** (different models may tokenize differently)
- **Billing-accurate counts** matching API charges

### Implementation Steps

#### 4.1 Add Token Counter Utility

**File:** `attune_llm/utils/tokens.py` (NEW)

```python
"""Token counting utilities using Anthropic's tokenizer."""

from typing import List, Dict, Any
from anthropic import Anthropic

# Initialize client for token counting
_client = Anthropic()


def count_tokens(
    text: str,
    model: str = "claude-sonnet-4-5"
) -> int:
    """Count tokens using Anthropic's tokenizer.

    Args:
        text: Text to tokenize
        model: Model ID (different models may have different tokenizers)

    Returns:
        Exact token count as would be billed by API

    Example:
        >>> count_tokens("Hello, world!")
        4
    """
    # Use Anthropic's count_tokens method
    result = _client.count_tokens(text)
    return result


def count_message_tokens(
    messages: List[Dict[str, str]],
    system_prompt: str | None = None,
    model: str = "claude-sonnet-4-5"
) -> Dict[str, int]:
    """Count tokens in a conversation.

    Args:
        messages: List of message dicts
        system_prompt: Optional system prompt
        model: Model ID

    Returns:
        Dict with token counts by component

    Example:
        >>> messages = [{"role": "user", "content": "Hello!"}]
        >>> count_message_tokens(messages, system_prompt="You are helpful")
        {"system": 4, "messages": 6, "total": 10}
    """
    counts = {}

    # Count system prompt
    if system_prompt:
        counts["system"] = count_tokens(system_prompt, model)
    else:
        counts["system"] = 0

    # Count messages
    message_text = "\n".join(
        f"{msg['role']}: {msg['content']}"
        for msg in messages
    )
    counts["messages"] = count_tokens(message_text, model)

    # Total
    counts["total"] = counts["system"] + counts["messages"]

    return counts


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-sonnet-4-5"
) -> float:
    """Estimate cost in USD.

    Args:
        input_tokens: Input token count
        output_tokens: Output token count
        model: Model ID

    Returns:
        Estimated cost in USD

    Example:
        >>> estimate_cost(1000, 500, "claude-sonnet-4-5")
        0.0105  # $3/M input + $15/M output
    """
    from attune.models import get_model_by_id

    model_info = get_model_by_id(model)
    if not model_info:
        raise ValueError(f"Unknown model: {model}")

    input_cost = (input_tokens / 1_000_000) * model_info.input_price
    output_cost = (output_tokens / 1_000_000) * model_info.output_price

    return input_cost + output_cost
```

#### 4.2 Replace Rough Estimates

**File:** `attune_llm/providers.py`

**Update AnthropicProvider:**
```python
from attune_llm.utils.tokens import count_message_tokens, estimate_cost

class AnthropicProvider:
    # ... existing code ...

    def estimate_tokens(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None = None,
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, int]:
        """Estimate tokens BEFORE making API call.

        Use this to:
        - Validate input size before API call
        - Estimate costs for budgeting
        - Warn users about large requests

        Returns:
            Dict with token counts (system, messages, total)
        """
        return count_message_tokens(messages, system_prompt, model)

    def calculate_actual_cost(self, response: Dict[str, Any]) -> float:
        """Calculate actual cost from API response.

        Args:
            response: API response with usage stats

        Returns:
            Actual cost in USD
        """
        usage = response.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        model = response.get("model", "claude-sonnet-4-5")

        # Include cache tokens if present
        cache_creation = usage.get("cache_creation_input_tokens", 0)
        cache_read = usage.get("cache_read_input_tokens", 0)

        # Calculate costs
        base_cost = estimate_cost(input_tokens, output_tokens, model)

        # Adjust for cache (if used)
        if cache_creation or cache_read:
            from attune.models import get_model_by_id
            model_info = get_model_by_id(model)

            # Cache writes: 25% markup
            cache_write_cost = (cache_creation / 1_000_000) * model_info.input_price * 1.25

            # Cache reads: 90% discount
            cache_read_cost = (cache_read / 1_000_000) * model_info.input_price * 0.1

            base_cost += cache_write_cost + cache_read_cost

        return base_cost
```

#### 4.3 Add Pre-Request Validation

**File:** `src/attune/workflows/base.py`

**Add validation:**
```python
class BaseWorkflow:
    def __init__(self, max_input_tokens: int = 100_000):
        """Initialize workflow.

        Args:
            max_input_tokens: Maximum input tokens allowed (safety limit)
        """
        self.max_input_tokens = max_input_tokens

    def _validate_request_size(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str | None = None,
        model: str = "claude-sonnet-4-5"
    ):
        """Validate request size before API call.

        Raises:
            ValueError: If request exceeds max_input_tokens
        """
        from attune_llm.utils.tokens import count_message_tokens

        counts = count_message_tokens(messages, system_prompt, model)

        if counts["total"] > self.max_input_tokens:
            raise ValueError(
                f"Request too large: {counts['total']:,} tokens "
                f"(max: {self.max_input_tokens:,})"
            )

        # Warn if approaching limit
        if counts["total"] > self.max_input_tokens * 0.8:
            logger.warning(
                f"Request is large: {counts['total']:,} tokens "
                f"({counts['total']/self.max_input_tokens:.0%} of max)"
            )
```

#### 4.4 Update Telemetry

**File:** `src/attune/telemetry/usage_tracker.py`

**Track accurate costs:**
```python
class UsageTracker:
    def track_request(
        self,
        workflow_id: str,
        model: str,
        response: Dict[str, Any]
    ):
        """Track request with accurate cost calculation."""
        from attune_llm.providers import AnthropicProvider

        provider = AnthropicProvider()
        actual_cost = provider.calculate_actual_cost(response)

        usage = response.get("usage", {})

        self._records.append({
            "timestamp": datetime.now(),
            "workflow": workflow_id,
            "model": model,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens", 0),
            "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
            "cost": actual_cost,  # Accurate cost
        })
```

### Success Criteria
- [ ] Token counting utility using Anthropic SDK
- [ ] Replace all rough estimates with accurate counts
- [ ] Pre-request validation with token counts
- [ ] Accurate cost tracking in telemetry
- [ ] CLI command to estimate costs before running
- [ ] Documentation on token counting
- [ ] Cost accuracy within 1% of actual bills

### Estimated Impact
- **Cost Tracking:** Accurate to within 1% (vs 10-20% error)
- **Budget Management:** Better cost predictions
- **Optimization:** Identify actual token usage patterns

---

## 🎨 Track 5: Vision Workflows

### Objective
Create workflows that leverage Claude's vision capabilities for image analysis, OCR, and visual debugging.

### Background
Claude Vision (Sonnet 4.5, Opus 4.5):
- **Multi-modal understanding** (text + images)
- **OCR capabilities** (extract text from images)
- **Visual reasoning** (understand charts, diagrams, UI)
- **Code screenshots** (debug from error screenshots)
- **Supported formats:** PNG, JPEG, GIF, WebP

### Implementation Steps

#### 5.1 Add Vision Support to Provider

**File:** `attune_llm/providers.py`

**Add image handling:**
```python
import base64
from pathlib import Path

class AnthropicProvider:
    # ... existing code ...

    def complete_with_images(
        self,
        messages: List[Dict[str, Any]],  # Now supports image content
        model: str = "claude-sonnet-4-5",
        system_prompt: str | None = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Complete a prompt with text and images.

        Args:
            messages: Messages with text and/or image content
            model: Model ID (must support vision)
            system_prompt: System prompt

        Message format with images:
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "<base64_data>"
                            }
                        }
                    ]
                }
            ]

        Returns:
            API response
        """
        from attune.models import get_model_by_id

        # Validate model supports vision
        model_info = get_model_by_id(model)
        if not model_info or not model_info.supports_vision:
            raise ValueError(f"Model {model} does not support vision")

        # Build request
        request_params = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_prompt:
            request_params["system"] = system_prompt

        return self.client.messages.create(**request_params).model_dump()

    @staticmethod
    def load_image(image_path: str) -> Dict[str, Any]:
        """Load image file and encode as base64.

        Args:
            image_path: Path to image file

        Returns:
            Image content block for API

        Example:
            >>> image = provider.load_image("screenshot.png")
            >>> messages = [{
            ...     "role": "user",
            ...     "content": [
            ...         {"type": "text", "text": "What error is shown?"},
            ...         image
            ...     ]
            ... }]
        """
        path = Path(image_path)

        # Validate file exists
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Determine media type
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(path.suffix.lower())
        if not media_type:
            raise ValueError(f"Unsupported image format: {path.suffix}")

        # Encode as base64
        image_data = base64.b64encode(path.read_bytes()).decode("utf-8")

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data
            }
        }
```

#### 5.2 Create Image Analysis Workflow

**File:** `src/attune/workflows/image_analysis.py` (NEW)

```python
"""Image analysis workflow using Claude Vision."""

from typing import List, Dict, Any
from pathlib import Path
import logging

from attune.workflows.base import BaseWorkflow
from attune_llm.providers import AnthropicProvider

logger = logging.getLogger(__name__)


class ImageAnalysisWorkflow(BaseWorkflow):
    """Analyze images using Claude Vision."""

    def __init__(self):
        super().__init__()
        self.provider = AnthropicProvider()

    def analyze_image(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail.",
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, Any]:
        """Analyze a single image.

        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            model: Vision-capable model

        Returns:
            Analysis result with description

        Example:
            >>> workflow = ImageAnalysisWorkflow()
            >>> result = workflow.analyze_image(
            ...     "screenshot.png",
            ...     "What error is shown in this screenshot?"
            ... )
            >>> print(result["analysis"])
        """
        # Load image
        image = self.provider.load_image(image_path)

        # Build message
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                image
            ]
        }]

        # Analyze
        response = self.provider.complete_with_images(
            messages=messages,
            model=model
        )

        # Extract text content
        content = response.get("content", [])
        text = " ".join(
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        )

        return {
            "success": True,
            "image": image_path,
            "analysis": text,
            "model": model,
            "usage": response.get("usage", {})
        }

    def extract_text_ocr(
        self,
        image_path: str,
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, Any]:
        """Extract text from image (OCR).

        Args:
            image_path: Path to image with text
            model: Vision-capable model

        Returns:
            Extracted text
        """
        return self.analyze_image(
            image_path,
            prompt=(
                "Extract all text from this image. "
                "Preserve formatting and structure. "
                "Return only the extracted text, no commentary."
            ),
            model=model
        )

    def analyze_diagram(
        self,
        image_path: str,
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, Any]:
        """Analyze a technical diagram or chart.

        Args:
            image_path: Path to diagram/chart
            model: Vision-capable model

        Returns:
            Analysis of diagram structure and content
        """
        return self.analyze_image(
            image_path,
            prompt=(
                "Analyze this technical diagram or chart. Describe:\n"
                "1. The type of diagram (flowchart, architecture, UML, etc.)\n"
                "2. The main components and their relationships\n"
                "3. The flow or data flow if applicable\n"
                "4. Any issues or improvements you notice"
            ),
            model=model
        )

    def debug_from_screenshot(
        self,
        screenshot_path: str,
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, Any]:
        """Debug an error from a screenshot.

        Args:
            screenshot_path: Path to error screenshot
            model: Vision-capable model

        Returns:
            Debug analysis with fix suggestions
        """
        return self.analyze_image(
            screenshot_path,
            prompt=(
                "Analyze this error screenshot. Provide:\n"
                "1. What error occurred\n"
                "2. The likely root cause\n"
                "3. Step-by-step fix instructions\n"
                "4. How to prevent this error in the future"
            ),
            model=model
        )

    def compare_images(
        self,
        image1_path: str,
        image2_path: str,
        prompt: str = "What are the differences between these two images?",
        model: str = "claude-sonnet-4-5"
    ) -> Dict[str, Any]:
        """Compare two images.

        Args:
            image1_path: First image
            image2_path: Second image
            prompt: Comparison prompt
            model: Vision-capable model

        Returns:
            Comparison analysis
        """
        # Load both images
        image1 = self.provider.load_image(image1_path)
        image2 = self.provider.load_image(image2_path)

        # Build message with both images
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                image1,
                image2
            ]
        }]

        # Analyze
        response = self.provider.complete_with_images(
            messages=messages,
            model=model
        )

        content = response.get("content", [])
        text = " ".join(
            block.get("text", "")
            for block in content
            if block.get("type") == "text"
        )

        return {
            "success": True,
            "images": [image1_path, image2_path],
            "comparison": text,
            "model": model,
            "usage": response.get("usage", {})
        }
```

#### 5.3 Add CLI Commands

**File:** `src/attune/cli.py`

**Add image commands:**
```python
@app.command()
def image_analyze(
    image_path: str = typer.Argument(..., help="Path to image file"),
    prompt: str = typer.Option(
        "Describe this image in detail.",
        help="Analysis prompt"
    ),
    model: str = typer.Option("claude-sonnet-4-5", help="Vision model"),
):
    """Analyze an image using Claude Vision.

    Example:
        attune image-analyze screenshot.png --prompt "What error is shown?"
    """
    from attune.workflows.image_analysis import ImageAnalysisWorkflow

    workflow = ImageAnalysisWorkflow()

    console.print(f"[cyan]Analyzing {image_path}...[/cyan]")

    result = workflow.analyze_image(image_path, prompt, model)

    if result["success"]:
        console.print("\n[green]Analysis:[/green]")
        console.print(result["analysis"])

        usage = result["usage"]
        console.print(f"\n[dim]Tokens: {usage['input_tokens']:,} in, {usage['output_tokens']:,} out[/dim]")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


@app.command()
def image_ocr(
    image_path: str = typer.Argument(..., help="Path to image with text"),
    output_file: str = typer.Option(None, help="Save extracted text to file"),
):
    """Extract text from image (OCR).

    Example:
        attune image-ocr document.png --output-file text.txt
    """
    from attune.workflows.image_analysis import ImageAnalysisWorkflow

    workflow = ImageAnalysisWorkflow()

    console.print(f"[cyan]Extracting text from {image_path}...[/cyan]")

    result = workflow.extract_text_ocr(image_path)

    if result["success"]:
        extracted_text = result["analysis"]

        console.print("\n[green]Extracted Text:[/green]")
        console.print(extracted_text)

        if output_file:
            Path(output_file).write_text(extracted_text)
            console.print(f"\n[cyan]Saved to: {output_file}[/cyan]")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


@app.command()
def image_debug(
    screenshot_path: str = typer.Argument(..., help="Path to error screenshot"),
):
    """Debug an error from a screenshot.

    Example:
        attune image-debug error_screenshot.png
    """
    from attune.workflows.image_analysis import ImageAnalysisWorkflow
    from rich.panel import Panel

    workflow = ImageAnalysisWorkflow()

    console.print(f"[cyan]Analyzing error in {screenshot_path}...[/cyan]")

    result = workflow.debug_from_screenshot(screenshot_path)

    if result["success"]:
        console.print(Panel(
            result["analysis"],
            title="🐛 Debug Analysis",
            border_style="red"
        ))
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")
```

#### 5.4 Add Tests

**File:** `tests/unit/workflows/test_image_analysis.py` (NEW)

```python
"""Tests for image analysis workflow."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from attune.workflows.image_analysis import ImageAnalysisWorkflow


class TestImageAnalysisWorkflow:
    """Test suite for image analysis."""

    @patch("attune_llm.providers.AnthropicProvider")
    def test_analyze_image(self, mock_provider, tmp_path):
        """Test basic image analysis."""
        # Create test image
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image data")

        # Mock response
        mock_provider.return_value.complete_with_images.return_value = {
            "content": [{"type": "text", "text": "A test image"}],
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }

        workflow = ImageAnalysisWorkflow()
        result = workflow.analyze_image(str(test_image))

        assert result["success"]
        assert "test image" in result["analysis"].lower()

    @patch("attune_llm.providers.AnthropicProvider")
    def test_extract_text_ocr(self, mock_provider, tmp_path):
        """Test OCR text extraction."""
        test_image = tmp_path / "document.png"
        test_image.write_bytes(b"fake document")

        mock_provider.return_value.complete_with_images.return_value = {
            "content": [{"type": "text", "text": "Extracted text from document"}],
            "usage": {"input_tokens": 200, "output_tokens": 10}
        }

        workflow = ImageAnalysisWorkflow()
        result = workflow.extract_text_ocr(str(test_image))

        assert result["success"]
        assert "Extracted text" in result["analysis"]

    def test_load_image_not_found(self):
        """Test that loading non-existent image raises error."""
        from attune_llm.providers import AnthropicProvider

        with pytest.raises(FileNotFoundError):
            AnthropicProvider.load_image("nonexistent.png")

    def test_load_image_unsupported_format(self, tmp_path):
        """Test that unsupported format raises error."""
        from attune_llm.providers import AnthropicProvider

        test_file = tmp_path / "test.txt"
        test_file.write_text("not an image")

        with pytest.raises(ValueError, match="Unsupported image format"):
            AnthropicProvider.load_image(str(test_file))
```

### Success Criteria
- [ ] Vision support added to provider
- [ ] Image analysis workflow implemented
- [ ] OCR, diagram analysis, debug workflows
- [ ] CLI commands for image operations
- [ ] Unit tests with mocked responses
- [ ] Documentation with examples
- [ ] Successfully analyze 10+ real images

### Estimated Impact
- **New Capabilities:** Image analysis, OCR, visual debugging
- **Use Cases:** Error screenshots, diagram analysis, document processing
- **User Value:** Multi-modal understanding

---

## 🔄 Track 6: Streaming Support

### Objective
Add real-time streaming for long-running workflows to improve perceived performance and user experience.

### Background
Anthropic Streaming:
- **Server-Sent Events (SSE)** for real-time chunks
- **Token-by-token delivery** reduces perceived latency
- **Better UX** for long responses (>500 tokens)
- **Same pricing** as non-streaming

### Implementation Steps

#### 6.1 Add Streaming to Provider

**File:** `attune_llm/providers.py`

**Add streaming method:**
```python
from typing import Iterator

class AnthropicProvider:
    # ... existing code ...

    def complete_streaming(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-5",
        system_prompt: str | None = None,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Stream completion chunks in real-time.

        Args:
            messages: Conversation messages
            model: Model ID
            system_prompt: System prompt
            **kwargs: Additional parameters

        Yields:
            Chunk dicts with incremental content

        Example:
            >>> for chunk in provider.complete_streaming(messages):
            ...     print(chunk["delta"], end="", flush=True)
        """
        request_params = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True  # Enable streaming
        }

        if system_prompt:
            request_params["system"] = system_prompt

        # Stream response
        with self.client.messages.stream(**request_params) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    yield {
                        "type": "content",
                        "delta": event.delta.text,
                        "done": False
                    }
                elif event.type == "message_stop":
                    yield {
                        "type": "done",
                        "delta": "",
                        "done": True,
                        "usage": event.message.usage
                    }
```

#### 6.2 Create Streaming Workflow Base

**File:** `src/attune/workflows/base.py`

**Add streaming support:**
```python
from typing import Iterator

class BaseWorkflow:
    # ... existing code ...

    def execute_streaming(
        self,
        input_data: Dict[str, Any],
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Execute workflow with streaming output.

        Yields:
            Progress updates and incremental results

        Example:
            >>> for chunk in workflow.execute_streaming(data):
            ...     if chunk["type"] == "progress":
            ...         print(f"Progress: {chunk['message']}")
            ...     elif chunk["type"] == "content":
            ...         print(chunk["delta"], end="", flush=True)
        """
        yield {"type": "progress", "message": "Preparing request..."}

        # Build prompt
        messages = self._build_messages(input_data)
        system_prompt = self._build_system_prompt(input_data)

        yield {"type": "progress", "message": "Streaming response..."}

        # Stream completion
        for chunk in self.provider.complete_streaming(
            messages=messages,
            system_prompt=system_prompt,
            **kwargs
        ):
            yield chunk

        yield {"type": "progress", "message": "Complete!"}
```

#### 6.3 Add Streaming CLI

**File:** `src/attune/cli.py`

**Add streaming option:**
```python
@app.command()
def chat_stream(
    message: str = typer.Argument(..., help="Your message"),
    model: str = typer.Option("claude-sonnet-4-5", help="Model to use"),
):
    """Interactive chat with streaming responses.

    Example:
        attune chat-stream "Explain async programming in Python"
    """
    from attune_llm.providers import AnthropicProvider
    from rich.live import Live
    from rich.markdown import Markdown

    provider = AnthropicProvider()

    messages = [{"role": "user", "content": message}]

    console.print("[cyan]Claude:[/cyan] ", end="")

    response_text = ""
    with Live(console=console, refresh_per_second=10) as live:
        for chunk in provider.complete_streaming(messages, model=model):
            if chunk["type"] == "content":
                response_text += chunk["delta"]
                live.update(Markdown(response_text))
            elif chunk["type"] == "done":
                usage = chunk.get("usage", {})
                console.print(f"\n\n[dim]Tokens: {usage.get('output_tokens', 0)}[/dim]")
```

### Success Criteria
- [ ] Streaming implemented in provider
- [ ] Streaming workflow base class
- [ ] CLI command with live updates
- [ ] Handle connection errors gracefully
- [ ] Display token usage after stream
- [ ] Documentation on when to use streaming

### Estimated Impact
- **UX Improvement:** Perceived latency reduction
- **Use Cases:** Long responses, interactive chat
- **User Satisfaction:** Real-time feedback

---

## 📏 Track 7: Max Tokens Optimization

### Objective
Set tier-appropriate max_tokens limits to avoid unnecessary costs.

### Implementation

**File:** `src/attune/models/registry.py`

**Update max_tokens:**
```python
# Cheap tier - Lower limit for cost control
ModelInfo(
    provider="anthropic",
    id="claude-3-5-haiku-20241022",
    tier="cheap",
    max_tokens=2048,  # Reduced from 8192
    # ...
),

# Capable tier - Moderate limit
ModelInfo(
    provider="anthropic",
    id="claude-sonnet-4-6",
    tier="capable",
    max_tokens=4096,  # Reduced from 8192
    # ...
),

# Premium tier - Higher limit
ModelInfo(
    provider="anthropic",
    id="claude-opus-4-5-20251101",
    tier="premium",
    max_tokens=8192,  # Keep at 8192
    # ...
),
```

**Success Criteria:**
- [ ] Tier-appropriate max_tokens set
- [ ] No workflow failures due to truncation
- [ ] Minor cost savings (<5%)

---

## 📅 Implementation Schedule

### Week 1: Foundational Improvements
**Days 1-3:**
- [ ] Track 2: Enable prompt caching by default
- [ ] Track 4: Implement precise token counting
- [ ] Track 7: Optimize max_tokens by tier

**Days 4-5:**
- [ ] Testing and validation
- [ ] Update documentation
- [ ] Track cache hit rates

### Week 2: Batch API & Thinking Mode
**Days 1-3:**
- [ ] Track 1: Implement Batch API client
- [ ] Track 1: Create batch workflow
- [ ] Track 1: Add CLI commands

**Days 4-5:**
- [ ] Track 3: Implement thinking mode
- [ ] Track 3: Auto-enable for complex tasks
- [ ] Testing and validation

### Week 3: Vision & Streaming
**Days 1-3:**
- [ ] Track 5: Implement vision workflows
- [ ] Track 5: Add image analysis CLI
- [ ] Track 5: Create OCR and debug workflows

**Days 4-5:**
- [ ] Track 6: Implement streaming
- [ ] Track 6: Add streaming CLI
- [ ] Testing and validation

### Week 4: Polish & Documentation
**Days 1-2:**
- [ ] Integration testing across all tracks
- [ ] Performance benchmarking
- [ ] Fix any issues

**Days 3-4:**
- [ ] Complete documentation
- [ ] Create usage examples
- [ ] Write migration guide

**Day 5:**
- [ ] Final review
- [ ] Release preparation
- [ ] Announcement

---

## 📊 Success Metrics

### Cost Reduction
- [ ] 30-50% reduction for batch-eligible workflows
- [ ] 20-30% reduction for cache-heavy workflows
- [ ] Overall 25%+ cost reduction across all workflows

### Quality Improvement
- [ ] 15-20% better reasoning on complex tasks (thinking mode)
- [ ] Zero accuracy loss on existing workflows

### New Capabilities
- [ ] Vision workflows operational
- [ ] OCR with >95% accuracy
- [ ] Streaming for responses >500 tokens

### Operational Excellence
- [ ] Cost tracking accurate to <1% error
- [ ] Cache hit rate >50% for repeated contexts
- [ ] Token counting precise (SDK-based)

---

## 🔍 Testing Strategy

### Unit Tests
- [ ] Each track has 80%+ code coverage
- [ ] Mock Anthropic API responses
- [ ] Test error handling

### Integration Tests
- [ ] End-to-end workflow tests
- [ ] Real API calls (limited, in CI)
- [ ] Cross-track interactions

### Performance Tests
- [ ] Benchmark before/after
- [ ] Cost tracking validation
- [ ] Cache hit rate monitoring

### User Acceptance
- [ ] Test with real use cases
- [ ] Gather feedback
- [ ] Iterate based on findings

---

## 📝 Documentation Plan

### User Documentation
- [ ] Update README with new features
- [ ] Add vision workflow examples
- [ ] Document batch API usage
- [ ] Explain when to use thinking mode

### Developer Documentation
- [ ] API reference for new methods
- [ ] Architecture diagrams
- [ ] Migration guide from v3.9 → v4.0

### Operations
- [ ] Monitoring dashboards
- [ ] Cost optimization guide
- [ ] Troubleshooting common issues

---

## ⚠️ Risks & Mitigation

### Risk 1: Batch API Adoption
**Risk:** Users may not understand 24-hour delay
**Mitigation:** Clear documentation, warnings in CLI, alternative workflows

### Risk 2: Vision Cost
**Risk:** Images increase token costs significantly
**Mitigation:** Pre-request cost estimation, warnings for large images

### Risk 3: Breaking Changes
**Risk:** New features may break existing code
**Mitigation:** Backward compatibility, deprecation warnings, version bumps

### Risk 4: Cache Hit Rate
**Risk:** Cache hit rate may be lower than expected
**Mitigation:** Monitoring, optimization recommendations, documentation

---

## 🎯 Next Steps

1. **Review this plan** with team
2. **Prioritize tracks** based on business needs
3. **Assign owners** to each track
4. **Set up tracking** (GitHub project, issues)
5. **Begin implementation** following schedule

---

**Questions or feedback?**
- Open discussion in GitHub Discussions
- Slack: #attune-ai-dev
- Email: engineering@empathyframework.com

**Document Version:** 1.0
**Last Updated:** January 16, 2026
**Next Review:** End of Week 1
