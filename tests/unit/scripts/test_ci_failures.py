"""scripts/ci_failures.py anchors on pytest's own result lines (retro 2026-09-06 R4).

The failure it exists to prevent: a substring grep for ``passed|failed``
over a job log matches test NAMES containing those words and reports
phantom failures. Every fixture here contains such names and asserts they
are never reported.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "ci_failures.py"


@pytest.fixture(scope="module")
def cf():
    spec = importlib.util.spec_from_file_location("_ci_failures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_ci_failures"] = module
    spec.loader.exec_module(module)
    return module


_PREFIX = "test (ubuntu-latest, 3.12)\tRun tests\t2026-09-06T05:28:22.9782634Z "

_GREEN_LOG = "\n".join(
    _PREFIX + line
    for line in [
        "tests/unit/x/test_a.py::test_prose_panel_failed_run_not_a_false_all_clear ",
        "[gw3] [ 23%] PASSED tests/unit/x/test_a.py::test_prose_panel_failed_run_not_a_false_all_clear ",
        "tests/unit/x/test_b.py::test_default_days_passed_to_tracker ",
        "[gw1] [ 24%] PASSED tests/unit/x/test_b.py::test_default_days_passed_to_tracker ",
        "====== 8885 passed, 46 skipped, 3 xfailed in 201.18s (0:03:21) ======",
    ]
)

_RED_LOG = "\n".join(
    _PREFIX + line
    for line in [
        "[gw0] [ 10%] PASSED tests/unit/x/test_a.py::test_status_probe_error_falls_back_to_write_failed ",
        "FAILED tests/adaptive/test_task_complexity.py::test_complex_task_scoring - tests._inference_guard.InferenceBlocked: Inference HTTP endpoint blocked",
        "FAILED tests/models/test_token_estimator.py::TestEstimateTokens::test_claude_model - tests._inference_guard.InferenceBlocked: Inference HTTP endpoint blocked",
        "FAILED tests/adaptive/test_task_complexity.py::test_complex_task_scoring - duplicate line in the short summary",
        "ERROR tests/integration/test_ams_remember_readback_live.py - tests._inference_guard.InferenceBlocked",
        "====== 40 failed, 8885 passed, 46 skipped, 3 xfailed in 257.35s (0:04:17) ======",
    ]
)

_INTERNAL_LOG = "\n".join(
    _PREFIX + line
    for line in [
        'INTERNALERROR>   File "D:\\a\\attune-ai\\tests\\_inference_guard.py", line 98, in check_command',
        "INTERNALERROR> TypeError: expected str, bytes or os.PathLike object, not NoneType",
    ]
)


def test_green_log_with_failure_like_names_reports_nothing(cf) -> None:
    report = cf.parse_log(_GREEN_LOG, "ubuntu")
    assert report.results == []
    assert report.red is False
    assert report.summary.startswith("8885 passed")


def test_red_log_lists_each_failed_node_once_with_its_reason(cf) -> None:
    report = cf.parse_log(_RED_LOG, "ubuntu")
    nodes = [node for _, node, _ in report.results]
    assert nodes == [
        "tests/adaptive/test_task_complexity.py::test_complex_task_scoring",
        "tests/models/test_token_estimator.py::TestEstimateTokens::test_claude_model",
        "tests/integration/test_ams_remember_readback_live.py",
    ]
    assert report.results[0][2].startswith("tests._inference_guard.InferenceBlocked")
    assert report.results[2][0] == "ERROR"
    assert "falls_back_to_write_failed" not in cf.render([report])
    assert report.red is True and report.summary.startswith("40 failed")


def test_internal_error_is_reported_even_without_a_summary(cf) -> None:
    report = cf.parse_log(_INTERNAL_LOG, "windows")
    assert report.results == []
    assert report.internal_errors == [
        "TypeError: expected str, bytes or os.PathLike object, not NoneType"
    ]
    assert report.red is True


def test_render_and_exit_code_from_a_saved_log(cf, tmp_path, capsys) -> None:
    log = tmp_path / "job.log"
    log.write_text(_RED_LOG, encoding="utf-8")
    assert cf.main(["--log", str(log)]) == 1
    out = capsys.readouterr().out
    assert out.startswith("## job.log\nsummary: 40 failed")
    assert out.count("FAILED ") == 2 and out.count("ERROR ") == 1
    log.write_text(_GREEN_LOG, encoding="utf-8")
    assert cf.main(["--log", str(log)]) == 0


def test_requires_a_run_id_or_a_log(cf) -> None:
    with pytest.raises(SystemExit):
        cf.main([])
