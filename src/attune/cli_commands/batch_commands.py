"""Batch processing CLI commands.

Commands for submitting, monitoring, and retrieving Anthropic Batch API jobs.
Batch API processes requests within 24 hours at 50% of standard pricing.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

logger = logging.getLogger(__name__)


def _get_api_key() -> str | None:
    """Get Anthropic API key from environment.

    Returns:
        API key string or None if not set.
    """
    return os.getenv("ANTHROPIC_API_KEY")


def cmd_batch_submit(args: Namespace) -> int:
    """Submit a batch of requests from a JSON file.

    Loads requests, validates them, and submits to the Anthropic
    Message Batches API without waiting for completion.

    Args:
        args: Parsed CLI arguments with input_file attribute.

    Returns:
        0 on success, 1 on failure.
    """
    from attune.config import _validate_file_path
    from attune.models import get_model

    api_key = _get_api_key()
    if not api_key:
        print("❌ Missing ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    try:
        validated_path = _validate_file_path(args.input_file)
        if not validated_path.exists():
            print(f"❌ File not found: {args.input_file}")
            return 1

        print(f"📤 Submitting batch from {validated_path}...")

        from attune.workflows.batch_processing import BatchProcessingWorkflow

        workflow = BatchProcessingWorkflow(api_key=api_key)
        requests = workflow.load_requests_from_file(str(validated_path))

        print(f"  Found {len(requests)} requests")

        # Convert to API format (same logic as execute_batch)
        api_requests = []
        for req in requests:
            model = get_model("anthropic", req.model_tier)
            if model is None:
                print(f"❌ Unknown model tier: {req.model_tier}")
                return 1

            api_requests.append(
                {
                    "custom_id": req.task_id,
                    "params": {
                        "model": model.id,
                        "messages": workflow._format_messages(req),
                        "max_tokens": 12000,
                    },
                }
            )

        # Submit without waiting
        batch_id = workflow.batch_provider.create_batch(api_requests)

        print("\n✅ Batch submitted successfully!")
        print(f"   Batch ID: {batch_id}")
        print(f"\nMonitor status with: attune batch status {batch_id}")
        print(f"Retrieve results with: attune batch results {batch_id} output.json")
        print(
            f"Or wait for completion: attune batch wait {batch_id} output.json"
            f" --poll-interval 300"
        )
        return 0

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in input file: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"❌ Validation error: {e}")
        return 1
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands catch all errors and report gracefully
        logger.exception(f"Batch submit failed: {e}")
        print(f"❌ Batch submit failed: {e}")
        return 1


def cmd_batch_status(args: Namespace) -> int:
    """Check status of a batch job.

    Args:
        args: Parsed CLI arguments with batch_id and optional json flag.

    Returns:
        0 on success, 1 on failure.
    """
    api_key = _get_api_key()
    if not api_key:
        print("❌ Missing ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    try:
        from attune.llm.providers import AnthropicBatchProvider

        provider = AnthropicBatchProvider(api_key=api_key)
        batch_id = args.batch_id

        print(f"🔍 Checking status for batch {batch_id}...")

        status = provider.get_batch_status(batch_id)

        if hasattr(args, "json") and args.json:
            status_dict: dict = {
                "id": batch_id,
                "processing_status": status.processing_status,
            }
            try:
                counts = status.request_counts
                status_dict["request_counts"] = {
                    "processing": counts.processing,
                    "succeeded": counts.succeeded,
                    "errored": counts.errored,
                    "canceled": counts.canceled,
                    "expired": counts.expired,
                }
            except AttributeError:
                pass
            print(json.dumps(status_dict, indent=2, default=str))
        else:
            print("\n📊 Batch Status:")
            print(f"   ID: {batch_id}")
            print(f"   Processing Status: {status.processing_status}")

            try:
                counts = status.request_counts
                print("\n📈 Request Counts:")
                print(f"   Processing: {counts.processing}")
                print(f"   Succeeded: {counts.succeeded}")
                print(f"   Errored: {counts.errored}")
                print(f"   Canceled: {counts.canceled}")
                print(f"   Expired: {counts.expired}")
            except AttributeError:
                pass

            if status.processing_status == "ended":
                print("\n✅ Batch complete. Retrieve results with:")
                print(f"   attune batch results {batch_id} output.json")
            else:
                print("\n⏳ Batch still processing...")

        return 0

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands catch all errors and report gracefully
        logger.exception(f"Batch status check failed: {e}")
        print(f"❌ Batch status check failed: {e}")
        return 1


def cmd_batch_results(args: Namespace) -> int:
    """Download results from a completed batch.

    Args:
        args: Parsed CLI arguments with batch_id and output_file.

    Returns:
        0 on success, 1 on failure.
    """
    from attune.config import _validate_file_path

    api_key = _get_api_key()
    if not api_key:
        print("❌ Missing ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    try:
        validated_output = _validate_file_path(args.output_file)

        from attune.llm.providers import AnthropicBatchProvider

        provider = AnthropicBatchProvider(api_key=api_key)
        batch_id = args.batch_id

        print(f"📥 Retrieving results for batch {batch_id}...")

        results = provider.get_batch_results(batch_id)

        with validated_output.open("w") as f:
            json.dump(results, f, indent=2, default=str)

        succeeded = sum(1 for r in results if r.get("result", {}).get("type") == "succeeded")
        errored = sum(1 for r in results if r.get("result", {}).get("type") == "errored")

        print(f"\n✅ Results saved to {validated_output}")
        print(f"   Total: {len(results)} results")
        print(f"   Succeeded: {succeeded}")
        print(f"   Errored: {errored}")
        return 0

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"❌ Error: {e}")
        return 1
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands catch all errors and report gracefully
        logger.exception(f"Batch results retrieval failed: {e}")
        print(f"❌ Batch results retrieval failed: {e}")
        return 1


def cmd_batch_wait(args: Namespace) -> int:
    """Wait for batch to complete, then download results.

    Polls the batch status at the specified interval until processing
    ends, then saves results to the output file.

    Args:
        args: Parsed CLI arguments with batch_id, output_file,
            poll_interval, and timeout.

    Returns:
        0 on success, 1 on failure.
    """
    from attune.config import _validate_file_path

    api_key = _get_api_key()
    if not api_key:
        print("❌ Missing ANTHROPIC_API_KEY environment variable.")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        return 1

    try:
        validated_output = _validate_file_path(args.output_file)

        from attune.llm.providers import AnthropicBatchProvider

        provider = AnthropicBatchProvider(api_key=api_key)
        batch_id = args.batch_id
        poll_interval = args.poll_interval
        timeout = args.timeout

        print(f"⏳ Waiting for batch {batch_id} to complete...")
        print(f"   Polling every {poll_interval}s (max {timeout}s)")

        results = asyncio.run(
            provider.wait_for_batch(
                batch_id,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        )

        with validated_output.open("w") as f:
            json.dump(results, f, indent=2, default=str)

        succeeded = sum(1 for r in results if r.get("result", {}).get("type") == "succeeded")
        errored = sum(1 for r in results if r.get("result", {}).get("type") == "errored")

        print(f"\n✅ Batch completed! Results saved to {validated_output}")
        print(f"   Total: {len(results)} results")
        print(f"   Succeeded: {succeeded}")
        print(f"   Errored: {errored}")
        return 0

    except TimeoutError as e:
        logger.error(f"Batch timed out: {e}")
        print(f"❌ Batch timed out after {args.timeout}s.")
        print(f"Check status with: attune batch status {args.batch_id}")
        return 1
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"❌ Error: {e}")
        return 1
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: CLI commands catch all errors and report gracefully
        logger.exception(f"Batch wait failed: {e}")
        print(f"❌ Batch wait failed: {e}")
        return 1
