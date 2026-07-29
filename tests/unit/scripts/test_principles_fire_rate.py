"""Tests for the principles fire-rate read (D12).

Pure functions only — the ``gh`` boundary is exercised through an
injected runner, never the real CLI.
"""

from __future__ import annotations

import json

import pytest

from scripts.principles_fire_rate import (
    MASTER,
    Principle,
    failed_run_logs,
    fire_counts,
    format_report,
    parse_principles,
)

SECTION = """\
### Principles

Preamble text.

1. **First rule.** Body text.
   *Enforcers: `tests/unit/gates/test_a.py`,
   `src/attune/hooks/scripts/guard.py` (PreToolUse block).*

2. **Second rule.** Entirely aspirational body, no citations.

3. **Third rule.** Wrapped citation:
   *Enforcer: `tests/unit/gates/
   test_wrapped.py`.*

### Shared truth

- `tests/unit/should_not_be_parsed.py` lives outside the section.
"""


class TestParsePrinciples:
    def test_parses_numbers_titles_and_enforcers(self):
        principles = parse_principles(SECTION)
        assert [p.number for p in principles] == [1, 2, 3]
        assert principles[0].title == "First rule"
        assert principles[0].enforcers == [
            "tests/unit/gates/test_a.py",
            "src/attune/hooks/scripts/guard.py",
        ]

    def test_aspirational_principle_has_no_enforcers(self):
        assert parse_principles(SECTION)[1].enforcers == []

    def test_line_wrapped_citation_is_collapsed(self):
        assert parse_principles(SECTION)[2].enforcers == ["tests/unit/gates/test_wrapped.py"]

    def test_citations_outside_section_are_ignored(self):
        all_enforcers = [e for p in parse_principles(SECTION) for e in p.enforcers]
        assert "tests/unit/should_not_be_parsed.py" not in all_enforcers

    def test_missing_heading_raises(self):
        with pytest.raises(ValueError):
            parse_principles("no principles here")

    def test_parses_the_real_master(self):
        principles = parse_principles(MASTER.read_text(encoding="utf-8"))
        assert len(principles) >= 15

    def test_no_numbered_items_raises(self):
        with pytest.raises(ValueError):
            parse_principles("### Principles\n\nprose only\n\n### Next\n")


class TestFireCounts:
    def test_counts_runs_where_enforcer_failed(self):
        principles = [Principle(1, "R", ["tests/unit/gates/test_a.py"])]
        logs = {"11": "FAILED tests/unit/gates/test_a.py::test_x", "12": "unrelated failure"}
        assert fire_counts(principles, logs) == {"tests/unit/gates/test_a.py": ["11"]}

    def test_bare_mention_without_failure_does_not_count(self):
        # A failed run's log names every COLLECTED test file; only a
        # FAILED line for the enforcer itself is a fire (first live-fire
        # read caught the inflated counts).
        principles = [Principle(1, "R", ["tests/unit/gates/test_a.py"])]
        logs = {"11": "collected tests/unit/gates/test_a.py\nFAILED tests/other/test_z.py::t"}
        assert fire_counts(principles, logs) == {"tests/unit/gates/test_a.py": []}

    def test_hook_class_enforcers_are_not_counted(self):
        principles = [Principle(1, "R", ["src/attune/hooks/scripts/guard.py"])]
        logs = {"11": "guard.py exploded"}
        assert fire_counts(principles, logs) == {}


class TestFailedRunLogs:
    def test_lists_then_fetches_each_log(self):
        calls = []

        def runner(cmd):
            calls.append(cmd)
            if cmd[1:3] == ["run", "list"]:
                return json.dumps([{"databaseId": 7}])
            return "log body 7"

        assert failed_run_logs("2026-07-01", 50, runner) == {"7": "log body 7"}
        assert calls[0][:3] == ["gh", "run", "list"]
        assert calls[1][:4] == ["gh", "run", "view", "7"]

    def test_empty_listing_yields_no_logs(self):
        assert failed_run_logs("2026-07-01", 50, lambda cmd: "") == {}


class TestFormatReport:
    def test_report_names_fires_aspirational_and_hook_rows(self):
        principles = [
            Principle(1, "Fired", ["tests/unit/gates/test_a.py"]),
            Principle(2, "Aspirational", []),
            Principle(3, "Hooked", ["src/attune/hooks/scripts/guard.py"]),
            Principle(4, "Quiet", ["tests/unit/gates/test_b.py"]),
        ]
        counts = {"tests/unit/gates/test_a.py": ["11", "12"], "tests/unit/gates/test_b.py": []}
        report = format_report(principles, counts, "2026-07-01")
        assert "| 1 | Fired | `tests/unit/gates/test_a.py` | 2 | 11, 12 |" in report
        assert "*(aspirational)*" in report
        assert "not observable (hook-class)" in report
        assert "P4 `tests/unit/gates/test_b.py`" in report  # never-fired list
