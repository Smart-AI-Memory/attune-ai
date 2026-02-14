"""Sync commands for pattern synchronization.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json as json_mod
from pathlib import Path

from attune.config import _validate_file_path
from attune.logging_config import get_logger

logger = get_logger(__name__)


def cmd_sync_claude(args):
    """Sync patterns to Claude Code rules directory.

    Converts learned patterns into Claude Code markdown rules.

    Args:
        args: Namespace object from argparse with attributes:
            - patterns_dir (str): Source patterns directory.
            - output_dir (str): Target Claude Code rules directory.

    Returns:
        int: 0 on success, 1 on failure.

    Raises:
        ValueError: If output path is invalid or unsafe.
    """
    patterns_dir = Path(args.patterns_dir)
    # Validate output directory path
    validated_output_dir = _validate_file_path(args.output_dir)
    output_dir = validated_output_dir

    print("=" * 60)
    print("  SYNC PATTERNS TO CLAUDE CODE")
    print("=" * 60 + "\n")

    if not patterns_dir.exists():
        print(f"✗ Patterns directory not found: {patterns_dir}")
        print("  Run 'attune learn --analyze 20' first to learn patterns")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    synced_count = 0
    pattern_files = ["debugging.json", "security.json", "tech_debt.json", "inspection.json"]

    for pattern_file in pattern_files:
        source_path = patterns_dir / pattern_file
        if not source_path.exists():
            continue

        try:
            with open(source_path) as f:
                data = json_mod.load(f)

            patterns = data.get("patterns", data.get("items", []))
            if not patterns:
                continue

            # Generate markdown rule file
            category = pattern_file.replace(".json", "")
            rule_content = _generate_claude_rule(category, patterns)

            # Write rule file
            rule_file = output_dir / f"{category}.md"
            # Validate rule file path before writing
            validated_rule_file = _validate_file_path(str(rule_file), allowed_dir=str(output_dir))
            with open(validated_rule_file, "w") as f:
                f.write(rule_content)

            print(f"  ✓ {category}: {len(patterns)} patterns → {rule_file}")
            synced_count += len(patterns)

        except (json_mod.JSONDecodeError, OSError) as e:
            print(f"  ✗ Failed to process {pattern_file}: {e}")

    print(f"\n{'─' * 60}")
    print(f"  Total: {synced_count} patterns synced to {output_dir}")
    print("=" * 60 + "\n")

    if synced_count == 0:
        print("No patterns to sync. Run 'attune learn' first.")
        return 1

    return 0


def _generate_claude_rule(category: str, patterns: list) -> str:
    """Generate a Claude Code rule file from patterns."""
    lines = [
        f"# {category.replace('_', ' ').title()} Patterns",
        "",
        "Auto-generated from Attune AI learned patterns.",
        f"Total patterns: {len(patterns)}",
        "",
        "---",
        "",
    ]

    if category == "debugging":
        lines.extend(
            [
                "## Bug Fix Patterns",
                "",
                "When debugging similar issues, consider these historical fixes:",
                "",
            ],
        )
        for p in patterns[:20]:  # Limit to 20 most recent
            bug_type = p.get("bug_type", "unknown")
            root_cause = p.get("root_cause", "Unknown")
            fix = p.get("fix", "See commit history")
            files = p.get("files_affected", [])

            lines.append(f"### {bug_type}")
            lines.append(f"- **Root cause**: {root_cause}")
            lines.append(f"- **Fix**: {fix}")
            if files:
                lines.append(f"- **Files**: {', '.join(files[:3])}")
            lines.append("")

    elif category == "security":
        lines.extend(
            [
                "## Security Decisions",
                "",
                "Previously reviewed security items:",
                "",
            ],
        )
        for p in patterns[:20]:
            decision = p.get("decision", "unknown")
            reason = p.get("reason", "")
            lines.append(f"- **{p.get('type', 'unknown')}**: {decision}")
            if reason:
                lines.append(f"  - Reason: {reason}")
            lines.append("")

    elif category == "tech_debt":
        lines.extend(
            [
                "## Tech Debt Tracking",
                "",
                "Known technical debt items:",
                "",
            ],
        )
        for p in patterns[:20]:
            lines.append(f"- {p.get('description', str(p))}")

    else:
        lines.extend(
            [
                f"## {category.title()} Items",
                "",
            ],
        )
        for p in patterns[:20]:
            lines.append(f"- {p.get('description', str(p)[:100])}")

    return "\n".join(lines)
