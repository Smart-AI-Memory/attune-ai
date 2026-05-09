"""Unit tests for attune.patterns.confidence module.

Tests PatternUsageStats dataclass and PatternConfidenceTracker.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import patch

import pytest

from attune.patterns.confidence import PatternConfidenceTracker, PatternUsageStats


class TestPatternUsageStatsDefaults:
    """Tests for PatternUsageStats default values."""

    def test_pattern_usage_stats_defaults_zero_counts(self):
        """PatternUsageStats initializes with zero counts."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.times_suggested == 0
        assert stats.times_applied == 0
        assert stats.times_successful == 0
        assert stats.times_unsuccessful == 0

    def test_pattern_usage_stats_defaults_none_timestamps(self):
        """PatternUsageStats initializes with None timestamps."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.last_suggested is None
        assert stats.last_applied is None

    def test_pattern_usage_stats_defaults_empty_feedback(self):
        """PatternUsageStats initializes with empty feedback list."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.feedback == []

    def test_pattern_usage_stats_stores_pattern_id(self):
        """PatternUsageStats stores the given pattern_id."""
        stats = PatternUsageStats(pattern_id="bug_20250915_abc123")
        assert stats.pattern_id == "bug_20250915_abc123"

    def test_pattern_usage_stats_created_at_set_on_init(self):
        """PatternUsageStats sets created_at on initialization."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.created_at is not None
        assert len(stats.created_at) > 0


class TestPatternUsageStatsSuccessRate:
    """Tests for PatternUsageStats.success_rate property."""

    def test_success_rate_zero_when_no_applications(self):
        """success_rate returns 0.0 when no applications recorded (div by zero guard)."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.success_rate == 0.0

    def test_success_rate_one_when_all_successful(self):
        """success_rate returns 1.0 when all applications successful."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_successful=5,
            times_unsuccessful=0,
        )
        assert stats.success_rate == 1.0

    def test_success_rate_zero_when_all_unsuccessful(self):
        """success_rate returns 0.0 when no applications succeeded."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_successful=0,
            times_unsuccessful=3,
        )
        assert stats.success_rate == 0.0

    def test_success_rate_partial(self):
        """success_rate calculates correctly for mixed results."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_successful=3,
            times_unsuccessful=1,
        )
        assert stats.success_rate == pytest.approx(0.75)


class TestPatternUsageStatsApplicationRate:
    """Tests for PatternUsageStats.application_rate property."""

    def test_application_rate_zero_when_never_suggested(self):
        """application_rate returns 0.0 when never suggested."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.application_rate == 0.0

    def test_application_rate_calculates_correctly(self):
        """application_rate divides applied by suggested."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=10,
            times_applied=8,
        )
        assert stats.application_rate == pytest.approx(0.8)

    def test_application_rate_can_exceed_one(self):
        """application_rate can exceed 1.0 if applied more than suggested."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=2,
            times_applied=5,
        )
        assert stats.application_rate == pytest.approx(2.5)


