"""`AgentGraphConfig` rename — deprecated alias contract. REMOVE IN v16.0.0.

Spec ``models-workflows-layering`` D5: ``agent_factory.base`` held one of
four classes named ``WorkflowConfig``. It is now ``AgentGraphConfig`` —
the fields it carries (``mode`` ∈ sequential/parallel/graph/conversation,
``state_schema``, ``checkpointing``, ``framework_options``) are
graph-construction concerns, and the ``Agent`` prefix matches its
neighbours ``AgentRole``/``AgentCapability``/``AgentConfig``.

Recorded because the ruling turned on it: inside its own module the old
name was already coherent, so this rename buys nothing locally — the
collision was only visible globally, and the chair ruled the
one-bare-name intent outranks local coherence.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib
import warnings

import pytest

PATHS = ("attune.agent_factory", "attune.agent_factory.base")


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_new_name_does_not_warn(path: str) -> None:
    module = importlib.import_module(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = module.AgentGraphConfig  # access IS the trigger under PEP 562
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_old_name_warns_and_names_the_version(path: str) -> None:
    module = importlib.import_module(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = module.WorkflowConfig  # access IS the trigger under PEP 562
    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, f"{path}.WorkflowConfig did not warn"
    assert "v16.0.0" in messages[0], messages[0]
    assert "AgentGraphConfig" in messages[0], messages[0]


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_alias_is_the_same_object_not_a_copy(path: str) -> None:
    """Identity — a copy would silently vacate patches (#2162 class)."""
    from attune.agent_factory.base import AgentGraphConfig

    module = importlib.import_module(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert module.WorkflowConfig is AgentGraphConfig


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_unknown_attribute_still_raises(path: str) -> None:
    module = importlib.import_module(path)
    with pytest.raises(AttributeError, match="NoSuchThing"):
        _ = module.NoSuchThing


@pytest.mark.unit
def test_this_rename_no_longer_collides_with_the_canonical_name() -> None:
    """D5's point: the bare name belongs to the ``workflows.yaml``-backed
    class, and this one no longer competes for it.

    Deliberately scoped to the two classes THIS branch can speak for. The
    third former collision (``config.sections`` -> ``WorkflowsConfig``)
    ships separately, so asserting it here would couple this PR to that
    one's merge order and fail for a reason that is not about this diff.
    The full three-way assertion belongs in a follow-up once both have
    landed.
    """
    from attune.agent_factory.base import AgentGraphConfig
    from attune.workflows.config import WorkflowConfig as Canonical

    assert Canonical.__name__ == "WorkflowConfig"
    assert AgentGraphConfig.__name__ == "AgentGraphConfig"
    assert Canonical is not AgentGraphConfig
