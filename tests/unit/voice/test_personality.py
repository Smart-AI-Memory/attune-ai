"""Tests for voice personality module."""

from attune.voice.personality import (
    phrase_error,
    phrase_next_step,
    phrase_next_step_short,
    score_commentary,
)


class TestScoreCommentary:
    """Test score_commentary returns appropriate messaging."""

    def test_excellent_score(self):
        """Scores >= 85 get the excellent message."""
        result = score_commentary(92)
        assert "solid" in result.lower() or "great" in result.lower()

    def test_good_score(self):
        """Scores 70-84 get the good message."""
        result = score_commentary(75)
        assert "good" in result.lower() or "tighten" in result.lower()

    def test_needs_work_score(self):
        """Scores 50-69 get the needs work message."""
        result = score_commentary(55)
        assert "work" in result.lower()

    def test_critical_score(self):
        """Scores < 50 get the critical message."""
        result = score_commentary(30)
        assert "attention" in result.lower()

    def test_boundary_85(self):
        """Score exactly 85 is excellent."""
        result = score_commentary(85)
        assert "solid" in result.lower() or "great" in result.lower()

    def test_boundary_70(self):
        """Score exactly 70 is good."""
        result = score_commentary(70)
        assert "good" in result.lower()

    def test_boundary_50(self):
        """Score exactly 50 is needs work."""
        result = score_commentary(50)
        assert "work" in result.lower()


class TestPhraseNextStep:
    """Test next-step phrasing."""

    def test_contains_workflow_name(self):
        """Phrased step includes the workflow command."""
        result = phrase_next_step("security-audit", "found issues")
        assert "security-audit" in result

    def test_contains_description(self):
        """Phrased step includes the description."""
        result = phrase_next_step("test-gen", "coverage is low")
        assert "coverage is low" in result

    def test_sounds_like_a_colleague(self):
        """Phrased step uses natural language, not menu syntax."""
        result = phrase_next_step("code-review", "check quality")
        assert "I'd" in result or "run" in result.lower()


class TestPhraseNextStepShort:
    """Test compact next-step phrasing."""

    def test_shorter_than_full(self):
        """Short version is more compact."""
        full = phrase_next_step("security-audit", "found issues")
        short = phrase_next_step_short("security-audit", "found issues")
        assert len(short) < len(full)

    def test_contains_workflow_name(self):
        """Short version still includes workflow name."""
        result = phrase_next_step_short("test-gen", "gaps found")
        assert "test-gen" in result


class TestPhraseError:
    """Test error phrasing."""

    def test_transient_error(self):
        """Transient errors suggest retry."""
        result = phrase_error("transient")
        assert "retry" in result.lower() or "temporary" in result.lower()

    def test_config_error(self):
        """Config errors suggest checking setup."""
        result = phrase_error("config")
        assert "config" in result.lower() or "setup" in result.lower()

    def test_generic_error(self):
        """Unknown errors give generic guidance."""
        result = phrase_error(None)
        assert "error" in result.lower() or "dig in" in result.lower()
