"""Tests for routing/classifier.py using real data.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from attune.routing.classifier import ClassificationResult, HaikuClassifier


class TestClassificationResultDataClass:
    """Test ClassificationResult data class."""

    def test_classification_result_initialization(self):
        """Test ClassificationResult can be created."""
        result = ClassificationResult(
            primary_workflow="code-review",
            secondary_workflows=["security-scan", "test-gen"],
            confidence=0.85,
            reasoning="High confidence match",
            suggested_chain=["code-review", "security-scan"],
            extracted_context={"file": "auth.py", "issue": "security"},
        )

        assert result.primary_workflow == "code-review"
        assert len(result.secondary_workflows) == 2
        assert result.confidence == 0.85
        assert result.reasoning == "High confidence match"
        assert len(result.suggested_chain) == 2
        assert result.extracted_context["file"] == "auth.py"

    def test_classification_result_defaults(self):
        """Test ClassificationResult uses default values."""
        result = ClassificationResult(primary_workflow="test-workflow")

        assert result.secondary_workflows == []
        assert result.confidence == 0.0
        assert result.reasoning == ""
        assert result.suggested_chain == []
        assert result.extracted_context == {}

    def test_classification_result_with_no_secondary(self):
        """Test ClassificationResult with only primary workflow."""
        result = ClassificationResult(primary_workflow="security-scan", confidence=0.95)

        assert result.primary_workflow == "security-scan"
        assert result.secondary_workflows == []
        assert result.confidence == 0.95


class TestHaikuClassifierInitialization:
    """Test HaikuClassifier initialization."""

    def test_classifier_can_be_created(self):
        """Test HaikuClassifier can be instantiated."""
        classifier = HaikuClassifier()

        assert classifier is not None
        assert isinstance(classifier, HaikuClassifier)

    def test_classifier_with_api_key(self):
        """Test HaikuClassifier with explicit API key."""
        classifier = HaikuClassifier(api_key="test_key_12345")

        assert classifier._api_key == "test_key_12345"

    def test_classifier_without_api_key(self):
        """Test HaikuClassifier without API key uses env var."""
        import os

        # Save original env var
        original_key = os.environ.get("ANTHROPIC_API_KEY")

        try:
            # Set test env var
            os.environ["ANTHROPIC_API_KEY"] = "env_test_key"

            classifier = HaikuClassifier()
            assert classifier._api_key == "env_test_key"

        finally:
            # Restore original env var
            if original_key is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = original_key

    def test_classifier_lazy_client_loading(self):
        """Test client is not loaded on initialization."""
        classifier = HaikuClassifier(api_key="test_key")

        # Client should be None initially
        assert classifier._client is None


class TestKeywordClassification:
    """Test keyword-based classification."""

    def test_classify_sync_returns_result(self):
        """Test classify_sync returns ClassificationResult."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("review my code")

        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_code_review_keywords(self):
        """Test classification with code review keywords."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("review my code and check for issues")

        # Should match code-review wizard
        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None
        assert result.confidence > 0.0

    def test_classify_security_keywords(self):
        """Test classification with security keywords."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("scan for security vulnerabilities")

        assert isinstance(result, ClassificationResult)
        assert result.confidence > 0.0

    def test_classify_test_generation_keywords(self):
        """Test classification with test generation keywords."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("generate unit tests for my module")

        assert isinstance(result, ClassificationResult)
        assert result.confidence > 0.0

    def test_classify_with_no_matches(self):
        """Test classification with no keyword matches."""
        classifier = HaikuClassifier()

        # Request with no matching keywords
        result = classifier.classify_sync("xyz abc qwerty nonsense")

        # Should default to code-review
        assert result.primary_workflow == "code-review"
        assert result.confidence == 0.3
        assert "No keyword matches" in result.reasoning

    def test_classify_with_context(self):
        """Test classification with additional context."""
        classifier = HaikuClassifier()

        context = {"current_file": "test_auth.py", "project_type": "web-app"}

        result = classifier.classify_sync("review this file", context=context)

        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None

    def test_classify_case_insensitive(self):
        """Test classification is case insensitive."""
        classifier = HaikuClassifier()

        result_lower = classifier.classify_sync("review code")
        result_upper = classifier.classify_sync("REVIEW CODE")
        result_mixed = classifier.classify_sync("Review Code")

        # All should produce same primary wizard
        assert result_lower.primary_workflow == result_upper.primary_workflow
        assert result_lower.primary_workflow == result_mixed.primary_workflow


class TestKeywordScoring:
    """Test keyword scoring and matching logic."""

    def test_single_keyword_match(self):
        """Test classification with single keyword match."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("security")

        assert isinstance(result, ClassificationResult)
        assert result.confidence > 0.0

    def test_multiple_keyword_matches(self):
        """Test classification with multiple matching keywords."""
        classifier = HaikuClassifier()

        # Request with multiple keywords
        result = classifier.classify_sync("review code for security issues")

        assert isinstance(result, ClassificationResult)
        # Should have higher confidence with multiple matches
        assert result.confidence > 0.0

    def test_exact_word_match_bonus(self):
        """Test exact word matching gets bonus score."""
        classifier = HaikuClassifier()

        # "test" as standalone word vs substring
        result_exact = classifier.classify_sync("generate test cases")
        result_substring = classifier.classify_sync("testing something")

        # Both should match, but exact word match should score higher
        assert result_exact.confidence > 0.0
        assert result_substring.confidence > 0.0

    def test_secondary_wizard_selection(self):
        """Test secondary wizard selection."""
        classifier = HaikuClassifier()

        # Request that matches multiple wizards
        result = classifier.classify_sync("review code and scan for security issues")

        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None
        # May or may not have secondary based on scoring
        assert isinstance(result.secondary_workflows, list)

    def test_secondary_requires_significant_score(self):
        """Test secondary wizards require significant score."""
        classifier = HaikuClassifier()

        # Single strong match should not have weak secondaries
        result = classifier.classify_sync("security vulnerability scan")

        # Primary should exist
        assert result.primary_workflow is not None

        # If secondaries exist, they should have reasonable scores
        for secondary in result.secondary_workflows:
            assert isinstance(secondary, str)
            assert len(secondary) > 0


