"""Unified output formatting for workflows.

Provides consistent Rich-based output components for workflow results:
- WorkflowReport: Main report container with sections
- FindingsTable: Render findings as Rich Table or plain text
- MetricsPanel: Color-coded score display
- ReportSection: Individual report sections

Supports graceful fallback to plain text when Rich is unavailable.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

# Rich imports with fallback
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None  # type: ignore[misc,assignment]
    Panel = None  # type: ignore[misc,assignment]
    Table = None  # type: ignore[misc,assignment]
    Text = None  # type: ignore[misc,assignment]

if TYPE_CHECKING:
    from rich.console import Console as ConsoleType


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class Finding:
    """Individual finding from a workflow."""

    severity: str  # "high", "medium", "low", "info"
    file: str
    line: int | None = None
    message: str = ""
    code: str | None = None

    @property
    def severity_icon(self) -> str:
        """Get icon for severity level."""
        icons = {
            "high": "[red]:x:[/red]" if RICH_AVAILABLE else "X",
            "medium": "[yellow]:warning:[/yellow]" if RICH_AVAILABLE else "!",
            "low": "[blue]:information:[/blue]" if RICH_AVAILABLE else "i",
            "info": "[dim]o[/dim]" if RICH_AVAILABLE else "o",
        }
        return icons.get(self.severity.lower(), "o")

    @property
    def location(self) -> str:
        """Get file:line location string."""
        if self.line:
            return f"{self.file}:{self.line}"
        return self.file


@dataclass
class ReportSection:
    """Individual section of a workflow report."""

    title: str
    content: Any  # str, list[Finding], dict, or Rich renderable
    collapsed: bool = False
    style: str = "default"  # "default", "success", "warning", "error"


@dataclass
class WorkflowReport:
    """Main workflow report container."""

    title: str
    summary: str = ""
    sections: list[ReportSection] = field(default_factory=list)
    score: int | None = None
    level: str = "info"  # "info", "success", "warning", "error"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_section(
        self,
        title: str,
        content: Any,
        collapsed: bool = False,
        style: str = "default",
    ) -> None:
        """Add a section to the report."""
        self.sections.append(
            ReportSection(title=title, content=content, collapsed=collapsed, style=style),
        )

    def render(self, console: ConsoleType | None = None, use_rich: bool = True) -> str:
        """Render the report.

        Args:
            console: Rich Console instance (optional)
            use_rich: Whether to use Rich formatting

        Returns:
            Rendered report as string (for plain text) or prints to console (for Rich)

        """
        if use_rich and RICH_AVAILABLE and console is not None:
            self._render_rich(console)
            return ""
        return self._render_plain()

    def _render_rich(self, console: ConsoleType) -> None:
        """Render report using Rich."""
        # Score panel (title shown via score panel)
        if self.score is not None:
            score_panel = MetricsPanel.render_score(self.score)
            console.print(score_panel)

        if self.summary:
            console.print(f"\n{self.summary}\n")

        # Sections
        for section in self.sections:
            self._render_section_rich(console, section)

    def _render_section_rich(self, console: ConsoleType, section: ReportSection) -> None:
        """Render a single section using Rich."""
        border_style = {
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "default": "blue",
        }.get(section.style, "blue")

        if isinstance(section.content, str):
            console.print(Panel(section.content, title=section.title, border_style=border_style))
        elif isinstance(section.content, list) and all(
            isinstance(f, Finding) for f in section.content
        ):
            table = FindingsTable(section.content).to_rich_table()
            console.print(Panel(table, title=section.title, border_style=border_style))
        elif isinstance(section.content, dict):
            # Render dict as key-value table
            table = Table(show_header=False, box=None)
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            for key, value in section.content.items():
                table.add_row(str(key), str(value))
            console.print(Panel(table, title=section.title, border_style=border_style))
        else:
            # Try to print directly (might be a Rich renderable)
            try:
                console.print(
                    Panel(section.content, title=section.title, border_style=border_style),
                )
            except Exception:
                # INTENTIONAL: Graceful fallback for unknown content types
                console.print(f"\n[bold]{section.title}[/bold]")
                console.print(str(section.content))

    def _render_plain(self) -> str:
        """Render report as plain text."""
        lines = []
        separator = "=" * 60

        # Header
        lines.append(separator)
        lines.append(self.title.upper())
        lines.append(separator)

        if self.score is not None:
            level = MetricsPanel.get_level(self.score)
            lines.append(f"Score: {self.score}/100 ({level.upper()})")
            lines.append("")

        if self.summary:
            lines.append(self.summary)
            lines.append("")

        # Sections
        for section in self.sections:
            lines.append("-" * 60)
            lines.append(section.title.upper())
            lines.append("-" * 60)

            if isinstance(section.content, str):
                lines.append(section.content)
            elif isinstance(section.content, list) and all(
                isinstance(f, Finding) for f in section.content
            ):
                lines.append(FindingsTable(section.content).to_plain())
            elif isinstance(section.content, dict):
                for key, value in section.content.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(str(section.content))

            lines.append("")

        lines.append(separator)
        return "\n".join(lines)


# =============================================================================
# FINDINGS TABLE
# =============================================================================


class FindingsTable:
    """Render findings as Rich Table or plain text."""

    def __init__(self, findings: list[Finding]) -> None:
        """Initialize with list of findings."""
        self.findings = findings

    def to_rich_table(self) -> Table:
        """Convert findings to Rich Table."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Severity", style="bold", width=8)
        table.add_column("Location", style="cyan")
        table.add_column("Message")

        for finding in self.findings:
            severity_style = {
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "dim",
            }.get(finding.severity.lower(), "white")

            table.add_row(
                Text(finding.severity.upper(), style=severity_style),
                finding.location,
                finding.message,
            )

        return table

    def to_plain(self) -> str:
        """Convert findings to plain text."""
        if not self.findings:
            return "  No findings."

        lines = []
        for finding in self.findings:
            lines.append(f"  [{finding.severity.upper()}] {finding.location}")
            if finding.message:
                lines.append(f"      {finding.message}")

        return "\n".join(lines)


