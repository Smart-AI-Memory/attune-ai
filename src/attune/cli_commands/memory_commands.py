"""CLI commands for quick-memory lessons.

Provides `attune remember`, `attune forget`, and `attune lessons`
commands for managing lessons learned from previous sessions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from argparse import Namespace

logger = logging.getLogger(__name__)


def cmd_remember(args: Namespace) -> int:
    """Add a lesson to the lessons file.

    Args:
        args: Parsed arguments with lesson_text and optional global flag.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.memory.lessons import LessonsManager

    try:
        manager = LessonsManager()
        global_ = getattr(args, "global", False)
        message = manager.add_lesson(args.lesson_text, global_=global_)
        print(message)
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except OSError as e:
        logger.error("Failed to save lesson: %s", e)
        print(f"Error saving lesson: {e}")
        return 1


def cmd_forget(args: Namespace) -> int:
    """Remove a lesson by line number or keyword.

    Args:
        args: Parsed arguments with identifier.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.memory.lessons import LessonsManager

    try:
        manager = LessonsManager()
        message = manager.remove_lesson(args.identifier)
        print(message)
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except OSError as e:
        logger.error("Failed to remove lesson: %s", e)
        print(f"Error removing lesson: {e}")
        return 1


def cmd_lessons(args: Namespace) -> int:
    """List current lessons with line numbers.

    Args:
        args: Parsed arguments with optional global flag.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.memory.lessons import LessonsManager

    try:
        manager = LessonsManager()
        global_only = getattr(args, "global", False)
        lessons = manager.get_lessons(global_only=global_only)

        if not lessons:
            scope = "global" if global_only else "project or global"
            print(f"No lessons found ({scope}).")
            print('Add one with: attune remember "your lesson here"')
            return 0

        print("Attune Lessons")
        print("=" * 50)
        for lesson in lessons:
            source_tag = f" [{lesson['source']}]" if not global_only else ""
            print(
                f"  {lesson['number']:3d}. [{lesson['date']}] {lesson['text']}{source_tag}",
            )

        print(f"\n{len(lessons)} lesson(s) total.")
        print("Remove with: attune forget <number> or attune forget <keyword>")
        return 0

    except OSError as e:
        logger.error("Failed to list lessons: %s", e)
        print(f"Error reading lessons: {e}")
        return 1


__all__ = ["cmd_forget", "cmd_lessons", "cmd_remember"]
