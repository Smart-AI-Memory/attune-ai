"""Curator source + graduation tests (advanced-debugging-plugin T8).

Exclusion parity with the store's purity rules, allowlist redaction,
the publisher interface, and the file publisher shipped under the
2026-07-20 corpus-ownership ruling (chair-gated appends to
`.claude/lessons.md`).
"""

import json

import pytest

from attune.diagnosis.graduation import (
    GraduationError,
    LessonsFilePublisher,
    RenderForChairPublisher,
    build_candidate,
    graduate,
)
from attune.models.telemetry.data_models import DiagnosisHypothesis, DiagnosisRecord

POST_CUTOVER = "2026-07-20T12:00:00+00:00"


def _record(**overrides):
    base = {
        "diagnosis_id": "d1",
        "source_run_id": "run-1",
        "workflow_name": "code-review",
        "created_at": POST_CUTOVER,
        "symptom": "path argument is required",
        "status": "verified",
        "hypotheses": [DiagnosisHypothesis(statement="[s] missing path kwarg", confidence="high")],
        "synthesis": "the run omitted its required path argument",
    }
    base.update(overrides)
    return DiagnosisRecord(**base)


class TestCuratorSource:
    def _seed_store(self, tmp_path, monkeypatch, records):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        stream = tmp_path / "home" / "telemetry" / "diagnosis_records.jsonl"
        stream.parent.mkdir(parents=True)
        stream.write_text(
            "\n".join(json.dumps(r.to_dict()) for r in records) + "\n", encoding="utf-8"
        )

    def test_reads_eligible_and_excludes_fixture_named(self, tmp_path, monkeypatch):
        from attune.curator.sources.diagnoses import read

        self._seed_store(
            tmp_path,
            monkeypatch,
            [_record(), _record(diagnosis_id="dF", workflow_name="stub-workflow")],
        )
        summary = read(project_root=tmp_path)
        assert [i.item_id for i in summary.items] == ["diagnosis:d1"]
        assert summary.state_hash not in ("", "error")

    def test_redaction_is_allowlist_no_diff_or_evidence_content(self, tmp_path, monkeypatch):
        from attune.curator.sources.diagnoses import read

        secret_diff = "SECRET_DIFF_CONTENT do not leak"
        record = _record(
            proposed_fix={"disposition": "proposed", "diff": secret_diff},
        )
        self._seed_store(tmp_path, monkeypatch, [record])
        summary = read(project_root=tmp_path)
        rendered = summary.items[0].title + summary.items[0].detail
        assert "SECRET_DIFF_CONTENT" not in rendered
        assert "fix: proposed" in summary.items[0].detail
        assert summary.items[0].link == "/runs/run-1/view"

    def test_broken_store_never_raises(self, tmp_path, monkeypatch):
        import attune.diagnosis as diag_pkg
        from attune.curator.sources import diagnoses as src

        def boom():
            raise RuntimeError("store on fire")

        monkeypatch.setattr(diag_pkg, "load_diagnoses", boom)
        summary = src.read(project_root=tmp_path)
        assert summary.items == [] and summary.state_hash == "error"


class TestGraduation:
    def test_unverified_never_graduates(self):
        with pytest.raises(GraduationError, match="only verified"):
            build_candidate(_record(status="open"), evidence="x")

    def test_verified_with_evidence_renders(self):
        rendered = graduate(_record(), evidence="reproduced: exit 1 then fixed by --path")
        assert "missing path kwarg" in rendered

    def test_no_evidence_and_no_waiver_blocked_at_lint(self):
        with pytest.raises(GraduationError, match="lint"):
            graduate(_record(), evidence="")

    def test_waived_candidate_renders_with_tag(self):
        rendered = graduate(_record(), evidence="", waived=True)
        assert "chair-waived" in rendered or "unverified" in rendered

    def test_default_publisher_writes_no_files(self, tmp_path, monkeypatch):
        # The 2026-07-20 ruling made file writes legal, but ONLY via the
        # opt-in LessonsFilePublisher — graduate()'s default still renders
        # for the chair and leaves the filesystem untouched.
        monkeypatch.chdir(tmp_path)
        rendered = graduate(_record(), evidence="receipt")
        assert "missing path kwarg" in rendered
        assert list(tmp_path.iterdir()) == []

    def test_custom_publisher_receives_linted_candidate(self):
        received = []

        class Capture:
            def publish(self, candidate):
                received.append(candidate)
                return "captured"

        out = graduate(_record(), evidence="receipt", publisher=Capture())
        assert out == "captured"
        assert received[0].thread == "diagnosis:d1"

    def test_default_publisher_is_render_for_chair(self):
        assert isinstance(
            RenderForChairPublisher().publish(build_candidate(_record(), evidence="receipt")), str
        )


