"""Deprecated re-exports on ``attune.config`` — REMOVE IN v16.0.0.

Spec ``models-workflows-layering`` D4 ruled that
``config.agent_config.WorkflowConfig`` (a field-for-field pydantic twin of
``agent_factory.base.WorkflowConfig``, with no consumer in this tree) is
deleted rather than renamed. D6 moved the TIMING to the next major,
because the symbol has been a public export since v2.7.1 — six months and
135 releases — and this project has no usage telemetry, so a break would
be undetectable from our side.

These tests pin the shim's four load-bearing properties. The one most
likely to regress silently is the first: making the import eager would
warn every consumer of the package for a symbol they never touch, and
nothing else in the suite would notice.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import warnings

import pytest

DEPRECATED = ("AgentWorkflowConfig", "WorkflowMode")


@pytest.mark.unit
def test_importing_the_package_does_not_warn() -> None:
    """``import attune.config`` must be silent.

    PEP 562 ``__getattr__`` exists here precisely so the warning fires on
    ACCESS. An eager ``from … import X as Y`` would emit a
    DeprecationWarning for every consumer of the package, including those
    who never touch the deprecated names.
    """
    import importlib

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(importlib.import_module("attune.config"))

    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]


@pytest.mark.unit
@pytest.mark.parametrize("name", DEPRECATED)
def test_access_warns_and_names_the_removal_version(name: str) -> None:
    """Accessing a deprecated export warns and says when it goes."""
    import attune.config as config

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        getattr(config, name)

    messages = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
    assert messages, f"{name} did not warn"
    assert "v16.0.0" in messages[0], messages[0]
    assert name in messages[0], messages[0]


@pytest.mark.unit
def test_deprecated_exports_still_work() -> None:
    """Deprecated does not mean broken — the objects stay usable.

    This is the half that makes the deprecation worth having: an external
    caller's code keeps running, it just tells them to move.
    """
    import attune.config as config

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cfg = config.AgentWorkflowConfig(name="probe")
        mode = config.WorkflowMode

    assert cfg.name == "probe"
    assert cfg.max_iterations == 10
    assert mode.SEQUENTIAL.value == "sequential"


@pytest.mark.unit
def test_unknown_attribute_still_raises_attribute_error() -> None:
    """The shim must not swallow genuine typos into a warning."""
    import attune.config as config

    with pytest.raises(AttributeError, match="NoSuchAttribute"):
        config.NoSuchAttribute  # noqa: B018


@pytest.mark.unit
@pytest.mark.parametrize("name", DEPRECATED)
def test_still_advertised_in_dunder_all(name: str) -> None:
    """``__all__`` keeps them until removal, so ``import *`` is unbroken."""
    import attune.config as config

    assert name in config.__all__
