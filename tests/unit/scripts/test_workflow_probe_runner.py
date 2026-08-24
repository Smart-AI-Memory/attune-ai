"""Free guards for the workflow probe runner + its fixtures.

These run on every push (no LLM spend). They keep the planted-defect
fixtures honest and pin the runner's fixture-validation contract, so a
later "cleanup" that removes a seeded defect fails CI instead of
silently turning a probe vacuous. The billed LLM probes themselves are
never run here — only via ``scripts/workflow_probe_runner.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "workflow_probe_runner.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "workflow_probes"


def _load_runner():
    spec = importlib.util.spec_from_file_location("workflow_probe_runner", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_fixtures_validate_clean() -> None:
    assert runner.validate_fixtures() == []


def test_security_fixture_still_carries_both_defects() -> None:
    text = (FIXTURES / "security" / "vulnerable_service.py").read_text()
    assert runner._EVAL_TOKEN in text, "the planted eval() defect vanished"
    assert runner._KEY_MARKER in text, "the planted fake key vanished"


def test_dependency_fixture_pins_known_cves() -> None:
    text = (FIXTURES / "dependency" / "cve_pins.txt").read_text()
    assert "requests==2.19.1" in text
    assert "PyYAML==5.3.1" in text


def test_dependency_fixture_is_not_a_requirements_file() -> None:
    # Named cve_pins.txt so dependabot / GitHub alerts never flag the
    # planted pins across the whole repo. The runner stages it AS
    # requirements.txt only inside the throwaway probe workdir.
    assert not (FIXTURES / "dependency" / "requirements.txt").exists()
    assert (FIXTURES / "dependency" / "cve_pins.txt").exists()


def test_testgen_fixture_has_target_and_no_tests() -> None:
    directory = FIXTURES / "testgen"
    files = {p.name for p in directory.iterdir()}
    assert "orders.py" in files
    assert not any(name.startswith("test_") or name.endswith("_test.py") for name in files)


def test_analytical_fixture_carries_all_planted_defects() -> None:
    text = (FIXTURES / "analytical" / "sample_service.py").read_text()
    # One marker per planted defect class the analytical probes assert.
    assert "def find_duplicates" in text  # perf O(n^2)
    assert "tags: list[str] = []" in text  # mutable default arg
    assert "def validate_label" in text  # duplication
    assert "def categorize" in text  # nested conditional
    assert "def summarize(items):" in text  # missing docstring


def test_analytical_probes_registered_and_costed() -> None:
    # Each analytical workflow is wired into PROBES, PROBE_ORDER, and has
    # a cost estimate — the same guard the batch relies on to not go
    # silently un-run.
    for name in runner._ANALYTICAL:
        assert name in runner.PROBES
        assert name in runner.PROBE_ORDER
        assert name in runner._EST_COST_USD


def test_analytical_probe_names_are_real_workflows() -> None:
    # The probe names must resolve to registered workflows, or a probe
    # errors at run time (verify-before-coding).
    from attune.workflows import get_workflow

    for name in runner._ANALYTICAL:
        assert get_workflow(name) is not None


def test_missing_fixture_is_reported() -> None:
    original = runner.FIXTURES
    try:
        runner.FIXTURES = Path("/nonexistent/workflow_probes")
        problems = runner.validate_fixtures()
        assert problems
        assert any("missing fixture" in p for p in problems)
    finally:
        runner.FIXTURES = original


def test_plan_mode_exits_zero_without_spending(capsys) -> None:
    # No --run / --all -> validate fixtures, print plan, exit 0. No probe
    # is invoked, so nothing is billed.
    rc = runner.main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ESTIMATED TOTAL" in out
    for name in runner.PROBE_ORDER:
        assert name in out


def test_unknown_probe_rejected() -> None:
    assert runner.main(["--run", "not-a-real-probe"]) == 1


def test_extract_test_code_keeps_only_test_blocks() -> None:
    text = (
        "prose\n"
        "```python\nimport os\nprint(os)\n```\n"
        "more\n"
        "```python\ndef test_thing():\n    assert True\n```\n"
    )
    code = runner._extract_test_code(text)
    assert "def test_thing" in code
    assert "print(os)" not in code


def test_every_probe_has_a_cost_estimate() -> None:
    for name in runner.PROBE_ORDER:
        assert name in runner._EST_COST_USD
        assert name in runner.PROBES


@pytest.mark.parametrize(
    "score,expected",
    [(None, None), (42, 42.0), (100, 100.0)],
)
def test_score_of_reads_report_dict(score, expected) -> None:
    class _R:
        final_output = {"score": score} if score is not None else {}

    assert runner._score_of(_R()) == expected


def test_total_findings_is_key_agnostic() -> None:
    # security-audit keys findings by SEVERITY, not category "security".
    # Counting one hard-coded key would read 0 here and go vacuous.
    class _R:
        metadata = {"findings": {"CRITICAL": ["a"], "HIGH": ["b", "c"], "LOW": []}}

    assert runner._total_findings(_R()) == 3
    # And the category-keyed shape still counts.

    class _R2:
        metadata = {"findings": {"dependencies": ["x", "y"]}}

    assert runner._total_findings(_R2()) == 2


def test_total_findings_zero_when_absent() -> None:
    class _R:
        metadata: dict = {}

    assert runner._total_findings(_R()) == 0


def test_analytical_receipt_is_named_class_not_count() -> None:
    # Live validation 2026-08-23: refactor-plan returned 0 structured
    # findings on one run and 44 on the next for the SAME fixture, while
    # naming the duplication both times. The analytical gate is the
    # NAMED CLASS (behavioral); the count is evidence only. This pins
    # that a zero-count result with the class named still PASSES, so a
    # later "tighten the assertion" doesn't reintroduce the flake.
    import asyncio

    class _R:
        success = True
        error = None
        metadata = {
            "findings": {},  # zero structured findings
            "raw_result_text": "The validate_ blocks are duplicated; refactor.",
        }
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    try:
        out = asyncio.run(runner._probe_analytical("refactor-plan", 1.0))
    finally:
        runner._run_workflow = original
    assert out.passed, out.reason
    assert out.evidence["num_findings"] == 0
    assert out.evidence["named_class"] is True


def test_crash_reason_none_on_success() -> None:
    class _R:
        success = True
        error = None
        metadata: dict = {}

    assert runner._crash_reason(_R()) is None


def test_crash_reason_distinguishes_crash_from_miss() -> None:
    # A workflow that ERRORED must be reported as a crash, never as an
    # analytical miss — that distinction is the point of the harness.
    class _R:
        success = False
        error = "Claude Code returned an error result: success\nmore lines"
        metadata = {"sdk_error_kind": "is_error_on_success"}

    reason = runner._crash_reason(_R())
    assert reason is not None
    assert "CRASHED before analysis" in reason
    assert "is_error_on_success" in reason
    # Only the first line of the error is carried, not the whole trace.
    assert "more lines" not in reason


def test_write_record_schema_and_verdicts(tmp_path) -> None:
    import json as _json

    cases = [
        (runner.ProbeResult("security-audit", True, "surfaced it", 0.5, 10.0), "pass"),
        (runner.ProbeResult("test-gen", False, "emitted no runnable test code", 0.6, 20.0), "fail"),
        (
            runner.ProbeResult(
                "perf-audit", False, "workflow CRASHED before analysis (not an analytical miss): x"
            ),
            "crash",
        ),
        (runner.ProbeResult("doc-audit", False, "probe raised ValueError: boom"), "crash"),
    ]
    for result, expected_verdict in cases:
        path = runner.write_record(
            result, tmp_path, ran_at="2026-08-23T21:20:00Z", git_sha="abc123def"
        )
        record = _json.loads(path.read_text())
        # Full design schema present.
        for key in (
            "workflow",
            "fixture",
            "receipt_type",
            "verdict",
            "cost_usd",
            "duration_s",
            "ran_at",
            "runner_version",
            "git_sha",
            "evidence",
        ):
            assert key in record, f"missing {key}"
        assert record["verdict"] == expected_verdict
        assert record["evidence"]["reason"] == result.reason


def test_write_record_is_append_only(tmp_path) -> None:
    # Same probe, same second: the second record must NOT clobber the
    # first (append-only record set — D7).
    first = runner.write_record(
        runner.ProbeResult("code-review", True, "ok", 0.1, 1.0),
        tmp_path,
        ran_at="2026-08-23T21:20:00Z",
        git_sha="abc",
    )
    second = runner.write_record(
        runner.ProbeResult("code-review", False, "different", 0.2, 2.0),
        tmp_path,
        ran_at="2026-08-23T21:20:00Z",
        git_sha="abc",
    )
    assert first != second
    assert first.exists() and second.exists()


def _with_gate_stub(result_obj, probe_coro_factory):
    """Run one gate probe with _run_gate_workflow stubbed to result_obj."""
    import asyncio

    async def fake(name, **kwargs):
        return result_obj

    original = runner._run_gate_workflow
    runner._run_gate_workflow = fake
    try:
        return asyncio.run(probe_coro_factory(1.0))
    finally:
        runner._run_gate_workflow = original


def test_secure_release_probe_fails_on_go() -> None:
    # The Sev1 shape: GO on a planted-critical fixture must FAIL the
    # probe; NO_GO and CONDITIONAL both pass (fail-closed).
    class _Go:
        go_no_go = "GO"
        total_cost = 1.0
        critical_count = 0
        high_count = 0
        blockers: list = []

    class _NoGo(_Go):
        go_no_go = "NO_GO"

    class _Cond(_Go):
        go_no_go = "CONDITIONAL"

    assert not _with_gate_stub(_Go(), runner.probe_secure_release).passed
    assert _with_gate_stub(_NoGo(), runner.probe_secure_release).passed
    assert _with_gate_stub(_Cond(), runner.probe_secure_release).passed


def test_health_check_probe_rejects_fabricated_perfection() -> None:
    # The Sev2 shape: a complete-looking grade with degraded=False on an
    # unmeasurable dir fails; degraded=True or grade N/A passes.
    class _Fabricated:
        degraded = False
        grade = "A"

        def to_dict(self):
            return {"score": 100, "total_cost": 0.0}

    class _Honest(_Fabricated):
        degraded = True
        grade = "C"

    class _NA(_Fabricated):
        degraded = False
        grade = "N/A"

    assert not _with_gate_stub(_Fabricated(), runner.probe_health_check).passed
    assert _with_gate_stub(_Honest(), runner.probe_health_check).passed
    assert _with_gate_stub(_NA(), runner.probe_health_check).passed


def test_doc_orchestrator_probe_rejects_fabricated_no_gaps() -> None:
    # The Sev5 shape: "scan found no gaps" (degraded=False, 0 items) on
    # a fixture WITH a planted doc gap fails; honest degraded or a scan
    # that found the gap passes.
    class _NoGaps:
        degraded = False
        items_found = 0
        total_cost = 0.0

    class _Degraded(_NoGaps):
        degraded = True

    class _Found(_NoGaps):
        items_found = 3

    assert not _with_gate_stub(_NoGaps(), runner.probe_doc_orchestrator).passed
    assert _with_gate_stub(_Degraded(), runner.probe_doc_orchestrator).passed
    assert _with_gate_stub(_Found(), runner.probe_doc_orchestrator).passed


def test_release_prep_probe_requires_honest_fail() -> None:
    # #2221 correction: release-prep's execute() returns success=True
    # even when BLOCKED — the verdict is metadata["approved"]. The
    # probe judges THAT key; a missing key is a phantom-read failure,
    # never a silent pass.
    class _Approved:
        success = True
        cost_report = None
        metadata = {"approved": True, "confidence": "high"}

    class _Blocked(_Approved):
        metadata = {"approved": False, "confidence": "low"}

    class _NoKey(_Approved):
        metadata = {"confidence": "high"}

    assert not _with_gate_stub(_Approved(), runner.probe_release_prep).passed
    assert _with_gate_stub(_Blocked(), runner.probe_release_prep).passed
    missing = _with_gate_stub(_NoKey(), runner.probe_release_prep)
    assert not missing.passed
    assert "approved" in missing.reason


def test_every_probe_has_a_receipt_type() -> None:
    # A probe without a receipt-type mapping would silently default;
    # keep the map total over the fleet of probes.
    for name in runner.PROBE_ORDER:
        assert name in runner._RECEIPT_TYPES


def test_run_flag_accepts_repeats_and_commas() -> None:
    # Retro 2026-08-24 item 3.3: repeated --run silently kept only the
    # last value (argparse default store); it now appends and flattens.
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="append", default=[])
    ns = parser.parse_args(["--run", "a,b", "--run", "c"])
    flat = [p.strip() for chunk in ns.run for p in chunk.split(",") if p.strip()]
    assert flat == ["a", "b", "c"]


def test_unknown_probe_rejected_with_repeated_flags() -> None:
    assert runner.main(["--run", "security-audit", "--run", "not-a-real-probe"]) == 1
