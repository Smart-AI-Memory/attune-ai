"""Run SEO workflow with in-memory backend (no Redis needed).

This script demonstrates how to run the SEO workflow with an in-memory backend
so agent activity can be tracked WITHOUT needing Redis.
"""

import asyncio
from pathlib import Path

# Import memory backend FIRST - must be done before any other empathy imports
from attune.coordination import InMemoryHeartbeatBackend
from attune.memory import ShortTermMemory


async def main():
    """Run SEO workflow with in-memory backend."""
    print("=" * 70)
    print("SEO Optimization with In-Memory Backend (No Redis Required)")
    print("=" * 70)
    print()

    # Step 1: Create in-memory backend
    print("📦 Setting up in-memory backend...")
    memory_backend = InMemoryHeartbeatBackend()
    memory = ShortTermMemory(backend=memory_backend)

    print("✅ In-memory backend initialized")
    print()

    # Step 2: Configure UsageTracker to use this memory
    print("🔧 Configuring telemetry to use in-memory backend...")
    from attune.telemetry import UsageTracker

    tracker = UsageTracker.get_instance()
    tracker._memory = memory

    print("✅ Telemetry configured")
    print()

    # Step 3: Now import and run workflow (after backend is set up)
    print("🚀 Starting SEO workflow...")
    print()

    from attune.workflows import SEOOptimizationWorkflow

    workflow = SEOOptimizationWorkflow()
    result = await workflow.execute(
        docs_path=Path("../../docs"),
        site_url="https://smartaimemory.com",
        mode="audit",
        interactive=False,
    )

    print()
    print("=" * 70)
    print("✅ Workflow Complete")
    print("=" * 70)
    print()

    if result.success:
        # Get results from stages
        scan_data = None
        analyze_data = None

        for stage in result.stages:
            if stage.name == "scan":
                scan_data = stage.result if isinstance(stage.result, dict) else {}
            elif stage.name == "analyze":
                analyze_data = stage.result if isinstance(stage.result, dict) else {}

        print(f"📁 Files scanned: {scan_data.get('file_count', 0) if scan_data else 0}")
        print(f"⚠️  Issues found: {analyze_data.get('total_issues', 0) if analyze_data else 0}")
        print(f"💰 Cost: ${result.cost_report.total_cost:.4f}")
        print(f"💾 Savings: {result.cost_report.savings_percent:.1f}%")
    else:
        print(f"❌ Error: {result.error}")

    print()
    print("=" * 70)
    print("📊 Next Steps")
    print("=" * 70)
    print()
    print("Agent tracking data is available in the memory backend.")
    print("Use scripts/monitor_agents.py to view live status.")
    print()
    print("⚠️  Note: In-memory backend data is ephemeral")
    print("   For persistent tracking, use Redis instead")
    print()


if __name__ == "__main__":
    asyncio.run(main())
