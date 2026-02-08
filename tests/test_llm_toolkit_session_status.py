"""Tests for empathy_llm_toolkit session_status module.

Comprehensive test coverage for SessionStatusCollector, StatusItem,
and SessionStatus classes.

Created: 2026-01-20
Coverage target: 80%+
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from attune_llm.session_status import (
    DEFAULT_CONFIG,
    PRIORITY_WEIGHTS,
    SessionStatus,
    SessionStatusCollector,
    StatusItem,
)

# =============================================================================
# StatusItem Tests
# =============================================================================


class TestStatusItem:
    """Tests for StatusItem dataclass."""

    def test_creation_basic(self):
        """Test creating a basic StatusItem."""
        item = StatusItem(
            category="bugs_high",
            priority=80,
            icon="🔴",
            title="High severity bug",
            description="Fix the bug",
        )

        assert item.category == "bugs_high"
        assert item.priority == 80
        assert item.icon == "🔴"
        assert item.title == "High severity bug"
        assert item.description == "Fix the bug"
        assert item.action_prompt == ""
        assert item.details == {}

    def test_creation_with_all_fields(self):
        """Test creating StatusItem with all fields."""
        item = StatusItem(
            category="security_pending",
            priority=100,
            icon="🔴",
            title="Security review needed",
            description="Review the finding",
            action_prompt="Review finding XYZ",
            details={"count": 3, "items": ["a", "b", "c"]},
        )

        assert item.action_prompt == "Review finding XYZ"
        assert item.details["count"] == 3
        assert len(item.details["items"]) == 3

    def test_weight_property_known_category(self):
        """Test weight property for known categories."""
        item = StatusItem(
            category="security_pending",
            priority=100,
            icon="🔴",
            title="Test",
            description="Test",
        )

        assert item.weight == PRIORITY_WEIGHTS["security_pending"]
        assert item.weight == 100

    def test_weight_property_unknown_category(self):
        """Test weight property for unknown categories."""
        item = StatusItem(
            category="unknown_category",
            priority=50,
            icon="⚪",
            title="Test",
            description="Test",
        )

        assert item.weight == 0


# =============================================================================
# SessionStatus Tests
# =============================================================================


class TestSessionStatus:
    """Tests for SessionStatus dataclass."""

    def test_creation_default(self):
        """Test creating SessionStatus with defaults."""
        status = SessionStatus()

        assert status.items == []
        assert status.wins == []
        assert status.total_attention_items == 0
        assert status.generated_at is not None

    def test_add_item(self):
        """Test adding items to status."""
        status = SessionStatus()

        item = StatusItem(
            category="bugs_high",
            priority=80,
            icon="🔴",
            title="Bug",
            description="Fix it",
        )

        status.add_item(item)

        assert len(status.items) == 1
        assert status.total_attention_items == 1
        assert status.items[0] == item

    def test_add_multiple_items(self):
        """Test adding multiple items."""
        status = SessionStatus()

        for i in range(5):
            item = StatusItem(
                category=f"category_{i}",
                priority=i * 10,
                icon="⚪",
                title=f"Item {i}",
                description="Description",
            )
            status.add_item(item)

        assert len(status.items) == 5
        assert status.total_attention_items == 5

    def test_get_sorted_items(self):
        """Test sorting items by weight."""
        status = SessionStatus()

        # Add items with different priorities
        low_priority = StatusItem(
            category="commits_wip",  # weight 20
            priority=20,
            icon="⚪",
            title="Low",
            description="Low priority",
        )
        high_priority = StatusItem(
            category="security_pending",  # weight 100
            priority=100,
            icon="🔴",
            title="High",
            description="High priority",
        )
        medium_priority = StatusItem(
            category="bugs_high",  # weight 80
            priority=80,
            icon="🔴",
            title="Medium",
            description="Medium priority",
        )

        # Add in random order
        status.add_item(low_priority)
        status.add_item(high_priority)
        status.add_item(medium_priority)

        sorted_items = status.get_sorted_items()

        # Should be sorted by weight descending
        assert sorted_items[0].category == "security_pending"
        assert sorted_items[1].category == "bugs_high"
        assert sorted_items[2].category == "commits_wip"


# =============================================================================
# SessionStatusCollector Tests
# =============================================================================


class TestSessionStatusCollector:
    """Tests for SessionStatusCollector class."""

    def test_init_default(self, tmp_path):
        """Test initialization with defaults."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        assert collector.patterns_dir == tmp_path / "patterns"
        assert collector.project_root == tmp_path
        assert collector.config == DEFAULT_CONFIG

    def test_init_custom_config(self, tmp_path):
        """Test initialization with custom config."""
        custom_config = {
            "inactivity_minutes": 120,
            "max_display_items": 10,
        }

        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
            config=custom_config,
        )

        assert collector.config["inactivity_minutes"] == 120
        assert collector.config["max_display_items"] == 10
        # Should still have default for show_wins
        assert collector.config["show_wins"] is True


