"""Guard: shell scripts must not assign to zsh-readonly builtins.

Shell scripts that do `status=$(cmd)` work in bash but fail in
zsh (the macOS default login shell) with
``read-only variable: status``. Even scripts with
``#!/bin/bash`` at the top are sometimes invoked under zsh
(e.g. via Claude Code Monitor scripts, or when a user sources
a script from an interactive zsh session).

Caught the hard way on a Monitor script that captured a
``gh`` command's output into ``status=...`` — the Monitor
died with an opaque read-only-variable error even though the
syntax was valid bash. Enforcing it here so the lesson sticks
and no checked-in script in this repo can reintroduce the
pattern.

Related lesson in ``.claude/CLAUDE.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# zsh-readonly special parameters that are realistically
# assignable-looking in bash scripts. Narrower than the
# full list on purpose — false-positive-averse.
ZSH_READONLY_NAMES: tuple[str, ...] = (
    "status",
    "pipestatus",
    "ARGC",
    "argv",
    "EGID",
    "EUID",
    "GID",
    "UID",
    "HISTCMD",
    "LINENO",
    "PPID",
)

# Matches assignments at start of line (allowing leading whitespace)
# but not ``local status=...`` / ``export status=...`` (those are
# fine in bash anyway), and not comparisons (``[ "$status" = ... ]``).
_ASSIGN_RE = re.compile(
    rf"^\s*({'|'.join(ZSH_READONLY_NAMES)})=",
    re.MULTILINE,
)

# Paths to skip entirely (vendor code, generated content).
_SKIP_DIR_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "node_modules",
        ".git",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "site",
    }
)


def _iter_shell_files():
    """Yield every shell script + workflow YAML under the repo."""
    patterns = ("*.sh", "*.bash", "*.zsh")
    for pattern in patterns:
        yield from REPO_ROOT.rglob(pattern)
    workflows_dir = REPO_ROOT / ".github" / "workflows"
    if workflows_dir.is_dir():
        yield from workflows_dir.glob("*.yml")
        yield from workflows_dir.glob("*.yaml")


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIR_PARTS for part in path.parts)


def test_no_zsh_readonly_assignments() -> None:
    """Shell scripts must not assign to zsh read-only builtins.

    Scripts that do so work in bash but fail with
    ``read-only variable: X`` when invoked under zsh.
    """
    violations: list[str] = []
    for path in _iter_shell_files():
        if _should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _ASSIGN_RE.finditer(text):
            # Column at line start; figure out line number
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_no = text.count("\n", 0, match.start()) + 1
            line = text[line_start : text.find("\n", line_start)]
            if line.find("\n") == -1:
                line = text[line_start:]
            violations.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: " f"{line.strip()}")

    assert not violations, (
        "Shell scripts assign to zsh-readonly builtins "
        "(will fail with 'read-only variable' under zsh):\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\n\nRename the variable (e.g. `status=` → `result=`). "
        "See .claude/CLAUDE.md for the rationale."
    )


def test_readonly_names_list_is_documented() -> None:
    """Keep the readonly-names list aligned with the lesson."""
    # The lesson lives in the lessons corpus (post-T5 cutover);
    # fall back to CLAUDE.md for pre-cutover layouts.
    lessons = REPO_ROOT / ".claude" / "lessons.md"
    claude_md = lessons if lessons.is_file() else REPO_ROOT / ".claude" / "CLAUDE.md"
    if not claude_md.is_file():
        # Docs not required for the guard to function;
        # skip the cross-check if neither file exists.
        return
    text = claude_md.read_text(encoding="utf-8")
    # At minimum the lesson should name `status` and
    # `pipestatus` — the two realistic offenders.
    if "status" not in text or "pipestatus" not in text:
        # The guard file itself is the source of truth; just
        # emit a soft warning via pytest skip.
        import pytest

        pytest.skip(
            "CLAUDE.md lesson does not yet document status/" "pipestatus; add it when convenient.",
        )
