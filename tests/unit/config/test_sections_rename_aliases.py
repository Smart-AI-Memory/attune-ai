"""`WorkflowsConfig` rename — deprecated alias contract. REMOVE IN v16.0.0.

Spec ``models-workflows-layering`` D2/D5: ``config.sections.workflows``
held the only section class not named after its own module — its six
siblings are ``AnalysisConfig``, ``AuthConfig``, ``EnvironmentConfig``,
``PersistenceConfig``, ``RoutingConfig``, ``TelemetryConfig``. It is now
``WorkflowsConfig``, with the old name served as a deprecated alias on
BOTH public paths until the next major.

The identity assertion is the load-bearing one: an alias that drifts to a
copy silently vacates every monkeypatch and isinstance check aimed at it
(the #2162 class).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib
import warnings

import pytest

# Both public paths the old name was reachable through.
PATHS = ("attune.config.sections", "attune.config.sections.workflows")


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_new_name_does_not_warn(path: str) -> None:
    """The rename must be free for callers who already moved."""
    module = importlib.import_module(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = module.WorkflowsConfig  # access IS the trigger under PEP 562
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
    assert "WorkflowsConfig" in messages[0], messages[0]


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_alias_is_the_same_object_not_a_copy(path: str) -> None:
    """Identity, not equality — a copy would vacate patches silently."""
    from attune.config.sections.workflows import WorkflowsConfig

    module = importlib.import_module(path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert module.WorkflowConfig is WorkflowsConfig


@pytest.mark.unit
@pytest.mark.parametrize("path", PATHS)
def test_unknown_attribute_still_raises(path: str) -> None:
    """The shim must not swallow typos into a deprecation warning."""
    module = importlib.import_module(path)
    with pytest.raises(AttributeError, match="NoSuchThing"):
        _ = module.NoSuchThing


@pytest.mark.unit
def test_unified_config_uses_the_new_name() -> None:
    """The live consumer is migrated, not riding the alias."""
    from attune.config.sections.workflows import WorkflowsConfig
    from attune.config.unified import UnifiedConfig

    cfg = UnifiedConfig()
    assert isinstance(cfg.workflows, WorkflowsConfig)


@pytest.mark.unit
def test_sibling_sections_follow_the_same_convention() -> None:
    """Pins the convention the rename restored.

    If a future section lands misnamed, this fails and says why.
    """
    import attune.config.sections as sections

    for module_name, expected in (
        ("analysis", "AnalysisConfig"),
        ("auth", "AuthConfig"),
        ("environment", "EnvironmentConfig"),
        ("persistence", "PersistenceConfig"),
        ("routing", "RoutingConfig"),
        ("telemetry", "TelemetryConfig"),
        ("workflows", "WorkflowsConfig"),
    ):
        mod = importlib.import_module(f"attune.config.sections.{module_name}")
        assert hasattr(mod, expected), (
            f"{module_name}.py should define {expected} — section classes are "
            f"named after their module (spec models-workflows-layering D5)"
        )
        assert hasattr(sections, expected)
