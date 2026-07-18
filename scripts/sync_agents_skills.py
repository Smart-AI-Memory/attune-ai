#!/usr/bin/env python3
"""Sync Claude Code skills to agentskills.io-compliant format.

Reads SKILL.md files from plugin/skills/*/SKILL.md AND
.claude/skills/*/SKILL.md, strips Claude Code-specific frontmatter
fields, validates naming rules, and writes to
.agents/skills/<name>/SKILL.md. On a name collision between the two
sources, plugin/skills/ wins and the .claude/skills/ copy is skipped
(reported as [SKIP]).

The tracked .agents/skills/ tree is the one skill mirror other
agents (e.g. Codex) read — keeping it complete stops Codex's init
from regenerating its own mangled untracked copies of
.claude/skills/ (see the 2026-07-18 lesson).

Usage:
    python scripts/sync_agents_skills.py          # Verify in sync
    python scripts/sync_agents_skills.py --check  # Verify in sync
    python scripts/sync_agents_skills.py --write  # Generate files
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# Fields allowed in agentskills.io skill frontmatter.
ALLOWED_FIELDS: set[str] = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}

# Fields specific to Claude Code that must be stripped.
CLAUDE_CODE_FIELDS: set[str] = {
    "argument-hint",
    "disable-model-invocation",
    "user-invocable",
}

# Regex for valid skill names: lowercase letters, digits, hyphens.
# 1-64 chars; no leading, trailing, or consecutive hyphens.
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter and body from a SKILL.md file.

    Handles simple key: value pairs and one level of nesting
    (for the metadata block). Does not use PyYAML -- stdlib only.

    Args:
        text: Full file contents.

    Returns:
        Tuple of (frontmatter dict, body string). The frontmatter
        dict maps field names to their raw YAML text (including
        nested lines for metadata). The body is everything after
        the closing ``---``.

    Raises:
        ValueError: If the file has no valid frontmatter delimiters.
    """
    lines = text.split("\n")

    if not lines or lines[0].strip() != "---":
        raise ValueError("File does not start with --- frontmatter delimiter")

    # Find closing ---
    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        raise ValueError("No closing --- frontmatter delimiter found")

    fm_lines = lines[1:closing_idx]
    body = "\n".join(lines[closing_idx + 1 :])

    # Parse frontmatter lines into fields.
    # Each top-level field is "key: value" (no leading whitespace).
    # Nested lines (indented) belong to the preceding top-level field.
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_key is not None:
            fields[current_key] = "\n".join(current_lines)

    for line in fm_lines:
        if line and not line[0].isspace():
            # Top-level key
            _flush()
            colon_idx = line.find(":")
            if colon_idx == -1:
                # Bare key with no value -- skip
                current_key = line.strip()
                current_lines = [line]
                continue
            current_key = line[:colon_idx].strip()
            current_lines = [line]
        else:
            # Continuation / nested line
            current_lines.append(line)

    _flush()

    return fields, body


def validate_name(name: str, dir_name: str) -> list[str]:
    """Validate a skill name against agentskills.io rules.

    Args:
        name: The ``name`` field from frontmatter.
        dir_name: The directory name the SKILL.md lives in.

    Returns:
        List of validation error strings (empty if valid).
    """
    errors: list[str] = []

    if not name:
        errors.append("name is empty")
        return errors

    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"name '{name}' exceeds {MAX_NAME_LENGTH} chars " f"({len(name)})")

    if not NAME_PATTERN.match(name):
        errors.append(
            f"name '{name}' must be lowercase letters, digits, "
            f"and hyphens only; no leading/trailing/consecutive "
            f"hyphens"
        )

    if name != dir_name:
        errors.append(f"name '{name}' does not match directory name " f"'{dir_name}'")

    return errors