class TestSessionStatusCollectorShouldShow:
    """Tests for should_show functionality."""

    def test_should_show_first_time(self, tmp_path):
        """Test that status shows on first interaction."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        assert collector.should_show() is True

    def test_should_show_new_day(self, tmp_path):
        """Test that status shows on new calendar day."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        # Create state with yesterday's interaction
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        state = {"last_interaction": yesterday}

        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()
        state_file = empathy_dir / "session_state.json"
        state_file.write_text(json.dumps(state))

        assert collector.should_show() is True

    def test_should_show_after_inactivity(self, tmp_path):
        """Test that status shows after inactivity threshold."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
            config={"inactivity_minutes": 30},
        )

        # Create state with 45 minutes ago
        old_time = (datetime.now() - timedelta(minutes=45)).isoformat()
        state = {"last_interaction": old_time}

        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()
        state_file = empathy_dir / "session_state.json"
        state_file.write_text(json.dumps(state))

        assert collector.should_show() is True

    def test_should_not_show_recent_activity(self, tmp_path):
        """Test that status doesn't show for recent activity."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
            config={"inactivity_minutes": 60},
        )

        # Create state with 5 minutes ago
        recent_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        state = {"last_interaction": recent_time}

        empathy_dir = tmp_path / ".empathy"
        empathy_dir.mkdir()
        state_file = empathy_dir / "session_state.json"
        state_file.write_text(json.dumps(state))

        assert collector.should_show() is False


class TestSessionStatusCollectorRecordInteraction:
    """Tests for record_interaction functionality."""

    def test_record_interaction(self, tmp_path):
        """Test recording an interaction."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        collector.record_interaction()

        # Check state was saved
        state_file = tmp_path / ".empathy" / "session_state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert "last_interaction" in state
        assert state["interaction_count"] == 1

    def test_record_multiple_interactions(self, tmp_path):
        """Test recording multiple interactions."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        collector.record_interaction()
        collector._state = None  # Clear cache to force reload
        collector.record_interaction()

        state_file = tmp_path / ".empathy" / "session_state.json"
        state = json.loads(state_file.read_text())
        assert state["interaction_count"] == 2


