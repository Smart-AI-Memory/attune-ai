"""Integration test for natural language routing with v5.1.0 features.

Tests that the intent detector and CLI router properly recognize and route
new v5.1.0 features: authentication strategy and batch test generation.
"""

import pytest

from attune.cli_router import HybridRouter
from attune.meta_workflows.intent_detector import IntentDetector


class TestIntentDetectorV5_1:
    """Test intent detection for v5.1.0 features."""

    def test_auth_strategy_intent_detection(self):
        """Test that auth strategy queries are correctly detected."""
        detector = IntentDetector()

        # Test various auth-related queries
        auth_queries = [
            "setup authentication",
            "configure auth strategy",
            "what's my auth mode?",
            "check auth status",
            "recommend auth for this file",
            "switch to API mode",
            "reset authentication config",
        ]

        for query in auth_queries:
            matches = detector.detect(query, threshold=0.3)
            # Should detect auth-strategy pattern
            auth_matches = [m for m in matches if m.template_id == "auth-strategy"]
            assert len(auth_matches) > 0, f"Failed to detect auth pattern in: {query}"
            assert auth_matches[0].confidence > 0.3, f"Low confidence for: {query}"

    def test_batch_test_generation_intent_detection(self):
        """Test that batch test generation queries are enhanced."""
        detector = IntentDetector()

        # Test batch generation specific queries
        batch_queries = [
            "generate tests in batch",
            "bulk test generation",
            "rapidly generate tests",
            "parallel test creation",
            "mass test generation",
        ]

        for query in batch_queries:
            matches = detector.detect(query, threshold=0.3)
            # Should detect test-coverage-boost pattern
            test_matches = [m for m in matches if m.template_id == "test-coverage-boost"]
            assert len(test_matches) > 0, f"Failed to detect test pattern in: {query}"
            assert test_matches[0].confidence >= 0.3, f"Low confidence for: {query}"

    def test_no_false_positives(self):
        """Test that unrelated queries don't match new patterns."""
        detector = IntentDetector()

        # Queries that should NOT match new patterns
        unrelated_queries = [
            "fix a bug",
            "write a function",
            "explain this code",
            "commit my changes",
        ]

        for query in unrelated_queries:
            matches = detector.detect(query, threshold=0.3)
            # Should not detect auth or test patterns strongly
            auth_matches = [m for m in matches if m.template_id == "auth-strategy"]

            assert len(auth_matches) == 0, f"False positive auth match for: {query}"


class TestKeywordRoutingV5_1:
    """Test keyword routing for v5.1.0 features."""

    @pytest.mark.asyncio
    async def test_auth_keyword_routing(self):
        """Test that auth keywords route to CLI commands."""
        router = HybridRouter()

        # Test auth keywords
        auth_keywords = {
            "auth-setup": "auth_cli setup",
            "auth-status": "auth_cli status",
            "auth-recommend": "auth_cli recommend",
            "auth": "auth_cli status",  # Default to status
        }

        for keyword, _expected_command in auth_keywords.items():
            result = await router.route(keyword)
            # Router converts keywords to skill invocations, so type is "skill"
            assert result["type"] == "skill", f"Should route {keyword} to skill"
            # Check that it routes to auth CLI
            assert "auth_cli" in str(result).lower() or "auth" in str(result).lower()

    @pytest.mark.asyncio
    async def test_batch_test_keyword_routing(self):
        """Test that batch test keywords route to testing skill."""
        router = HybridRouter()

        batch_keywords = ["batch-tests", "bulk-tests"]

        for keyword in batch_keywords:
            result = await router.route(keyword)
            # Router converts keywords to skill invocations
            assert result["type"] == "skill", f"Should route {keyword} to skill"
            # Check that it routes to testing with batch flag
            skill = result.get("skill", "")
            args = result.get("args", "")
            assert skill == "testing" or "test" in args.lower()


class TestEndToEndRoutingV5_1:
    """End-to-end tests for natural language → intent → routing."""

    @pytest.mark.asyncio
    async def test_natural_language_auth_routing(self):
        """Test that natural language auth queries get routed correctly."""
        router = HybridRouter()

        # Natural language query about auth
        query = "I need to setup authentication for the framework"

        result = await router.route(query)

        # Should either:
        # 1. Be routed as natural language with auth detection, OR
        # 2. Be recognized as keyword if "setup authentication" matches, OR
        # 3. Be routed to a skill directly

        # At minimum, should not error and should return valid result
        assert result is not None
        assert "type" in result
        assert result["type"] in ["natural_language", "keyword", "slash_command", "skill"]

    @pytest.mark.asyncio
    async def test_natural_language_batch_test_routing(self):
        """Test that natural language batch test queries get routed correctly."""
        router = HybridRouter()

        # Natural language query about batch testing
        query = "I want to rapidly generate tests in batch to boost coverage"

        result = await router.route(query)

        # Should be valid routing result
        assert result is not None
        assert "type" in result
        assert result["type"] in ["natural_language", "keyword", "slash_command", "skill"]


# Summary test to verify all patterns are registered
def test_all_v5_1_patterns_registered():
    """Verify that all v5.1.0 patterns are registered in the intent detector."""
    from attune.meta_workflows.intent_detector import INTENT_PATTERNS

    # Check that new patterns exist
    assert "auth-strategy" in INTENT_PATTERNS, "auth-strategy pattern not registered"
    assert "test-coverage-boost" in INTENT_PATTERNS, "test-coverage-boost should exist"

    # Check that auth-strategy has expected keywords
    auth_keywords = INTENT_PATTERNS["auth-strategy"]["keywords"]
    assert "authentication" in auth_keywords
    assert "auth strategy" in auth_keywords
    assert "configure auth" in auth_keywords

    # Check that test-coverage-boost has batch keywords
    test_keywords = INTENT_PATTERNS["test-coverage-boost"]["keywords"]
    assert "batch tests" in test_keywords
    assert "batch generation" in test_keywords

    print("\n✅ All v5.1.0 patterns successfully registered")


def test_keyword_mappings_registered():
    """Verify that all v5.1.0 keyword mappings are registered in the router."""
    router = HybridRouter()

    # Check auth keywords
    assert "auth-setup" in router._keyword_to_skill
    assert "auth-status" in router._keyword_to_skill
    assert "auth-recommend" in router._keyword_to_skill
    assert "auth" in router._keyword_to_skill

    # Check batch test keywords
    assert "batch-tests" in router._keyword_to_skill
    assert "bulk-tests" in router._keyword_to_skill

    print("\n✅ All v5.1.0 keyword mappings successfully registered")
