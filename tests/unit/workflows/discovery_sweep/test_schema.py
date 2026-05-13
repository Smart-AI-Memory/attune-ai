"""Tests for the discovery-sweep schema and serialization layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from attune.workflows.discovery_sweep import (
    Finding,
    ResolutionComplexity,
    Severity,
    VerificationStatus,
    read_jsonl,
    write_jsonl,
    write_questions_markdown,
)
from attune.workflows.discovery_sweep.schema import _new_sweep_id


def _make_finding(
    *,
    status: VerificationStatus = VerificationStatus.UNSURE,
    complexity: ResolutionComplexity | None = None,
    reasoning: str = "",
    sweep_id: str = "sweep1234abcd",
) -> Finding:
    return Finding(
        source_workflow="bug_predict",
        file_path="src/attune/example.py",
        severity=Severity.MEDIUM,
        message="Example finding message.",
        raw_finding={"pattern": "example_pattern", "score": 0.7},
        sweep_id=sweep_id,
        line=42,
        verification_status=status,
        verification_reasoning=reasoning,
        resolution_complexity=complexity,
    )


class TestFindingRoundTrip:
    def test_roundtrip_minimal_finding(self):
        original = _make_finding()
        roundtripped = Finding.from_jsonl_dict(original.to_jsonl_dict())
        assert roundtripped == original

    def test_roundtrip_accepted_finding_with_complexity(self):
        original = _make_finding(
            status=VerificationStatus.ACCEPT,
            complexity=ResolutionComplexity.NEEDS_PATRICK,
            reasoning="touches src/attune/security/",
        )
        roundtripped = Finding.from_jsonl_dict(original.to_jsonl_dict())
        assert roundtripped == original
        assert roundtripped.resolution_complexity == ResolutionComplexity.NEEDS_PATRICK

    def test_roundtrip_rejected_finding(self):
        original = _make_finding(
            status=VerificationStatus.REJECT,
            reasoning="dirs[:] pattern in os.walk loop — see CLAUDE.md",
        )
        roundtripped = Finding.from_jsonl_dict(original.to_jsonl_dict())
        assert roundtripped == original

    def test_jsonl_dict_has_string_enum_values(self):
        finding = _make_finding(
            status=VerificationStatus.ACCEPT,
            complexity=ResolutionComplexity.ROUTINE,
        )
        payload = finding.to_jsonl_dict()
        assert payload["severity"] == "medium"
        assert payload["verification_status"] == "accept"
        assert payload["resolution_complexity"] == "routine"

    def test_jsonl_dict_serializes_to_json(self):
        finding = _make_finding()
        payload = finding.to_jsonl_dict()
        serialized = json.dumps(payload)
        deserialized = json.loads(serialized)
        roundtripped = Finding.from_jsonl_dict(deserialized)
        assert roundtripped == finding

    def test_resolution_complexity_none_roundtrips(self):
        original = _make_finding(status=VerificationStatus.UNSURE, complexity=None)
        roundtripped = Finding.from_jsonl_dict(original.to_jsonl_dict())
        assert roundtripped.resolution_complexity is None


class TestTimestamps:
    def test_default_timestamp_is_utc_aware(self):
        finding = _make_finding()
        parsed = datetime.fromisoformat(finding.timestamp_utc)
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timezone.utc.utcoffset(None)

    def test_no_naive_z_suffix(self):
        finding = _make_finding()
        assert not finding.timestamp_utc.endswith("Z+00:00")
        assert not finding.timestamp_utc.endswith("+00:00Z")


class TestSweepId:
    def test_sweep_id_is_hex_short(self):
        sweep_id = _new_sweep_id()
        assert len(sweep_id) == 12
        int(sweep_id, 16)

    def test_sweep_ids_are_unique(self):
        ids = {_new_sweep_id() for _ in range(50)}
        assert len(ids) == 50


class TestWriteReadJsonl:
    def test_roundtrip_jsonl_file(self, tmp_path):
        sweep_id = "abc123def456"
        findings = [
            _make_finding(
                status=VerificationStatus.ACCEPT,
                complexity=ResolutionComplexity.ROUTINE,
                sweep_id=sweep_id,
            ),
            _make_finding(
                status=VerificationStatus.ACCEPT,
                complexity=ResolutionComplexity.NEEDS_PATRICK,
                reasoning="cross-cutting",
                sweep_id=sweep_id,
            ),
        ]
        target = tmp_path / "queue.jsonl"
        write_jsonl(target, findings)
        assert target.exists()
        roundtripped = read_jsonl(target)
        assert roundtripped == findings

    def test_write_jsonl_creates_parent_dirs(self, tmp_path):
        target = tmp_path / "nested" / "deeper" / "queue.jsonl"
        findings = [_make_finding()]
        write_jsonl(target, findings)
        assert target.exists()

    def test_jsonl_one_finding_per_line(self, tmp_path):
        target = tmp_path / "queue.jsonl"
        findings = [_make_finding() for _ in range(3)]
        write_jsonl(target, findings)
        lines = target.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        for line in lines:
            json.loads(line)

    def test_empty_findings_writes_empty_file(self, tmp_path):
        target = tmp_path / "queue.jsonl"
        write_jsonl(target, [])
        assert target.exists()
        assert target.read_text(encoding="utf-8") == ""


class TestQuestionsMarkdown:
    def test_writes_markdown_with_only_unsure_findings(self, tmp_path):
        accept = _make_finding(status=VerificationStatus.ACCEPT)
        reject = _make_finding(status=VerificationStatus.REJECT)
        unsure = _make_finding(
            status=VerificationStatus.UNSURE,
            reasoning="could not classify; ambiguous match",
        )

        target = tmp_path / "questions.md"
        write_questions_markdown(
            target,
            [accept, reject, unsure],
            sweep_id="sweep1234abcd",
            scope="src/attune/example/",
        )
        content = target.read_text(encoding="utf-8")
        assert "sweep1234abcd" in content
        assert "src/attune/example/" in content
        assert "could not classify; ambiguous match" in content
        assert "## 1." in content
        assert "## 2." not in content

    def test_empty_unsure_writes_explicit_note(self, tmp_path):
        target = tmp_path / "questions.md"
        write_questions_markdown(target, [], sweep_id="sweep1234abcd", scope="src/")
        content = target.read_text(encoding="utf-8")
        assert "No UNSURE findings" in content

    def test_markdown_includes_raw_finding_json(self, tmp_path):
        unsure = _make_finding(status=VerificationStatus.UNSURE)
        target = tmp_path / "questions.md"
        write_questions_markdown(target, [unsure], sweep_id="sweep1234abcd", scope="src/")
        content = target.read_text(encoding="utf-8")
        assert "```json" in content
        assert '"pattern": "example_pattern"' in content

    def test_markdown_ends_with_newline(self, tmp_path):
        target = tmp_path / "questions.md"
        write_questions_markdown(target, [], sweep_id="sweep1234abcd", scope="src/")
        content = target.read_text(encoding="utf-8")
        assert content.endswith("\n")


class TestSweepIdConsistencyAcrossFiles:
    def test_same_sweep_id_in_all_three_files(self, tmp_path):
        sweep_id = "feedfacecafe"
        scope = "src/attune/security/"
        accept = _make_finding(
            status=VerificationStatus.ACCEPT,
            complexity=ResolutionComplexity.NEEDS_PATRICK,
            sweep_id=sweep_id,
        )
        reject = _make_finding(
            status=VerificationStatus.REJECT,
            reasoning="known false positive",
            sweep_id=sweep_id,
        )
        unsure = _make_finding(status=VerificationStatus.UNSURE, sweep_id=sweep_id)

        queue = tmp_path / f"{sweep_id}.jsonl"
        rejected = tmp_path / f"{sweep_id}.rejected.jsonl"
        questions = tmp_path / f"{sweep_id}.questions.md"

        write_jsonl(queue, [accept])
        write_jsonl(rejected, [reject])
        write_questions_markdown(questions, [unsure], sweep_id=sweep_id, scope=scope)

        assert all(p.exists() for p in (queue, rejected, questions))
        for finding in read_jsonl(queue):
            assert finding.sweep_id == sweep_id
        for finding in read_jsonl(rejected):
            assert finding.sweep_id == sweep_id
        assert sweep_id in questions.read_text(encoding="utf-8")