class TestSessionStatusCollectorCollect:
    """Tests for collect functionality."""

    def test_collect_empty(self, tmp_path):
        """Test collecting with no data sources."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        assert isinstance(status, SessionStatus)
        assert status.total_attention_items == 0

    def test_collect_security_items(self, tmp_path):
        """Test collecting security pending items."""
        # Create patterns directory with security data
        patterns_dir = tmp_path / "patterns"
        security_dir = patterns_dir / "security"
        security_dir.mkdir(parents=True)

        decisions_file = security_dir / "team_decisions.json"
        decisions_file.write_text(
            json.dumps(
                {
                    "decisions": [
                        {"decision": "PENDING", "finding_hash": "abc123"},
                        {"decision": "ACCEPTED", "finding_hash": "def456"},
                    ]
                }
            )
        )

        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        # Should find the pending security item
        security_items = [i for i in status.items if i.category == "security_pending"]
        assert len(security_items) == 1
        assert "abc123" in security_items[0].description

    def test_collect_bug_items_high_severity(self, tmp_path):
        """Test collecting high severity bugs."""
        patterns_dir = tmp_path / "patterns"
        debugging_dir = patterns_dir / "debugging"
        debugging_dir.mkdir(parents=True)

        bug_file = debugging_dir / "bug_001.json"
        bug_file.write_text(
            json.dumps(
                {
                    "bug_id": "BUG-001",
                    "status": "open",
                    "severity": "high",
                    "error_type": "TypeError",
                    "error_message": "Cannot read property of undefined",
                    "file_path": "src/utils.ts",
                }
            )
        )

        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        bug_items = [i for i in status.items if i.category == "bugs_high"]
        assert len(bug_items) == 1
        assert "TypeError" in bug_items[0].description

    def test_collect_bug_items_investigating(self, tmp_path):
        """Test collecting investigating bugs."""
        patterns_dir = tmp_path / "patterns"
        debugging_dir = patterns_dir / "debugging"
        debugging_dir.mkdir(parents=True)

        bug_file = debugging_dir / "bug_002.json"
        bug_file.write_text(
            json.dumps(
                {
                    "bug_id": "BUG-002",
                    "status": "investigating",
                    "severity": "medium",
                    "error_message": "Race condition in async code",
                }
            )
        )

        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        investigating_items = [i for i in status.items if i.category == "bugs_investigating"]
        assert len(investigating_items) == 1

    def test_collect_tech_debt_increasing(self, tmp_path):
        """Test collecting tech debt trajectory."""
        patterns_dir = tmp_path / "patterns"
        debt_dir = patterns_dir / "tech_debt"
        debt_dir.mkdir(parents=True)

        debt_file = debt_dir / "debt_history.json"
        debt_file.write_text(
            json.dumps(
                {
                    "snapshots": [
                        {"date": "2026-01-18", "total_items": 10},
                        {"date": "2026-01-19", "total_items": 15},  # Increased
                    ]
                }
            )
        )

        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        debt_items = [i for i in status.items if i.category == "tech_debt_increasing"]
        assert len(debt_items) == 1
        assert "+5" in debt_items[0].title

    def test_collect_tech_debt_decreasing_adds_win(self, tmp_path):
        """Test that decreasing tech debt adds a win."""
        patterns_dir = tmp_path / "patterns"
        debt_dir = patterns_dir / "tech_debt"
        debt_dir.mkdir(parents=True)

        debt_file = debt_dir / "debt_history.json"
        debt_file.write_text(
            json.dumps(
                {
                    "snapshots": [
                        {"date": "2026-01-18", "total_items": 15},
                        {"date": "2026-01-19", "total_items": 10},  # Decreased
                    ]
                }
            )
        )

        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        # Should be added as a win, not an item
        debt_items = [i for i in status.items if "tech_debt" in i.category]
        assert len(debt_items) == 0
        assert any("decreased" in w.lower() for w in status.wins)

    def test_collect_roadmap_items(self, tmp_path):
        """Test collecting roadmap unchecked items."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        plan_file = docs_dir / "PLAN_v3.md"
        plan_file.write_text(
            """
# Plan v3

## Tasks
- [x] Completed task
- [ ] Unchecked task 1
- [ ] Unchecked task 2
- [x] Another completed
"""
        )

        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = collector.collect()

        roadmap_items = [i for i in status.items if i.category == "roadmap_unchecked"]
        assert len(roadmap_items) == 1
        assert "2 unchecked" in roadmap_items[0].title


