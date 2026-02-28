"""Unit tests for MetaOrchestrator escalation decision logic.

Tests cover:
- Escalation decision making
- Stagnation detection
- Agent team creation
- Prompt building
"""

from datetime import datetime

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    Tier,
    TierResult,
)
from attune.workflows.progressive.orchestrator import MetaOrchestrator


class TestMetaOrchestrator:
    """Test MetaOrchestrator class."""

    def test_init(self):
        """Test orchestrator initialization."""
        orchestrator = MetaOrchestrator()
        assert orchestrator is not None
        assert orchestrator.tier_history is not None

    def test_should_escalate_syntax_errors(self):
        """Test escalation with multiple syntax errors."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Create result with syntax errors
        analysis = FailureAnalysis(
            test_pass_rate=0.75,
            coverage_percent=70.0,
            assertion_depth=4.0,
            confidence_score=0.80,
            syntax_errors=[
                SyntaxError("error 1"),
                SyntaxError("error 2"),
                SyntaxError("error 3"),
                SyntaxError("error 4"),
            ],
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,  # Met min attempts
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        # Multiple syntax errors should trigger escalation
        assert should_escalate is True
        assert "syntax" in reason.lower()

    def test_should_not_escalate_good_quality(self):
        """Test no escalation with good quality."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Create result with excellent CQS (well above threshold)
        analysis = FailureAnalysis(
            test_pass_rate=0.95,
            coverage_percent=90.0,
            assertion_depth=9.0,  # Will give 90 for assertion quality
            confidence_score=0.95,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,  # Met min attempts
            timestamp=datetime.now(),
            failure_analysis=analysis,
            # Add generated items with high quality scores
            generated_items=[
                {"quality_score": 95},
                {"quality_score": 90},
                {"quality_score": 92},
                {"quality_score": 88},
                {"quality_score": 91},
            ],
        )

        # CQS should be: 0.4*95 + 0.25*90 + 0.2*90 + 0.15*95 = 92.5
        # Success rate: 5/5 = 100% (all above 80 threshold)
        # Both well above escalation thresholds
        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        # Excellent quality should not escalate
        assert should_escalate is False

    def test_should_escalate_min_attempts_not_met(self):
        """Test no escalation when minimum attempts not met."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(cheap_min_attempts=2)

        # Even with poor quality, should not escalate on first attempt
        analysis = FailureAnalysis(
            test_pass_rate=0.50,
            coverage_percent=45.0,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,  # First attempt
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=1,
            config=config,
        )

        # Should not escalate (min attempts not met)
        assert should_escalate is False
        assert "attempt" in reason.lower()

    def test_detect_stagnation_consecutive_runs(self):
        """Test stagnation detection with consecutive low improvement."""
        orchestrator = MetaOrchestrator()

        # Simulate CQS history with minimal improvement (<5 points each)
        cqs_history = [75.0, 76.0, 77.0]  # Only 1 point improvement each

        # Check if stagnation detected
        is_stagnant, reason = orchestrator._detect_stagnation(
            cqs_history,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )

        # With <5 point improvement per run, should detect stagnation
        assert is_stagnant is True
        assert "consecutive" in reason.lower() or "stagnation" in reason.lower()

    def test_detect_no_stagnation_with_improvement(self):
        """Test no stagnation detected when improvements are good."""
        orchestrator = MetaOrchestrator()

        # CQS history with good improvements (>5 points)
        cqs_history = [70.0, 78.0, 86.0]  # 8-point improvements

        is_stagnant, reason = orchestrator._detect_stagnation(
            cqs_history,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )

        # Good improvements should not be stagnant
        assert is_stagnant is False

    def test_create_agent_team_cheap_tier(self):
        """Test agent team creation for cheap tier."""
        orchestrator = MetaOrchestrator()

        team = orchestrator.create_agent_team(Tier.CHEAP, failure_context=None)

        # Cheap tier should have minimal team
        assert team is not None
        assert isinstance(team, list)

    def test_create_agent_team_capable_tier(self):
        """Test agent team creation for capable tier with failure context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CHEAP,
            "previous_cqs": 65.0,
            "failures": [],
        }

        team = orchestrator.create_agent_team(Tier.CAPABLE, failure_context)

        # Capable tier should have more agents
        assert team is not None
        assert isinstance(team, list)

    def test_create_agent_team_premium_tier(self):
        """Test agent team creation for premium tier."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CAPABLE,
            "previous_cqs": 75.0,
            "failures": [],
        }

        team = orchestrator.create_agent_team(Tier.PREMIUM, failure_context)

        # Premium tier should have full team
        assert team is not None
        assert isinstance(team, list)

    def test_build_tier_prompt_cheap(self):
        """Test prompt building for cheap tier."""
        orchestrator = MetaOrchestrator()

        prompt = orchestrator.build_tier_prompt(
            tier=Tier.CHEAP,
            base_task="Generate tests for app.py",
            failure_context=None,
        )

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_tier_prompt_capable_with_context(self):
        """Test prompt building for capable tier with failure context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CHEAP,
            "cqs": 65.0,
            "failures": [{"error": "async syntax error"}],
        }

        prompt = orchestrator.build_tier_prompt(
            tier=Tier.CAPABLE,
            base_task="Generate tests for async functions",
            failure_context=failure_context,
        )

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be enhanced

    def test_build_tier_prompt_premium(self):
        """Test prompt building for premium tier."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CAPABLE,
            "cqs": 75.0,
            "cheap_cqs": 65.0,
            "failures": [],
        }

        prompt = orchestrator.build_tier_prompt(
            tier=Tier.PREMIUM,
            base_task="Generate tests for complex async code",
            failure_context=failure_context,
        )

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Premium prompt should be comprehensive

    def test_should_escalate_low_quality_after_min_attempts(self):
        """Test escalation with low quality after meeting min attempts."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Create result with low CQS
        analysis = FailureAnalysis(
            test_pass_rate=0.50,
            coverage_percent=45.0,
            assertion_depth=2.0,
            confidence_score=0.60,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,  # Met minimum attempts
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        # Low CQS after min attempts should trigger escalation
        assert should_escalate is True


class TestMetaOrchestratorEdgeCases:
    """Test edge cases and error handling."""

    def test_escalate_from_premium_tier(self):
        """Test escalation decision from premium tier (should not escalate)."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Even with poor quality at premium tier
        analysis = FailureAnalysis(test_pass_rate=0.60, coverage_percent=50.0)

        result = TierResult(
            tier=Tier.PREMIUM,
            model="claude-opus-4",
            attempt=1,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.PREMIUM,
            result,
            attempt=1,
            config=config,
        )

        # Cannot escalate beyond premium
        assert should_escalate is False
        assert "premium" in reason.lower() or "final" in reason.lower()

    def test_detect_stagnation_insufficient_history(self):
        """Test stagnation detection with insufficient history."""
        orchestrator = MetaOrchestrator()

        # Only 1 data point - cannot detect stagnation (need consecutive_limit + 1)
        cqs_history = [75.0]

        is_stagnant, reason = orchestrator._detect_stagnation(
            cqs_history,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )

        assert is_stagnant is False
        assert "insufficient" in reason.lower() or "history" in reason.lower()

    def test_escalate_critical_severity(self):
        """Test escalation on CRITICAL failure severity."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Create result with metrics that trigger CRITICAL severity
        # (>5 syntax errors OR <30% pass rate)
        analysis = FailureAnalysis(
            test_pass_rate=0.25,  # <30% triggers CRITICAL
            coverage_percent=70.0,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        # Verify CRITICAL severity is calculated
        assert analysis.failure_severity == "CRITICAL"

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        # CRITICAL severity should trigger immediate escalation
        assert should_escalate is True
        assert "critical" in reason.lower()

    def test_escalate_high_failure_rate(self):
        """Test escalation due to high failure rate."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Create result with high failure rate (>30%)
        analysis = FailureAnalysis(
            test_pass_rate=0.60,  # 40% failure rate
            coverage_percent=75.0,
            assertion_depth=5.0,
            confidence_score=0.85,
        )

        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        # High failure rate should trigger escalation
        assert should_escalate is True
        assert "failure rate" in reason.lower()

    def test_capable_tier_max_attempts_reached(self):
        """Test capable tier escalation when max attempts reached."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(capable_max_attempts=6)

        # Borderline quality but max attempts reached
        analysis = FailureAnalysis(
            test_pass_rate=0.75,
            coverage_percent=72.0,
            assertion_depth=4.5,
            confidence_score=0.80,
        )

        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=6,  # Max attempts
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=6,
            config=config,
        )

        # Max attempts should force escalation
        assert should_escalate is True
        assert "max attempts" in reason.lower()

    def test_capable_tier_stagnation_detection(self):
        """Test capable tier escalation due to stagnation."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(
            capable_min_attempts=2,
            capable_to_premium_failure_rate=0.30,  # Increase to avoid failure rate check
            improvement_threshold=5.0,
            consecutive_stagnation_limit=2,
        )

        # Simulate 3 attempts with minimal improvement
        # Include generated_items with good quality scores to avoid failure rate escalation
        for cqs in [75.0, 76.0, 77.0]:  # <5 point improvements
            analysis = FailureAnalysis(
                test_pass_rate=0.95,  # High pass rate to avoid failure rate check
                coverage_percent=cqs,
                assertion_depth=4.0,
                confidence_score=0.80,
            )
            result = TierResult(
                tier=Tier.CAPABLE,
                model="claude-3-5-sonnet",
                attempt=3,
                timestamp=datetime.now(),
                failure_analysis=analysis,
                generated_items=[{"quality_score": 85, "passed": True} for _ in range(10)],
            )
            orchestrator.should_escalate(Tier.CAPABLE, result, attempt=3, config=config)

        # Now check latest result - should detect stagnation
        analysis = FailureAnalysis(
            test_pass_rate=0.95,
            coverage_percent=78.0,
            assertion_depth=4.0,
            confidence_score=0.80,
        )
        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=4,
            timestamp=datetime.now(),
            failure_analysis=analysis,
            generated_items=[{"quality_score": 85, "passed": True} for _ in range(10)],
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=4,
            config=config,
        )

        assert should_escalate is True
        assert "stagnation" in reason.lower()

    def test_detect_stagnation_with_improvement_then_stagnation(self):
        """Test stagnation detection resets on good improvement."""
        orchestrator = MetaOrchestrator()

        # Good improvement, then stagnation
        cqs_history = [70.0, 80.0, 81.0, 82.0]  # First jump is good, then minimal

        is_stagnant, reason = orchestrator._detect_stagnation(
            cqs_history,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )

        # Recent stagnation should be detected (81→82 and 82→83 are both <5)
        assert is_stagnant is True

    def test_capable_tier_low_cqs_after_min_attempts(self):
        """Test capable tier escalation on low CQS after min attempts."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(
            capable_min_attempts=2,
            capable_to_premium_failure_rate=0.35,  # High threshold to avoid failure rate check
        )

        # Low CQS after meeting min attempts
        # Use pass rate that avoids failure rate escalation (>80% pass = 20% failure)
        analysis = FailureAnalysis(
            test_pass_rate=0.85,  # Avoid failure rate check
            coverage_percent=65.0,  # Below capable_to_premium_min_cqs (80)
            assertion_depth=3.0,
            confidence_score=0.70,
        )

        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=3,  # >= min_attempts
            timestamp=datetime.now(),
            failure_analysis=analysis,
            generated_items=[{"quality_score": 85, "passed": True} for _ in range(10)],
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=3,
            config=config,
        )

        assert should_escalate is True
        assert "quality score" in reason.lower()

    def test_capable_tier_high_syntax_errors(self):
        """Test capable tier escalation on too many syntax errors."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(capable_to_premium_max_syntax_errors=1)

        # Multiple syntax errors
        analysis = FailureAnalysis(
            test_pass_rate=0.80,
            coverage_percent=75.0,
            syntax_errors=[SyntaxError("error 1"), SyntaxError("error 2")],
        )

        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=2,
            config=config,
        )

        assert should_escalate is True
        assert "syntax" in reason.lower()

    def test_capable_tier_high_failure_rate(self):
        """Test capable tier escalation on high failure rate."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(capable_to_premium_failure_rate=0.15)

        # Failure rate > 15%
        analysis = FailureAnalysis(
            test_pass_rate=0.80,  # 20% failure rate
            coverage_percent=75.0,
        )

        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=analysis,
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=2,
            config=config,
        )

        assert should_escalate is True
        assert "failure rate" in reason.lower()


