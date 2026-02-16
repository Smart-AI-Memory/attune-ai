"""Session Start Hook

Loads previous context and patterns on new session start.
Ported from everything-claude-code/scripts/hooks/session-start.js

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_sessions_dir() -> Path:
    """Get the sessions directory path."""
    return Path.home() / ".attune" / "sessions"


def get_patterns_dir() -> Path:
    """Get the patterns directory path."""
    return Path.home() / ".attune" / "patterns"


def get_learned_skills_dir() -> Path:
    """Get the learned skills directory path."""
    return Path.home() / ".attune" / "skills" / "learned"


def find_recent_files(
    directory: Path,
    pattern: str = "*.json",
    max_age_days: int = 7,
) -> list[Path]:
    """Find files matching pattern modified within max_age_days.

    Args:
        directory: Directory to search
        pattern: Glob pattern for files
        max_age_days: Maximum file age in days

    Returns:
        List of matching file paths, sorted by modification time (newest first)

    """
    if not directory.exists():
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    matching = []

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime >= cutoff:
                matching.append((file_path, mtime))

    # Sort by modification time, newest first
    matching.sort(key=lambda x: x[1], reverse=True)
    return [path for path, _ in matching]


def load_session_state(session_file: Path) -> dict[str, Any] | None:
    """Load session state from a file.

    Args:
        session_file: Path to session state file

    Returns:
        Session state dict or None if failed

    """
    try:
        with open(session_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load session state from %s: %s", session_file, e)
        return None


def main(**context: Any) -> dict[str, Any]:
    """Session start hook main function.

    Loads:
    - Previous session state (trust level, patterns, preferences)
    - Learned skills from previous sessions
    - Project-specific patterns

    Args:
        **context: Hook context (session_id, project_path, etc.)

    Returns:
        Session initialization data

    """
    sessions_dir = get_sessions_dir()
    patterns_dir = get_patterns_dir()
    learned_dir = get_learned_skills_dir()

    # Ensure directories exist
    sessions_dir.mkdir(parents=True, exist_ok=True)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    learned_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "initialized": True,
        "timestamp": datetime.now().isoformat(),
        "loaded_state": None,
        "learned_skills_count": 0,
        "patterns_count": 0,
        "messages": [],
    }

    # Find and load recent session state
    recent_sessions = find_recent_files(sessions_dir, "*.json", max_age_days=7)

    if recent_sessions:
        latest = recent_sessions[0]
        state = load_session_state(latest)

        if state:
            result["loaded_state"] = {
                "file": str(latest),
                "trust_level": state.get("trust_level"),
                "interaction_count": state.get("interaction_count", 0),
                "patterns_detected": len(state.get("detected_patterns", [])),
            }
            result["messages"].append(f"[SessionStart] Restored state from {latest.name}")
            logger.info("Loaded session state from %s", latest)

    # Count learned skills
    learned_skills = list(learned_dir.glob("*.md"))
    result["learned_skills_count"] = len(learned_skills)

    if learned_skills:
        result["messages"].append(
            f"[SessionStart] {len(learned_skills)} learned skill(s) available"
        )

    # Count and load patterns with quality gates
    pattern_files = find_recent_files(patterns_dir, "*.json", max_age_days=90)
    result["patterns_count"] = len(pattern_files)

    if pattern_files:
        result["messages"].append(f"[SessionStart] {len(pattern_files)} pattern file(s) found")

        # Inject high-confidence pattern content (quality gates)
        injected_patterns = []
        for pf in pattern_files[:5]:  # Cap at 5 most recent
            try:
                with open(pf) as f:
                    pattern_data = json.load(f)
                confidence = pattern_data.get("confidence", 0.0)
                if confidence < 0.7:
                    continue  # Skip low-confidence patterns
                injected_patterns.append(
                    {
                        "source": pf.stem,
                        "patterns": pattern_data.get("patterns", []),
                        "confidence": confidence,
                    }
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Skipping pattern file %s: %s", pf, e)

        if injected_patterns:
            result["injected_patterns"] = injected_patterns
            result["messages"].append(
                f"[Learning] Injected {len(injected_patterns)} high-confidence pattern set(s)"
            )

    # Load learned skill summaries
    if learned_skills:
        skill_summaries = []
        for sf in learned_skills[:10]:  # Cap at 10
            try:
                content = sf.read_text()
                first_line = content.strip().split("\n")[0].lstrip("# ")
                skill_summaries.append({"name": sf.stem, "summary": first_line})
            except OSError:
                pass
        if skill_summaries:
            result["learned_skills"] = skill_summaries

    # Cleanup expired pattern files (older than 90 days)
    _cleanup_expired_patterns(patterns_dir, max_age_days=90)

    # Log summary
    for msg in result["messages"]:
        logger.info(msg)

    return result


def _cleanup_expired_patterns(patterns_dir: Path, max_age_days: int = 90) -> int:
    """Remove pattern files older than max_age_days.

    Args:
        patterns_dir: Directory containing pattern files.
        max_age_days: Maximum age before deletion.

    Returns:
        Number of files removed.

    """
    if not patterns_dir.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0

    for pf in patterns_dir.glob("*.json"):
        try:
            mtime = datetime.fromtimestamp(pf.stat().st_mtime)
            if mtime < cutoff:
                pf.unlink()
                removed += 1
                logger.debug("Removed expired pattern file: %s", pf)
        except OSError as e:
            logger.debug("Could not remove %s: %s", pf, e)

    return removed


def _read_stdin_context() -> dict[str, Any]:
    """Read hook context from stdin (Claude Code protocol).

    Claude Code passes JSON on stdin with session_id, cwd, transcript_path, etc.
    Handles empty stdin, malformed JSON, and missing fields gracefully.

    Returns:
        Parsed context dict, or empty dict if stdin is empty/invalid.

    """
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug("Could not parse stdin JSON: %s", e)
    return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    context = _read_stdin_context()
    result = main(**context)
    print(json.dumps(result, indent=2))