class TestSessionStatusCollectorGitItems:
    """Tests for git-related collection."""

    def test_collect_git_wip_commits(self, tmp_path):
        """Test collecting WIP commits from git."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc1234|WIP: Adding new feature\ndef5678|fix: Bug fix"

        with patch("subprocess.run", return_value=mock_result):
            status = collector.collect()

        wip_items = [i for i in status.items if i.category == "commits_wip"]
        assert len(wip_items) == 1
        assert "WIP" in wip_items[0].details["commits"][0]["message"]

    def test_collect_git_not_available(self, tmp_path):
        """Test handling when git is not available."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        mock_result = MagicMock()
        mock_result.returncode = 128  # Git error

        with patch("subprocess.run", return_value=mock_result):
            status = collector.collect()

        wip_items = [i for i in status.items if i.category == "commits_wip"]
        assert len(wip_items) == 0


class TestSessionStatusCollectorFormatOutput:
    """Tests for format_output functionality."""

    def test_format_output_empty(self, tmp_path):
        """Test formatting empty status."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        output = collector.format_output(status)

        assert "0 items need attention" in output

    def test_format_output_with_items(self, tmp_path):
        """Test formatting status with items."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="security_pending",
                priority=100,
                icon="🔴",
                title="Security: 1 pending review",
                description="Review finding xyz",
            )
        )

        output = collector.format_output(status)

        assert "1 items need attention" in output
        assert "🔴" in output
        assert "Security" in output
        assert "Review finding xyz" in output

    def test_format_output_with_wins(self, tmp_path):
        """Test formatting status with wins."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.wins.append("2 bugs fixed!")
        status.wins.append("Coverage increased")

        output = collector.format_output(status)

        assert "🎉 Wins" in output
        assert "2 bugs fixed" in output
        assert "Coverage increased" in output

    def test_format_output_max_items(self, tmp_path):
        """Test that max_items limits output."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        for i in range(10):
            status.add_item(
                StatusItem(
                    category=f"category_{i}",
                    priority=i,
                    icon="⚪",
                    title=f"Item {i}",
                    description="Description",
                )
            )

        output = collector.format_output(status, max_items=3)

        # Should only show 3 items (count titles)
        title_count = output.count("Item ")
        assert title_count <= 3


class TestSessionStatusCollectorFormatJson:
    """Tests for JSON formatting."""

    def test_format_json(self, tmp_path):
        """Test JSON formatting."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="bugs_high",
                priority=80,
                icon="🔴",
                title="Bug found",
                description="Fix it",
                action_prompt="Run fix command",
            )
        )
        status.wins.append("Test passed")

        json_output = collector.format_json(status)
        data = json.loads(json_output)

        assert data["total_attention_items"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["category"] == "bugs_high"
        assert data["wins"] == ["Test passed"]


class TestSessionStatusCollectorActionPrompt:
    """Tests for action prompt functionality."""

    def test_get_action_prompt_valid_selection(self, tmp_path):
        """Test getting action prompt for valid selection."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="bugs_high",
                priority=80,
                icon="🔴",
                title="Bug",
                description="Desc",
                action_prompt="Fix the bug please",
            )
        )

        prompt = collector.get_action_prompt(status, 1)

        assert prompt == "Fix the bug please"

    def test_get_action_prompt_invalid_selection(self, tmp_path):
        """Test getting action prompt for invalid selection."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="bugs_high",
                priority=80,
                icon="🔴",
                title="Bug",
                description="Desc",
            )
        )

        # Selection out of range
        assert collector.get_action_prompt(status, 0) is None
        assert collector.get_action_prompt(status, 5) is None


class TestSessionStatusCollectorSnapshots:
    """Tests for snapshot functionality."""

    def test_save_daily_snapshot(self, tmp_path):
        """Test saving daily snapshot."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="bugs_investigating",
                priority=60,
                icon="🟡",
                title="Bug",
                description="Desc",
                details={"count": 3},
            )
        )

        collector._save_daily_snapshot(status)

        # Check snapshot was saved
        today = datetime.now().strftime("%Y-%m-%d")
        snapshot_file = tmp_path / ".empathy" / "status_history" / f"{today}.json"
        assert snapshot_file.exists()

        snapshot = json.loads(snapshot_file.read_text())
        assert snapshot["total_attention_items"] == 1
        assert snapshot["bugs_investigating"] == 3

    def test_load_previous_snapshot(self, tmp_path):
        """Test loading previous snapshot."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        # Create history directory with yesterday's snapshot
        history_dir = tmp_path / ".empathy" / "status_history"
        history_dir.mkdir(parents=True)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        snapshot_file = history_dir / f"{yesterday}.json"
        snapshot_file.write_text(
            json.dumps(
                {
                    "date": yesterday,
                    "bugs_investigating": 5,
                }
            )
        )

        snapshot = collector._load_previous_snapshot()

        assert snapshot is not None
        assert snapshot["bugs_investigating"] == 5

    def test_load_previous_snapshot_none(self, tmp_path):
        """Test loading previous snapshot when none exists."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        snapshot = collector._load_previous_snapshot()

        assert snapshot is None


