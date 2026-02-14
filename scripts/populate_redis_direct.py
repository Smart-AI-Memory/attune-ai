#!/usr/bin/env python3
"""Directly populate Redis with test data for dashboard testing.

This script bypasses the telemetry API and writes directly to Redis,
useful for testing the dashboard without initializing the full framework.
"""

import itertools
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta

import redis


def generate_test_data():
    """Generate test data directly in Redis."""
    # Connect to Redis
    r = redis.Redis(host="localhost", port=6379, decode_responses=False)

    print("=" * 60)
    print("POPULATING REDIS DIRECTLY (NO API)")
    print("=" * 60)
    print()

    # Agent Types: Workflow-based + Role-based
    WORKFLOW_AGENTS = [
        ("code-review", "Analyzing code quality"),
        ("test-generation", "Generating unit tests"),
        ("security-audit", "Scanning for vulnerabilities"),
        ("refactoring", "Refactoring legacy code"),
        ("bug-predict", "Predicting potential bugs"),
    ]

    ROLE_AGENTS = [
        ("orchestrator", "Coordinating workflow pipeline"),
        ("validator", "Validating outputs"),
        ("monitor", "Monitoring system health"),
    ]

    # Combine all agents for heartbeats
    ALL_AGENTS = WORKFLOW_AGENTS + ROLE_AGENTS

    # Pattern 1: Agent Heartbeats
    print("📊 Pattern 1: Creating agent heartbeats...")
    agent_ids = []  # Track for use in signals

    for agent_name, default_task in ALL_AGENTS:
        # Create unique agent ID with run suffix
        agent_id = f"{agent_name}-{uuid.uuid4().hex[:6]}"
        agent_ids.append(agent_id)

        heartbeat_data = {
            "agent_id": agent_id,
            "status": secrets.choice(["running", "idle", "running", "running"]),
            "progress": int.from_bytes(os.urandom(4), "big") / (2**32),
            "current_task": default_task,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "demo": True,
                "type": "workflow" if agent_name in [a[0] for a in WORKFLOW_AGENTS] else "role",
            },
        }

        key = f"heartbeat:{agent_id}".encode()
        value = json.dumps(heartbeat_data).encode()
        r.setex(key, 60, value)  # 60 second TTL
        print(f"  ✓ {agent_id}: {heartbeat_data['status']} ({heartbeat_data['progress']*100:.0f}%)")

    print()

    # Pattern 2: Coordination Signals
    print("📡 Pattern 2: Creating coordination signals...")
    signal_types_with_context = [
        ("task_complete", "Task completed successfully"),
        ("request_help", "Requesting assistance"),
        ("ready", "Ready for next stage"),
        ("status_update", "Status update"),
        ("error", "Error encountered"),
        ("checkpoint", "Checkpoint reached"),
    ]

    for i in range(10):
        source = secrets.choice(agent_ids)
        target = secrets.choice(agent_ids)
        signal_type, message = secrets.choice(signal_types_with_context)

        signal_data = {
            "signal_id": f"signal_{uuid.uuid4().hex[:8]}",
            "signal_type": signal_type,
            "source_agent": source,
            "target_agent": target,
            "timestamp": datetime.utcnow().isoformat(),
            "ttl_seconds": 300,
            "payload": {"message": message, "demo": True},
        }

        # Key format matches CoordinationSignals API: attune:signal:{target}:{type}:{id}
        key = f"attune:signal:{target}:{signal_type}:{signal_data['signal_id']}".encode()
        value = json.dumps(signal_data).encode()
        r.setex(key, 300, value)  # 5 minute TTL

        # Show short names for readability
        source_short = source.split("-")[0]
        target_short = target.split("-")[0]
        print(f"  ✓ Signal: {source_short} → {target_short} ({signal_type})")
        time.sleep(0.01)  # Small delay for unique timestamps

    print()

    # Pattern 4: Event Streaming
    print("📤 Pattern 4: Creating events...")
    for i in range(15):
        event_data = {
            "event_id": f"event-{int(time.time() * 1000)}-{i}",
            "event_type": secrets.choice(
                ["workflow_progress", "agent_heartbeat", "coordination_signal"]
            ),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "workflow": secrets.choice(["code-review", "test-generation", "refactoring"]),
                "stage": secrets.choice(["analysis", "generation", "validation"]),
                "progress": int.from_bytes(os.urandom(4), "big") / (2**32),
                "demo": True,
            },
            "source": f"agent-{secrets.randbelow(5) + 1}",
        }

        # Add to stream
        stream_key = f"stream:{event_data['event_type']}".encode()
        r.xadd(stream_key, {b"data": json.dumps(event_data).encode()}, maxlen=1000)
        print(f"  ✓ Event {i+1} added to stream")
        time.sleep(0.01)

    print()

    # Pattern 5: Approval Requests
    print("✋ Pattern 5: Creating approval requests...")
    for i in range(2):
        request_id = f"approval-{int(time.time() * 1000)}-{i}"
        approval_data = {
            "request_id": request_id,
            "approval_type": secrets.choice(
                ["deploy_to_staging", "delete_old_data", "refactor_module"]
            ),
            "agent_id": "demo-workflow",
            "context": {"version": "1.0.0", "demo": True},
            "timestamp": datetime.utcnow().isoformat(),
            "timeout_seconds": 300.0,
        }

        key = f"approval:pending:{request_id}".encode()
        value = json.dumps(approval_data).encode()
        r.setex(key, 300, value)  # 5 minute TTL
        print(f"  ✓ Approval request {i+1}: {approval_data['approval_type']}")
        time.sleep(0.1)

    print()

    # Pattern 6: Quality Feedback
    print("📊 Pattern 6: Creating quality feedback...")
    workflows = ["code-review", "test-generation", "refactoring"]
    stages = ["analysis", "generation", "validation"]
    tiers = ["cheap", "capable", "premium"]

    tier_quality = {"cheap": 0.65, "capable": 0.80, "premium": 0.90}
    feedback_count = 0
    pipe = r.pipeline()

    for workflow, stage, tier in itertools.product(workflows, stages, tiers):
        num_samples = secrets.randbelow(6) + 10
        base_quality = tier_quality[tier]

        for j in range(num_samples):
            quality = base_quality + (int.from_bytes(os.urandom(4), "big") / (2**32) * 0.15 - 0.075)
            quality = max(0.0, min(1.0, quality))  # Clamp to 0-1

            feedback_id = f"fb-{int(time.time() * 1000)}-{feedback_count}"
            feedback_data = {
                "workflow_name": workflow,
                "stage_name": stage,
                "tier": tier,
                "quality_score": quality,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"demo": True, "tokens": secrets.randbelow(251) + 50},
            }

            key = f"feedback:{workflow}:{stage}:{tier}:{feedback_id}".encode()
            value = json.dumps(feedback_data).encode()
            pipe.setex(key, 604800, value)  # 7 day TTL
            feedback_count += 1

        print(f"  ✓ {workflow}/{stage}/{tier}: {num_samples} samples")

    pipe.execute()  # Single round-trip to Redis

    print()
    print("=" * 60)
    print("✅ REDIS POPULATED SUCCESSFULLY")
    print("=" * 60)
    print()
    print(f"Total keys in Redis: {r.dbsize()}")
    print()
    print("🚀 Now you can start the dashboard:")
    print("   python examples/dashboard_demo.py")
    print()
    print("   Or directly:")
    print("   python -m src.attune.dashboard.simple_server")


if __name__ == "__main__":
    generate_test_data()
