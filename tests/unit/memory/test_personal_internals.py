"""Internal-branch tests for PersonalMemory.

Covers the optional-dependency lazy imports, the polish fallback ladder,
the RAG grounding/query degradation paths, and the summaries-sidecar +
forget guards — branches the main personal-memory suite leaves
uncovered. Optional deps are simulated via sys.modules so these pass
whether or not attune-author / attune-rag are installed.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
import types

import pytest

from attune.memory.personal import (
    _SUMMARIES_FILE,
    PersonalMemory,
    _load_author,
    _load_rag,
)


class TestLazyImports:
    """_load_author / _load_rag success and graceful-failure branches."""

    def test_load_author_success(self, monkeypatch):
        def fake_polish(text, template_type):
            return text

        mod = types.ModuleType("attune.authoring.polish")
        mod.polish_template = fake_polish
        monkeypatch.setitem(sys.modules, "attune.authoring.polish", mod)

        assert _load_author() is fake_polish

    def test_load_author_failure_returns_none(self, monkeypatch):
        # A None entry forces ImportError on
        # `from attune.authoring.polish import …`.
        monkeypatch.setitem(sys.modules, "attune.authoring.polish", None)
        assert _load_author() is None

    def test_load_rag_success(self, monkeypatch):
        dc = type("DirectoryCorpus", (), {})
        rp = type("RagPipeline", (), {})
        directory = types.ModuleType("attune_rag.corpus.directory")
        directory.DirectoryCorpus = dc
        pipeline = types.ModuleType("attune_rag.pipeline")
        pipeline.RagPipeline = rp
        monkeypatch.setitem(sys.modules, "attune_rag", types.ModuleType("attune_rag"))
        monkeypatch.setitem(sys.modules, "attune_rag.corpus", types.ModuleType("attune_rag.corpus"))
        monkeypatch.setitem(sys.modules, "attune_rag.corpus.directory", directory)
        monkeypatch.setitem(sys.modules, "attune_rag.pipeline", pipeline)

        assert _load_rag() == (dc, rp)

    def test_load_rag_failure_returns_none(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "attune_rag.corpus.directory", None)
        assert _load_rag() is None


class TestGroundPersonal:
    """_ground_personal returns the skeleton unchanged in every degraded case."""

    def test_returns_skeleton_when_rag_unavailable(self, monkeypatch, tmp_path):
        monkeypatch.setattr("attune.memory.personal._load_rag", lambda: None)
        pm = PersonalMemory(global_root=tmp_path)

        assert pm._ground_personal("SKEL", tmp_path) == "SKEL"

    def test_returns_skeleton_when_corpus_empty(self, monkeypatch, tmp_path):
        class FakeCorpus:
            def __init__(self, *a, **k):
                pass

            def entries(self):
                return iter([])

        monkeypatch.setattr("attune.memory.personal._load_rag", lambda: (FakeCorpus, object))
        pm = PersonalMemory(global_root=tmp_path)

        assert pm._ground_personal("SKEL", tmp_path) == "SKEL"

    def test_returns_skeleton_on_corpus_error(self, monkeypatch, tmp_path):
        class FakeCorpus:
            def __init__(self, *a, **k):
                raise RuntimeError("corpus boom")

        monkeypatch.setattr("attune.memory.personal._load_rag", lambda: (FakeCorpus, object))
        pm = PersonalMemory(global_root=tmp_path)

        assert pm._ground_personal("SKEL", tmp_path) == "SKEL"


class TestPolish:
    """_polish fallback ladder: no-op, empty result, newline, strict raise."""

    def test_empty_polish_result_returns_original(self, monkeypatch):
        monkeypatch.setattr(
            "attune.memory.personal._load_author",
            lambda: (lambda text, template_type: ""),
        )
        pm = PersonalMemory()

        assert pm._polish("RAW", "decision", strict=False) == "RAW"

    def test_appends_trailing_newline(self, monkeypatch):
        monkeypatch.setattr(
            "attune.memory.personal._load_author",
            lambda: (lambda text, template_type: "polished"),
        )
        pm = PersonalMemory()

        assert pm._polish("RAW", "decision", strict=False) == "polished\n"

    def test_strict_reraises_on_polish_error(self, monkeypatch):
        def boom(text, template_type):
            raise RuntimeError("polish failed")

        monkeypatch.setattr("attune.memory.personal._load_author", lambda: boom)
        pm = PersonalMemory()

        with pytest.raises(RuntimeError, match="polish failed"):
            pm._polish("RAW", "decision", strict=True)

    def test_non_strict_swallows_polish_error(self, monkeypatch):
        def boom(text, template_type):
            raise RuntimeError("polish failed")

        monkeypatch.setattr("attune.memory.personal._load_author", lambda: boom)
        pm = PersonalMemory()

        assert pm._polish("RAW", "decision", strict=False) == "RAW"


class TestQueryAndForgetGuards:
    """query error-swallow and forget_topic missing-dir skip."""

    def test_query_swallows_corpus_error(self, monkeypatch, tmp_path):
        class FakeCorpus:
            def __init__(self, *a, **k):
                raise RuntimeError("corpus boom")

        monkeypatch.setattr("attune.memory.personal._load_rag", lambda: (FakeCorpus, object))
        pm = PersonalMemory(global_root=tmp_path, project_root=tmp_path / "noproj")

        assert pm.query("anything") == []

    def test_forget_topic_missing_dir_returns_zero(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path, project_root=tmp_path / "noproj")

        assert pm.forget_topic("ghost-topic") == 0


class TestSummariesSidecar:
    """_remove_from_summaries tolerates a corrupt sidecar."""

    def test_corrupt_sidecar_is_ignored(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path)
        sidecar = tmp_path / _SUMMARIES_FILE
        sidecar.write_text("{not valid json", encoding="utf-8")

        # Must not raise on unparseable JSON.
        pm._remove_from_summaries(tmp_path, tmp_path / "topic" / "decision.md")

        # Corrupt file is left untouched (nothing to remove).
        assert sidecar.read_text(encoding="utf-8") == "{not valid json"
