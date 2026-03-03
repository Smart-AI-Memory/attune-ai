---
description: Batch API Integration Guide API reference: **Version:** 5.0.2 **Last Updated:** January 27, 2026 **Cost Savings:** 50% off standard pricing ---
---

# Batch API Integration Guide

**Version:** 5.0.2
**Last Updated:** January 27, 2026
**Cost Savings:** 50% off standard pricing

---

## Overview

Anthropic's Message Batches API enables asynchronous processing of multiple requests at 50% of standard API costs. Batches are processed within 24 hours, making this ideal for non-urgent, bulk operations.

**Key Features:**
- 50% cost reduction compared to real-time API
- Process up to 10,000 requests per batch
- Automatic retry and error handling
- Results delivered within 24 hours

**When to Use Batch API:**
- Log analysis and report generation
- Bulk content classification
- Test case generation
- Documentation generation
- Any non-urgent, parallelizable tasks

**When NOT to Use Batch API:**
- Interactive workflows requiring immediate responses
- Real-time user interactions
- Tasks requiring sequential dependencies

---

## Quick Start

### 1. Create a Batch Request File

Create a JSON file with your batch requests:

**`batch_requests.json`:**
```json
[
  {
    "task_id": "analyze_logs_1",
    "task_type": "analyze_logs",
    "input_data": {
      "logs": "2026-01-27 ERROR: Connection timeout to database\n2026-01-27 ERROR: Failed to process request"
    },
    "model_tier": "capable"
  },
  {
    "task_id": "generate_report_1",
    "task_type": "generate_report",
    "input_data": {
      "data": "Monthly metrics: 1000 users, 5000 requests, 99.9% uptime"
    },
    "model_tier": "cheap"
  }
]
```

**Field Descriptions:**
- `task_id`: Unique identifier for this task (required)
- `task_type`: Type of task - determines prompt template (required)
- `input_data`: Dict with task-specific input fields (required)
- `model_tier`: "cheap", "capable", or "premium" (optional, default: "capable")

### 2. Submit the Batch

```bash
attune batch submit batch_requests.json
```

**Output:**
```
📤 Submitting batch from batch_requests.json...
  Found 2 requests

✅ Batch submitted successfully!
   Batch ID: msgbatch_abc123xyz789

Monitor status with: attune batch status msgbatch_abc123xyz789
Retrieve results with: attune batch results msgbatch_abc123xyz789 output.json
Or wait for completion: attune batch wait msgbatch_abc123xyz789 output.json --poll-interval 300
```

### 3. Monitor Batch Status

```bash
attune batch status msgbatch_abc123xyz789
```

**Output:**
```
🔍 Checking status for batch msgbatch_abc123xyz789...

📊 Batch Status:
   ID: msgbatch_abc123xyz789
   Processing Status: in_progress
   Created: 2026-01-27T20:00:00Z

📈 Request Counts:
   Processing: 2
   Succeeded: 0
   Errored: 0
   Canceled: 0
   Expired: 0

⏳ Batch still processing...
```

### 4. Retrieve Results (When Complete)

**Option A: Wait for completion (recommended)**
```bash
attune batch wait msgbatch_abc123xyz789 results.json --poll-interval 300
```

This polls every 5 minutes (300 seconds) until completion, then automatically downloads results.

**Option B: Manually check and retrieve**
```bash
# Check if batch is done
attune batch status msgbatch_abc123xyz789

# Once processing_status is "ended", retrieve results
attune batch results msgbatch_abc123xyz789 results.json
```

**Output:**
```
⏳ Waiting for batch msgbatch_abc123xyz789 to complete...
   Polling every 300s (max 86400s)

✅ Batch completed! Results saved to results.json
   Total: 2 results
   Succeeded: 2
   Errored: 0
```

---

## Supported Task Types

The workflow includes pre-defined prompt templates for common tasks:

| Task Type | Input Fields | Use Case |
|-----------|--------------|----------|
| `analyze_logs` | `logs` | Analyze error logs and identify issues |
| `generate_report` | `data` | Generate reports from data |
| `classify_bulk` | `items` | Classify multiple items |
| `generate_docs` | `code` | Generate documentation from code |
| `generate_tests` | `code` | Generate unit tests for code |

**Custom task types**: If `task_type` doesn't match a pre-defined template, the framework uses a default prompt with your raw `input_data`.

---

## CLI Command Reference

### Submit Batch

```bash
attune batch submit <input_file>
```

**Arguments:**
- `input_file`: Path to JSON file with batch requests

**Example:**
```bash
attune batch submit requests.json
```

---

### Check Status

```bash
attune batch status <batch_id> [--json]
```

**Arguments:**
- `batch_id`: Batch identifier (e.g., `msgbatch_abc123`)
- `--json`: Output raw JSON status (optional)

**Example:**
```bash
attune batch status msgbatch_abc123 --json
```

---

### Retrieve Results

```bash
attune batch results <batch_id> <output_file>
```

**Arguments:**
- `batch_id`: Batch identifier
- `output_file`: Path to save results JSON

**Requirements:**
- Batch must have `processing_status: "ended"`

