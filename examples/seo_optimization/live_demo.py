"""Live demo showing SEO workflow with agent coordination.

Run this to see agents coordinating in real-time.

Usage:
    python examples/seo_optimization/live_demo.py
"""

import asyncio
from pathlib import Path

from attune.workflows import SEOOptimizationWorkflow


async def main():
    """Run SEO optimization workflow with agent tracking."""
    print("=" * 70)
    print("SEO Optimization - Live Agent Coordination Demo")
    print("=" * 70)
    print("\n💡 Starting SEO optimization workflow...")
    print("\nStarting in 5 seconds...")
    await asyncio.sleep(5)

    # Initialize workflow with coordination enabled
    workflow = SEOOptimizationWorkflow()

    print("\n🚀 Running SEO audit on Attune AI documentation...")
    print("   Watch the output to see:")
    print("   - Agent heartbeat updates")
    print("   - Stage progression (scan → analyze)")
    print("   - Cost accumulation\n")

    # Run the workflow
    result = await workflow.execute(
        docs_path=Path("../../docs"),
        site_url="https://smartaimemory.com",
        mode="audit",
    )

    print("\n" + "=" * 70)
    print("Results:")
    print("=" * 70)

    if result.success:
        # Extract results from stages
        for stage in result.stages:
            if stage.name == "scan" and not stage.skipped:
                scan_output = stage.result if isinstance(stage.result, dict) else {}
                files_scanned = scan_output.get("file_count", 0)
                print(f"📁 Files scanned: {files_scanned}")

            elif stage.name == "analyze" and not stage.skipped:
                analyze_output = stage.result if isinstance(stage.result, dict) else {}
                issues_found = analyze_output.get("total_issues", 0)
                print(f"⚠️  SEO issues found: {issues_found}")

        print(f"\n💰 Total cost: ${result.cost_report.total_cost:.4f}")
        print(f"💾 Savings: {result.cost_report.savings_percent:.1f}%")

        print(f"\n⏱️  Execution time: {result.total_duration_ms / 1000:.2f}s")
        print(f"🎯 Provider: {result.provider}")

    else:
        print(f"❌ Error: {result.error}")

    print("\n" + "=" * 70)
    print("✅ Demo complete!")
    print("=" * 70)
    print("\n💡 The agent has completed. Check heartbeat history for details.\n")


if __name__ == "__main__":
    asyncio.run(main())