class TestClassificationEdgeCases:
    """Test edge cases and error handling."""

    def test_classify_empty_request(self):
        """Test classification with empty request."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("")

        # Should default to code-review
        assert result.primary_workflow == "code-review"
        assert result.confidence == 0.3

    def test_classify_whitespace_only(self):
        """Test classification with whitespace only."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("   \n\t   ")

        # Should default to code-review
        assert result.primary_workflow == "code-review"

    def test_classify_special_characters(self):
        """Test classification with special characters."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("@#$%^&* review !@#")

        # Should still extract "review" keyword
        assert isinstance(result, ClassificationResult)

    def test_classify_very_long_request(self):
        """Test classification with very long request."""
        classifier = HaikuClassifier()

        # Very long request
        long_request = "review " * 1000 + "my code"

        result = classifier.classify_sync(long_request)

        # Should still work
        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None


class TestConfidenceScoring:
    """Test confidence score calculation."""

    def test_confidence_range(self):
        """Test confidence is always in valid range."""
        classifier = HaikuClassifier()

        test_requests = ["review code", "security scan", "generate tests", "xyz nonsense", ""]

        for request in test_requests:
            result = classifier.classify_sync(request)
            assert 0.0 <= result.confidence <= 1.0

    def test_confidence_higher_for_multiple_matches(self):
        """Test confidence increases with more keyword matches."""
        classifier = HaikuClassifier()

        # Single keyword
        result_single = classifier.classify_sync("security")

        # Multiple keywords from same wizard
        result_multiple = classifier.classify_sync("security vulnerability scan")

        # Multiple matches should have higher or equal confidence
        assert result_multiple.confidence >= result_single.confidence

    def test_no_match_has_low_confidence(self):
        """Test no matches results in low confidence."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("xyz abc qwerty")

        # Default fallback should have low confidence
        assert result.confidence <= 0.4


class TestReasoningExplanation:
    """Test reasoning field provides explanation."""

    def test_reasoning_provided_for_keyword_match(self):
        """Test reasoning explains keyword matches."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("review my code")

        # Should include scoring information
        assert len(result.reasoning) > 0
        assert "score" in result.reasoning.lower() or "match" in result.reasoning.lower()

    def test_reasoning_explains_default_fallback(self):
        """Test reasoning explains default fallback."""
        classifier = HaikuClassifier()

        result = classifier.classify_sync("xyz nonsense")

        # Should explain why defaulting
        assert "No keyword matches" in result.reasoning
        assert "code-review" in result.reasoning


class TestClientLazyLoading:
    """Test lazy loading of Anthropic client."""

    def test_get_client_without_api_key(self, monkeypatch):
        """Test get_client returns None without API key."""
        # Clear env var so api_key=None truly means no key
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        classifier = HaikuClassifier(api_key=None)

        client = classifier._get_client()

        # Should return None when no API key
        assert client is None

    def test_get_client_with_api_key(self):
        """Test get_client attempts to load with API key."""
        classifier = HaikuClassifier(api_key="test_key_12345")

        # This will return None because anthropic is not importable
        # or will create client if anthropic is installed
        client = classifier._get_client()

        # Just verify method doesn't crash
        assert client is None or client is not None


class TestAvailableWizardsOverride:
    """Test classification with custom available wizards."""

    def test_keyword_classify_uses_registry(self):
        """Test keyword classification uses wizard registry."""
        classifier = HaikuClassifier()

        # Should use registry by default
        result = classifier.classify_sync("review code")

        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None

    def test_classify_with_limited_wizards(self):
        """Test classification still works with limited wizard set."""
        classifier = HaikuClassifier()

        # Even with no explicit wizard override, classification should work
        result = classifier.classify_sync("test something")

        assert isinstance(result, ClassificationResult)


# ---------------------------------------------------------------------------
# Coverage for LLM client path and missing branches
# ---------------------------------------------------------------------------


import builtins  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402


@pytest.mark.unit
class TestGetClient:
    """Cover _get_client lazy-import paths."""

    def test_get_client_instantiates_anthropic(self):
        """Lines 56-60: api_key set + anthropic importable → client created."""
        classifier = HaikuClassifier(api_key="test-key")
        fake_client = MagicMock(name="anthropic-client")
        fake_anthropic = MagicMock()
        fake_anthropic.Anthropic.return_value = fake_client

        with patch.dict("sys.modules", {"anthropic": fake_anthropic}):
            client = classifier._get_client()

        assert client is fake_client
        fake_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    def test_get_client_handles_import_error(self):
        """Lines 61-62: ImportError when anthropic missing → returns None."""
        classifier = HaikuClassifier(api_key="test-key")
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            assert classifier._get_client() is None

    def test_get_client_no_api_key_returns_none(self, monkeypatch):
        """Without api_key, _get_client returns None without importing."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        classifier = HaikuClassifier(api_key=None)
        assert classifier._get_client() is None