# =============================================================================
# METRICS PANEL
# =============================================================================


class MetricsPanel:
    """Display score with color-coded indicator."""

    @staticmethod
    def get_level(score: int) -> str:
        """Get level name for score."""
        if score >= 85:
            return "excellent"
        if score >= 70:
            return "good"
        if score >= 50:
            return "needs work"
        return "critical"

    @staticmethod
    def get_style(score: int) -> str:
        """Get Rich style for score."""
        if score >= 85:
            return "green"
        if score >= 70:
            return "yellow"
        if score >= 50:
            return "orange1"
        return "red"

    @staticmethod
    def get_icon(score: int) -> str:
        """Get icon for score."""
        if score >= 85:
            return "[green]:heavy_check_mark:[/green]"
        if score >= 70:
            return "[yellow]:large_yellow_circle:[/yellow]"
        if score >= 50:
            return "[orange1]:warning:[/orange1]"
        return "[red]:x:[/red]"

    @staticmethod
    def get_plain_icon(score: int) -> str:
        """Get plain text icon for score."""
        if score >= 85:
            return "[OK]"
        if score >= 70:
            return "[--]"
        if score >= 50:
            return "[!!]"
        return "[XX]"

    @classmethod
    def render_score(cls, score: int, label: str = "Score") -> Panel:
        """Render score as Rich Panel.

        Args:
            score: Score value (0-100)
            label: Label for the score

        Returns:
            Rich Panel with formatted score

        """
        if not RICH_AVAILABLE or Panel is None:
            raise RuntimeError("Rich library not available. Install with: pip install rich")

        style = cls.get_style(score)
        icon = cls.get_icon(score)
        level = cls.get_level(score)

        content = f"{icon} [bold]{score}[/bold]/100 ({level.upper()})"
        return Panel(content, title=f"[bold]{label}[/bold]", border_style=style)

    @classmethod
    def render_plain(cls, score: int, label: str = "Score") -> str:
        """Render score as plain text.

        Args:
            score: Score value (0-100)
            label: Label for the score

        Returns:
            Plain text score display

        """
        icon = cls.get_plain_icon(score)
        level = cls.get_level(score)
        return f"{label}: {icon} {score}/100 ({level.upper()})"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def format_workflow_result(
    title: str,
    summary: str = "",
    findings: list[dict] | None = None,
    score: int | None = None,
    recommendations: str = "",
    metadata: dict[str, Any] | None = None,
    suggestions: list | None = None,
) -> WorkflowReport:
    """Create a standardized workflow report.

    Args:
        title: Report title
        summary: Brief summary text
        findings: List of finding dicts with severity, file, line, message
        score: Overall score (0-100)
        recommendations: Recommendations text
        metadata: Additional metadata
        suggestions: List of NextAction for project-aware guidance

    Returns:
        WorkflowReport instance

    """
    report = WorkflowReport(
        title=title,
        summary=summary,
        score=score,
        metadata=metadata or {},
    )

    if findings:
        finding_objs = [
            Finding(
                severity=f.get("severity", "info"),
                file=f.get("file", "unknown"),
                line=f.get("line"),
                message=f.get("message", ""),
                code=f.get("code"),
            )
            for f in findings
        ]
        report.add_section("Findings", finding_objs)

    if recommendations:
        report.add_section("Recommendations", recommendations)

    # Project-aware guidance (v3.5)
    if suggestions:
        from .suggestions import format_suggestions_markdown

        guidance_text = format_suggestions_markdown(suggestions)
        if guidance_text:
            report.add_section("What's Next", guidance_text, style="success")

    return report


def get_console() -> Console | None:
    """Get Rich Console if available."""
    if RICH_AVAILABLE and Console is not None:
        return Console()
    return None
