"""Phase A substrate tests (advanced-debugging-plugin T1/T2).

Covers the DiagnosisRecord schema, the canonical diagnosis stream,
loader purity rules, and the attune-heal trigger contract.
"""

import json
import os
from datetime import datetime, timezone

from attune.diagnosis.store import (
    DIAGNOSIS_CUTOVER,
    load_diagnoses,
    records_for_run,
)
from attune.models.telemetry.data_models import (
    DiagnosisEvidence,
    DiagnosisHypothesis,
    DiagnosisRecord,
)
from attune.models.telemetry.run_context import resolve_run_trigger
from attune.models.telemetry.storage import TelemetryStore

POST_CUTOVER = "2026-07-20T12:00:00+00:00"


def _record(**overrides) -> DiagnosisRecord:
    base = {
        "diagnosis_id": "d1",
        "source_run_id": "run-abc",
        "workflow_name": "code-review",
        "created_at": POST_CUTOVER,
    }
    base.update(overrides)
    return DiagnosisRecord(**base)


class TestSchema:
    def test_round_trip_preserves_nested_types(self):
        rec = _record(
            evidence=[DiagnosisEvidence(kind="prior", source="lesson:mapping-trap")],
            hypotheses=[DiagnosisHypothesis(statement="stale MAPPING", confidence="high")],
            config_used={"confidence_scale": ["low", "medium", "high"]},
        )
        restored = DiagnosisRecord.from_dict(json.loads(json.dumps(rec.to_dict())))
        assert restored == rec
        assert isinstance(restored.evidence[0], DiagnosisEvidence)
        assert isinstance(restored.hypotheses[0], DiagnosisHypothesis)

    def test_from_dict_tolerates_missing_fields(self):
        minimal = {
            "diagnosis_id": "d2",
            "source_run_id": "run-x",
            "workflow_name": "code-review",
            "created_at": POST_CUTOVER,
        }
        rec = DiagnosisRecord.from_dict(minimal)
        assert rec.status == "open"
        assert rec.evidence == [] and rec.priors_degraded is None

    def test_from_dict_drops_unknown_keys(self):
        data = _record().to_dict()
        data["from_the_future"] = {"schema_version": 2}
        assert DiagnosisRecord.from_dict(data).diagnosis_id == "d1"


class TestStore:
    def test_default_store_resolves_diagnoses_under_attune_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        store = TelemetryStore()
        assert store.diagnoses_file == (tmp_path / "home" / "telemetry" / "diagnosis_records.jsonl")

    def test_explicit_storage_dir_keeps_diagnoses_local(self, tmp_path):
        store = TelemetryStore(storage_dir=str(tmp_path / "iso"))
        assert store.diagnoses_file == tmp_path / "iso" / "diagnosis_records.jsonl"

    def test_suite_isolation_covers_diagnosis_stream(self, tmp_path):
        # The autouse ATTUNE_HOME fixture must redirect the third file
        # exactly like the run stream — a drift guard for RC-4 parity.
        store = TelemetryStore()
        assert os.environ.get("ATTUNE_HOME"), "suite must run with ATTUNE_HOME isolation"
        assert str(store.diagnoses_file).startswith(os.environ["ATTUNE_HOME"])

    def test_log_diagnosis_appends_and_rotates(self, tmp_path, monkeypatch):
        import attune.models.telemetry.storage as storage_mod

        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        monkeypatch.chdir(tmp_path)
        store = TelemetryStore()
        store.log_diagnosis(_record())
        store.log_diagnosis(_record(diagnosis_id="d2"))
        lines = store.diagnoses_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

        # Shrink the rotation threshold: next write rotates history.
        monkeypatch.setattr(storage_mod, "_RUNS_ROTATE_BYTES", 1)
        store.log_diagnosis(_record(diagnosis_id="d3"))
        archive = list((store.diagnoses_file.parent / "archive").glob("diagnosis_records-*"))
        assert len(archive) == 1
        live = store.diagnoses_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(live) == 1  # fresh stream holds only the new record


class TestLoaderPurity:
    def test_drops_are_counted_never_silent(self, tmp_path):
        stream = tmp_path / "diagnosis_records.jsonl"
        good = _record().to_dict()
        fixture = _record(diagnosis_id="dF", workflow_name="stub-workflow").to_dict()
        pre_cutover = _record(diagnosis_id="dP", created_at="2026-07-01T00:00:00+00:00").to_dict()
        lines = [json.dumps(good), "not-json{", json.dumps(fixture), json.dumps(pre_cutover)]
        stream.write_text("\n".join(lines) + "\n", encoding="utf-8")

        records, stats = load_diagnoses(stream)
        assert [r.diagnosis_id for r in records] == ["d1"]
        assert stats.total_lines == 4
        assert stats.eligible == 1
        assert stats.dropped_malformed == 1
        assert stats.dropped_fixture == 1
        assert stats.dropped_pre_cutover == 1

    def test_records_for_run_filters_by_source(self, tmp_path):
        stream = tmp_path / "diagnosis_records.jsonl"
        a = _record(diagnosis_id="dA", source_run_id="run-a").to_dict()
        b = _record(diagnosis_id="dB", source_run_id="run-b").to_dict()
        stream.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n", encoding="utf-8")
        found = records_for_run("run-b", stream)
        assert [r.diagnosis_id for r in found] == ["dB"]

    def test_missing_stream_is_empty_not_error(self, tmp_path):
        records, stats = load_diagnoses(tmp_path / "absent.jsonl")
        assert records == [] and stats.total_lines == 0

    def test_cutover_is_pinned_post_run_corpus(self):
        from attune.pipeline_learner.corpus import CUTOVER

        assert DIAGNOSIS_CUTOVER >= CUTOVER  # diagnosis purity postdates corpus purity


class TestAttuneHealTrigger:
    def test_resolver_accepts_attune_heal(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_TRIGGER", "attune-heal")
        assert resolve_run_trigger() == "attune-heal"

    def test_resolver_still_rejects_junk(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_RUN_TRIGGER", "attune-healing")
        assert resolve_run_trigger() == "manual"

    def test_corpus_excludes_attune_heal_with_counter(self, tmp_path):
        from attune.pipeline_learner.corpus import load_corpus

        stream = tmp_path / "workflow_runs.jsonl"
        base = {
            "workflow_name": "code-review",
            "started_at": POST_CUTOVER,
            "project": "attune-ai",
        }
        heal = {**base, "run_id": "r-heal", "trigger": "attune-heal"}
        manual = {**base, "run_id": "r-man", "trigger": "manual"}
        stream.write_text(json.dumps(heal) + "\n" + json.dumps(manual) + "\n", encoding="utf-8")
        records, stats = load_corpus("attune-ai", [stream])
        assert [r.run_id for r in records] == ["r-man"]
        assert stats.dropped_attune_heal == 1


# Keep DIAGNOSIS_CUTOVER honest if someone edits it to a naive datetime.
def test_cutover_is_timezone_aware():
    assert DIAGNOSIS_CUTOVER.tzinfo is not None
    assert DIAGNOSIS_CUTOVER > datetime(2026, 1, 1, tzinfo=timezone.utc)
