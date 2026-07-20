"""Triage tests (advanced-debugging-plugin T7) — selection exclusions,
clustering, digest honesty, and the manual-only binding.
"""

import json

from attune.diagnosis.config import DiagnosisConfig
from attune.diagnosis.triage import (
    cluster_by_hypothesis,
    render_digest,
    run_triage,
    select_failed_runs,
)
from attune.models.telemetry.data_models import DiagnosisHypothesis, DiagnosisRecord


def _run_line(run_id, *, success=False, trigger="manual"):
    return json.dumps(
        {
            "run_id": run_id,
            "workflow_name": "code-review",
            "started_at": "2026-07-20T12:00:00+00:00",
            "trigger": trigger,
            "project": "attune-ai",
            "success": success,
            "error": "boom",
        }
    )


def _diagnosis(diagnosis_id, source, statement):
    return DiagnosisRecord(
        diagnosis_id=diagnosis_id,
        source_run_id=source,
        workflow_name="code-review",
        created_at="2026-07-20T12:00:00+00:00",
        symptom="boom",
        hypotheses=[DiagnosisHypothesis(statement=statement, confidence="high")],
    )


class TestSelection:
    def test_excludes_heal_success_and_diagnosed(self, tmp_path):
        stream = tmp_path / "runs.jsonl"
        stream.write_text(
            "\n".join(
                [
                    _run_line("r-old"),
                    _run_line("r-ok", success=True),
                    _run_line("r-heal", trigger="attune-heal"),
                    _run_line("r-done"),
                    _run_line("r-new"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        selected = select_failed_runs(
            stream, limit=5, already_diagnosed=lambda rid: rid == "r-done"
        )
        assert [r.run_id for r in selected] == ["r-new", "r-old"]  # newest first

    def test_batch_cap_enforced(self, tmp_path):
        stream = tmp_path / "runs.jsonl"
        stream.write_text("\n".join(_run_line(f"r{i}") for i in range(10)) + "\n", encoding="utf-8")
        selected = select_failed_runs(stream, limit=3, already_diagnosed=lambda _: False)
        assert len(selected) == 3


class TestClustering:
    def test_material_agreement_groups_conflicts_stay_separate(self):
        a = _diagnosis("dA", "r1", "stale editable install MAPPING points at main")
        b = _diagnosis("dB", "r2", "editable install MAPPING stale, resolves main")
        c = _diagnosis("dC", "r3", "network timeout during subprocess spawn")
        clusters = cluster_by_hypothesis([a, b, c])
        assert [len(cl) for cl in clusters] == [2, 1]

    def test_digest_links_every_record_and_never_promotes(self):
        a = _diagnosis("dA", "r1", "stale mapping")
        digest = render_digest([[a]], selected=1)
        assert "dA" in digest and "r1" in digest
        assert "No promotion" in digest


class TestRunTriage:
    def test_stubbed_batch_produces_digest_without_board(self, tmp_path):
        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n" + _run_line("r2") + "\n", encoding="utf-8")
        calls = []

        def fake_diagnose(run_id, config):
            calls.append(run_id)
            return _diagnosis(f"d-{run_id}", run_id, f"cause of {run_id}")

        digest = run_triage(
            DiagnosisConfig(),
            stream=stream,
            diagnose_fn=fake_diagnose,
            post_to_board=False,
        )
        assert sorted(calls) == ["r1", "r2"]
        assert "d-r1" in digest and "d-r2" in digest

    def test_source_errors_skip_not_abort(self, tmp_path):
        from attune.diagnosis.engine import DiagnosisSourceError

        stream = tmp_path / "runs.jsonl"
        stream.write_text(_run_line("r1") + "\n" + _run_line("r2") + "\n", encoding="utf-8")

        def flaky_diagnose(run_id, config):
            if run_id == "r2":
                raise DiagnosisSourceError("gone")
            return _diagnosis("d-r1", run_id, "cause")

        digest = run_triage(
            DiagnosisConfig(), stream=stream, diagnose_fn=flaky_diagnose, post_to_board=False
        )
        assert "d-r1" in digest and "1 run(s) diagnosed" in digest


class TestManualOnlyBinding:
    def test_not_registered_as_a_schedulable_routine(self):
        from attune.roundtable.routine import ROUTINES

        assert "failed-run-triage" not in ROUTINES  # 2-1 binding: manual only