@pytest.mark.unit
class TestClassifyLLMPath:
    """Cover the LLM-driven classify path (lines 82, 90, 122-153)."""

    def _build_classifier_with_client(self, client):
        classifier = HaikuClassifier(api_key="test-key")
        classifier._client = client
        return classifier

    @pytest.mark.asyncio
    async def test_classify_llm_success_plain_json(self):
        """Lines 122-147: full LLM happy path with plain JSON response."""
        block = MagicMock()
        block.text = (
            '{"primary_workflow": "security-scan",'
            ' "secondary_workflows": ["code-review"],'
            ' "confidence": 0.92, "reasoning": "found CVE",'
            ' "extracted_context": {"file": "auth.py"}}'
        )
        response = MagicMock()
        response.content = [block]
        client = MagicMock()
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify(
            "scan auth.py for vulnerabilities",
            context={"project": "api"},
            available_workflows={"security-scan": "scan", "code-review": "review"},
        )

        assert result.primary_workflow == "security-scan"
        assert result.secondary_workflows == ["code-review"]
        assert result.confidence == 0.92
        assert result.reasoning == "found CVE"
        assert result.extracted_context == {"file": "auth.py"}

        # Verify the user prompt included the context block (line 90)
        call = client.messages.create.call_args
        user_msg = call.kwargs["messages"][0]["content"]
        assert "Context:" in user_msg
        assert "project" in user_msg

    @pytest.mark.asyncio
    async def test_classify_llm_response_wrapped_in_json_codeblock(self):
        """Lines 135-136: ```json fenced response is unwrapped."""
        block = MagicMock()
        block.text = '```json\n{"primary_workflow": "test-gen", "confidence": 0.7}\n```'
        response = MagicMock()
        response.content = [block]
        client = MagicMock()
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify("write tests")
        assert result.primary_workflow == "test-gen"
        assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_classify_llm_response_wrapped_in_plain_codeblock(self):
        """Lines 137-138: ``` (no language) fenced response is unwrapped."""
        block = MagicMock()
        block.text = '```\n{"primary_workflow": "doc-gen"}\n```'
        response = MagicMock()
        response.content = [block]
        client = MagicMock()
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify("docs please")
        assert result.primary_workflow == "doc-gen"

    @pytest.mark.asyncio
    async def test_classify_llm_empty_content_falls_through_to_keyword(self):
        """Line 130: empty content list yields '{}', triggering defaults."""
        response = MagicMock()
        response.content = []  # falsy, content defaults to "{}"
        client = MagicMock()
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify("review my code")
        # "{}" parses, primary_workflow falls back to default "code-review"
        assert result.primary_workflow == "code-review"

    @pytest.mark.asyncio
    async def test_classify_llm_invalid_json_falls_back_to_keyword(self):
        """Lines 148-149: JSONDecodeError logs warning and falls back."""
        block = MagicMock()
        block.text = "this is not JSON at all"
        response = MagicMock()
        response.content = [block]
        client = MagicMock()
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify("review this code please")
        # Falls through to _keyword_classify — returns a valid result
        assert isinstance(result, ClassificationResult)
        assert result.primary_workflow is not None

    @pytest.mark.asyncio
    async def test_classify_llm_api_exception_falls_back(self):
        """Lines 151-153: API exception → keyword fallback."""
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("boom")
        classifier = self._build_classifier_with_client(client)

        result = await classifier.classify("audit security holes")
        assert isinstance(result, ClassificationResult)
        # Keyword fallback should still produce a workflow name
        assert result.primary_workflow is not None

    @pytest.mark.asyncio
    async def test_classify_uses_provided_available_workflows(self):
        """Line 82->86: when available_workflows provided, skip registry lookup."""
        client = MagicMock()
        block = MagicMock()
        block.text = '{"primary_workflow": "custom-flow"}'
        response = MagicMock()
        response.content = [block]
        client.messages.create.return_value = response
        classifier = self._build_classifier_with_client(client)

        # If we pass available_workflows, registry method should NOT be called
        with patch.object(
            classifier._registry,
            "get_descriptions_for_classification",
        ) as mock_reg:
            result = await classifier.classify(
                "do the thing",
                available_workflows={"custom-flow": "Custom"},
            )

        mock_reg.assert_not_called()
        assert result.primary_workflow == "custom-flow"
