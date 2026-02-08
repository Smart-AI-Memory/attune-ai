"""Test authentication strategy for subscription vs API routing.

Demonstrates:
1. Module size-based routing
2. Cost estimation comparison
3. Pros/cons display for user education
"""

from pathlib import Path

from attune.models import (
    AuthMode,
    AuthStrategy,
    SubscriptionTier,
    count_lines_of_code,
    get_module_size_category,
)


def test_auth_strategy():
    """Test authentication strategy functionality."""
    print("🔐 Testing Authentication Strategy\n")
    print("=" * 60)

    # Test different subscription tiers
    print("\n1. Testing Pro User (Recommended → API)")
    pro_strategy = AuthStrategy(subscription_tier=SubscriptionTier.PRO, default_mode=AuthMode.AUTO)

    small_module = 300  # 300 LOC
    medium_module = 1000  # 1000 LOC
    large_module = 3000  # 3000 LOC

    print(
        f"   Small module ({small_module} LOC): {pro_strategy.get_recommended_mode(small_module).value}"
    )
    print(
        f"   Medium module ({medium_module} LOC): {pro_strategy.get_recommended_mode(medium_module).value}"
    )
    print(
        f"   Large module ({large_module} LOC): {pro_strategy.get_recommended_mode(large_module).value}"
    )

    print("\n2. Testing Max User (Recommended → Dynamic)")
    max_strategy = AuthStrategy(subscription_tier=SubscriptionTier.MAX, default_mode=AuthMode.AUTO)

    print(
        f"   Small module ({small_module} LOC): {max_strategy.get_recommended_mode(small_module).value}"
    )
    print(
        f"   Medium module ({medium_module} LOC): {max_strategy.get_recommended_mode(medium_module).value}"
    )
    print(
        f"   Large module ({large_module} LOC): {max_strategy.get_recommended_mode(large_module).value}"
    )

    # Test cost estimation
    print("\n3. Cost Estimation Comparison (1000 LOC module)")
    print("=" * 60)

    sub_cost = max_strategy.estimate_cost(medium_module, AuthMode.SUBSCRIPTION)
    api_cost = max_strategy.estimate_cost(medium_module, AuthMode.API)

    print("\n   Subscription Mode:")
    print(f"      Monetary cost: ${sub_cost['monetary_cost']}")
    print(f"      Quota cost: {sub_cost['quota_cost']}")
    print(f"      Tokens used: {sub_cost['tokens_used']:,}")
    print(f"      Fits in 200K context: {sub_cost['fits_in_context']}")

    print("\n   API Mode:")
    print(f"      Monetary cost: ${api_cost['monetary_cost']}")
    print(f"      Quota cost: {api_cost['quota_cost']}")
    print(f"      Tokens used: {api_cost['tokens_used']:,}")
    print(f"      Fits in 1M context: {api_cost['fits_in_context']}")

    # Test pros/cons comparison
    print("\n4. Pros/Cons Comparison (for user education)")
    print("=" * 60)

    comparison = max_strategy.get_pros_cons(medium_module)

    for _mode_name, mode_data in comparison.items():
        print(f"\n   ### {mode_data['name']}")
        print(f"   Cost: {mode_data['cost']}")
        print("\n   Pros:")
        for pro in mode_data["pros"][:2]:  # Show first 2 pros
            print(f"      ✓ {pro}")
        print("\n   Cons:")
        for con in mode_data["cons"][:2]:  # Show first 2 cons
            print(f"      ✗ {con}")

    # Test module size calculation
    print("\n5. Real Module Size Detection")
    print("=" * 60)

    test_files = [
        "src/attune/cache_stats.py",
        "src/attune/config.py",
        "src/attune/workflows/document_gen.py",
    ]

    for file_path in test_files:
        path = Path(file_path)
        if path.exists():
            lines = count_lines_of_code(path)
            category = get_module_size_category(lines)
            recommended = max_strategy.get_recommended_mode(lines)
            print(f"\n   {path.name}:")
            print(f"      Lines: {lines}")
            print(f"      Category: {category}")
            print(f"      Recommended: {recommended.value}")
        else:
            print(f"\n   {file_path}: Not found")

    # Test recommendation summary
    print("\n6. Recommendation Summary")
    print("=" * 60)

    print("\n   For PRO users ($20/month):")
    print("      → Use API (pay-per-token more economical)")
    print("      → Cost: ~$0.10-0.15 per module")

    print("\n   For MAX users ($200/month):")
    print("      → Use AUTO mode (smart routing)")
    print("      → Small/medium modules → Subscription (saves money)")
    print("      → Large modules → API (1M context window)")

    print("\n   Module Size Thresholds:")
    print(f"      Small: < {max_strategy.small_module_threshold} LOC")
    print(
        f"      Medium: {max_strategy.small_module_threshold}-{max_strategy.medium_module_threshold} LOC"
    )
    print(f"      Large: > {max_strategy.medium_module_threshold} LOC")

    print("\n" + "=" * 60)
    print("✅ Authentication Strategy Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_auth_strategy()
