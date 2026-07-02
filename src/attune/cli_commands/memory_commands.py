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


def cmd_memory_capture(args: Namespace) -> int:
    """Save content to personal cross-session memory.

    Args:
        args: Parsed arguments with topic, content, kind, project_local.

    Returns:
        0 on success, 1 on failure.

    """
    from pathlib import Path

    from attune.memory.personal import PersonalMemory

    project_local = getattr(args, "project_local", False)
    project_root = Path.cwd() / ".attune" / "memory" if project_local else None
    try:
        pm = PersonalMemory(project_root=project_root)
        dest = pm.capture(
            args.topic,
            args.content,
            kind=getattr(args, "kind", "decision"),
            project_local=project_local,
        )
        print(f"Saved: {dest}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except OSError as e:
        logger.error("Failed to capture memory: %s", e)
        print(f"Error saving memory: {e}")
        return 1


def cmd_memory_recall(args: Namespace) -> int:
    """Search personal cross-session memory.

    Args:
        args: Parsed arguments with query, k, kind_filter, json.

    Returns:
        0 on success, 1 on failure.

    """
    import contextlib
    import io
    import json as json_mod
    import sys

    from attune.memory.personal import PersonalMemory

    try:
        pm = PersonalMemory(project_root=None)
        # The RAG layer logs to stdout (structlog's default PrintLogger),
        # which pollutes `--json` output and breaks machine consumers
        # (`attune memory recall ... --json | jq` fails on the log line).
        # Capture anything the query writes to stdout and forward it to
        # stderr, keeping stdout pure result output in both modes.
        log_noise = io.StringIO()
        with contextlib.redirect_stdout(log_noise):
            hits = pm.query(
                args.query,
                k=getattr(args, "k", 3),
                kind_filter=getattr(args, "kind_filter", None),
            )
        if log_noise.getvalue():
            print(log_noise.getvalue(), file=sys.stderr, end="")
        if getattr(args, "json", False):
            print(json_mod.dumps(hits, indent=2))
            return 0
        if not hits:
            print("No results found.")
            return 0
        for i, hit in enumerate(hits, 1):
            print(f"{i}. [{hit['score']:.3f}] {hit['path']}")
            if hit.get("summary"):
                print(f"   {hit['summary']}")
            if hit.get("excerpt"):
                print(f"   ...{hit['excerpt']}...")
        return 0
    except OSError as e:
        logger.error("Failed to query memory: %s", e)
        print(f"Error querying memory: {e}")
        return 1


def cmd_memory_topics(args: Namespace) -> int:
    """List all personal memory topics.

    Args:
        args: Parsed arguments (no additional args required).

    Returns:
        0 on success, 1 on failure.

    """
    from attune.memory.personal import PersonalMemory

    try:
        pm = PersonalMemory(project_root=None)
        topics = pm.list_topics()
        if not topics:
            print("No memory topics found.")
            print('Capture one with: attune memory capture <topic> "<content>"')
            return 0
        print(f"{len(topics)} topic(s):")
        for topic in topics:
            print(f"  {topic}")
        return 0
    except OSError as e:
        logger.error("Failed to list memory topics: %s", e)
        print(f"Error listing topics: {e}")
        return 1


def cmd_memory_forget_topic(args: Namespace) -> int:
    """Delete a topic (or specific kind) from personal memory.

    Args:
        args: Parsed arguments with topic and optional kind.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.memory.personal import PersonalMemory

    try:
        pm = PersonalMemory(project_root=None)
        kind = getattr(args, "kind", None) or None
        deleted = pm.forget_topic(args.topic, kind=kind)
        if deleted == 0:
            print(f"Topic not found: {args.topic}")
            return 1
        what = f"{args.topic}/{kind}.md" if kind else f"{args.topic}/"
        print(f"Deleted {deleted} file(s) from {what}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except OSError as e:
        logger.error("Failed to forget topic: %s", e)
        print(f"Error deleting topic: {e}")
        return 1


__all__ = [
    "cmd_forget",
    "cmd_lessons",
    "cmd_memory_capture",
    "cmd_memory_forget_topic",
    "cmd_memory_recall",
    "cmd_memory_topics",
    "cmd_remember",
]