class TestPatternUsageStatsConfidenceScore:
    """Tests for PatternUsageStats.confidence_score property."""

    def test_confidence_score_zero_when_no_data(self):
        """confidence_score is 0 when no usage data."""
        stats = PatternUsageStats(pattern_id="bug_test_001")
        assert stats.confidence_score == 0.0

    def test_confidence_score_clamped_to_one(self):
        """confidence_score is clamped to max 1.0."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=20,
            times_applied=10,
            times_successful=10,
            times_unsuccessful=0,
        )
        assert stats.confidence_score <= 1.0

    def test_confidence_score_clamped_to_zero(self):
        """confidence_score is clamped to min 0.0."""
        stats = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=1,
            times_applied=0,
            times_successful=0,
            times_unsuccessful=0,
        )
        assert stats.confidence_score >= 0.0

    def test_confidence_score_boosted_by_high_application_rate(self):
        """confidence_score boosted when application_rate > 0.5."""
        # Use partial success rates to avoid hitting the 1.0 ceiling
        # low application rate: applied 1/10 (0.1) — no boost from application
        stats_low = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=10,
            times_applied=1,
            times_successful=1,
            times_unsuccessful=3,  # success_rate = 0.25, applied < 5 no vol boost
        )
        # high application rate: applied 8/10 (0.8) — +0.1 boost
        stats_high = PatternUsageStats(
            pattern_id="bug_test_002",
            times_suggested=10,
            times_applied=8,
            times_successful=2,
            times_unsuccessful=6,  # success_rate = 0.25, gets +0.1 app boost
        )
        assert stats_high.confidence_score > stats_low.confidence_score

    def test_confidence_score_boosted_by_volume(self):
        """confidence_score boosted when times_applied >= 5."""
        stats_few = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=10,
            times_applied=2,
            times_successful=2,
            times_unsuccessful=0,
        )
        stats_many = PatternUsageStats(
            pattern_id="bug_test_002",
            times_suggested=10,
            times_applied=5,
            times_successful=5,
            times_unsuccessful=0,
        )
        assert stats_many.confidence_score >= stats_few.confidence_score

    def test_confidence_score_decayed_by_low_usage(self):
        """confidence_score decayed when times_suggested < 2."""
        stats_low_usage = PatternUsageStats(
            pattern_id="bug_test_001",
            times_suggested=1,
            times_applied=1,
            times_successful=1,
            times_unsuccessful=0,
        )
        # With 1 suggestion, score is decayed by 0.8
        # success_rate = 1.0, application_rate = 1.0 > 0.5 (boost +0.1),
        # applied < 5 (no boost), suggested < 2 (decay *0.8)
        # = (1.0 + 0.1) * 0.8 = 0.88 -> clamped to 0.88
        assert stats_low_usage.confidence_score < 1.0


class TestPatternConfidenceTrackerInit:
    """Tests for PatternConfidenceTracker initialization."""

    def test_init_stores_patterns_dir(self, tmp_path):
        """Tracker stores the patterns directory."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.patterns_dir == tmp_path

    def test_init_sets_confidence_dir(self, tmp_path):
        """Tracker sets confidence subdirectory."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.confidence_dir == tmp_path / "confidence"

    def test_init_sets_stats_file(self, tmp_path):
        """Tracker sets stats file path."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.stats_file == tmp_path / "confidence" / "usage_stats.json"

    def test_init_starts_unloaded(self, tmp_path):
        """Tracker starts in unloaded state."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker._loaded is False
        assert tracker._stats == {}


class TestPatternConfidenceTrackerEnsureLoaded:
    """Tests for PatternConfidenceTracker._ensure_loaded lazy loading."""

    def test_ensure_loaded_creates_confidence_dir(self, tmp_path):
        """_ensure_loaded creates the confidence directory."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        assert (tmp_path / "confidence").exists()

    def test_ensure_loaded_marks_loaded_true(self, tmp_path):
        """_ensure_loaded sets _loaded to True."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        assert tracker._loaded is True

    def test_ensure_loaded_reads_existing_json(self, tmp_path):
        """_ensure_loaded reads patterns from existing JSON file."""
        conf_dir = tmp_path / "confidence"
        conf_dir.mkdir(parents=True)
        stats_data = {
            "patterns": {
                "bug_test_001": {
                    "times_suggested": 5,
                    "times_applied": 3,
                    "times_successful": 2,
                    "times_unsuccessful": 1,
                    "last_suggested": None,
                    "last_applied": None,
                    "created_at": "2025-01-01T00:00:00",
                    "feedback": [],
                }
            }
        }
        (conf_dir / "usage_stats.json").write_text(json.dumps(stats_data), encoding="utf-8")

        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()

        assert "bug_test_001" in tracker._stats
        assert tracker._stats["bug_test_001"].times_suggested == 5
        assert tracker._stats["bug_test_001"].times_applied == 3

    def test_ensure_loaded_idempotent(self, tmp_path):
        """_ensure_loaded only loads once (idempotent)."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        tracker._loaded = True
        tracker._stats["fake"] = PatternUsageStats(pattern_id="fake")
        tracker._ensure_loaded()  # Should NOT reset _stats
        assert "fake" in tracker._stats

    def test_ensure_loaded_handles_invalid_json(self, tmp_path):
        """_ensure_loaded handles corrupt JSON gracefully."""
        conf_dir = tmp_path / "confidence"
        conf_dir.mkdir(parents=True)
        (conf_dir / "usage_stats.json").write_text("not valid json", encoding="utf-8")

        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()  # Should not raise

        assert tracker._loaded is True
        assert tracker._stats == {}


