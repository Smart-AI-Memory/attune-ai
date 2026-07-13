"""Drift guard — the PEP 735 ``dev`` dependency-group mirrors the ``dev`` extra.

Two provisioning surfaces install the dev toolchain:

1. ``pip install -e .[dev]`` — CI and pip users (extras).
2. ``uv sync`` / ``uv run`` — local checkouts and worktrees, which
   include the ``dev`` *dependency group* by default (PEP 735) but do
   NOT include extras unless ``--extra dev`` is remembered.

Before the group existed, every fresh sibling/worktree venv started
without pytest/fastapi and the failure recurred often enough to earn a
lesson (the 2026-07-13 attune-ai-fable checkout was the latest hit).
The group closes that class — but only while its contents stay
identical to the extra. This test pins that equality so a dep added to
one surface cannot silently drift from the other.

Parsing is line-based bracket tracking, NOT a regex across the block —
dep specs like ``"uvicorn[standard]>=0.27"`` contain ``]`` and
silently truncate DOTALL matches (see test_extras_honesty.py, which
hit the same bug).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _dep_list(section_header: str, key: str) -> list[str]:
    """Extract the quoted dep specs of ``key = [...]`` inside a section."""
    text = PYPROJECT.read_text(encoding="utf-8")
    block = re.search(
        rf"^\[{re.escape(section_header)}\]\n(.*?)(?=^\[)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    assert block, f"[{section_header}] not found in pyproject.toml"
    deps: list[str] = []
    in_key = False
    for line in block.group(1).splitlines():
        if re.match(rf"^{re.escape(key)}\s*=\s*\[", line):
            in_key = True
            continue
        if in_key:
            if line.strip() == "]":
                break
            match = re.match(r'\s*"([^"]+)"', line)
            if match:
                deps.append(match.group(1))
    assert deps, f"{key} list not found under [{section_header}]"
    return deps


def test_dev_group_mirrors_dev_extra() -> None:
    extra = _dep_list("project.optional-dependencies", "dev")
    group = _dep_list("dependency-groups", "dev")
    assert sorted(group) == sorted(extra), (
        "The [dependency-groups] dev group has drifted from the "
        "[project.optional-dependencies] dev extra. Keep them identical: "
        "pip/CI install the extra, uv sync/uv run install the group — a "
        "dep present in only one surface reintroduces the "
        "fresh-venv-lacks-test-deps failure class.\n"
        f"only in extra: {sorted(set(extra) - set(group))}\n"
        f"only in group: {sorted(set(group) - set(extra))}"
    )
