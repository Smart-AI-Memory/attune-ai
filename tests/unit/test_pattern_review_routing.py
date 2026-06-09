"""Tests for opt-in review routing of contributed patterns (R7).

Covers the env-var flag (:func:`review_routing_enabled`), the
:func:`stage_for_review` helper, and the two live contribution seams that
honour the flag (verified in Phase 0 to be the only real ones):

- ``SharedLibraryMixin.contribute_pattern`` (the agent-facing API), and
- ``ConfigurationStore._contribute_to_pattern_library`` (meta-orchestrator).

Default is OFF: with the flag unset, both seams contribute straight to the
library exactly as before — no surprise gating.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from attune.core import EmpathyOS
from attune.memory.file_stash import FileStashBackend
from attune.orchestration.config_store import AgentConfiguration, ConfigurationStore
from attune.pattern_library import Pattern, PatternLibrary
from attune.pattern_review import (
    REVIEW_ENABLED_ENV,
    PatternReviewQueue,
    review_routing_enabled,
    stage_for_review,
)


@pytest.fixture
def routing_backend(tmp_path: Path, monkeypatch) -> FileStashBackend:
    """Pin the default backend so ``stage_for_review`` writes to tmp.

    ``stage_for_review`` constructs ``PatternReviewQueue(None)``, which falls
    back to ``_default_backend()`` — patch it to a tmp file backend so the
    seam tests can assert against the same store without touching real state.
    """
    backend = FileStashBackend(base_dir=str(tmp_path / "stash"))
    monkeypatch.setattr("attune.pattern_review._default_backend", lambda: backend)
    return backend


def _pattern(pattern_id: str = "p1") -> Pattern:
    return Pattern(
        id=pattern_id,
        agent_id="agent7",
        pattern_type="behavioral",
        name="Retry on 503",
        description="Back off and retry transient 503s.",
        code="x = 1",
        confidence=0.8,
    )


class TestReviewRoutingEnabled:
    def test_unset_is_off(self, monkeypatch):
        monkeypatch.delenv(REVIEW_ENABLED_ENV, raising=False)
        assert review_routing_enabled() is False

    @pytest.mark.parametrize("val", ["1", "true", "yes", "on", "ON", " True "])
    def test_truthy_values_on(self, monkeypatch, val):
        monkeypatch.setenv(REVIEW_ENABLED_ENV, val)
        assert review_routing_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
    def test_falsy_values_off(self, monkeypatch, val):
        monkeypatch.setenv(REVIEW_ENABLED_ENV, val)
        assert review_routing_enabled() is False


class TestStageForReview:
    def test_converts_and_stages(self, routing_backend):
        staged_id = stage_for_review("agent7", _pattern("p1"))
        assert staged_id == "p1"
        got = PatternReviewQueue(backend=routing_backend).get("p1")
        assert got is not None
        assert got.agent_id == "agent7"
        assert got.pattern_type == "behavioral"
        assert got.confidence == 0.8
        assert got.code == "x = 1"


class TestSharedLibrarySeam:
    def test_flag_on_stages_instead_of_contributing(self, routing_backend, monkeypatch):
        monkeypatch.setenv(REVIEW_ENABLED_ENV, "1")
        library = PatternLibrary()
        agent = EmpathyOS(user_id="agent7", shared_library=library)

        agent.contribute_pattern(_pattern("p1"))

        # Routed to the queue, NOT the live library.
        assert "p1" not in library.patterns
        assert PatternReviewQueue(backend=routing_backend).get("p1") is not None

    def test_flag_off_contributes_directly(self, routing_backend, monkeypatch):
        monkeypatch.delenv(REVIEW_ENABLED_ENV, raising=False)
        library = PatternLibrary()
        agent = EmpathyOS(user_id="agent7", shared_library=library)

        agent.contribute_pattern(_pattern("p1"))

        assert "p1" in library.patterns
        assert PatternReviewQueue(backend=routing_backend).get("p1") is None


class TestConfigStoreSeam:
    def _proven_config(self) -> AgentConfiguration:
        return AgentConfiguration(
            id="abc",
            task_pattern="release_prep",
            agents=[{"role": "tester", "tier": "CHEAP"}],
            strategy="parallel",
            quality_gates={"min_score": 80},
            success_rate=0.9,
            usage_count=5,
            success_count=4,
        )

    def test_flag_on_stages_instead_of_contributing(self, tmp_path, routing_backend, monkeypatch):
        monkeypatch.setenv(REVIEW_ENABLED_ENV, "1")
        library = PatternLibrary()
        store = ConfigurationStore(storage_dir=str(tmp_path / "cfg"), pattern_library=library)
        store._contribute_to_pattern_library(self._proven_config())

        assert "orchestration_abc" not in library.patterns
        assert PatternReviewQueue(backend=routing_backend).get("orchestration_abc") is not None

    def test_flag_off_contributes_directly(self, tmp_path, routing_backend, monkeypatch):
        monkeypatch.delenv(REVIEW_ENABLED_ENV, raising=False)
        library = PatternLibrary()
        store = ConfigurationStore(storage_dir=str(tmp_path / "cfg"), pattern_library=library)
        store._contribute_to_pattern_library(self._proven_config())

        assert "orchestration_abc" in library.patterns
        assert PatternReviewQueue(backend=routing_backend).get("orchestration_abc") is None

    def test_unproven_config_contributes_nothing_either_way(
        self, tmp_path, routing_backend, monkeypatch
    ):
        # The success-threshold guard fires before any routing decision.
        monkeypatch.setenv(REVIEW_ENABLED_ENV, "1")
        library = PatternLibrary()
        store = ConfigurationStore(storage_dir=str(tmp_path / "cfg"), pattern_library=library)
        weak = AgentConfiguration(
            id="weak",
            task_pattern="t",
            agents=[],
            strategy="sequential",
            quality_gates={},
            success_rate=0.1,
            usage_count=1,
        )
        store._contribute_to_pattern_library(weak)

        assert library.patterns == {}
        assert PatternReviewQueue(backend=routing_backend).list() == []