class TestLessonsFilePublisher:
    """Chair-approved corpus appends (2026-07-20 ruling)."""

    def _publisher(self, tmp_path, seed="- **An earlier lesson**: already here.\n"):
        corpus = tmp_path / ".claude" / "lessons.md"
        corpus.parent.mkdir()
        corpus.write_text(seed, encoding="utf-8")
        return LessonsFilePublisher(corpus, project_root=tmp_path), corpus

    def test_appends_in_corpus_format(self, tmp_path):
        publisher, corpus = self._publisher(tmp_path)
        receipt = graduate(
            _record(), evidence="reproduced: exit 1, fixed by --path", publisher=publisher
        )
        text = corpus.read_text(encoding="utf-8")
        # Existing content intact, blank line between entries, dash-bulleted
        # bold-lead entry, single trailing newline.
        assert text.startswith("- **An earlier lesson**: already here.\n\n- **code-review:")
        assert text.endswith(")\n") and not text.endswith("\n\n")
        entry_lines = text.split("\n\n", 1)[1].splitlines()
        assert all(len(line) <= 72 for line in entry_lines)
        assert all(line.startswith("  ") for line in entry_lines[1:])
        assert str(corpus) in receipt and "code-review: path argument is required" in receipt

    def test_provenance_thread_embedded(self, tmp_path):
        publisher, corpus = self._publisher(tmp_path)
        graduate(_record(), evidence="receipt", publisher=publisher)
        assert "thread diagnosis:d1)" in corpus.read_text(encoding="utf-8")

    def test_lint_gate_blocks_and_leaves_file_untouched(self, tmp_path):
        publisher, corpus = self._publisher(tmp_path)
        before = corpus.read_text(encoding="utf-8")
        with pytest.raises(GraduationError, match="lint"):
            graduate(_record(), evidence="", publisher=publisher)
        assert corpus.read_text(encoding="utf-8") == before

    def test_republish_is_already_published_noop(self, tmp_path):
        # Documented duplicate policy: receipted as already-published,
        # idempotent no-op — retrying an interrupted chair-approval flow
        # must neither double-append nor raise.
        publisher, corpus = self._publisher(tmp_path)
        graduate(_record(), evidence="receipt", publisher=publisher)
        after_first = corpus.read_text(encoding="utf-8")
        receipt = graduate(_record(), evidence="receipt", publisher=publisher)
        assert "already published" in receipt and "diagnosis:d1" in receipt
        assert corpus.read_text(encoding="utf-8") == after_first

    def test_prefix_thread_id_is_not_a_duplicate(self, tmp_path):
        # diagnosis:d1 in the corpus must not block diagnosis:d12.
        publisher, corpus = self._publisher(tmp_path)
        graduate(_record(), evidence="receipt", publisher=publisher)
        receipt = graduate(_record(diagnosis_id="d12"), evidence="receipt", publisher=publisher)
        assert receipt.startswith("appended")
        text = corpus.read_text(encoding="utf-8")
        assert "thread diagnosis:d1)" in text and "thread diagnosis:d12)" in text

    def test_creates_missing_corpus_file(self, tmp_path):
        corpus = tmp_path / ".claude" / "lessons.md"
        corpus.parent.mkdir()
        publisher = LessonsFilePublisher(corpus, project_root=tmp_path)
        graduate(_record(), evidence="receipt", publisher=publisher)
        text = corpus.read_text(encoding="utf-8")
        assert text.startswith("- **code-review:") and text.endswith(")\n")

    def test_appends_after_file_missing_trailing_newline(self, tmp_path):
        publisher, corpus = self._publisher(tmp_path, seed="- **No newline at EOF**: entry.")
        graduate(_record(), evidence="receipt", publisher=publisher)
        assert "entry.\n\n- **code-review:" in corpus.read_text(encoding="utf-8")

    def test_default_path_is_dot_claude_lessons(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        publisher = LessonsFilePublisher(project_root=tmp_path)
        graduate(_record(), evidence="receipt", publisher=publisher)
        assert (tmp_path / ".claude" / "lessons.md").exists()


class TestLessonsFilePublisherSecurity:
    """Path validation (CWE-22) on the corpus target."""

    def test_traversal_outside_project_root_rejected(self, tmp_path):
        root = tmp_path / "repo"
        root.mkdir()
        with pytest.raises(ValueError, match="outside allowed"):
            LessonsFilePublisher("../escape.md", project_root=root)

    def test_absolute_path_outside_root_rejected(self, tmp_path):
        root = tmp_path / "repo"
        root.mkdir()
        with pytest.raises(ValueError, match="outside allowed"):
            LessonsFilePublisher(tmp_path / "elsewhere.md", project_root=root)

    def test_null_byte_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="null"):
            LessonsFilePublisher("lessons\x00.md", project_root=tmp_path)

    def test_symlink_escape_rejected(self, tmp_path):
        root = tmp_path / "repo"
        outside = tmp_path / "outside"
        root.mkdir()
        outside.mkdir()
        link = root / "sneaky"
        link.symlink_to(outside)
        with pytest.raises(ValueError, match="outside allowed"):
            LessonsFilePublisher(link / "lessons.md", project_root=root)