def build_output(fields: dict[str, str], body: str) -> str:
    """Build the agentskills.io-compliant SKILL.md content.

    Strips Claude Code-specific fields and keeps only allowed
    fields, preserving their original order and raw YAML text.

    Args:
        fields: Parsed frontmatter fields (key -> raw YAML text).
        body: Everything after the closing frontmatter delimiter.

    Returns:
        Complete file content with filtered frontmatter and body.
    """
    # Preserve the original field order, keeping only allowed fields.
    kept_lines: list[str] = []
    for key, raw in fields.items():
        if key in CLAUDE_CODE_FIELDS:
            continue
        if key not in ALLOWED_FIELDS:
            continue
        kept_lines.append(raw)

    parts = ["---"]
    parts.extend(kept_lines)
    parts.append("---")

    frontmatter_text = "\n".join(parts)
    return frontmatter_text + body


def discover_skills(plugin_dir: Path) -> list[Path]:
    """Find all SKILL.md files under plugin/skills/.

    Args:
        plugin_dir: Path to the plugin/ directory.

    Returns:
        Sorted list of SKILL.md paths.
    """
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(skills_dir.glob("*/SKILL.md"))


def sync_one(
    skill_path: Path,
    output_root: Path,
    *,
    check: bool = False,
) -> tuple[bool, str]:
    """Sync a single SKILL.md to the .agents/ output directory.

    Args:
        skill_path: Path to the source plugin SKILL.md.
        output_root: Path to the .agents/skills/ directory.
        check: If True, compare instead of writing.

    Returns:
        Tuple of (success, message).
    """
    dir_name = skill_path.parent.name
    text = skill_path.read_text(encoding="utf-8")

    try:
        fields, body = parse_frontmatter(text)
    except ValueError as e:
        return False, f"{dir_name}: frontmatter parse error: {e}"

    # Validate name
    name = ""
    if "name" in fields:
        # Extract the value from the raw line "name: value"
        raw_line = fields["name"]
        colon_idx = raw_line.find(":")
        if colon_idx != -1:
            name = raw_line[colon_idx + 1 :].strip().strip('"').strip("'")

    errors = validate_name(name, dir_name)
    if errors:
        return False, f"{dir_name}: " + "; ".join(errors)

    output = build_output(fields, body)
    output_dir = output_root / name
    output_file = output_dir / "SKILL.md"

    if check:
        if not output_file.exists():
            return False, f"{name}: missing (not yet generated)"
        existing = output_file.read_text(encoding="utf-8")
        if existing == output:
            return True, f"{name}: in sync"
        return False, f"{name}: out of sync"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file.write_text(output, encoding="utf-8")
    return True, f"{name}: generated"


def main(argv: list[str] | None = None) -> int:
    """Entry point for the sync script.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify mirrors without writing (default)",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="regenerate tracked mirrors",
    )
    args = parser.parse_args(argv)
    check = not args.write

    # Determine repo root (script lives in scripts/)
    repo_root = Path(__file__).resolve().parent.parent
    plugin_dir = repo_root / "plugin"
    output_root = repo_root / ".agents" / "skills"

    plugin_paths = discover_skills(plugin_dir)
    if not plugin_paths:
        print("No SKILL.md files found in plugin/skills/")
        return 1

    # Second source: repo-level user skills. Plugin skills shadow
    # same-named .claude skills (the plugin copy is the product
    # surface; the .claude copy is the repo-local variant).
    claude_paths = discover_skills(repo_root / ".claude")
    plugin_names = {p.parent.name for p in plugin_paths}

    mode = "Checking" if check else "Generating"
    total = len(plugin_paths) + len(claude_paths)
    print(f"{mode} agentskills.io skills from {total} sources\n")

    successes = 0
    failures = 0

    for skill_path in plugin_paths:
        ok, msg = sync_one(skill_path, output_root, check=check)
        status = "  OK" if ok else "FAIL"
        print(f"  [{status}] {msg}")
        if ok:
            successes += 1
        else:
            failures += 1

    for skill_path in claude_paths:
        name = skill_path.parent.name
        if name in plugin_names:
            print(f"  [SKIP] {name}: shadowed by plugin/skills/")
            continue
        ok, msg = sync_one(skill_path, output_root, check=check)
        status = "  OK" if ok else "FAIL"
        print(f"  [{status}] {msg}")
        if ok:
            successes += 1
        else:
            failures += 1

    print(f"\n{'Checked' if check else 'Generated'}: " f"{successes} ok, {failures} failed")

    if check and failures > 0:
        print("\nRun 'python scripts/sync_agents_skills.py --write' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
