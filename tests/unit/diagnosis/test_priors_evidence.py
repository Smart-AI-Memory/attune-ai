"""Phase B front-half tests (advanced-debugging-plugin T3).

Priors: term extraction, explicit degraded modes, prior/observed
separation. Evidence: deterministic bounded assembly.
"""

import json

from attune.diagnosis.evidence import build_evidence_pack, ops_log_tail
from attune.diagnosis.priors import (
    extract_error_terms,
    recall_priors,
)
from attune.models.telemetry.data_models import WorkflowRunRecord


def _run(**overrides) -> WorkflowRunRecord:
    base = {
        "run_id": "run-1",
        "workflow_name": "code-review",
        "started_at": "2026-07-20T12:00:00+00:00",
        "success": False,
        "error": "ValueError in attune.ops.runner during `start_run`",
    }
    base.update(overrides)
    return WorkflowRunRecord(**base)


class TestTermExtraction:
    def test_extracts_error_classes_paths_and_backticks(self):
        terms = extract_error_terms(
            "ValueError in attune.ops.runner while calling `start_run` (runner.py)"
        )
        assert "ValueError" in terms
        assert "attune.ops.runner" in terms
        assert "start_run" in terms
        assert "runner.py" in terms

    def test_dedupes_and_caps(self):
        text = "TimeoutError TimeoutError " + " ".join(f"mod.pkg{i}" for i in range(20))
        terms = extract_error_terms(text, limit=5)
        assert len(terms) == 5
        assert terms.count("TimeoutError") == 1

    def test_empty_text_yields_no_terms(self):
        assert extract_error_terms("") == []


class _FakeRedis:
    def __init__(self, reply=None, exc=None):
        self.reply = reply
        self.exc = exc
        self.commands = []

    def execute_command(self, *args):
        self.commands.append(args)
        if self.exc:
            raise self.exc
        return self.reply


class TestRecallPriors:
    def test_no_terms_is_explicitly_degraded(self):
        result = recall_priors([])
        assert result.lessons == []
        assert result.degraded == "no-terms-extracted"

    def test_parses_search_reply_and_or_joins(self):
        reply = [
            2,
            "attune:memory:lesson:1",
            ["name", "mapping-trap", "description", "editable install maps to main"],
            "attune:memory:lesson:2",
            [b"name", b"stash-dance", b"description", b"pre-commit stash conflict"],
        ]
        client = _FakeRedis(reply=reply)
        result = recall_priors(["ValueError", "runner.py"], client=client)
        assert result.degraded is None
        assert result.lessons == [
            "mapping-trap — editable install maps to main",
            "stash-dance — pre-commit stash conflict",
        ]
        # OR-join, not AND-join (paraphrase-miss lesson)
        assert "ValueError|runner.py" in client.commands[0]

    def test_transport_failure_degrades_with_reason(self):
        client = _FakeRedis(exc=ConnectionError("refused"))
        result = recall_priors(["ValueError"], client=client)
        assert result.lessons == []
        assert result.degraded == "recall-failed: ConnectionError"


class TestEvidencePack:
    def test_fixed_order_and_kinds(self):
        entries = build_evidence_pack(
            _run(),
            log_tail="line1\nline2",
            source_excerpts={"b.py": "bbb", "a.py": "aaa"},
            git_context="abc123 fix",
        )
        assert [e.source for e in entries] == [
            "run-record",
            "log-tail",
            "source:a.py",
            "source:b.py",
            "git-log",
        ]
        assert all(e.kind == "observed" for e in entries)
        assert "run-1" in entries[0].content

    def test_budget_truncates_deterministically(self):
        entries = build_evidence_pack(
            _run(),
            log_tail="x" * 10_000,
            git_context="never-reached",
            budget_bytes=1_000,
        )
        assert entries[0].source == "run-record"  # highest value survives whole
        assert entries[1].source == "log-tail"
        assert "<TRUNCATED" in entries[1].content
        assert all(e.source != "git-log" for e in entries)  # dropped past budget

    def test_identical_inputs_identical_pack(self):
        kwargs = {"log_tail": "t", "source_excerpts": {"a.py": "a"}, "git_context": "g"}
        assert build_evidence_pack(_run(), **kwargs) == build_evidence_pack(_run(), **kwargs)


class TestOpsLogTail:
    def test_reads_persisted_ops_record(self, tmp_path):
        wf_dir = tmp_path / "code-review"
        wf_dir.mkdir(parents=True)
        (wf_dir / "abc123.json").write_text(
            json.dumps({"lines": [f"line-{i}" for i in range(60)]}), encoding="utf-8"
        )
        tail = ops_log_tail("abc123", ops_runs_dir=tmp_path)
        assert tail is not None
        assert "line-59" in tail and "line-10" not in tail  # last 40 only

    def test_missing_record_is_none(self, tmp_path):
        assert ops_log_tail("nope", ops_runs_dir=tmp_path) is None
