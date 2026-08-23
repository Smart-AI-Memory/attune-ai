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
