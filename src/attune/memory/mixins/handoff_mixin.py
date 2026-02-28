"""Session handoff and export mixin for UnifiedMemory.

Provides compact state generation and Claude Code integration.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from ..file_session import FileSessionMemory

logger = structlog.get_logger(__name__)


class HandoffAndExportMixin:
    """Mixin providing session handoff and export capabilities for UnifiedMemory."""

    # Type hints for attributes that will be provided by UnifiedMemory
    _file_session: "FileSessionMemory | None"
    config: Any  # MemoryConfig

    # Needs access to capabilities from CapabilitiesMixin
    def get_capabilities(self) -> dict[str, bool]:
        """Get capabilities - provided by CapabilitiesMixin."""

    # =========================================================================
    # COMPACT STATE GENERATION
    # =========================================================================

    def generate_compact_state(self) -> str:
        """Generate SBAR-format compact state from current session.

        Creates a human-readable summary of the current session state,
        suitable for Claude Code's .claude/compact-state.md file.

        Returns:
            Markdown-formatted compact state string

        """
        lines = [
            "# Compact State - Session Handoff",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]

        # Add session info
        if self._file_session:
            session = self._file_session._state
            lines.extend(
                [
                    f"**Session ID:** {session.session_id}",
                    f"**User ID:** {session.user_id}",
                    "",
                ],
            )

        lines.extend(
            [
                "## SBAR Handoff",
                "",
                "### Situation",
            ],
        )

        # Get context from file session
        context = {}
        if self._file_session:
            context = self._file_session.get_all_context()

        situation = context.get("situation", "Session in progress.")
        background = context.get("background", "No background information recorded.")
        assessment = context.get("assessment", "No assessment recorded.")
        recommendation = context.get("recommendation", "Continue with current task.")

        lines.extend(
            [
                situation,
                "",
                "### Background",
                background,
                "",
                "### Assessment",
                assessment,
                "",
                "### Recommendation",
                recommendation,
                "",
            ],
        )

        # Add working memory summary
        if self._file_session:
            working_keys = list(self._file_session._state.working_memory.keys())
            if working_keys:
                lines.extend(
                    [
                        "## Working Memory",
                        "",
                        f"**Active keys:** {len(working_keys)}",
                        "",
                    ],
                )
                for key in working_keys[:10]:  # Show max 10
                    lines.append(f"- `{key}`")
                if len(working_keys) > 10:
                    lines.append(f"- ... and {len(working_keys) - 10} more")
                lines.append("")

        # Add staged patterns summary
        if self._file_session:
            staged = list(self._file_session._state.staged_patterns.values())
            if staged:
                lines.extend(
                    [
                        "## Staged Patterns",
                        "",
                        f"**Pending validation:** {len(staged)}",
                        "",
                    ],
                )
                for pattern in staged[:5]:  # Show max 5
                    lines.append(
                        f"- {pattern.name} ({pattern.pattern_type}, conf: {pattern.confidence:.2f})",
                    )
                if len(staged) > 5:
                    lines.append(f"- ... and {len(staged) - 5} more")
                lines.append("")

        # Add capabilities
        caps = self.get_capabilities()
        lines.extend(
            [
                "## Capabilities",
                "",
                f"- File session: {'Yes' if caps['file_session'] else 'No'}",
                f"- Redis: {'Yes' if caps['redis'] else 'No'}",
                f"- Long-term memory: {'Yes' if caps['long_term'] else 'No'}",
                f"- Real-time sync: {'Yes' if caps['realtime'] else 'No'}",
                "",
            ],
        )

        return "\n".join(lines)

    def export_to_claude_md(self, path: str | None = None) -> Path:
        """Export current session state to Claude Code's compact-state.md.

        Args:
            path: Path to write to (defaults to config.compact_state_path)

        Returns:
            Path where state was written

        """
        from attune.security.path_validation import _validate_file_path

        path = path or self.config.compact_state_path
        validated_path = _validate_file_path(path)

        # Ensure parent directory exists
        validated_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and write compact state
        content = self.generate_compact_state()
        validated_path.write_text(content, encoding="utf-8")

        logger.info("compact_state_exported", path=str(validated_path))
        return validated_path

    def set_handoff(
        self,
        situation: str,
        background: str,
        assessment: str,
        recommendation: str,
        **extra_context,
    ) -> None:
        """Set SBAR handoff context for session continuity.

        This data is used by generate_compact_state() and export_to_claude_md().

        Args:
            situation: Current situation summary
            background: Relevant background information
            assessment: Assessment of progress/state
            recommendation: Recommended next steps
            **extra_context: Additional context key-value pairs

        """
        if not self._file_session:
            logger.warning("file_session_not_available")
            return

        self._file_session.set_context("situation", situation)
        self._file_session.set_context("background", background)
        self._file_session.set_context("assessment", assessment)
        self._file_session.set_context("recommendation", recommendation)

        for key, value in extra_context.items():
            self._file_session.set_context(key, value)

        # Auto-export if configured
        if self.config.auto_generate_compact_state:
            self.export_to_claude_md()
