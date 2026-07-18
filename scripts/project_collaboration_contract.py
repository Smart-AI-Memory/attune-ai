#!/usr/bin/env python3
"""Project the shared collaboration contract into its consumer surfaces.

The master at ``content/collaboration/contract.md`` owns the common
Codex/ChatGPT-tools/Claude operating contract. This script writes only
between explicit markers in provider instruction files, leaving their
provider-specific content untouched, and emits the portable handoff
template. ``--check`` is the drift gate for CI and pre-commit use.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

START_MARKER = "<!-- attune:collaboration:start -->"
END_MARKER = "<!-- attune:collaboration:end -->"
MASTER_PATH = Path("content/collaboration/contract.md")
CONTRACT_HEADING = "Shared contract"
HANDOFF_HEADING = "Portable handoff template"
CONTRACT_TARGETS = (Path("AGENTS.md"), Path(".claude/CLAUDE.md"))
HANDOFF_TARGET = Path("templates/agent-handoff.md")


class ProjectionError(ValueError):
    """Raised when the master or a marked target is malformed."""


@dataclass
class ProjectionResult:
    """Paths changed, unchanged, or stale during one projection."""

    written: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    stale: list[Path] = field(default_factory=list)


def _validate_file_path(root: Path, relative_path: Path) -> Path:
    """Return a repository-contained path, resolving symlinks."""
    resolved_root = root.resolve()
    resolved_path = (resolved_root / relative_path).resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise ProjectionError(f"path escapes repository: {relative_path}") from None
    return resolved_path


def _parse_sections(text: str) -> dict[str, str]:
    """Return the two contract-level section bodies from a Markdown master.

    The handoff template intentionally has its own H2 headings, so only
    the two declared master headings delimit sections here. A repeated
    required heading raises: silent last-wins could project half an
    edit (spec D4).
    """
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and line[3:].strip() in {CONTRACT_HEADING, HANDOFF_HEADING}:
            heading = line[3:].strip()
            if heading in sections or heading == current:
                raise ProjectionError(f"master repeats required heading: {heading}")
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        elif current is not None:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def _master_sections(root: Path) -> dict[str, str]:
    """Read and validate the collaboration master under ``root``."""
    path = _validate_file_path(root, MASTER_PATH)
    if not path.is_file():
        raise ProjectionError(f"master missing: {MASTER_PATH}")
    sections = _parse_sections(path.read_text(encoding="utf-8"))
    missing = [
        heading for heading in (CONTRACT_HEADING, HANDOFF_HEADING) if not sections.get(heading)
    ]
    if missing:
        raise ProjectionError(f"master missing required section(s): {', '.join(missing)}")
    return sections


GENERATED_NOTICE = (
    "<!-- generated from content/collaboration/contract.md - edit the "
    "master, then run scripts/project_collaboration_contract.py -->"
)


def _render_marked_block(contract: str) -> str:
    """Return the provider-neutral contract inserted in instruction files."""
    return GENERATED_NOTICE + "\n\n## Cross-provider collaboration\n\n" + contract.strip() + "\n"


def _replace_marked_block(content: str, rendered: str, path: Path) -> str:
    """Replace exactly one marker-delimited block while preserving all else."""
    if content.count(START_MARKER) != 1 or content.count(END_MARKER) != 1:
        raise ProjectionError(f"{path}: expected exactly one collaboration marker pair")
    start = content.index(START_MARKER)
    end = content.index(END_MARKER)
    if end <= start:
        raise ProjectionError(f"{path}: collaboration markers are out of order")
    prefix = content[: start + len(START_MARKER)]
    suffix = content[end:]
    return prefix + "\n\n" + rendered.rstrip() + "\n\n" + suffix


def project(root: Path, *, check: bool = False) -> ProjectionResult:
    """Project the master under ``root`` and optionally only report drift."""
    sections = _master_sections(root)
    result = ProjectionResult()
    rendered_contract = _render_marked_block(sections[CONTRACT_HEADING])
    projections: list[tuple[Path, Path, str | None, str]] = []

    for relative_path in CONTRACT_TARGETS:
        path = _validate_file_path(root, relative_path)
        if not path.is_file():
            raise ProjectionError(f"target missing: {relative_path}")
        current = path.read_text(encoding="utf-8")
        expected = _replace_marked_block(current, rendered_contract, relative_path)
        projections.append((relative_path, path, current, expected))

    handoff_path = _validate_file_path(root, HANDOFF_TARGET)
    expected_handoff = sections[HANDOFF_HEADING].strip() + "\n"
    current_handoff = handoff_path.read_text(encoding="utf-8") if handoff_path.is_file() else None
    projections.append((HANDOFF_TARGET, handoff_path, current_handoff, expected_handoff))

    for relative_path, path, current, expected in projections:
        if current == expected:
            result.unchanged.append(relative_path)
        elif check:
            result.stale.append(relative_path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
            result.written.append(relative_path)

    return result


def main(argv: list[str] | None = None) -> int:
    """Run projection or report targets that have drifted from the master."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    try:
        result = project(root, check=args.check)
    except ProjectionError as error:
        print(f"error: {error}")
        return 1

    if result.stale:
        print("collaboration projection drift:")
        for path in result.stale:
            print(f"  {path}")
        return 1
    for path in result.written:
        print(f"wrote {path}")
    for path in result.unchanged:
        print(f"unchanged {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