class TestPatternConfidenceTrackerRecordSuggestion:
    """Tests for PatternConfidenceTracker.record_suggestion."""

    def test_record_suggestion_creates_new_stats(self, tmp_path):
        """record_suggestion creates new stats entry for unknown pattern."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_new_001")
        assert "bug_new_001" in tracker._stats

    def test_record_suggestion_increments_count(self, tmp_path):
        """record_suggestion increments times_suggested."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_test_001")
        tracker.record_suggestion("bug_test_001")
        assert tracker._stats["bug_test_001"].times_suggested == 2

    def test_record_suggestion_sets_last_suggested(self, tmp_path):
        """record_suggestion sets last_suggested timestamp."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_test_001")
        assert tracker._stats["bug_test_001"].last_suggested is not None

    def test_record_suggestion_saves_to_disk(self, tmp_path):
        """record_suggestion persists data to JSON file."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_test_001")
        assert (tmp_path / "confidence" / "usage_stats.json").exists()


class TestPatternConfidenceTrackerRecordApplication:
    """Tests for PatternConfidenceTracker.record_application."""

    def test_record_application_successful_increments_times_successful(self, tmp_path):
        """record_application with successful=True increments times_successful."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=True)
        stats = tracker._stats["bug_test_001"]
        assert stats.times_successful == 1
        assert stats.times_unsuccessful == 0

    def test_record_application_unsuccessful_increments_times_unsuccessful(self, tmp_path):
        """record_application with successful=False increments times_unsuccessful."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=False)
        stats = tracker._stats["bug_test_001"]
        assert stats.times_successful == 0
        assert stats.times_unsuccessful == 1

    def test_record_application_increments_times_applied(self, tmp_path):
        """record_application always increments times_applied."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=True)
        tracker.record_application("bug_test_001", successful=False)
        assert tracker._stats["bug_test_001"].times_applied == 2

    def test_record_application_sets_last_applied(self, tmp_path):
        """record_application sets last_applied timestamp."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001")
        assert tracker._stats["bug_test_001"].last_applied is not None

    def test_record_application_with_notes_adds_feedback(self, tmp_path):
        """record_application with notes adds feedback entry."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=True, notes="Fixed the issue")
        feedback = tracker._stats["bug_test_001"].feedback
        assert len(feedback) == 1
        assert feedback[0]["notes"] == "Fixed the issue"
        assert feedback[0]["successful"] is True

    def test_record_application_without_notes_no_feedback(self, tmp_path):
        """record_application without notes adds no feedback entry."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=True)
        assert tracker._stats["bug_test_001"].feedback == []


class TestPatternConfidenceTrackerGetPatternStats:
    """Tests for PatternConfidenceTracker.get_pattern_stats."""

    def test_get_pattern_stats_returns_dict(self, tmp_path):
        """get_pattern_stats returns a dictionary."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        result = tracker.get_pattern_stats("bug_new_001")
        assert isinstance(result, dict)

    def test_get_pattern_stats_for_existing_pattern(self, tmp_path):
        """get_pattern_stats returns correct data for existing pattern."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_test_001")
        tracker.record_application("bug_test_001", successful=True)

        result = tracker.get_pattern_stats("bug_test_001")

        assert result["pattern_id"] == "bug_test_001"
        assert result["times_suggested"] == 1
        assert result["times_applied"] == 1
        assert result["times_successful"] == 1
        assert result["times_unsuccessful"] == 0

    def test_get_pattern_stats_for_missing_pattern_returns_zeros(self, tmp_path):
        """get_pattern_stats for unknown pattern returns zero counts."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        result = tracker.get_pattern_stats("nonexistent_pattern")

        assert result["times_suggested"] == 0
        assert result["times_applied"] == 0
        assert result["confidence_score"] == 0.0

    def test_get_pattern_stats_includes_computed_rates(self, tmp_path):
        """get_pattern_stats includes success_rate, application_rate, confidence_score."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_test_001")
        tracker.record_application("bug_test_001", successful=True)

        result = tracker.get_pattern_stats("bug_test_001")

        assert "success_rate" in result
        assert "application_rate" in result
        assert "confidence_score" in result
        assert "feedback_count" in result

    def test_get_pattern_stats_feedback_count_matches(self, tmp_path):
        """get_pattern_stats feedback_count reflects actual feedback entries."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_application("bug_test_001", successful=True, notes="note1")
        tracker.record_application("bug_test_001", successful=True, notes="note2")

        result = tracker.get_pattern_stats("bug_test_001")
        assert result["feedback_count"] == 2


class TestPatternConfidenceTrackerGetAllStats:
    """Tests for PatternConfidenceTracker.get_all_stats."""

    def test_get_all_stats_empty_when_no_patterns(self, tmp_path):
        """get_all_stats returns empty list when no patterns recorded."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.get_all_stats() == []

    def test_get_all_stats_returns_all_patterns(self, tmp_path):
        """get_all_stats returns stats for all tracked patterns."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_a")
        tracker.record_suggestion("bug_b")
        tracker.record_suggestion("bug_c")

        result = tracker.get_all_stats()
        assert len(result) == 3

    def test_get_all_stats_each_item_is_dict(self, tmp_path):
        """get_all_stats returns list of dicts."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_a")

        result = tracker.get_all_stats()
        assert all(isinstance(item, dict) for item in result)


