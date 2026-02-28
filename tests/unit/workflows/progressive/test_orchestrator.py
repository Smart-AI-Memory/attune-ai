"""Integration tests for MetaOrchestrator."""

from datetime import datetime

from attune.workflows.progressive.core import (
    EscalationConfig,
    FailureAnalysis,
    Tier,
    TierResult,
)
from attune.workflows.progressive.orchestrator import MetaOrchestrator


class TestMetaOrchestrator:
    """Test MetaOrchestrator escalation logic."""

    def test_cheap_escalation_on_low_cqs(self):
        """Test that cheap tier escalates when CQS is too low."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Low quality result - need enough successful items to avoid failure_rate trigger
        # Failure rate threshold is 30%, so need <=29% failures (strictly less than 30%)
        # 8 success + 2 fail = 20% failure rate (safe margin)
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 65},  # Below 80 threshold
                {"quality_score": 70},
                {"quality_score": 82},  # Above threshold
                {"quality_score": 85},
                {"quality_score": 88},
                {"quality_score": 90},
                {"quality_score": 83},
                {"quality_score": 87},
                {"quality_score": 91},
                {"quality_score": 86},
            ],
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.75,  # High enough to avoid failure_rate trigger
                coverage_percent=50.0,
                assertion_depth=3.0,
                confidence_score=0.70,
            ),
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        assert should_escalate is True
        assert "Quality score" in reason or "below threshold" in reason.lower()

    def test_cheap_no_escalation_on_good_quality(self):
        """Test that cheap tier doesn't escalate when quality is good."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Good quality result with successful items
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[
                {"quality_score": 92},
                {"quality_score": 88},
                {"quality_score": 95},
                {"quality_score": 85},
            ],
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.90,
                coverage_percent=85.0,
                assertion_depth=7.0,
                confidence_score=0.95,
            ),
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        assert should_escalate is False
        assert "acceptable" in reason.lower()

    def test_cheap_escalation_on_syntax_errors(self):
        """Test that cheap tier escalates on excessive syntax errors."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(cheap_to_capable_max_syntax_errors=3)

        # Result with many syntax errors
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=2,
            timestamp=datetime.now(),
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.80,
                coverage_percent=70.0,
                syntax_errors=[SyntaxError(f"error {i}") for i in range(5)],
            ),
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=2,
            config=config,
        )

        assert should_escalate is True
        assert "syntax" in reason.lower()

    def test_capable_escalation_on_stagnation(self):
        """Test that capable tier escalates on stagnation."""
        orchestrator = MetaOrchestrator()
        # Reset history to avoid cross-test contamination
        orchestrator.tier_history[Tier.CAPABLE] = []

        config = EscalationConfig(improvement_threshold=5.0, consecutive_stagnation_limit=2)

        # First attempt: CQS ~80 (high enough to avoid immediate escalation)
        result1 = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 82}] * 8 + [{"quality_score": 75}] * 2,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.80,  # Above threshold
                coverage_percent=80.0,
                assertion_depth=8.0,  # Higher to boost CQS
                confidence_score=0.82,
            ),
        )

        should_esc1, _ = orchestrator.should_escalate(
            Tier.CAPABLE,
            result1,
            attempt=1,
            config=config,
        )
        assert should_esc1 is False  # First attempt, no history for stagnation

        # Second attempt: CQS ~83 (+3%, <5% improvement = first stagnation)
        result2 = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 83}] * 8 + [{"quality_score": 79}] * 2,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.83,
                coverage_percent=83.0,
                assertion_depth=8.5,
                confidence_score=0.84,
            ),
        )

        should_esc2, reason2 = orchestrator.should_escalate(
            Tier.CAPABLE,
            result2,
            attempt=2,
            config=config,
        )
        # Need 3 items in history (consecutive_stagnation_limit + 1) before checking stagnation
        # After result2, we have 2 items, so no stagnation check yet
        assert should_esc2 is False  # Not enough history for stagnation detection

        # Third attempt: CQS ~85 (+2%, <5% improvement) - second stagnation
        result3 = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=3,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 85}] * 8 + [{"quality_score": 79}] * 2,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.85,
                coverage_percent=85.0,
                assertion_depth=9.0,
                confidence_score=0.86,
            ),
        )

        should_esc3, reason3 = orchestrator.should_escalate(
            Tier.CAPABLE,
            result3,
            attempt=3,
            config=config,
        )

        assert should_esc3 is True  # 2 consecutive stagnations
        assert "stagnation" in reason3.lower()

    def test_capable_no_escalation_on_improvement(self):
        """Test that capable tier doesn't escalate when improving."""
        orchestrator = MetaOrchestrator()
        # Reset history
        orchestrator.tier_history[Tier.CAPABLE] = []

        config = EscalationConfig(improvement_threshold=5.0)

        # First attempt: CQS 80 (with items to pass threshold)
        result1 = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 82}] * 8 + [{"quality_score": 75}] * 2,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.80,
                coverage_percent=80.0,
                assertion_depth=6.0,
                confidence_score=0.82,
            ),
        )

        orchestrator.should_escalate(Tier.CAPABLE, result1, attempt=1, config=config)

        # Second attempt: CQS 88 (+8%, >5% improvement)
        result2 = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=2,
            timestamp=datetime.now(),
            generated_items=[{"quality_score": 90}] * 9 + [{"quality_score": 85}] * 1,
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.88,
                coverage_percent=88.0,
                assertion_depth=7.5,
                confidence_score=0.90,
            ),
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result2,
            attempt=2,
            config=config,
        )

        assert should_escalate is False
        assert "acceptable" in reason.lower() or "continuing" in reason.lower()

    def test_capable_escalation_on_max_attempts(self):
        """Test that capable tier escalates at max attempts."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(capable_max_attempts=6)

        result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=6,  # At max attempts
            timestamp=datetime.now(),
            failure_analysis=FailureAnalysis(
                test_pass_rate=0.78,  # Decent but not great
                coverage_percent=75.0,
                assertion_depth=6.0,
                confidence_score=0.80,
            ),
        )

        # Build history to avoid early escalation
        for i in range(6):
            orchestrator.tier_history[Tier.CAPABLE].append(70 + i)

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CAPABLE,
            result,
            attempt=6,
            config=config,
        )

        assert should_escalate is True
        assert "max attempts" in reason.lower()

    def test_stagnation_detection(self):
        """Test stagnation detection algorithm."""
        orchestrator = MetaOrchestrator()

        # No stagnation: good improvement
        history1 = [70.0, 78.0, 86.0, 92.0]
        is_stagnant1, _ = orchestrator._detect_stagnation(
            history1,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )
        assert is_stagnant1 is False

        # Stagnation: <5% improvement for 2 consecutive runs
        history2 = [70.0, 78.0, 79.0, 80.0]  # Last two improvements: +1%, +1%
        is_stagnant2, reason2 = orchestrator._detect_stagnation(
            history2,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )
        assert is_stagnant2 is True
        assert "consecutive" in reason2.lower()

        # Not enough history
        history3 = [70.0]
        is_stagnant3, _ = orchestrator._detect_stagnation(
            history3,
            improvement_threshold=5.0,
            consecutive_limit=2,
        )
        assert is_stagnant3 is False


class TestPromptGeneration:
    """Test XML-enhanced prompt generation."""

    def test_cheap_prompt_basic(self):
        """Test basic cheap tier prompt."""
        orchestrator = MetaOrchestrator()

        prompt = orchestrator.build_tier_prompt(
            Tier.CHEAP,
            "Generate tests for module.py",
            failure_context=None,
        )

        assert "<task>" in prompt
        assert "<objective>Generate tests for module.py</objective>" in prompt
        assert "<quality_requirements>" in prompt
        assert "70%+" in prompt  # Cheap tier has lower requirements

    def test_capable_prompt_with_failure_context(self):
        """Test capable tier prompt with failure context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CHEAP,
            "previous_cqs": 65.0,
            "reason": "Quality score below threshold",
            "failures": [
                {"error": "SyntaxError: invalid syntax in async function"},
                {"error": "SyntaxError: missing await in async call"},
                {"error": "MockError: mock not configured properly"},
            ],
            "examples": [
                {
                    "error": "SyntaxError: invalid syntax",
                    "code": "def test_async():\n    result = async_function()",
                    "quality_score": 45,
                },
            ],
        }

        prompt = orchestrator.build_tier_prompt(
            Tier.CAPABLE,
            "Generate tests for async module",
            failure_context=failure_context,
        )

        assert "<context_from_previous_tier>" in prompt
        assert "<quality_score>65.0</quality_score>" in prompt
        assert "<failure_analysis>" in prompt
        assert "async_errors" in prompt  # Should detect async pattern
        assert "<failed_attempts>" in prompt
        assert "SyntaxError" in prompt
        assert "80%+" in prompt  # Capable tier requirements

    def test_premium_prompt_with_comprehensive_context(self):
        """Test premium tier prompt with full context."""
        orchestrator = MetaOrchestrator()

        failure_context = {
            "previous_tier": Tier.CAPABLE,
            "previous_cqs": 78.0,
            "reason": "Stagnation detected: 2 consecutive runs with <5% improvement",
            "failures": [
                {"error": "AssertionError: async timeout not handled"},
                {"error": "MockError: fixture not properly reset"},
            ],
            "examples": [
                {
                    "error": "AssertionError: timeout",
                    "code": "async def test_timeout():\n    result = await slow_function()",
                    "quality_score": 75,
                },
            ],
        }

        prompt = orchestrator.build_tier_prompt(
            Tier.PREMIUM,
            "Generate tests for complex async module",
            failure_context=failure_context,
        )

        assert "<escalation_context>" in prompt
        assert "<previous_tier>capable</previous_tier>" in prompt
        assert "<progression_analysis>" in prompt
        assert "FINAL tier" in prompt or "final tier" in prompt.lower()
        assert "<persistent_issues>" in prompt
        assert "<capable_tier_attempts>" in prompt
        assert "<critical_notice>" in prompt
        assert "95%+" in prompt  # Premium tier requirements
        assert "<zero_syntax_errors>MANDATORY</zero_syntax_errors>" in prompt

    def test_xml_escaping(self):
        """Test XML special character escaping."""
        orchestrator = MetaOrchestrator()

        # Test all special characters
        text = "Error: <missing> & \"invalid\" 'quote'"
        escaped = orchestrator._escape_xml(text)

        assert "&lt;" in escaped  # <
        assert "&gt;" in escaped  # >
        assert "&amp;" in escaped  # &
        assert "&quot;" in escaped  # "
        assert "&apos;" in escaped  # '
        assert "<missing>" not in escaped  # Original should be escaped


