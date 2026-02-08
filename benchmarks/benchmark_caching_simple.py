#!/usr/bin/env python
"""Simplified benchmark - just code-review and security-audit workflows."""

import asyncio
import time
from pathlib import Path

from attune.cache import create_cache
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.security_audit import SecurityAuditWorkflow


async def benchmark_code_review(cache):
    """Benchmark code-review workflow."""
    print("🔍 Testing: Code Review")

    test_diff = """
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -15,10 +15,15 @@ class AuthManager:
     def authenticate(self, username: str, password: str) -> bool:
         user = self.get_user(username)
         if user is None:
+            logger.warning(f"Failed login for {username}")
             return False
-        return user.check_password(password)
+        return user.verify_password(password)
"""

    workflow = CodeReviewWorkflow(use_crew=False, cache=cache, enable_cache=True)

    # Clear cache to ensure Run 1 is cold
    cache.clear()

    # Run 1 (cold cache - should be 0% hit rate)
    print("  ▶ Run 1 (cold cache)...")
    start = time.time()
    r1 = await workflow.execute(diff=test_diff, files_changed=["src/auth.py"], is_core_module=False)
    t1 = time.time() - start

    # Run 2 (warm cache - should be ~100% hit rate)
    print("  ▶ Run 2 (warm cache)...")
    start = time.time()
    r2 = await workflow.execute(diff=test_diff, files_changed=["src/auth.py"], is_core_module=False)
    t2 = time.time() - start

    print("\n  Results:")
    print(
        f"    Run 1: ${r1.cost_report.total_cost:.6f} ({t1:.1f}s) - {r1.cost_report.cache_hit_rate:.0f}% hit rate"
    )
    print("      Tier breakdown:")
    print(f"        CHEAP:   ${r1.cost_report.by_tier.get('cheap', 0):.6f}")
    print(f"        CAPABLE: ${r1.cost_report.by_tier.get('capable', 0):.6f}")
    print(f"        PREMIUM: ${r1.cost_report.by_tier.get('premium', 0):.6f}")
    print(
        f"    Run 2: ${r2.cost_report.total_cost:.6f} ({t2:.1f}s) - {r2.cost_report.cache_hit_rate:.0f}% hit rate"
    )
    print("      Tier breakdown:")
    print(f"        CHEAP:   ${r2.cost_report.by_tier.get('cheap', 0):.6f}")
    print(f"        CAPABLE: ${r2.cost_report.by_tier.get('capable', 0):.6f}")
    print(f"        PREMIUM: ${r2.cost_report.by_tier.get('premium', 0):.6f}")
    print(f"    Savings: ${r2.cost_report.savings_from_cache:.6f}")
    print()

    return r1, r2


async def benchmark_security_audit(cache):
    """Benchmark security-audit workflow."""
    print("🔍 Testing: Security Audit")

    # Create test file
    test_dir = Path("/tmp/empathy_security_test")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "app.py"
    test_file.write_text(
        """
import os

def run_command(user_input):
    # Command injection risk
    os.system(f"echo {user_input}")

def get_secret():
    password = "admin123"  # Hardcoded secret
    return password
"""
    )

    workflow = SecurityAuditWorkflow(cache=cache, enable_cache=True)

    try:
        # Clear cache to ensure Run 1 is cold
        cache.clear()

        # Run 1 (cold cache - should be 0% hit rate)
        print("  ▶ Run 1 (cold cache)...")
        start = time.time()
        r1 = await workflow.execute(target_path=str(test_dir))
        t1 = time.time() - start

        # Run 2 (warm cache - should be ~100% hit rate)
        print("  ▶ Run 2 (warm cache)...")
        start = time.time()
        r2 = await workflow.execute(target_path=str(test_dir))
        t2 = time.time() - start

        print("\n  Results:")
        print(
            f"    Run 1: ${r1.cost_report.total_cost:.6f} ({t1:.1f}s) - {r1.cost_report.cache_hit_rate:.0f}% hit rate"
        )
        print("      Tier breakdown:")
        print(f"        CHEAP:   ${r1.cost_report.by_tier.get('cheap', 0):.6f}")
        print(f"        CAPABLE: ${r1.cost_report.by_tier.get('capable', 0):.6f}")
        print(f"        PREMIUM: ${r1.cost_report.by_tier.get('premium', 0):.6f}")
        print(
            f"    Run 2: ${r2.cost_report.total_cost:.6f} ({t2:.1f}s) - {r2.cost_report.cache_hit_rate:.0f}% hit rate"
        )
        print("      Tier breakdown:")
        print(f"        CHEAP:   ${r2.cost_report.by_tier.get('cheap', 0):.6f}")
        print(f"        CAPABLE: ${r2.cost_report.by_tier.get('capable', 0):.6f}")
        print(f"        PREMIUM: ${r2.cost_report.by_tier.get('premium', 0):.6f}")
        print(f"    Savings: ${r2.cost_report.savings_from_cache:.6f}")
        print()

        return r1, r2
    finally:
        # Cleanup
        test_file.unlink(missing_ok=True)
        test_dir.rmdir()


async def main():
    print("=" * 80)
    print("  EMPATHY FRAMEWORK v3.8.0 - SIMPLIFIED CACHING BENCHMARK")
    print("=" * 80)
    print()
    print("Testing 2 workflows with hash-only cache:")
    print("  1. Code Review")
    print("  2. Security Audit")
    print()

    # Create cache
    cache = create_cache(cache_type="hash")

    # Run benchmarks
    results = []

    try:
        r = await benchmark_code_review(cache)
        results.append(("code-review", r))
    except Exception as e:
        print(f"  ❌ Error: {e}\n")

    try:
        r = await benchmark_security_audit(cache)
        results.append(("security-audit", r))
    except Exception as e:
        print(f"  ❌ Error: {e}\n")

    # Summary
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print()

    total_run1_cost = sum(r[0].cost_report.total_cost for _, r in results)
    total_run2_cost = sum(r[1].cost_report.total_cost for _, r in results)
    total_savings = sum(r[1].cost_report.savings_from_cache for _, r in results)
    avg_hit_rate = sum(r[1].cost_report.cache_hit_rate for _, r in results) / len(results)

    print(f"Total workflows tested: {len(results)}")
    print(f"Average cache hit rate (Run 2): {avg_hit_rate:.1f}%")
    print(f"Total cost without cache (Run 1): ${total_run1_cost:.6f}")
    print(f"Total cost with cache (Run 2): ${total_run2_cost:.6f}")
    print(f"Total savings from cache: ${total_savings:.6f}")
    print()
    print("✅ Benchmark complete!")
    print()
    print("Key Findings:")
    print(f"  • Cache hit rate improves to ~{avg_hit_rate:.0f}% on repeated runs")
    print(f"  • Cost savings: ~${total_savings:.6f} per repeated workflow")
    print("  • Works with hash-only cache (no ML dependencies)")
    print()
    print("Next steps:")
    print("  • Test with hybrid cache for ~70% hit rate")
    print("  • Run full benchmark with more workflows")
    print("  • Update CHANGELOG.md with findings")


if __name__ == "__main__":
    asyncio.run(main())