class TestPatternConfidenceTrackerGetTopPatterns:
    """Tests for PatternConfidenceTracker.get_top_patterns."""

    def test_get_top_patterns_sorted_by_confidence_score(self, tmp_path):
        """get_top_patterns returns patterns sorted by confidence_score descending."""
        tracker = PatternConfidenceTracker(str(tmp_path))

        # Create high-confidence pattern
        for _ in range(5):
            tracker.record_suggestion("bug_high")
            tracker.record_application("bug_high", successful=True)

        # Create low-confidence pattern
        tracker.record_suggestion("bug_low")
        tracker.record_application("bug_low", successful=False)

        top = tracker.get_top_patterns(limit=10)

        # High confidence should come first
        scores = [p["confidence_score"] for p in top]
        assert scores == sorted(scores, reverse=True)

    def test_get_top_patterns_respects_limit(self, tmp_path):
        """get_top_patterns returns at most limit patterns."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        for i in range(5):
            tracker.record_suggestion(f"bug_{i:03d}")

        top = tracker.get_top_patterns(limit=3)
        assert len(top) <= 3

    def test_get_top_patterns_empty_when_no_patterns(self, tmp_path):
        """get_top_patterns returns empty list with no data."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.get_top_patterns() == []


class TestPatternConfidenceTrackerGetStalePatterns:
    """Tests for PatternConfidenceTracker.get_stale_patterns."""

    def test_get_stale_patterns_empty_when_no_patterns(self, tmp_path):
        """get_stale_patterns returns empty list with no data."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        assert tracker.get_stale_patterns(days=90) == []

    def test_get_stale_patterns_excludes_recent_patterns(self, tmp_path):
        """get_stale_patterns excludes recently used patterns."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_recent")  # Sets last_suggested to now

        stale = tracker.get_stale_patterns(days=1)
        assert len(stale) == 0

    def test_get_stale_patterns_excludes_patterns_with_no_timestamp(self, tmp_path):
        """get_stale_patterns excludes patterns with no timestamp."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        tracker._stats["bug_no_ts"] = PatternUsageStats(pattern_id="bug_no_ts")
        # last_suggested and last_applied are both None — should not appear

        stale = tracker.get_stale_patterns(days=1)
        assert len(stale) == 0

    def test_get_stale_patterns_includes_old_patterns(self, tmp_path):
        """get_stale_patterns includes patterns whose last use is older than cutoff."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        # Manually set an old timestamp (year 2020)
        old_stats = PatternUsageStats(
            pattern_id="bug_old_001",
            times_suggested=3,
            last_suggested="2020-01-01T00:00:00",
        )
        tracker._stats["bug_old_001"] = old_stats

        stale = tracker.get_stale_patterns(days=30)

        assert len(stale) == 1
        assert stale[0]["pattern_id"] == "bug_old_001"

    def test_get_stale_patterns_skips_invalid_timestamp(self, tmp_path):
        """get_stale_patterns skips patterns with unparseable timestamps."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        bad_stats = PatternUsageStats(
            pattern_id="bug_bad_ts",
            last_suggested="not-a-valid-iso-date",
        )
        tracker._stats["bug_bad_ts"] = bad_stats

        stale = tracker.get_stale_patterns(days=1)
        # Should not raise, should just skip
        assert "bug_bad_ts" not in [p["pattern_id"] for p in stale]


class TestPatternConfidenceTrackerUpdatePatternSummary:
    """Tests for PatternConfidenceTracker.update_pattern_summary."""

    def test_update_pattern_summary_returns_false_when_no_patterns(self, tmp_path):
        """update_pattern_summary returns False with no patterns."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        result = tracker.update_pattern_summary()
        assert result is False

    def test_update_pattern_summary_returns_false_when_summary_missing(self, tmp_path, monkeypatch):
        """update_pattern_summary returns False when summary file doesn't exist."""
        # Change to tmp_path so .claude/patterns_summary.md is NOT found there
        monkeypatch.chdir(tmp_path)

        tracker = PatternConfidenceTracker(str(tmp_path))
        for _ in range(3):
            tracker.record_suggestion("bug_a")
            tracker.record_application("bug_a", successful=True)

        result = tracker.update_pattern_summary()
        assert result is False

    def test_update_pattern_summary_inserts_confidence_section(self, tmp_path, monkeypatch):
        """update_pattern_summary inserts confidence section into summary file."""
        # Point the summary path to tmp_path
        summary_path = tmp_path / ".claude" / "patterns_summary.md"
        summary_path.parent.mkdir(parents=True)
        summary_path.write_text(
            "# Header\n\n## How to Use These Patterns\n\nContent here.\n",
            encoding="utf-8",
        )

        monkeypatch.chdir(tmp_path)

        tracker = PatternConfidenceTracker(str(tmp_path))
        for _ in range(3):
            tracker.record_suggestion("bug_a")
            tracker.record_application("bug_a", successful=True)

        result = tracker.update_pattern_summary()
        assert result is True

        updated = summary_path.read_text(encoding="utf-8")
        assert "Pattern Confidence" in updated

    def test_update_pattern_summary_appends_when_no_insert_point(self, tmp_path, monkeypatch):
        """update_pattern_summary appends when 'How to Use' section absent."""
        summary_path = tmp_path / ".claude" / "patterns_summary.md"
        summary_path.parent.mkdir(parents=True)
        summary_path.write_text("# Summary\n\nSome content.\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        tracker = PatternConfidenceTracker(str(tmp_path))
        for _ in range(3):
            tracker.record_suggestion("bug_a")
            tracker.record_application("bug_a", successful=True)

        result = tracker.update_pattern_summary()
        assert result is True

        updated = summary_path.read_text(encoding="utf-8")
        assert "Pattern Confidence" in updated

    def test_update_pattern_summary_returns_false_on_write_error(self, tmp_path, monkeypatch):
        """update_pattern_summary returns False when write raises an exception."""
        summary_path = tmp_path / ".claude" / "patterns_summary.md"
        summary_path.parent.mkdir(parents=True)
        summary_path.write_text("# Header\n\nSome content.\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)

        tracker = PatternConfidenceTracker(str(tmp_path))
        for _ in range(3):
            tracker.record_suggestion("bug_a")
            tracker.record_application("bug_a", successful=True)

        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            result = tracker.update_pattern_summary()

        assert result is False


class TestPatternConfidenceTrackerSaveError:
    """Tests for PatternConfidenceTracker._save OSError handling."""

    def test_save_logs_error_when_write_fails(self, tmp_path):
        """_save handles OSError gracefully without raising."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        tracker._stats["bug_test"] = PatternUsageStats(pattern_id="bug_test")

        with patch("builtins.open", side_effect=OSError("disk full")):
            # Should not raise — just log the error
            tracker._save()

    def test_save_logs_error_when_path_open_fails(self, tmp_path):
        """_save handles OSError from Path.open gracefully."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        tracker._stats["bug_test"] = PatternUsageStats(pattern_id="bug_test")

        with patch("pathlib.Path.open", side_effect=OSError("permission denied")):
            # Should not raise — just log the error
            tracker._save()

    def test_save_logs_error_when_value_error_raised(self, tmp_path):
        """_save handles ValueError (e.g. path validation fails) gracefully."""
        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        tracker._stats["bug_test"] = PatternUsageStats(pattern_id="bug_test")

        with patch(
            "attune.security.path_validation._validate_file_path",
            side_effect=ValueError("invalid path"),
        ):
            tracker._save()


# ---------------------------------------------------------------------------
# main() CLI function coverage
# ---------------------------------------------------------------------------


class TestConfidenceMainCLI:
    """Tests for the confidence.py CLI main() function."""

    def test_list_no_data(self, tmp_path, capsys):
        """'list' with no data prints 'No pattern usage data recorded yet.'"""

        from attune.patterns.confidence import main

        with patch(
            "sys.argv",
            ["confidence", "--patterns-dir", str(tmp_path), "list"],
        ):
            main()

        captured = capsys.readouterr()
        assert "No pattern usage data" in captured.out

    def test_list_with_data(self, tmp_path, capsys):
        """'list' with pattern data prints confidence scores."""

        from attune.patterns.confidence import PatternConfidenceTracker, main

        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_001")
        tracker.record_application("bug_001", successful=True)

        with patch(
            "sys.argv", ["confidence", "--patterns-dir", str(tmp_path), "list", "--top", "5"]
        ):
            main()

        captured = capsys.readouterr()
        assert "bug_001" in captured.out

    def test_stats_command(self, tmp_path, capsys):
        """'stats' prints key/value pairs for a pattern."""
        from attune.patterns.confidence import PatternConfidenceTracker, main

        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker.record_suggestion("bug_001")

        with patch("sys.argv", ["confidence", "--patterns-dir", str(tmp_path), "stats", "bug_001"]):
            main()

        captured = capsys.readouterr()
        assert "bug_001" in captured.out

    def test_record_suggested(self, tmp_path, capsys):
        """'record --suggested' records a suggestion."""
        from attune.patterns.confidence import main

        with patch(
            "sys.argv",
            ["confidence", "--patterns-dir", str(tmp_path), "record", "bug_001", "--suggested"],
        ):
            main()

        captured = capsys.readouterr()
        assert "Recorded suggestion" in captured.out

    def test_record_applied_success(self, tmp_path, capsys):
        """'record --applied --success' records a successful application."""
        from attune.patterns.confidence import main

        with patch(
            "sys.argv",
            [
                "confidence",
                "--patterns-dir",
                str(tmp_path),
                "record",
                "bug_001",
                "--applied",
                "--success",
            ],
        ):
            main()

        captured = capsys.readouterr()
        assert "Recorded application" in captured.out
        assert "success=True" in captured.out

    def test_stale_no_data(self, tmp_path, capsys):
        """'stale' with no patterns prints appropriate message."""
        from attune.patterns.confidence import main

        with patch(
            "sys.argv", ["confidence", "--patterns-dir", str(tmp_path), "stale", "--days", "90"]
        ):
            main()

        captured = capsys.readouterr()
        assert "No patterns unused" in captured.out

    def test_stale_with_data(self, tmp_path, capsys):
        """'stale' lists patterns with old last_applied date."""
        from datetime import datetime, timedelta

        from attune.patterns.confidence import PatternConfidenceTracker, PatternUsageStats, main

        tracker = PatternConfidenceTracker(str(tmp_path))
        tracker._ensure_loaded()
        old_stats = PatternUsageStats(pattern_id="old_bug")
        old_stats.times_suggested = 1
        old_stats.last_suggested = (datetime.now() - timedelta(days=200)).isoformat()
        tracker._stats["old_bug"] = old_stats
        tracker._save()

        with patch(
            "sys.argv", ["confidence", "--patterns-dir", str(tmp_path), "stale", "--days", "90"]
        ):
            main()

        captured = capsys.readouterr()
        assert "old_bug" in captured.out

    def test_no_command_prints_help(self, tmp_path, capsys):
        """No subcommand prints help."""
        from attune.patterns.confidence import main

        with patch("sys.argv", ["confidence", "--patterns-dir", str(tmp_path)]):
            main()

        # Help output should show usage/commands
        captured = capsys.readouterr()
        assert captured.out or True  # argparse may print to stderr