class TestFailurePatternAnalysis:
    """Test failure pattern analysis."""

    def test_analyze_async_errors(self):
        """Test detection of async-related errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "SyntaxError: invalid syntax in async function"},
            {"error": "RuntimeError: missing await keyword"},
            {"error": "AsyncError: timeout exceeded"},
            {"error": "ValueError: invalid input"},  # Not async
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 4
        assert "async_errors" in patterns["error_types"]
        assert patterns["error_types"]["async_errors"] == 3
        assert patterns["primary_issue"] == "async_errors"

    def test_analyze_mocking_errors(self):
        """Test detection of mocking-related errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "MockError: mock not configured"},
            {"error": "AttributeError: mock has no attribute 'reset'"},
            {"error": "MockError: fixture not set up properly"},
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 3
        assert "mocking_errors" in patterns["error_types"]
        assert patterns["error_types"]["mocking_errors"] == 3
        assert patterns["primary_issue"] == "mocking_errors"

    def test_analyze_syntax_errors(self):
        """Test detection of syntax errors."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "SyntaxError: invalid syntax"},
            {"error": "SyntaxError: unexpected EOF"},
            {"error": "IndentationError: unexpected indent"},  # Also syntax-related
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 3
        assert "syntax_errors" in patterns["error_types"]

    def test_analyze_mixed_errors(self):
        """Test analysis of mixed error types."""
        orchestrator = MetaOrchestrator()

        failures = [
            {"error": "SyntaxError: invalid async"},  # async_errors
            {"error": "MockError: not configured"},  # mocking_errors
            {"error": "SyntaxError: missing await"},  # async_errors
            {"error": "ValueError: bad input"},  # other_errors
        ]

        patterns = orchestrator.analyze_failure_patterns(failures)

        assert patterns["total_failures"] == 4
        assert len(patterns["error_types"]) >= 3
        assert "async_errors" in patterns["error_types"]
        assert patterns["error_types"]["async_errors"] == 2
        assert patterns["primary_issue"] == "async_errors"  # Most common

    def test_empty_failures(self):
        """Test analysis with no failures."""
        orchestrator = MetaOrchestrator()

        patterns = orchestrator.analyze_failure_patterns([])

        assert patterns["total_failures"] == 0
        assert patterns["error_types"] == {}
        assert patterns["primary_issue"] == "unknown"


class TestAgentTeamCreation:
    """Test agent team composition."""

    def test_cheap_tier_single_agent(self):
        """Test that cheap tier gets single agent."""
        orchestrator = MetaOrchestrator()

        agents = orchestrator.create_agent_team(Tier.CHEAP, failure_context=None)

        assert len(agents) == 1
        assert "generator" in agents

    def test_capable_tier_two_agents(self):
        """Test that capable tier gets two agents."""
        orchestrator = MetaOrchestrator()

        failure_context = {"previous_cqs": 65.0, "failures": []}

        agents = orchestrator.create_agent_team(Tier.CAPABLE, failure_context)

        assert len(agents) == 2
        assert "generator" in agents
        assert "analyzer" in agents

    def test_premium_tier_three_agents(self):
        """Test that premium tier gets three agents."""
        orchestrator = MetaOrchestrator()

        failure_context = {"previous_cqs": 78.0, "failures": []}

        agents = orchestrator.create_agent_team(Tier.PREMIUM, failure_context)

        assert len(agents) == 3
        assert "generator" in agents
        assert "analyzer" in agents
        assert "reviewer" in agents


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_attempts_not_met(self):
        """Test that escalation doesn't happen before min attempts."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig(cheap_min_attempts=2)

        # Poor quality result but only 1 attempt
        result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            failure_analysis=FailureAnalysis(test_pass_rate=0.30),  # Very low
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.CHEAP,
            result,
            attempt=1,
            config=config,
        )

        assert should_escalate is False
        assert "attempts" in reason.lower()

    def test_premium_tier_never_escalates(self):
        """Test that premium tier never escalates (it's final)."""
        orchestrator = MetaOrchestrator()
        config = EscalationConfig()

        # Even with poor quality
        result = TierResult(
            tier=Tier.PREMIUM,
            model="claude-opus-4",
            attempt=1,
            timestamp=datetime.now(),
            failure_analysis=FailureAnalysis(test_pass_rate=0.50),
        )

        should_escalate, reason = orchestrator.should_escalate(
            Tier.PREMIUM,
            result,
            attempt=1,
            config=config,
        )

        assert should_escalate is False
        assert "final" in reason.lower()
