"""Exactly one class in the tree is named ``WorkflowConfig``. (D5)

Spec ``models-workflows-layering`` D2/D5 resolved a four-way collision on
that name. This gate pins the RESULT, which no single PR could assert:
the renames shipped as three separate PRs (#2319, #2321, #2322), so each
one's tests could only speak for its own class, and the property they
exist to establish — *one* bare name — was verified by hand at merge time
and by nothing afterwards.

Deliberately an AST scan over the whole package rather than an import of
the three classes we already know about. Asserting
``{Canonical, WorkflowsConfig, AgentGraphConfig}`` would pass happily
while a FOURTH ``WorkflowConfig`` appeared in a module nobody thought to
check — which is exactly how the original collision accumulated: four
classes, added over months, each locally reasonable.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3] / "src" / "attune"

# The one module allowed to DEFINE a class named WorkflowConfig for good:
# the public, workflows.yaml-backed type (D2 — it keeps the name).
CANONICAL = "workflows/config.py"

# Classes that resolved the collision, and where they must live. A
# rename-back would silently recreate the collision; this catches it.
RENAMED = {
    "WorkflowsConfig": "config/sections/workflows.py",
    "AgentGraphConfig": "agent_factory/base.py",
}


def _class_definitions(name: str) -> list[str]:
    """Repo-relative paths of every module defining a class called ``name``."""
    found = []
    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, ValueError):
            # ValueError, not just SyntaxError: a source containing a null
            # byte raises ValueError, which would abort this whole scan
            # instead of skipping one file. Caught by
            # tests/unit/gates/test_ast_parse_null_byte_guard.py, which
            # flagged this file on its first run.
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                found.append(path.relative_to(SRC).as_posix())
    return found


@pytest.mark.unit
def test_no_new_class_is_named_workflowconfig() -> None:
    """Only the canonical type may carry the bare name (v16.0.0 final
    state — the deprecated twin and every alias are gone)."""
    definitions = _class_definitions("WorkflowConfig")
    assert definitions == [CANONICAL], (
        "Only the workflows.yaml-backed WorkflowConfig at "
        f"{CANONICAL} may carry the bare name (spec "
        "models-workflows-layering, D2/D5; the deprecated twin was "
        f"deleted at v16.0.0 per D4/D6). Found: {definitions or 'none'}. "
        "A new class needs a role-true name; see decisions.md D5 for "
        "the convention."
    )


@pytest.mark.unit
@pytest.mark.parametrize(("name", "expected_module"), sorted(RENAMED.items()))
def test_renamed_classes_stay_renamed(name: str, expected_module: str) -> None:
    """A rename-back would recreate the collision the gate above forbids."""
    assert _class_definitions(name) == [expected_module]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("module_path", "attribute"),
    [
        ("attune.config", "AgentWorkflowConfig"),
        ("attune.config", "WorkflowMode"),
        ("attune.config.sections", "WorkflowConfig"),
        ("attune.config.sections.workflows", "WorkflowConfig"),
        ("attune.agent_factory", "WorkflowConfig"),
        ("attune.agent_factory.base", "WorkflowConfig"),
    ],
)
def test_removed_aliases_stay_removed(module_path: str, attribute: str) -> None:
    """The six 15.x alias paths died at v16.0.0 (D4/D6) — a helpful
    re-add would silently resurrect the collision this gate exists to
    prevent, so absence is pinned as hard as presence was."""
    import importlib

    module = importlib.import_module(module_path)
    with pytest.raises(AttributeError):
        getattr(module, attribute)