**Example:**
```bash
attune batch results msgbatch_abc123 results.json
```

---

### Wait for Completion

```bash
attune batch wait <batch_id> <output_file> [--poll-interval SECONDS] [--timeout SECONDS]
```

**Arguments:**
- `batch_id`: Batch identifier
- `output_file`: Path to save results JSON
- `--poll-interval`: Seconds between status checks (default: 300 = 5 minutes)
- `--timeout`: Maximum wait time in seconds (default: 86400 = 24 hours)

**Example:**
```bash
# Check every 5 minutes (default)
attune batch wait msgbatch_abc123 results.json

# Check every 10 minutes, timeout after 12 hours
attune batch wait msgbatch_abc123 results.json --poll-interval 600 --timeout 43200
```

---

## Python API Usage

### Basic Batch Processing

```python
import asyncio
from attune.workflows.batch_processing import (
    BatchProcessingWorkflow,
    BatchRequest,
)

# Create workflow
workflow = BatchProcessingWorkflow(api_key="your-api-key")

# Define requests
requests = [
    BatchRequest(
        task_id="task_1",
        task_type="analyze_logs",
        input_data={"logs": "ERROR: Connection failed"},
        model_tier="capable",
    ),
    BatchRequest(
        task_id="task_2",
        task_type="generate_report",
        input_data={"data": "Monthly metrics"},
        model_tier="cheap",
    ),
]

# Execute batch (async)
async def main():
    results = await workflow.execute_batch(
        requests,
        poll_interval=300,  # Check every 5 minutes
        timeout=86400,      # Max 24 hours
    )

    # Process results
    for result in results:
        if result.success:
            print(f"{result.task_id}: Success")
            print(f"  Content: {result.output['content']}")
            print(f"  Tokens: {result.output['usage']}")
        else:
            print(f"{result.task_id}: Failed - {result.error}")

asyncio.run(main())
```

### Load Requests from File

```python
from attune.workflows.batch_processing import BatchProcessingWorkflow

workflow = BatchProcessingWorkflow(api_key="your-api-key")

# Load from JSON file
requests = workflow.load_requests_from_file("batch_requests.json")

# Execute
results = await workflow.execute_batch(requests)

# Save results to file
workflow.save_results_to_file(results, "output.json")
```

### Direct Provider Usage

For more control, use `AnthropicBatchProvider` directly:

```python
from attune_llm.providers import AnthropicBatchProvider

provider = AnthropicBatchProvider(api_key="your-api-key")

# Format requests for Message Batches API
requests = [
    {
        "custom_id": "task_1",
        "params": {
            "model": "claude-sonnet-4-6",
            "messages": [{"role": "user", "content": "Analyze this log..."}],
            "max_tokens": 4096,
        },
    }
]

# Submit batch
batch_id = provider.create_batch(requests)
print(f"Batch created: {batch_id}")

# Wait for completion
results = await provider.wait_for_batch(
    batch_id,
    poll_interval=300,
    timeout=86400,
)

# Process results
for result in results:
    custom_id = result["custom_id"]
    result_data = result["result"]

    if result_data["type"] == "succeeded":
        message = result_data["message"]
        content = message["content"][0]["text"]
        print(f"{custom_id}: {content}")
    else:
        error = result_data["error"]
        print(f"{custom_id}: Error - {error['message']}")
```

---

## Result Format

Results are returned as a list of result objects:

```json
[
  {
    "custom_id": "task_1",
    "result": {
      "type": "succeeded",
      "message": {
        "content": [
          {
            "type": "text",
            "text": "Analysis: The logs show connection timeout errors..."
          }
        ],
        "usage": {
          "input_tokens": 150,
          "output_tokens": 75
        },
        "model": "claude-sonnet-4-6",
        "stop_reason": "end_turn"
      }
    }
  },
  {
    "custom_id": "task_2",
    "result": {
      "type": "errored",
      "error": {
        "type": "invalid_request_error",
        "message": "Invalid input format"
      }
    }
  }
]
```

**Result Types:**
- `succeeded`: Request completed successfully, contains `message` object
- `errored`: Request failed with error, contains `error` object
- `expired`: Request expired before processing (24-hour limit)
- `canceled`: Request was canceled

---

## Cost Savings Calculator

### Standard vs. Batch API Pricing

**Example: 1,000 log analysis requests**

| Tier | Model | Input Tokens | Output Tokens | Standard Cost | Batch Cost | Savings |
|------|-------|--------------|---------------|---------------|------------|---------|
| Cheap | Haiku | 500 | 200 | $0.125 + $0.250 = $0.375 | $0.188 | 50% ($0.188) |
| Capable | Sonnet 4.5 | 500 | 200 | $1.50 + $3.00 = $4.50 | $2.25 | 50% ($2.25) |
| Premium | Opus 4.0 | 500 | 200 | $7.50 + $15.00 = $22.50 | $11.25 | 50% ($11.25) |

**Total savings for 1,000 requests on capable tier: $2,250**

### When Batch API Makes Sense

**Minimum batch size for ROI:**
- Setup time: ~2 minutes
- Processing time: Up to 24 hours
- Ideal batch size: 100+ requests

