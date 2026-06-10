"""Terminal rendering of WorkflowReport results (workflow-result-formatting T4).

Covers ``_collapse_details_for_terminal`` and the
``_print_workflow_result`` markdown/plain split: report-carrying
results render styled markdown on a TTY, summary mode swaps
``<details>`` blocks for a --verbose hint, and legacy results keep the
plain text path untouched.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import patch

from attune.cli_commands.workflow_commands import (
    _collapse_details_for_terminal,
    _print_workflow_result,
)
from attune.workflows.data_classes import WorkflowResult
from attune.workflows.output import (
    ProseSection,
    TableSection,
    WorkflowReport,
)

_DETAILS_BLOCK = "<details><summary>Hotspots</summary>\n\n| file |\n| --- |\n| a.py |\n\n</details>"


def _report_result(*, detail_section: bool = True) -> WorkflowResult:
    """A WorkflowResult whose final_output is a serialized report."""
    sections = [ProseSection(title="Overview", tier="essential", text="Solid.")]
    if detail_section:
        sections.append(
            TableSection(
                title="Hotspots",
                tier="detail",
                columns=["file"],
                rows=[{"file": "a.py"}],
            )
        )
    report = WorkflowReport(title="Code review", summary="ok", sections=sections)
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=True,
        stages=[],
        final_output=report.to_dict(),
        cost_report=None,
        started_at=now,
        completed_at=now,
        total_duration_ms=1000,
    )


def _legacy_result() -> WorkflowResult:
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=True,
        stages=[],
        final_output={"formatted_report": "plain legacy report"},
        cost_report=None,
        started_at=now,
        completed_at=now,
        total_duration_ms=1000,
    )


class TestCollapseDetailsForTerminal:
    """The <details> -> verbose-hint conversion."""

    def test_block_becomes_hint_line(self):
        """A details block collapses to the run-with-verbose pointer."""
        out = _collapse_details_for_terminal(f"before\n\n{_DETAILS_BLOCK}\n\nafter")
        assert "<details>" not in out
        assert '(section "Hotspots" collapsed — run with --verbose to expand)' in out

    def test_collapsed_body_is_hidden(self):
        """The detail body must not leak into the collapsed view."""
        out = _collapse_details_for_terminal(_DETAILS_BLOCK)
        assert "a.py" not in out

    def test_text_without_details_passes_through(self):
        """No-op on text with no details blocks."""
        text = "# Title\n\nplain body"
        assert _collapse_details_for_terminal(text) == text

    def test_multiple_blocks_all_collapse(self):
        """Every details block converts, not just the first."""
        second = _DETAILS_BLOCK.replace("Hotspots", "Appendix")
        out = _collapse_details_for_terminal(f"{_DETAILS_BLOCK}\n\n{second}")
        assert "<details>" not in out
        assert '"Hotspots" collapsed' in out
        assert '"Appendix" collapsed' in out


class TestPrintWorkflowResultTerminal:
    """_print_workflow_result rendering split."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_non_tty_prints_plain_markdown(self, _mock, capsys, monkeypatch, tmp_path):
        """Piped output: plain markdown text, details collapsed to hint."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _print_workflow_result(_report_result(), workflow_name="code-review")
        out = capsys.readouterr().out
        assert "\x1b[" not in out  # no ANSI styling off-TTY
        assert "# Code review" in out
        assert "run with --verbose to expand" in out
        assert "a.py" not in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_verbose_inlines_detail_sections(self, _mock, capsys, monkeypatch, tmp_path):
        """verbose=True renders the full report — detail body visible."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        _print_workflow_result(_report_result(), workflow_name="code-review", verbose=True)
        out = capsys.readouterr().out
        assert "a.py" in out
        assert "<details>" not in out
        assert "run with --verbose to expand" not in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_tty_renders_styled_markdown(self, _mock, capsys, monkeypatch, tmp_path):
        """On a TTY, the markdown heading renders styled (no raw '# ')."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
        _print_workflow_result(_report_result(), workflow_name="code-review")
        out = capsys.readouterr().out
        assert "Code review" in out
        assert "# Code review" not in out  # heading was markdown-rendered

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_legacy_result_keeps_plain_path_on_tty(self, _mock, capsys, monkeypatch):
        """Non-report results never go through the markdown renderer."""
        monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
        _print_workflow_result(_legacy_result(), workflow_name="code-review")
        out = capsys.readouterr().out
        assert "plain legacy report" in out
        assert "\x1b[" not in out

    def test_verbose_threads_full_disclosure(self, monkeypatch, tmp_path):
        """verbose=True asks the voice layer for disclosure='full'."""
        monkeypatch.chdir(tmp_path)
        captured: dict = {}

        def fake_format_output(name, result, **kwargs):
            captured.update(kwargs)
            return "out"

        with patch("attune.voice.format_output", side_effect=fake_format_output):
            _print_workflow_result(_legacy_result(), workflow_name="code-review", verbose=True)
        assert captured.get("disclosure") == "full"

    def test_default_threads_summary_disclosure(self, monkeypatch, tmp_path):
        """Default asks the voice layer for disclosure='summary'."""
        monkeypatch.chdir(tmp_path)
        captured: dict = {}

        def fake_format_output(name, result, **kwargs):
            captured.update(kwargs)
            return "out"

        with patch("attune.voice.format_output", side_effect=fake_format_output):
            _print_workflow_result(_legacy_result(), workflow_name="code-review")
        assert captured.get("disclosure") == "summary"
