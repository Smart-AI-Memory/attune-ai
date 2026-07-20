"""Curator source + graduation tests (advanced-debugging-plugin T8).

Exclusion parity with the store's purity rules, allowlist redaction,
and the dissent-bound publisher interface (no corpus writes in v1).
"""

import inspect
import json

import pytest

from attune.diagnosis import graduation
from attune.diagnosis.graduation import (
    GraduationError,
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

    def test_v1_publisher_writes_no_files(self):
        # Source-level guard: the graduation module has no file-writing
        # implementation — corpus ownership is unruled (dissent register).
        source = inspect.getsource(graduation)
        assert "write_text" not in source
        assert "open(" not in source
        assert ".write(" not in source

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