class TestEscapeXML:
    """Test XML escaping utility."""

    def test_escape_xml_special_characters(self):
        """Test that all XML special characters are escaped."""
        orchestrator = MetaOrchestrator()

        # Test all 5 special XML characters
        text = '<tag attr="value">text & more\'s</tag>'
        escaped = orchestrator._escape_xml(text)

        assert "&lt;" in escaped  # <
        assert "&gt;" in escaped  # >
        assert "&quot;" in escaped  # "
        assert "&apos;" in escaped  # '
        assert "&amp;" in escaped  # &

        # Verify specific escaping
        assert escaped == "&lt;tag attr=&quot;value&quot;&gt;text &amp; more&apos;s&lt;/tag&gt;"

    def test_escape_xml_empty_string(self):
        """Test escaping empty string."""
        orchestrator = MetaOrchestrator()
        assert orchestrator._escape_xml("") == ""

    def test_escape_xml_no_special_chars(self):
        """Test escaping text without special characters."""
        orchestrator = MetaOrchestrator()
        text = "Plain text without special characters"
        assert orchestrator._escape_xml(text) == text

    def test_escape_xml_ampersand_first(self):
        """Test that ampersand is escaped first (order matters)."""
        orchestrator = MetaOrchestrator()

        # If & is not escaped first, &lt; becomes &amp;lt; (double escaping)
        text = "A & B < C"
        escaped = orchestrator._escape_xml(text)

        assert escaped == "A &amp; B &lt; C"
        # Not "A &amp;amp; B &amp;lt; C"


