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
import warnings
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[3] / "src" / "attune"

# The one module allowed to DEFINE a class named WorkflowConfig for good:
# the public, workflows.yaml-backed type (D2 — it keeps the name).
CANONICAL = "workflows/config.py"

# Still defined, but only until the next major. D4 ruled this orphan twin
# deleted; D6 moved the timing to v16.0.0 rather than dropping a
# six-month-old public export without notice. The allowance is tied to
# that marker by `test_the_deprecated_definition_still_carries_its_marker`
# below — when 16.0.0 removes the class, BOTH must be updated together,
# so this list cannot quietly outlive the deprecation it exists for.
DEPRECATED_UNTIL_V16 = ["config/agent_config.py"]

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
    """Only the canonical type, plus definitions already scheduled for
    deletion, may carry the bare name.

    Shrink-only by construction: a NEW ``WorkflowConfig`` anywhere fails
    here, and removing the deprecated one at v16.0.0 requires shortening
    ``DEPRECATED_UNTIL_V16`` in the same commit.
    """
    allowed = sorted([CANONICAL, *DEPRECATED_UNTIL_V16])
    definitions = _class_definitions("WorkflowConfig")
    assert definitions == allowed, (
        "Only the workflows.yaml-backed WorkflowConfig at "
        f"{CANONICAL} may carry the bare name (spec "
        "models-workflows-layering, D2/D5), plus definitions already "
        f"scheduled for removal: {DEPRECATED_UNTIL_V16}. Found: "
        f"{definitions or 'none'}. A new class needs a role-true name; "
        "see decisions.md D5 for the convention."
    )


@pytest.mark.unit
@pytest.mark.parametrize("module_path", DEPRECATED_UNTIL_V16)
def test_the_deprecated_definition_still_carries_its_marker(module_path: str) -> None:
    """The allowance above is only legitimate while the marker exists.

    Without this, someone could un-deprecate the twin (dropping the
    REMOVE IN marker) and the collision gate would keep permitting it
    forever — the allowance would have quietly become a licence.
    """
    text = (SRC / module_path).read_text(encoding="utf-8")
    assert "REMOVE IN v16.0.0" in text, (
        f"{module_path} is allowed a duplicate WorkflowConfig ONLY because "
        "it is scheduled for deletion. Either restore the "
        "'REMOVE IN v16.0.0' marker or remove the class and drop it from "
        "DEPRECATED_UNTIL_V16."
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
def test_every_deprecated_alias_still_resolves_and_warns(module_path: str, attribute: str) -> None:
    """Removing an alias before v16.0.0 is a break, not a cleanup.

    Six access paths were preserved so callers on the old names keep
    working through the 15.x line. Each must still resolve AND still say
    when it goes — a silent alias is worse than none, because the caller
    learns of the rename only when the major breaks them.
    """
    import importlib

    module = importlib.import_module(module_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        resolved = getattr(module, attribute)

    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert resolved is not None
    assert messages, f"{module_path}.{attribute} resolved without warning"
    assert "v16.0.0" in messages[0], messages[0]
