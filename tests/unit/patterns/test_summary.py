"""Unit tests for attune.patterns.summary module.

Tests PatternSummaryGenerator: loading, generating markdown, writing files.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json

from attune.patterns.summary import PatternSummaryGenerator


class TestPatternSummaryGeneratorInit:
    """Tests for PatternSummaryGenerator initialization."""

    def test_init_stores_patterns_dir(self, tmp_path):
        """__init__ stores the patterns directory as a Path."""
        gen = PatternSummaryGenerator(str(tmp_path))
        assert gen.patterns_dir == tmp_path

    def test_init_empty_bug_patterns(self, tmp_path):
        """__init__ starts with empty bug patterns list."""
        gen = PatternSummaryGenerator(str(tmp_path))
        assert gen._bug_patterns == []

    def test_init_empty_security_decisions(self, tmp_path):
        """__init__ starts with empty security decisions list."""
        gen = PatternSummaryGenerator(str(tmp_path))
        assert gen._security_decisions == []

    def test_init_empty_tech_debt_history(self, tmp_path):
        """__init__ starts with empty tech debt history list."""
        gen = PatternSummaryGenerator(str(tmp_path))
        assert gen._tech_debt_history == []


class TestLoadAllPatternsEmpty:
    """Tests for load_all_patterns with no fixture files."""

    def test_load_all_patterns_empty_dir_sets_empty_lists(self, tmp_path):
        """load_all_patterns with no files leaves all lists empty."""
        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        assert gen._bug_patterns == []
        assert gen._security_decisions == []
        assert gen._tech_debt_history == []

    def test_load_all_patterns_missing_dir_does_not_raise(self, tmp_path):
        """load_all_patterns does not raise when patterns_dir has no subdirs."""
        gen = PatternSummaryGenerator(str(tmp_path / "nonexistent"))
        gen.load_all_patterns()  # Should not raise
        assert gen._bug_patterns == []


class TestLoadBugPatterns:
    """Tests for _load_bug_patterns from debugging directories."""

    def test_load_bug_patterns_finds_files_in_debugging(self, tmp_path):
        """_load_bug_patterns loads JSON from 'debugging' subdirectory."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        bug_data = {
            "bug_id": "bug_test_001",
            "error_type": "null_reference",
            "status": "resolved",
        }
        (debug_dir / "bug_test_001.json").write_text(json.dumps(bug_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 1
        assert patterns[0]["bug_id"] == "bug_test_001"
        assert patterns[0]["_source_dir"] == "debugging"

    def test_load_bug_patterns_finds_files_in_debugging_demo(self, tmp_path):
        """_load_bug_patterns loads JSON from 'debugging_demo' subdirectory."""
        debug_dir = tmp_path / "debugging_demo"
        debug_dir.mkdir()
        bug_data = {"bug_id": "bug_demo_001", "error_type": "type_mismatch"}
        (debug_dir / "bug_demo_001.json").write_text(json.dumps(bug_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 1
        assert patterns[0]["_source_dir"] == "debugging_demo"

    def test_load_bug_patterns_finds_files_in_repo_test_debugging(self, tmp_path):
        """_load_bug_patterns loads from 'repo_test/debugging' subdirectory."""
        debug_dir = tmp_path / "repo_test" / "debugging"
        debug_dir.mkdir(parents=True)
        bug_data = {"bug_id": "bug_repo_001", "error_type": "import_error"}
        (debug_dir / "bug_repo_001.json").write_text(json.dumps(bug_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 1
        assert patterns[0]["_source_dir"] == "repo_test/debugging"

    def test_load_bug_patterns_skips_non_bug_files(self, tmp_path):
        """_load_bug_patterns only loads files matching 'bug_*.json'."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "other_file.json").write_text(json.dumps({"key": "value"}), encoding="utf-8")
        (debug_dir / "bug_match.json").write_text(
            json.dumps({"bug_id": "bug_match"}), encoding="utf-8"
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 1
        assert patterns[0]["bug_id"] == "bug_match"

    def test_load_bug_patterns_handles_invalid_json(self, tmp_path):
        """_load_bug_patterns skips files with invalid JSON gracefully."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_bad.json").write_text("not valid json", encoding="utf-8")
        (debug_dir / "bug_good.json").write_text(
            json.dumps({"bug_id": "bug_good"}), encoding="utf-8"
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 1
        assert patterns[0]["bug_id"] == "bug_good"

    def test_load_bug_patterns_loads_from_multiple_dirs(self, tmp_path):
        """_load_bug_patterns aggregates from all three debugging directories."""
        for dir_name in ["debugging", "debugging_demo"]:
            d = tmp_path / dir_name
            d.mkdir()
            (d / f"bug_{dir_name}.json").write_text(
                json.dumps({"bug_id": f"bug_{dir_name}"}), encoding="utf-8"
            )

        gen = PatternSummaryGenerator(str(tmp_path))
        patterns = gen._load_bug_patterns()

        assert len(patterns) == 2


class TestLoadSecurityDecisions:
    """Tests for _load_security_decisions."""

    def test_load_security_decisions_finds_team_decisions_json(self, tmp_path):
        """_load_security_decisions reads from 'security/team_decisions.json'."""
        sec_dir = tmp_path / "security"
        sec_dir.mkdir()
        decisions_data = {
            "decisions": [
                {
                    "finding_hash": "hash_001",
                    "decision": "accepted",
                    "reason": "False positive",
                    "decided_by": "@dev",
                }
            ]
        }
        (sec_dir / "team_decisions.json").write_text(json.dumps(decisions_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        decisions = gen._load_security_decisions()

        assert len(decisions) == 1
        assert decisions[0]["finding_hash"] == "hash_001"
        assert decisions[0]["_source_dir"] == "security"

    def test_load_security_decisions_finds_security_demo(self, tmp_path):
        """_load_security_decisions reads from 'security_demo' directory."""
        sec_dir = tmp_path / "security_demo"
        sec_dir.mkdir()
        decisions_data = {"decisions": [{"finding_hash": "demo_hash", "decision": "rejected"}]}
        (sec_dir / "team_decisions.json").write_text(json.dumps(decisions_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        decisions = gen._load_security_decisions()

        assert len(decisions) == 1
        assert decisions[0]["_source_dir"] == "security_demo"

    def test_load_security_decisions_empty_when_no_file(self, tmp_path):
        """_load_security_decisions returns empty list when file absent."""
        gen = PatternSummaryGenerator(str(tmp_path))
        decisions = gen._load_security_decisions()
        assert decisions == []

    def test_load_security_decisions_handles_invalid_json(self, tmp_path):
        """_load_security_decisions handles corrupt JSON gracefully."""
        sec_dir = tmp_path / "security"
        sec_dir.mkdir()
        (sec_dir / "team_decisions.json").write_text("invalid json", encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        decisions = gen._load_security_decisions()
        assert decisions == []


class TestLoadTechDebtHistory:
    """Tests for _load_tech_debt_history."""

    def test_load_tech_debt_history_finds_debt_history_json(self, tmp_path):
        """_load_tech_debt_history reads from 'tech_debt/debt_history.json'."""
        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        history_data = {"snapshots": [{"date": "2025-01-01", "total_items": 42}]}
        (debt_dir / "debt_history.json").write_text(json.dumps(history_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        snapshots = gen._load_tech_debt_history()

        assert len(snapshots) == 1
        assert snapshots[0]["total_items"] == 42
        assert snapshots[0]["_source_dir"] == "tech_debt"

    def test_load_tech_debt_history_finds_tech_debt_demo(self, tmp_path):
        """_load_tech_debt_history reads from 'tech_debt_demo' directory."""
        debt_dir = tmp_path / "tech_debt_demo"
        debt_dir.mkdir()
        history_data = {"snapshots": [{"date": "2025-06-01", "total_items": 10}]}
        (debt_dir / "debt_history.json").write_text(json.dumps(history_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        snapshots = gen._load_tech_debt_history()

        assert len(snapshots) == 1
        assert snapshots[0]["_source_dir"] == "tech_debt_demo"

    def test_load_tech_debt_history_empty_when_no_file(self, tmp_path):
        """_load_tech_debt_history returns empty list when file absent."""
        gen = PatternSummaryGenerator(str(tmp_path))
        assert gen._load_tech_debt_history() == []


class TestGenerateMarkdown:
    """Tests for PatternSummaryGenerator.generate_markdown."""

    def test_generate_markdown_returns_string(self, tmp_path):
        """generate_markdown returns a string."""
        gen = PatternSummaryGenerator(str(tmp_path))
        result = gen.generate_markdown()
        assert isinstance(result, str)

    def test_generate_markdown_includes_header(self, tmp_path):
        """generate_markdown includes 'Pattern Library Summary' header."""
        gen = PatternSummaryGenerator(str(tmp_path))
        result = gen.generate_markdown()
        assert "Pattern Library Summary" in result

    def test_generate_markdown_calls_load_when_empty(self, tmp_path):
        """generate_markdown auto-loads patterns when internal lists are empty."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_auto.json").write_text(
            json.dumps({"bug_id": "bug_auto", "error_type": "null_reference"}),
            encoding="utf-8",
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        # _bug_patterns is empty; generate_markdown should call load_all_patterns
        result = gen.generate_markdown()
        assert "null_reference" in result

    def test_generate_markdown_no_bugs_shows_placeholder(self, tmp_path):
        """generate_markdown shows placeholder text when no bug patterns."""
        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()
        assert "No bug patterns stored yet" in result

    def test_generate_markdown_no_security_shows_placeholder(self, tmp_path):
        """generate_markdown shows placeholder when no security decisions."""
        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()
        assert "No security decisions stored yet" in result

    def test_generate_markdown_no_debt_shows_placeholder(self, tmp_path):
        """generate_markdown shows placeholder when no tech debt history."""
        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()
        assert "No tech debt history stored yet" in result

    def test_generate_markdown_includes_how_to_use_section(self, tmp_path):
        """generate_markdown includes 'How to Use These Patterns' section."""
        gen = PatternSummaryGenerator(str(tmp_path))
        result = gen.generate_markdown()
        assert "How to Use These Patterns" in result

    def test_generate_markdown_with_bugs_includes_bug_id(self, tmp_path):
        """generate_markdown with bug data includes bug_id in output."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        bug_data = {
            "bug_id": "bug_20250101_aabbccdd",
            "error_type": "null_reference",
            "status": "resolved",
            "root_cause": "Missing null check",
            "fix_applied": "Added guard clause",
        }
        (debug_dir / "bug_20250101_aabbccdd.json").write_text(
            json.dumps(bug_data), encoding="utf-8"
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()

        assert "bug_20250101_aabbccdd" in result
        assert "null_reference" in result

    def test_generate_markdown_with_security_includes_decision(self, tmp_path):
        """generate_markdown with security data includes decision info."""
        sec_dir = tmp_path / "security"
        sec_dir.mkdir()
        decisions_data = {
            "decisions": [
                {
                    "finding_hash": "abc123",
                    "decision": "accepted",
                    "reason": "Not exploitable",
                    "decided_by": "@security-team",
                }
            ]
        }
        (sec_dir / "team_decisions.json").write_text(json.dumps(decisions_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()

        assert "abc123" in result
        assert "ACCEPTED" in result

    def test_generate_markdown_debt_trajectory_decreasing(self, tmp_path):
        """generate_markdown shows DECREASING when debt went down."""
        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        history_data = {
            "snapshots": [
                {"date": "2025-01-01", "total_items": 100},
                {"date": "2025-06-01", "total_items": 60},
            ]
        }
        (debt_dir / "debt_history.json").write_text(json.dumps(history_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()

        assert "DECREASING" in result

    def test_generate_markdown_debt_trajectory_increasing(self, tmp_path):
        """generate_markdown shows INCREASING when debt went up."""
        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        history_data = {
            "snapshots": [
                {"date": "2025-01-01", "total_items": 10},
                {"date": "2025-06-01", "total_items": 50},
            ]
        }
        (debt_dir / "debt_history.json").write_text(json.dumps(history_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()

        assert "INCREASING" in result

    def test_generate_markdown_debt_trajectory_stable(self, tmp_path):
        """generate_markdown shows STABLE when debt unchanged."""
        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        history_data = {
            "snapshots": [
                {"date": "2025-01-01", "total_items": 42},
                {"date": "2025-06-01", "total_items": 42},
            ]
        }
        (debt_dir / "debt_history.json").write_text(json.dumps(history_data), encoding="utf-8")

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        result = gen.generate_markdown()

        assert "STABLE" in result


class TestWriteToFile:
    """Tests for PatternSummaryGenerator.write_to_file."""

    def test_write_to_file_creates_output_file(self, tmp_path):
        """write_to_file creates the output file."""
        gen = PatternSummaryGenerator(str(tmp_path))
        output_path = tmp_path / "output" / "summary.md"

        gen.write_to_file(str(output_path))

        assert output_path.exists()

    def test_write_to_file_creates_parent_dirs(self, tmp_path):
        """write_to_file creates parent directories if they don't exist."""
        gen = PatternSummaryGenerator(str(tmp_path))
        output_path = tmp_path / "deep" / "nested" / "summary.md"

        gen.write_to_file(str(output_path))

        assert output_path.exists()

    def test_write_to_file_content_matches_generate_markdown(self, tmp_path):
        """write_to_file writes the same content as generate_markdown."""
        gen = PatternSummaryGenerator(str(tmp_path))
        expected = gen.generate_markdown()

        output_path = tmp_path / "summary.md"
        gen.write_to_file(str(output_path))

        written = output_path.read_text(encoding="utf-8")
        assert written == expected

    def test_write_to_file_with_bug_data(self, tmp_path):
        """write_to_file includes bug data when present."""
        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_write_test.json").write_text(
            json.dumps({"bug_id": "bug_write_test", "error_type": "type_mismatch"}),
            encoding="utf-8",
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        output_path = tmp_path / "summary.md"
        gen.write_to_file(str(output_path))

        content = output_path.read_text(encoding="utf-8")
        assert "bug_write_test" in content


# ===========================================================================
# Coverage gap tests
# ===========================================================================


class TestSummaryCoverageGaps:
    """Cover lines 121-122, 203, 267-268, 271-272, 275, 280->302, 322-353."""

    def test_load_debt_history_malformed(self, tmp_path, caplog):
        """Lines 121-122: malformed debt_history.json → warning."""
        import logging

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text("not-json{")

        gen = PatternSummaryGenerator(str(tmp_path))
        with caplog.at_level(logging.WARNING):
            gen.load_all_patterns()
        # Should not crash
        assert any("Debt history load failed" in r.message for r in caplog.records)

    def test_bugs_with_resolution_time_shown(self, tmp_path):
        """Line 203: bug with time_mins truthy → 'Resolution time' line."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debug_dir = tmp_path / "debugging"
        debug_dir.mkdir()
        (debug_dir / "bug_x.json").write_text(
            _json.dumps(
                {
                    "bug_id": "bug_x",
                    "status": "resolved",
                    "root_cause": "missing check",
                    "fix_applied": "added check",
                    "resolution_time_minutes": 15,
                }
            )
        )
        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "Resolution time: 15 min" in markdown

    def test_debt_section_with_by_type(self, tmp_path):
        """Lines 266-268: by_type rendered."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {
                            "date": "2025-12-01",
                            "total_items": 10,
                            "by_type": {"complexity": 3, "duplication": 7},
                        }
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "By type:" in markdown
        assert "complexity: 3" in markdown

    def test_debt_section_with_by_severity(self, tmp_path):
        """Lines 270-272: by_severity rendered."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {
                            "date": "2025-12-01",
                            "total_items": 5,
                            "by_severity": {"high": 2, "low": 3},
                        }
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "By severity:" in markdown
        assert "high: 2" in markdown

    def test_debt_section_with_hotspots(self, tmp_path):
        """Line 275: hotspots rendered."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {
                            "date": "2025-12-01",
                            "total_items": 5,
                            "hotspots": ["src/a.py", "src/b.py", "src/c.py"],
                        }
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "Hotspots:" in markdown
        assert "src/a.py" in markdown

    def test_debt_trajectory_with_two_snapshots(self, tmp_path):
        """Line 280-300: trajectory section rendered."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {"date": "2025-12-01", "total_items": 10},
                        {"date": "2025-11-01", "total_items": 5},
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        # 10 > 5 → INCREASING
        assert "Trajectory: INCREASING" in markdown
        assert "Change: 5 items" in markdown

    def test_debt_trajectory_decreasing(self, tmp_path):
        """Trajectory DECREASING."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {"date": "2025-12-01", "total_items": 5},
                        {"date": "2025-11-01", "total_items": 10},
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "Trajectory: DECREASING" in markdown

    def test_debt_trajectory_stable(self, tmp_path):
        """Trajectory STABLE."""
        import json as _json

        from attune.patterns.summary import PatternSummaryGenerator

        debt_dir = tmp_path / "tech_debt"
        debt_dir.mkdir()
        (debt_dir / "debt_history.json").write_text(
            _json.dumps(
                {
                    "snapshots": [
                        {"date": "2025-12-01", "total_items": 7},
                        {"date": "2025-11-01", "total_items": 7},
                    ]
                }
            )
        )

        gen = PatternSummaryGenerator(str(tmp_path))
        gen.load_all_patterns()
        markdown = gen.generate_markdown()
        assert "Trajectory: STABLE" in markdown


class TestSummaryMain:
    """Cover lines 322-353: main() CLI entry point."""

    def test_main_writes_to_file(self, tmp_path, capsys):
        """Default path: writes to file."""
        from unittest.mock import patch as _patch

        from attune.patterns import summary as mod

        output_file = tmp_path / "out" / "summary.md"
        argv = [
            "prog",
            "--patterns-dir",
            str(tmp_path),
            "--output",
            str(output_file),
        ]
        with _patch("sys.argv", argv):
            mod.main()
        out = capsys.readouterr().out
        assert "Pattern summary written to" in out
        assert output_file.exists()

    def test_main_print_mode(self, tmp_path, capsys):
        """--print → output to stdout instead of file."""
        from unittest.mock import patch as _patch

        from attune.patterns import summary as mod

        argv = ["prog", "--patterns-dir", str(tmp_path), "--print"]
        with _patch("sys.argv", argv):
            mod.main()
        out = capsys.readouterr().out
        # Should print the markdown content (which contains the title)
        assert "Pattern" in out or "patterns" in out.lower()