class TestAnalyzeFailurePatterns:
    """Test failure pattern analysis."""

    def test_analyze_async_errors(self):
        """Test detection of async-related errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "SyntaxError: invalid syntax (async missing)"},
            {"error": "RuntimeError: await outside async function"},
            {"error": "asyncio timeout error"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 3
        assert patterns["error_types"]["async_errors"] == 3
        assert patterns["primary_issue"] == "async_errors"

    def test_analyze_mocking_errors(self):
        """Test detection of mock-related errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "AttributeError: mock object has no attribute 'foo'"},
            {"error": "TypeError: Mock not configured correctly"},
            {"error": "MagicMock call failed"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 3
        assert patterns["error_types"]["mocking_errors"] == 3
        assert patterns["primary_issue"] == "mocking_errors"

    def test_analyze_syntax_errors(self):
        """Test detection of syntax errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "SyntaxError: invalid syntax on line 10"},
            {"error": "IndentationError: syntax issue"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 2
        assert patterns["error_types"]["syntax_errors"] == 2
        assert patterns["primary_issue"] == "syntax_errors"

    def test_analyze_mixed_error_types(self):
        """Test analysis with mixed error types."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "async error"},
            {"error": "async await issue"},
            {"error": "mock setup failed"},
            {"error": "SyntaxError"},
            {"error": "Unknown error type"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 5
        assert patterns["error_types"]["async_errors"] == 2
        assert patterns["error_types"]["mocking_errors"] == 1
        assert patterns["error_types"]["syntax_errors"] == 1
        assert patterns["error_types"]["other_errors"] == 1

        # Primary issue should be async (most common)
        assert patterns["primary_issue"] == "async_errors"

    def test_analyze_other_errors(self):
        """Test categorization of uncategorized errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "ValueError: invalid value"},
            {"error": "TypeError: wrong type"},
            {"error": "IndexError: list index out of range"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 3
        assert patterns["error_types"]["other_errors"] == 3
        assert patterns["primary_issue"] == "other_errors"

    def test_analyze_empty_failures(self):
        """Test analysis with no failures."""
        orchestrator = MetaOrchestrator()

        patterns = orchestrator.analyze_failure_patterns([])

        assert patterns["total_failures"] == 0
        assert patterns["error_types"] == {}
        assert patterns["primary_issue"] == "unknown"

    def test_analyze_failures_missing_error_field(self):
        """Test analysis when failure dict is missing 'error' field."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"message": "something went wrong"},  # No 'error' field
            {"error": "async issue"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        # Missing error field should be categorized as "other"
        assert patterns["total_failures"] == 2
        assert patterns["error_types"]["other_errors"] == 1
        assert patterns["error_types"]["async_errors"] == 1


class TestPromptContentVerification:
    """Test that prompts contain expected XML structure and content."""

    def test_cheap_prompt_structure(self):
        """Test that cheap prompt has correct XML structure."""
        orchestrator = MetaOrchestrator()

        prompt = orchestrator._build_cheap_prompt("Generate tests for app.py")

        # Verify XML structure
        assert "<task>" in prompt
        assert "</task>" in prompt
        assert "<objective>Generate tests for app.py</objective>" in prompt
        assert "<quality_requirements>" in prompt
        assert "<pass_rate>70%+</pass_rate>" in prompt
        assert "<coverage>60%+</coverage>" in prompt
        assert "<syntax>No syntax errors</syntax>" in prompt
        assert "<instructions>" in prompt

    def test_capable_prompt_without_context(self):
        """Test capable prompt when no failure context provided."""
        orchestrator = MetaOrchestrator()

        prompt = orchestrator._build_capable_prompt("Generate tests", failure_context=None)

        # Should have enhanced base prompt
        assert "<task>" in prompt
        assert "<quality_requirements>" in prompt
        assert "<pass_rate>80%+</pass_rate>" in prompt
        assert "<coverage>70%+</coverage>" in prompt
        assert "<quality_score>80+</quality_score>" in prompt

    def test_capable_prompt_with_failure_context(self):
        """Test capable prompt includes failure context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_cqs": 65.5,
            "reason": "Quality score below threshold",
            "failures": [{"error": "async syntax error"}],
            "examples": [{"error": "await missing", "code": "def test(): pass"}],
        }

        prompt = orchestrator._build_capable_prompt("Generate tests", failure_context)

        # Verify failure context is included
        assert "<context_from_previous_tier>" in prompt
        assert "<tier>cheap</tier>" in prompt
        assert "<quality_score>65.5</quality_score>" in prompt
        assert "Quality score below threshold" in prompt
        assert "<failure_analysis>" in prompt
        assert "<failed_attempts>" in prompt
        assert "await missing" in prompt

    def test_capable_prompt_failure_pattern_focus_areas(self):
        """Test that capable prompt adds specific focus areas for error types."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_cqs": 65.0,
            "reason": "Multiple errors",
            "failures": [
                {"error": "async/await syntax error"},
                {"error": "mock setup failed"},
            ],
            "examples": [],
        }

        prompt = orchestrator._build_capable_prompt("Generate tests", failure_context)

        # Should have async and mocking focus areas
        assert '<focus area="async">' in prompt
        assert '<focus area="mocking">' in prompt

    def test_premium_prompt_without_context(self):
        """Test premium prompt when no failure context provided."""
        orchestrator = MetaOrchestrator()

        prompt = orchestrator._build_premium_prompt("Generate tests", failure_context=None)

        # Should have expert-level requirements
        assert "<expert_instructions>" in prompt
        assert "<pass_rate>95%+</pass_rate>" in prompt
        assert "<coverage>85%+</coverage>" in prompt
        assert "<quality_score>95+</quality_score>" in prompt

    def test_premium_prompt_with_escalation_context(self):
        """Test premium prompt includes full escalation context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CAPABLE,
            "previous_cqs": 75.2,
            "reason": "Stagnation detected after 4 attempts",
            "failures": [{"error": "persistent async issue"}],
            "examples": [
                {"error": "async timeout", "code": "async def test():", "quality_score": 72},
            ],
        }

        prompt = orchestrator._build_premium_prompt("Generate tests", failure_context)

        # Verify escalation context
        assert "<escalation_context>" in prompt
        assert "<previous_tier>capable</previous_tier>" in prompt
        assert "<quality_score>75.2</quality_score>" in prompt
        assert "Stagnation detected" in prompt
        assert "<progression_analysis>" in prompt
        assert "<persistent_issues>" in prompt
        assert "<capable_tier_attempts>" in prompt
        assert "<critical_notice>" in prompt
        assert "FINAL tier" in prompt

    def test_premium_prompt_expert_techniques_for_errors(self):
        """Test premium prompt adds specific techniques for error types."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CAPABLE,
            "previous_cqs": 70.0,
            "reason": "Quality issues",
            "failures": [
                {"error": "async error"},
                {"error": "mock issue"},
                {"error": "SyntaxError"},
            ],
            "examples": [],
        }

        prompt = orchestrator._build_premium_prompt("Generate tests", failure_context)

        # Should have specific expert techniques
        assert "Advanced async patterns" in prompt
        assert "Sophisticated mocking" in prompt
        assert "Rigorous syntax validation" in prompt

    def test_prompt_xml_escaping(self):
        """Test that prompts properly escape XML in example error content."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_cqs": 65.0,
            "reason": "Quality below threshold",
            "failures": [],
            "examples": [{"error": "<script>alert('xss')</script>", "code": "x = '<tag>'"}],
        }

        prompt = orchestrator._build_capable_prompt("Generate tests", failure_context)

        # Example errors and code snippets should be escaped
        assert "&lt;script&gt;alert(&apos;xss&apos;)&lt;/script&gt;" in prompt
        # Note: escalation_reason in capable prompt is not currently escaped (line 353)
        # This is tested separately in premium prompt which DOES escape (line 495)


class TestAgentTeamCreation:
    """Test agent team composition for each tier."""

    def test_cheap_tier_team_composition(self):
        """Test cheap tier creates minimal team."""
        orchestrator = MetaOrchestrator()

        team = orchestrator.create_agent_team(Tier.CHEAP, failure_context=None)

        assert team == ["generator"]
        assert len(team) == 1

    def test_capable_tier_team_composition(self):
        """Test capable tier creates enhanced team."""
        orchestrator = MetaOrchestrator()

        team = orchestrator.create_agent_team(Tier.CAPABLE, failure_context={})

        assert team == ["generator", "analyzer"]
        assert len(team) == 2
        assert "generator" in team
        assert "analyzer" in team

    def test_premium_tier_team_composition(self):
        """Test premium tier creates full expert team."""
        orchestrator = MetaOrchestrator()

        team = orchestrator.create_agent_team(Tier.PREMIUM, failure_context={})

        assert team == ["generator", "analyzer", "reviewer"]
        assert len(team) == 3
        assert "generator" in team
        assert "analyzer" in team
        assert "reviewer" in team
