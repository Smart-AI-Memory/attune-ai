"""Gate: no two workflows may share a name or a concurrency group.

``${{ github.workflow }}`` expands to a workflow's **name**, not its filename.
Two files sharing a ``name:`` therefore compute the *same* concurrency group,
and with ``cancel-in-progress: true`` they cancel each other — nondeterministically,
since it depends on which run GitHub starts second.

This is not hypothetical. ``security.yml`` and ``security-scan.yml`` were both
named "Security Scan". On every PR one of the two was cancelled at random, and
``gh pr checks`` renders a cancelled run as ``fail``, so the symptom read as a
flaky failure rather than a lost scan. Half the time the casualty was
``security-scan.yml``, which *blocks on critical findings* — a PR could have
merged past a gate that simply never ran.

Parsing is a lightweight line scan rather than a YAML load, matching the
convention used elsewhere in this repo for reading workflow and memory
frontmatter without taking a dependency.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
_GROUP_RE = re.compile(r"^\s+group:\s*(.+?)\s*$", re.MULTILINE)

#: Workflows deliberately sharing a concurrency group, mapped to the reason.
#: Sharing is occasionally correct (a family of workflows that must serialize),
#: but it must be a decision, not an accident from a duplicated ``name:``.
_ALLOWED_SHARED_GROUPS: dict[str, str] = {}


def _workflow_files() -> list[Path]:
    if not WORKFLOWS.is_dir():  # pragma: no cover - repo layout guard
        pytest.skip("no .github/workflows directory")
    return sorted(p for p in WORKFLOWS.iterdir() if p.suffix in (".yml", ".yaml"))


def _workflow_name(text: str, path: Path) -> str:
    match = _NAME_RE.search(text)
    return match.group(1) if match else path.stem


def _concurrency_group(text: str) -> str | None:
    """Return the raw ``group:`` expression inside a ``concurrency:`` block."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.rstrip() != "concurrency:":
            continue
        for follower in lines[i + 1 :]:
            if follower and not follower[0].isspace():
                break  # left the block without finding a group
            found = _GROUP_RE.match(follower)
            if found:
                return found.group(1)
    return None


def test_workflow_names_are_unique() -> None:
    """Two workflows sharing a name collide in ${{ github.workflow }}."""
    by_name: dict[str, list[str]] = {}
    for path in _workflow_files():
        name = _workflow_name(path.read_text(encoding="utf-8"), path)
        by_name.setdefault(name, []).append(path.name)

    collisions = {name: files for name, files in by_name.items() if len(files) > 1}
    assert not collisions, (
        "workflow name collision — ${{ github.workflow }} expands to the name, "
        "so these share a concurrency group and cancel each other: "
        f"{collisions}"
    )


def test_concurrency_groups_are_unique() -> None:
    """Distinct workflows must not compute the same concurrency group."""
    by_group: dict[str, list[str]] = {}
    for path in _workflow_files():
        text = path.read_text(encoding="utf-8")
        group = _concurrency_group(text)
        if group is None:
            continue
        # Resolve the one expansion that silently unifies distinct files.
        resolved = group.replace("${{ github.workflow }}", _workflow_name(text, path))
        by_group.setdefault(resolved, []).append(path.name)

    collisions = {
        group: files
        for group, files in by_group.items()
        if len(files) > 1 and group not in _ALLOWED_SHARED_GROUPS
    }
    assert not collisions, (
        "concurrency group collision — with cancel-in-progress these workflows "
        f"kill each other at random: {collisions}. Give each file a literal, "
        "unique group id, or record the sharing in _ALLOWED_SHARED_GROUPS."
    )


def test_the_two_security_workflows_stay_separated() -> None:
    """Regression pin for the specific collision that motivated this gate.

    Both files existed and both were named "Security Scan", so one died on
    every PR. Naming them apart is the fix; this pins it so a later rename
    cannot quietly restore the collision.
    """
    paths = [WORKFLOWS / "security.yml", WORKFLOWS / "security-scan.yml"]
    present = [p for p in paths if p.is_file()]
    if len(present) < 2:
        pytest.skip("both security workflows are no longer present")

    names, groups = set(), set()
    for path in present:
        text = path.read_text(encoding="utf-8")
        names.add(_workflow_name(text, path))
        groups.add(_concurrency_group(text))

    assert len(names) == 2, f"security workflows must not share a name: {names}"
    assert len(groups) == 2, f"security workflows must not share a group: {groups}"
    assert not any(
        g and "${{ github.workflow }}" in g for g in groups
    ), "security workflow groups must be literals — github.workflow is the name"
