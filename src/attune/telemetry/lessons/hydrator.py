"""Memory Hydrator for Attune AI.

Appends synthesized lessons to a repository lessons file
(``.claude/lessons.md`` by default).

DESIGN GATE (rescue branch): auto-appending machine-generated lessons
to the curated, human-ratified lessons corpus is NOT approved — this
class must route through a review inbox (or equivalent human gate)
before it is wired to any listener. The Redis hydration the original
docstring claimed was never implemented; the tracked corpus is
re-indexed by the existing hydration pipeline, so writing Markdown is
the correct integration point.
"""

import os


class MemoryHydrator:
    """Appends lesson markdown to a repository lessons file."""

    def __init__(self, lessons_path: str | None = None) -> None:
        """Initialize MemoryHydrator.

        Args:
            lessons_path: Optional path to lessons markdown file.
        """
        self.lessons_path = lessons_path or ".claude/lessons.md"

    def persist_lesson(self, lesson_markdown: str, is_ephemeral: bool = False) -> bool:
        """Appends lesson to file unless marked as ephemeral.

        Args:
            lesson_markdown: Formatted lesson markdown string.
            is_ephemeral: True if generated inside a ghost worktree
                trajectory (speculative runs must not pollute memory).

        Returns:
            True if persisted to file, False if skipped (ephemeral or
            missing lessons file).
        """
        if is_ephemeral:
            return False

        if os.path.exists(self.lessons_path):
            with open(self.lessons_path, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"\n{lesson_markdown}\n")
            return True

        return False
