#!/usr/bin/env python3
"""Test Approval Gates - Interactive Demo

This script creates approval requests and waits for you to approve/reject them.

Usage:
    python scripts/test_approval_gates.py
"""

import time
from datetime import datetime

from attune.telemetry import ApprovalGate


def create_test_approvals():
    """Create several test approval requests for demonstration."""
    gate = ApprovalGate(agent_id="demo-workflow")

    print("=" * 60)
    print("🚦 APPROVAL GATES DEMO")
    print("=" * 60)
    print("\nThis demo will create 3 approval requests.")
    print("You can approve or reject each request via the API.")
    print("=" * 60)

    # Approval 1: Deploy to Production
    print("\n📋 Request 1: Deploy to Production")
    print("   Creating approval request...")

    response = gate.request_approval(
        approval_type="deploy_to_production",
        context={
            "version": "5.0.0",
            "changes": 60,
            "risk": "medium",
            "timestamp": datetime.utcnow().isoformat(),
        },
        timeout=60.0,  # Wait 60 seconds
    )

    print(f"   ✅ Response received!")
    print(f"   Approved: {response.approved}")
    print(f"   Responder: {response.responder}")
    print(f"   Reason: {response.reason}")

    if not response.approved:
        print("\n❌ Deployment blocked by human review")
        return

    # Approval 2: Delete Resources
    print("\n📋 Request 2: Delete Resources")
    print("   Creating approval request...")

    response = gate.request_approval(
        approval_type="delete_resources",
        context={
            "resource_type": "database_records",
            "count": 1000,
            "impact": "high",
        },
        timeout=60.0,
    )

    print(f"   ✅ Response received!")
    print(f"   Approved: {response.approved}")
    print(f"   Responder: {response.responder}")
    print(f"   Reason: {response.reason}")

    # Approval 3: Refactor Code
    print("\n📋 Request 3: Refactor Code")
    print("   Creating approval request...")

    response = gate.request_approval(
        approval_type="refactor_code",
        context={
            "files": 50,
            "lines_changed": 5000,
            "risk": "low",
        },
        timeout=60.0,
    )

    print(f"   ✅ Response received!")
    print(f"   Approved: {response.approved}")
    print(f"   Responder: {response.responder}")
    print(f"   Reason: {response.reason}")

    print("\n" + "=" * 60)
    print("✅ DEMO COMPLETE")
    print("=" * 60)


def create_background_approval():
    """Create a single approval request that stays pending."""
    gate = ApprovalGate(agent_id="background-agent")

    print("\n🔄 Creating a persistent approval request...")
    print("This will stay pending until you approve/reject it.")

    gate.request_approval(
        approval_type="run_expensive_operation",
        context={
            "operation": "Train ML model",
            "estimated_cost": "$50",
            "estimated_time": "2 hours",
        },
        timeout=600.0,  # 10 minutes
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--background":
        # Create one that stays pending
        create_background_approval()
    else:
        # Interactive demo
        create_test_approvals()