**Break-even analysis:**
- Small batches (10-50 requests): ~10% savings after overhead
- Medium batches (100-500): ~45% savings
- Large batches (1,000+): Full 50% savings

---

## Best Practices

### 1. Batch Size Optimization

**Recommended:**
- Aim for 100-1,000 requests per batch
- Group similar tasks together
- Use consistent `model_tier` within batch

**Avoid:**
- Single-request batches (use real-time API instead)
- Mixing urgent and non-urgent tasks
- Batches >10,000 requests (split into multiple batches)

### 2. Error Handling

Always check result types:

```python
for result in results:
    result_type = result["result"]["type"]

    if result_type == "succeeded":
        # Process successful result
        message = result["result"]["message"]
        content = message["content"][0]["text"]

    elif result_type == "errored":
        # Log error and retry if needed
        error = result["result"]["error"]
        logger.error(f"Request failed: {error['message']}")

    elif result_type == "expired":
        # Resubmit expired requests
        logger.warning(f"Request expired, consider resubmitting")
```

### 3. Monitoring and Logging

Track batch performance:

```python
import logging

logger = logging.getLogger(__name__)

# Log batch submission
logger.info(f"Submitted batch {batch_id} with {len(requests)} requests")

# Log completion
logger.info(
    f"Batch {batch_id} completed: "
    f"{succeeded}/{total} succeeded, "
    f"{errored} errored"
)
```

### 4. Cost Tracking

Calculate actual costs:

```python
from attune.cost_tracker import log_request

for result in results:
    if result["result"]["type"] == "succeeded":
        usage = result["result"]["message"]["usage"]
        log_request(
            model="claude-sonnet-4-6",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            task_type="batch_processing",
            tier="capable",
        )
```

---

## Troubleshooting

### Batch Never Completes

**Symptoms:**
- `processing_status` stays "in_progress" for >24 hours
- Timeout error after maximum wait time

**Solutions:**
1. Check Anthropic API status: https://status.anthropic.com
2. Verify batch ID is correct
3. Contact Anthropic support with batch ID

### Some Requests Failed

**Symptoms:**
- `result.type == "errored"` for some requests
- Error messages like "invalid_request_error"

**Solutions:**
1. Check `input_data` format matches expected fields
2. Verify token counts don't exceed model limits
3. Review error messages for specific issues
4. Resubmit failed requests in new batch

### Results Missing After Retrieval

**Symptoms:**
- `processing_status` is "ended" but results are empty
- `results_url` returns 404

**Solutions:**
1. Verify batch completed recently (results expire after 24 hours)
2. Check network connectivity
3. Retry retrieval command

---

## Migration Guide

### From Real-Time API to Batch API

**Before (Real-time):**
```python
from attune.workflows.base import BaseWorkflow

class MyWorkflow(BaseWorkflow):
    async def execute(self, items):
        results = []
        for item in items:
            result = await self.llm.generate(...)
            results.append(result)
        return results
```

**After (Batch):**
```python
from attune.workflows.batch_processing import (
    BatchProcessingWorkflow,
    BatchRequest,
)

workflow = BatchProcessingWorkflow()
requests = [
    BatchRequest(
        task_id=f"item_{i}",
        task_type="process_item",
        input_data={"item": item},
    )
    for i, item in enumerate(items)
]
results = await workflow.execute_batch(requests)
```

**Key Differences:**
- Async batch submission vs. synchronous API calls
- 24-hour processing time vs. immediate results
- 50% cost savings vs. standard pricing
- Bulk error handling vs. per-request handling

---

## FAQ

**Q: Can I cancel a batch after submission?**
A: Yes, use `provider.cancel_batch(batch_id)`. Batches in "in_progress" status may complete before cancellation takes effect.

**Q: What's the maximum batch size?**
A: 10,000 requests per batch. For larger workloads, split into multiple batches.

**Q: How long are results available?**
A: Results are available for 24 hours after batch completion. Download promptly.

**Q: Can I use prompt caching with Batch API?**
A: Yes! Batch API supports all standard Message API features including prompt caching, which provides additional savings.

**Q: What happens if a request fails?**
A: Failed requests are marked as "errored" in results with error details. Other requests in the batch continue processing.

**Q: Can I mix different models in one batch?**
A: Yes, each request can specify its own model. However, grouping similar models may improve processing efficiency.

---

## Related Documentation

- [Cost Optimization Guide](./COST_OPTIMIZATION.md)
- [Prompt Caching Guide](./PROMPT_CACHING.md)
- [Token Counting Guide](./TOKEN_COUNTING.md)
- [Anthropic Batch API Docs](https://docs.claude.com/en/docs/build-with-claude/batch-processing)

---

## Support

**Issues with Batch API?**
- GitHub Issues: https://github.com/Smart-AI-Memory/attune-ai/issues
- Tag with: `batch-api`, `cost-optimization`
- Include batch ID and error messages

**Feature Requests:**
- Open a discussion on GitHub
- Share your use case and expected ROI

---

**Last Updated:** January 27, 2026
**Version:** 5.0.2
**Maintainer:** Attune AI Team
