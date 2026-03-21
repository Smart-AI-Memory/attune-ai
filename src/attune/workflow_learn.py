"""Pattern Learning Workflow for Attune AI.

Watch for bug fixes and extract patterns from git history.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path


def _wc():
    """Late-resolve the workflow_commands facade for patchable helper access."""
    return sys.modules["attune.workflow_commands"]


def learn_workflow(
    patterns_dir: str = "./patterns",
    analyze_commits: int | None = None,
    watch: bool = False,
    verbose: bool = False,
) -> int:
    """Watch for bug fixes and extract patterns.

    Modes:
    - analyze: Analyze recent commits for bug fix patterns
    - watch: Watch for new commits and learn in real-time

    Returns exit code (0 = success).
    """
    wc = _wc()

    print("\n" + "=" * 60)
    print("  PATTERN LEARNING")
    print("=" * 60 + "\n")

    patterns_path = Path(patterns_dir)
    patterns_path.mkdir(parents=True, exist_ok=True)

    if watch:
        print("Watch mode not yet implemented.")
        print("Use 'empathy learn --analyze N' to analyze recent commits.\n")
        return 1

    # Default to analyzing last 10 commits
    commit_count = analyze_commits or 10

    print(f"Analyzing last {commit_count} commits for bug fix patterns...\n")

    # Get recent commits
    success, output = wc._run_command(
        ["git", "log", f"-{commit_count}", "--oneline", "--format=%H|%s|%an|%ai"],
    )

    if not success:
        print("Failed to read git log. Are you in a git repository?")
        return 1

    commits = output.strip().split("\n")
    bug_fix_keywords = [
        "fix",
        "bug",
        "issue",
        "error",
        "crash",
        "broken",
        "repair",
        "patch",
        "resolve",
    ]

    learned = []

    for commit_line in commits:
        if not commit_line.strip():
            continue

        parts = commit_line.split("|")
        if len(parts) < 2:
            continue

        commit_hash = parts[0][:8]
        message = parts[1].lower()
        author = parts[2] if len(parts) > 2 else "unknown"
        date = parts[3][:10] if len(parts) > 3 else ""

        # Check if this looks like a bug fix
        is_bug_fix = any(kw in message for kw in bug_fix_keywords)

        if is_bug_fix:
            # Get the diff for this commit
            success, diff_output = wc._run_command(
                ["git", "show", commit_hash, "--stat", "--oneline"],
            )

            files_changed = []
            if success:
                for line in diff_output.split("\n"):
                    if "|" in line and ("+" in line or "-" in line):
                        file_name = line.split("|")[0].strip()
                        files_changed.append(file_name)

            # Classify bug type from message
            bug_type = "unknown"
            if any(kw in message for kw in ["null", "none", "undefined", "empty"]):
                bug_type = "null_reference"
            elif any(kw in message for kw in ["async", "await", "promise", "timeout"]):
                bug_type = "async_timing"
            elif any(kw in message for kw in ["type", "cast", "convert"]):
                bug_type = "type_mismatch"
            elif any(kw in message for kw in ["import", "module", "package"]):
                bug_type = "import_error"

            pattern = {
                "pattern_id": f"bug_{date.replace('-', '')}_{commit_hash}",
                "bug_type": bug_type,
                "status": "resolved",
                "root_cause": parts[1],  # Original message
                "fix": f"See commit {commit_hash}",
                "resolved_by": f"@{author.split()[0].lower()}",
                "resolved_at": date,
                "files_affected": files_changed[:3],
                "source": "git_history",
            }

            learned.append(pattern)

            if verbose:
                print(f"  Found: {bug_type} in {commit_hash}")
                print(f"         {parts[1][:60]}")

    # Load existing patterns and merge
    debugging_file = patterns_path / "debugging.json"
    existing: dict[str, Any] = {"patterns": []}

    try:
        validated_file = _validate_file_path(str(debugging_file))
    except ValueError as e:
        print(f"  Warning: path validation failed: {e}")
        validated_file = None

    if validated_file is not None:
        try:
            with validated_file.open() as f:
                existing = json.load(f)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            pass

    # Add new patterns (avoid duplicates)
    existing_ids = {p.get("pattern_id") for p in existing.get("patterns", [])}
    new_patterns = [p for p in learned if p["pattern_id"] not in existing_ids]

    if new_patterns and validated_file is not None:
        existing["patterns"].extend(new_patterns)
        existing["last_updated"] = datetime.now().isoformat()

        with validated_file.open("w") as f:
            json.dump(existing, f, indent=2)

    # Summary
    print("-" * 40)
    print(f"\nAnalyzed: {len(commits)} commits")
    print(f"Bug fixes found: {len(learned)}")
    print(f"New patterns learned: {len(new_patterns)}")

    if learned:
        print("\nBug types discovered:")
        types: dict[str, int] = {}
        for p in learned:
            t = p["bug_type"]
            types[t] = types.get(t, 0) + 1
        for bug_type, count in sorted(types.items(), key=lambda x: -x[1]):
            print(f"  {bug_type}: {count}")

    print("\n" + "=" * 60)
    print("  Run 'empathy sync-claude' to use these patterns with Claude Code")
    print("=" * 60 + "\n")

    # Update stats
    stats = wc._load_stats()
    stats["commands"]["learn"] = stats["commands"].get("learn", 0) + 1
    stats["patterns_learned"] = stats.get("patterns_learned", 0) + len(new_patterns)
    wc._save_stats(stats)

    return 0


def cmd_learn(args: object) -> int:
    """Learn command handler."""
    return _wc().learn_workflow(
        patterns_dir=getattr(args, "patterns_dir", "./patterns"),
        analyze_commits=getattr(args, "analyze", None),
        watch=getattr(args, "watch", False),
        verbose=getattr(args, "verbose", False),
    )
