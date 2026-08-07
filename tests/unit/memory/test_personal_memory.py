"""Tests for PersonalMemory — personal cross-session memory.

Covers _build_skeleton, _extract_summary, _update_summaries,
capture, query, list_topics, and forget_topic.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from attune.memory.personal import (
    PersonalMemory,
    _build_skeleton,
    _extract_summary,
)

# ---------------------------------------------------------------------------
# _build_skeleton
# ---------------------------------------------------------------------------


class TestBuildSkeleton:
    def test_decision_contains_h1_with_topic(self):
        out = _build_skeleton("auth-design", "decision", "JWT over sessions")
        assert out.startswith("# auth-design\n")
        assert "Decision" in out
        assert "JWT over sessions" in out

    def test_pattern_contains_h1_with_topic(self):
        out = _build_skeleton("retry-loop", "pattern", "Use exponential backoff")
        assert out.startswith("# retry-loop\n")
        assert "Problem" in out
        assert "Use exponential backoff" in out

    def test_troubleshooting_contains_h1_with_topic(self):
        out = _build_skeleton("redis-conn", "troubleshooting", "Connection refused")
        assert out.startswith("# redis-conn\n")
        assert "Symptoms" in out
        assert "Connection refused" in out

    def test_reference_contains_h1_with_topic(self):
        out = _build_skeleton("jwt-api", "reference", "jwt.encode(payload, key)")
        assert out.startswith("# jwt-api\n")
        assert "Overview" in out
        assert "jwt.encode(payload, key)" in out

    def test_unknown_kind_falls_through_to_reference(self):
        out = _build_skeleton("topic", "unknown-kind", "some content")
        assert out.startswith("# topic\n")
        assert "some content" in out

    def test_content_appears_in_all_kinds(self):
        content = "unique-content-string-xyz"
        for kind in ("decision", "pattern", "troubleshooting", "reference"):
            assert content in _build_skeleton("t", kind, content)


# ---------------------------------------------------------------------------
# _extract_summary
# ---------------------------------------------------------------------------


class TestExtractSummary:
    def test_first_non_heading_non_blank_line(self):
        text = "# Title\n\nThis is the summary line.\n\n## Section\n\nMore text."
        assert _extract_summary(text) == "This is the summary line."

    def test_skips_headings(self):
        text = "# H1\n## H2\nActual summary here."
        assert _extract_summary(text) == "Actual summary here."

    def test_skips_frontmatter(self):
        text = "---\ntitle: Foo\nkind: decision\n---\n\n# Topic\n\nReal summary."
        assert _extract_summary(text) == "Real summary."

    def test_all_headings_returns_empty(self):
        text = "# H1\n## H2\n### H3"
        assert _extract_summary(text) == ""

    def test_empty_text_returns_empty(self):
        assert _extract_summary("") == ""

    def test_truncates_at_120_chars(self):
        long_line = "x" * 200
        text = f"# Title\n\n{long_line}"
        result = _extract_summary(text)
        assert len(result) == 120

    def test_blank_lines_skipped(self):
        text = "\n\n\n# Title\n\n\n\nActual line."
        assert _extract_summary(text) == "Actual line."


# ---------------------------------------------------------------------------
# _update_summaries (via PersonalMemory private helper)
# ---------------------------------------------------------------------------


class TestUpdateSummaries:
    def _make_pm(self, tmp_path):
        return PersonalMemory(global_root=tmp_path / "global")

    def test_creates_sidecar_when_absent(self, tmp_path):
        pm = self._make_pm(tmp_path)
        root = tmp_path / "global"
        root.mkdir(parents=True)
        dest = root / "auth" / "decision.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("# auth\n\nWe chose JWT.", encoding="utf-8")

        pm._update_summaries(root, dest, "# auth\n\nWe chose JWT.")

        sidecar = root / "summaries_by_path.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "auth/decision.md" in data

    def test_upserts_without_losing_existing_keys(self, tmp_path):
        pm = self._make_pm(tmp_path)
        root = tmp_path / "global"
        root.mkdir(parents=True)
        sidecar = root / "summaries_by_path.json"
        sidecar.write_text(
            json.dumps({"existing/reference.md": "prior entry"}),
            encoding="utf-8",
        )

        dest = root / "new" / "decision.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("# new\n\nNew content.", encoding="utf-8")
        pm._update_summaries(root, dest, "# new\n\nNew content.")

        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "existing/reference.md" in data
        assert "new/decision.md" in data

    def test_corrupted_sidecar_is_replaced_cleanly(self, tmp_path):
        pm = self._make_pm(tmp_path)
        root = tmp_path / "global"
        root.mkdir(parents=True)
        sidecar = root / "summaries_by_path.json"
        sidecar.write_text("INVALID JSON {{{", encoding="utf-8")

        dest = root / "topic" / "pattern.md"
        dest.parent.mkdir(parents=True)
        dest.write_text("# topic\n\nContent.", encoding="utf-8")
        pm._update_summaries(root, dest, "# topic\n\nContent.")

        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "topic/pattern.md" in data


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


def _identity_polish(text: str, template_type: str) -> str:
    """Stub: return skeleton unchanged."""
    return text


class TestCapture:
    def _make_pm(self, tmp_path):
        return PersonalMemory(global_root=tmp_path / "global")

    def test_correct_path_created(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with patch("attune.memory.personal._load_author", return_value=_identity_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                dest = pm.capture("auth-arch", "JWT for auth", kind="decision")

        assert dest == tmp_path / "global" / "auth-arch" / "decision.md"
        assert dest.exists()

    def test_capture_refuses_content_with_a_secret(self, tmp_path):
        """R2: the curated write path fails closed on a secret — the file is
        never written and the polish LLM is never called with it."""
        from attune.memory.types import SecurityError

        pm = self._make_pm(tmp_path)
        secret = "The key is AKIAIOSFODNN7EXAMPLE, keep it safe."
        with patch("attune.memory.personal._load_author", return_value=_identity_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                with pytest.raises(SecurityError):
                    pm.capture("leak", secret, kind="decision")

        assert not (tmp_path / "global" / "leak" / "decision.md").exists()

    def test_capture_refuses_bare_anthropic_key(self, tmp_path):
        """The spec's proof case: a bare sk-ant value with no key= label."""
        from attune.memory.types import SecurityError

        pm = self._make_pm(tmp_path)
        content = "note to self: sk-ant-api03-" + "x" * 95
        with patch("attune.memory.personal._load_author", return_value=_identity_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                with pytest.raises(SecurityError):
                    pm.capture("leak2", content, kind="decision")

    def test_summaries_updated_after_capture(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with patch("attune.memory.personal._load_author", return_value=_identity_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                pm.capture("retry", "Retry with backoff", kind="pattern")

        sidecar = tmp_path / "global" / "summaries_by_path.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "retry/pattern.md" in data

    def test_unknown_kind_raises_value_error(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with pytest.raises(ValueError, match="Unknown kind"):
            pm.capture("topic", "content", kind="bogus-kind")

    def test_invalid_topic_slug_raises_value_error(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with pytest.raises(ValueError, match="Invalid topic slug"):
            pm.capture("../escape", "content", kind="decision")

    def test_topic_starting_with_dash_rejected(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with pytest.raises(ValueError, match="Invalid topic slug"):
            pm.capture("-bad-start", "content", kind="reference")

    def test_polish_failure_with_strict_false_writes_skeleton(self, tmp_path):
        pm = self._make_pm(tmp_path)

        def _failing_polish(text: str, template_type: str) -> str:
            raise RuntimeError("LLM error")

        with patch("attune.memory.personal._load_author", return_value=_failing_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                dest = pm.capture("fallback", "raw content", kind="reference")

        assert dest.exists()
        assert "raw content" in dest.read_text(encoding="utf-8")

    def test_project_local_flag_writes_to_project_root(self, tmp_path):
        project_root = tmp_path / "project" / ".attune" / "memory"
        pm = PersonalMemory(
            global_root=tmp_path / "global",
            project_root=project_root,
        )
        with patch("attune.memory.personal._load_author", return_value=_identity_polish):
            with patch("attune.memory.personal._load_rag", return_value=None):
                dest = pm.capture("local-topic", "data", kind="reference", project_local=True)

        assert dest.is_relative_to(project_root)

    def test_no_author_dep_writes_raw_skeleton(self, tmp_path):
        pm = self._make_pm(tmp_path)
        with patch("attune.memory.personal._load_author", return_value=None):
            with patch("attune.memory.personal._load_rag", return_value=None):
                dest = pm.capture("nodep", "some notes", kind="troubleshooting")

        assert dest.exists()
        assert "some notes" in dest.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


class _FakeCitedSource:
    """Mirrors attune_rag.provenance.CitedSource's public shape."""

    def __init__(self, template_path: str, score: float, category: str = "", excerpt: str = ""):
        self.template_path = template_path
        self.category = category
        self.score = score
        self.excerpt = excerpt


class _FakeCitation:
    def __init__(self, hits: list[_FakeCitedSource]):
        self.hits = tuple(hits)


class _FakeRagResult:
    """Mirrors attune_rag.pipeline.RagResult's public shape (citation.hits)."""

    def __init__(self, hits: list[_FakeCitedSource]):
        self.citation = _FakeCitation(hits)


def _make_fake_rag(hit_dicts: list[dict]):
    """Return a (DirectoryCorpus, RagPipeline) tuple with stubbed run().

    ``hit_dicts`` uses the same {"path", "score", ...} shape the tests
    already use for readability; wrapped into the real RagResult/
    CitedSource shape that RagPipeline.run() actually returns (see
    PersonalMemory.query()'s fix - it reads rag_result.citation.hits,
    not a plain list).
    """
    fake_hits = [
        _FakeCitedSource(
            template_path=h["path"],
            score=h["score"],
            category=h.get("category", ""),
            excerpt=h.get("excerpt", ""),
        )
        for h in hit_dicts
    ]

    class _FakeCorpus:
        def __init__(self, root, summaries_file, glob):
            pass

        def entries(self):
            return iter([object()])

    class _FakePipeline:
        def __init__(self, corpus):
            pass

        def run(self, query, k):
            return _FakeRagResult(fake_hits)

    return _FakeCorpus, _FakePipeline


class TestQuery:
    def test_empty_list_when_no_directory(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path / "nonexistent")
        with patch("attune.memory.personal._load_rag", return_value=None):
            result = pm.query("anything")
        assert result == []

    def test_returns_hits_sorted_by_score_descending(self, tmp_path):
        root = tmp_path / "global"
        root.mkdir(parents=True)
        (root / "dummy").mkdir()
        (root / "dummy" / "decision.md").write_text("x", encoding="utf-8")

        hits = [
            {"path": "a/decision.md", "summary": "a", "excerpt": "", "score": 0.5},
            {"path": "b/decision.md", "summary": "b", "excerpt": "", "score": 0.9},
        ]
        pm = PersonalMemory(global_root=root)
        with patch("attune.memory.personal._load_rag", return_value=_make_fake_rag(hits)):
            result = pm.query("something", k=5)

        assert result[0]["score"] >= result[1]["score"]

    def test_kind_filter_excludes_wrong_kinds(self, tmp_path):
        root = tmp_path / "global"
        root.mkdir(parents=True)
        (root / "dummy").mkdir()
        (root / "dummy" / "decision.md").write_text("x", encoding="utf-8")

        hits = [
            {"path": "a/decision.md", "summary": "", "excerpt": "", "score": 0.8},
            {"path": "b/pattern.md", "summary": "", "excerpt": "", "score": 0.7},
        ]
        pm = PersonalMemory(global_root=root)
        with patch("attune.memory.personal._load_rag", return_value=_make_fake_rag(hits)):
            result = pm.query("q", kind_filter="decision")

        assert len(result) == 1
        assert all(r["path"].endswith("/decision.md") for r in result)

    def test_project_hits_win_ties(self, tmp_path):
        global_root = tmp_path / "global"
        project_root = tmp_path / "project"
        global_root.mkdir(parents=True)
        project_root.mkdir(parents=True)

        (global_root / "t").mkdir()
        (global_root / "t" / "decision.md").write_text("x", encoding="utf-8")
        (project_root / "t").mkdir()
        (project_root / "t" / "decision.md").write_text("x", encoding="utf-8")

        global_hits = _FakeRagResult([_FakeCitedSource(template_path="t/decision.md", score=0.8)])
        project_hits = _FakeRagResult([_FakeCitedSource(template_path="t/decision.md", score=0.8)])

        call_count = 0

        def _fake_rag_factory():
            class _FakeCorpus:
                def __init__(self, root, summaries_file, glob):
                    self._root = str(root)

                def entries(self):
                    return iter([object()])

            class _FakePipeline:
                def __init__(self, corpus):
                    self._corpus = corpus

                def run(self, query, k):
                    nonlocal call_count
                    call_count += 1
                    if str(project_root) in self._corpus._root:
                        return project_hits
                    return global_hits

            return _FakeCorpus, _FakePipeline

        pm = PersonalMemory(global_root=global_root, project_root=project_root)
        with patch("attune.memory.personal._load_rag", return_value=_fake_rag_factory()):
            result = pm.query("something", k=2)

        # project hit has score boosted by 0.001 so it should sort first
        assert len(result) >= 1

    def test_query_round_trips_against_real_attune_rag(self, tmp_path):
        """Regression guard: before the fix, query() did `for hit in
        pipeline.run(...)`, but the installed attune_rag's
        RagPipeline.run() returns a RagResult (not iterable), raising
        `TypeError: 'RagResult' object is not iterable` on every call.
        That was swallowed by query()'s broad except and silently
        returned []. Exercises the REAL attune_rag dependency (no
        mocking of _load_rag) end to end: capture, then query."""
        pm = PersonalMemory(global_root=tmp_path, project_root=tmp_path / "no_project")
        pm.capture(
            "redis-timeout-config",
            "We set the Redis connection timeout to 30 seconds after "
            "seeing intermittent failures under load.",
            kind="decision",
        )

        result = pm.query("Why did we set the Redis timeout?", k=3)

        assert result, "query() returned no hits against a real attune_rag pipeline"
        assert result[0]["path"] == "redis-timeout-config/decision.md"
        assert result[0]["score"] > 0

    def test_query_same_root_twice_returns_each_file_once(self, tmp_path):
        """Regression guard (2026-07-02 live observation): when the
        process cwd is the home directory, the project-root default
        (`cwd/.attune/memory`) resolves to the global root itself, so
        every file was scanned twice and recall returned the same path
        twice with scores exactly 0.001 apart (the project boost).
        Real attune_rag, no mocking."""
        (tmp_path / "dispatch-test").mkdir(parents=True)
        (tmp_path / "dispatch-test" / "decision.md").write_text(
            "# dispatch-test\n\nverifying dispatch works\n", encoding="utf-8"
        )

        pm = PersonalMemory(global_root=tmp_path, project_root=tmp_path)

        assert pm._project_root is None  # identity guard collapsed it
        result = pm.query("verifying dispatch", k=3)
        paths = [r["path"] for r in result]
        assert len(paths) == len(set(paths)), f"duplicate paths: {paths}"
        assert paths == ["dispatch-test/decision.md"]

    def test_query_dedups_identical_relative_path_across_roots(self, tmp_path):
        """Two DISTINCT roots holding the same relative path must yield
        one result (best score wins — the project-boosted hit)."""
        global_root = tmp_path / "global"
        project_root = tmp_path / "project"
        for root in (global_root, project_root):
            (root / "shared-topic").mkdir(parents=True)
            (root / "shared-topic" / "decision.md").write_text(
                "# shared-topic\n\nshared decision content\n", encoding="utf-8"
            )

        pm = PersonalMemory(global_root=global_root, project_root=project_root)
        result = pm.query("shared decision", k=3)

        paths = [r["path"] for r in result]
        assert paths == ["shared-topic/decision.md"]


# ---------------------------------------------------------------------------
# list_topics / forget_topic
# ---------------------------------------------------------------------------


class TestListTopics:
    def test_returns_sorted_topic_slugs(self, tmp_path):
        root = tmp_path / "global"
        for name in ("zebra", "alpha", "beta"):
            (root / name).mkdir(parents=True)
            (root / name / "decision.md").write_text("x", encoding="utf-8")

        pm = PersonalMemory(global_root=root)
        topics = pm.list_topics()
        assert topics == sorted(topics)
        assert set(topics) == {"alpha", "beta", "zebra"}

    def test_ignores_files_at_root_level(self, tmp_path):
        root = tmp_path / "global"
        root.mkdir(parents=True)
        (root / "summaries_by_path.json").write_text("{}", encoding="utf-8")
        (root / "real-topic").mkdir()

        pm = PersonalMemory(global_root=root)
        assert pm.list_topics() == ["real-topic"]

    def test_merges_global_and_project(self, tmp_path):
        global_root = tmp_path / "global"
        project_root = tmp_path / "project"
        (global_root / "global-only").mkdir(parents=True)
        (project_root / "project-only").mkdir(parents=True)

        pm = PersonalMemory(global_root=global_root, project_root=project_root)
        topics = pm.list_topics()
        assert "global-only" in topics
        assert "project-only" in topics


class TestForgetTopic:
    def test_deletes_entire_topic_dir(self, tmp_path):
        root = tmp_path / "global"
        topic_dir = root / "auth-arch"
        topic_dir.mkdir(parents=True)
        (topic_dir / "decision.md").write_text("x", encoding="utf-8")

        pm = PersonalMemory(global_root=root)
        deleted = pm.forget_topic("auth-arch")

        assert deleted == 1
        assert not topic_dir.exists()

    def test_deletes_only_specified_kind(self, tmp_path):
        root = tmp_path / "global"
        topic_dir = root / "auth-arch"
        topic_dir.mkdir(parents=True)
        (topic_dir / "decision.md").write_text("x", encoding="utf-8")
        (topic_dir / "pattern.md").write_text("x", encoding="utf-8")

        pm = PersonalMemory(global_root=root)
        deleted = pm.forget_topic("auth-arch", kind="decision")

        assert deleted == 1
        assert not (topic_dir / "decision.md").exists()
        assert (topic_dir / "pattern.md").exists()

    def test_returns_zero_when_topic_missing(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path / "global")
        assert pm.forget_topic("nonexistent") == 0

    def test_invalid_topic_slug_raises(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path / "global")
        with pytest.raises(ValueError, match="Invalid topic slug"):
            pm.forget_topic("../etc/passwd")

    def test_invalid_kind_raises(self, tmp_path):
        pm = PersonalMemory(global_root=tmp_path / "global")
        with pytest.raises(ValueError, match="Unknown kind"):
            pm.forget_topic("valid-topic", kind="nonexistent")

    def test_removes_from_summaries_on_delete(self, tmp_path):
        root = tmp_path / "global"
        topic_dir = root / "x"
        topic_dir.mkdir(parents=True)
        (topic_dir / "reference.md").write_text("# x\n\nContent.", encoding="utf-8")

        sidecar = root / "summaries_by_path.json"
        sidecar.write_text(
            json.dumps({"x/reference.md": "Content."}),
            encoding="utf-8",
        )

        pm = PersonalMemory(global_root=root)
        pm.forget_topic("x", kind="reference")

        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "x/reference.md" not in data