class TestSessionStatusCollectorWins:
    """Tests for win detection."""

    def test_detect_wins_bugs_resolved(self, tmp_path):
        """Test detecting resolved bugs as wins."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        # Create previous snapshot with 5 investigating bugs
        history_dir = tmp_path / ".empathy" / "status_history"
        history_dir.mkdir(parents=True)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        snapshot_file = history_dir / f"{yesterday}.json"
        snapshot_file.write_text(
            json.dumps(
                {
                    "date": yesterday,
                    "bugs_investigating": 5,
                }
            )
        )

        # Current status with only 2 investigating bugs
        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="bugs_investigating",
                priority=60,
                icon="🟡",
                title="Bugs",
                description="Desc",
                details={"count": 2},
            )
        )

        collector._detect_wins(status)

        # Should detect 3 bugs resolved
        assert any("3 bug" in w for w in status.wins)


# =============================================================================
# Integration Tests
# =============================================================================


class TestSessionStatusIntegration:
    """Integration tests for session status system."""

    def test_full_workflow(self, tmp_path):
        """Test full status workflow."""
        # Setup patterns
        patterns_dir = tmp_path / "patterns"
        security_dir = patterns_dir / "security"
        security_dir.mkdir(parents=True)

        decisions_file = security_dir / "team_decisions.json"
        decisions_file.write_text(
            json.dumps(
                {
                    "decisions": [
                        {"decision": "PENDING", "finding_hash": "sec123"},
                    ]
                }
            )
        )

        # Setup docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        plan_file = docs_dir / "PLAN_v1.md"
        plan_file.write_text("- [ ] Task 1\n- [ ] Task 2")

        # Create collector
        collector = SessionStatusCollector(
            patterns_dir=str(patterns_dir),
            project_root=str(tmp_path),
        )

        # Should show (first time)
        assert collector.should_show() is True

        # Collect status
        status = collector.collect()

        # Should have security and roadmap items
        assert status.total_attention_items >= 2

        # Format output
        output = collector.format_output(status)
        assert "Security" in output
        assert "Roadmap" in output

        # Record interaction
        collector.record_interaction()

        # Should not show again (recent activity)
        collector._state = None  # Clear cache
        assert collector.should_show() is False

    def test_json_round_trip(self, tmp_path):
        """Test JSON format round trip."""
        collector = SessionStatusCollector(
            patterns_dir=str(tmp_path / "patterns"),
            project_root=str(tmp_path),
        )

        status = SessionStatus()
        status.add_item(
            StatusItem(
                category="security_pending",
                priority=100,
                icon="🔴",
                title="Security review",
                description="Review finding",
                action_prompt="Review XYZ",
                details={"count": 1},
            )
        )
        status.wins.append("Bug fixed")

        # Convert to JSON and back
        json_str = collector.format_json(status)
        data = json.loads(json_str)

        # Verify structure
        assert data["total_attention_items"] == 1
        assert data["items"][0]["category"] == "security_pending"
        assert data["items"][0]["details"]["count"] == 1
        assert data["wins"] == ["Bug fixed"]
