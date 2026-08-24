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


def test_dependency_manifest_staged_without_confession(tmp_path) -> None:
    # 2026-08-24: staged verbatim, the fixture's "this is a planted
    # test fixture" header made the workflow's agents dismiss the
    # findings on some runs (observer effect). The staged copy must be
    # bare pins.
    runner._stage_dependency_manifest(tmp_path)
    staged = (tmp_path / "requirements.txt").read_text()
    assert "#" not in staged
    assert "requests==2.19.1" in staged
    assert "PyYAML==5.3.1" in staged


def test_dependency_probe_gates_on_named_class() -> None:
    # Named-class grammar: prose naming the planted package passes even
    # when the findings buckets came back empty (run-to-run variance);
    # no naming fails regardless of buckets.
    import asyncio

    class _Named:
        success = True
        error = None
        metadata = {
            "findings": {},
            "raw_result_text": "requests 2.19.1 is vulnerable (CVE-2018-18074).",
        }
        final_output = ""
        cost_report = None

    class _Silent(_Named):
        metadata = {
            "findings": {"dependencies": ["something unrelated"]},
            "raw_result_text": "all clear",
        }

    async def run_with(stub):
        original = runner._run_workflow
        runner._run_workflow = lambda name, **kw: _wrap(stub)
        try:
            return await runner.probe_dependency_check(1.0)
        finally:
            runner._run_workflow = original

    async def _wrap(v):
        return v

    named = asyncio.run(run_with(_Named()))
    assert named.passed, named.reason
    assert named.evidence["num_findings"] == 0  # count kept as evidence

    silent = asyncio.run(run_with(_Silent()))
    assert not silent.passed


def test_python_fixture_staged_without_confession(tmp_path) -> None:
    # Retro 2026-08-24 1.2: the python fixtures announce themselves
    # ("Planted-defect fixture", "SEEDED BUG") — same observer effect
    # as the dependency manifest. Staged copies drop the module
    # docstring and comment-only lines; code and inline noqa survive.
    src = FIXTURES / "security" / "vulnerable_service.py"
    dst = tmp_path / "vulnerable_service.py"
    runner._stage_python_fixture(src, dst)
    staged = dst.read_text()
    assert "Planted-defect fixture" not in staged
    assert "SEEDED BUG" not in staged
    assert runner._EVAL_TOKEN in staged  # the defect itself survives
    assert runner._KEY_MARKER in staged
    compile(staged, str(dst), "exec")  # still valid python

    # The analytical fixture exercises the trailing-comment shape
    # (a confession riding the summarize() def line itself).
    src2 = FIXTURES / "analytical" / "sample_service.py"
    dst2 = dst.parent / "sample_service.py"
    runner._stage_python_fixture(src2, dst2)
    staged2 = dst2.read_text()
    assert "SEEDED BUG" not in staged2
    assert "planted defect" not in staged2
    assert "def summarize(items):" in staged2  # code survives its confession
    assert "def find_duplicates" in staged2
    compile(staged2, str(dst2), "exec")


def test_security_probe_gates_on_named_class() -> None:
    # Retro 1.3: naming + non-perfect score is the gate; the bucket
    # count is evidence only.
    import asyncio

    class _NamedZeroBuckets:
        success = True
        error = None
        metadata = {
            "findings": {},
            "raw_result_text": (
                "Found dynamic eval of untrusted input (CWE-95, code "
                "injection) and a hardcoded credential / API key (CWE-798)."
            ),
        }
        final_output = {"score": 40}
        cost_report = None

    async def _wrap(v):
        return v

    original = runner._run_workflow
    runner._run_workflow = lambda name, **kw: _wrap(_NamedZeroBuckets())
    try:
        out = asyncio.run(runner.probe_security_audit(1.0))
    finally:
        runner._run_workflow = original
    assert out.passed, out.reason
    assert out.evidence["num_findings"] == 0


def test_records_carry_raw_head() -> None:
    # Retro 1.1: the dependency-check triage cost an extra billed run
    # because records persisted no report text; raw_head fixes that.
    class _R:
        success = True
        error = None
        metadata = {"findings": {}, "raw_result_text": "HEAD " + "x" * 5000}
        final_output = ""
        cost_report = None

    head = runner._head(_R())
    assert head.startswith("HEAD ")
    assert len(head) == 2048


def test_generative_probes_registered_and_costed() -> None:
    # D5 batch 3 — doc-gen and research-synthesis are wired into every
    # registration surface (a probe missing from one table silently
    # drops out of --all runs or records with no receipt type).
    for name in ("doc-gen", "research-synthesis"):
        assert name in runner.PROBES
        assert name in runner.PROBE_ORDER
        assert name in runner._EST_COST_USD
        assert name in runner._RECEIPT_TYPES


def test_research_fixture_carries_planted_tokens() -> None:
    arch = (FIXTURES / "research" / "architecture.md").read_text(encoding="utf-8")
    assert "QuorumLattice" in arch
    assert "heliotrope" in arch
    for fname in ("operations.md", "roadmap.md"):
        assert (FIXTURES / "research" / fname).exists()


def test_research_fixture_is_confession_free() -> None:
    # The corpus must read as a normal project doc set — a fixture that
    # announces itself lets the agent discount the planted fact (the
    # dependency-check observer effect, 2026-08-24).
    for doc in (FIXTURES / "research").glob("*.md"):
        text = doc.read_text(encoding="utf-8").lower()
        for marker in ("fixture", "planted", "probe", "synthetic"):
            assert marker not in text, f"{doc.name} confesses: {marker!r}"


def test_fence_to_script_repl_and_plain() -> None:
    plain = "import orders\nprint(orders.order_total([1.0]))\n"
    assert runner._fence_to_script(plain) == plain
    repl = ">>> import orders\n>>> orders.order_total([1.0])\n1.0\n"
    out = runner._fence_to_script(repl).splitlines()
    assert "import orders" in out
    assert "orders.order_total([1.0])" in out
    assert "1.0" not in out  # illustrative output line dropped


def test_harden_expected_raises_pins_the_live_false_positive() -> None:
    # The exact line from the first live doc-gen run (2026-08-24): a
    # CORRECT example demonstrating the documented exception, which the
    # naive executor flagged as a workflow failure. The hardened script
    # must exit 0 on it.
    import subprocess as sp
    import sys as _sys
    import tempfile as tf
    from pathlib import Path as P

    code = (
        "def order_total(prices, discount=0.0):\n"
        "    if not 0 <= discount <= 1:\n"
        "        raise ValueError('discount must be between 0 and 1')\n"
        "    return sum(prices) * (1 - discount)\n"
        "order_total([10.0], discount=1.5)        "
        "# raises ValueError: discount must be between 0 and 1\n"
    )
    hardened = runner._harden_expected_raises(code)
    with tf.TemporaryDirectory() as tmp:
        f = P(tmp) / "ex.py"
        f.write_text(hardened, encoding="utf-8")
        proc = sp.run([_sys.executable, str(f)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr


def test_harden_expected_raises_still_fails_on_broken_claims() -> None:
    # The assertion cuts both ways: a '# raises X' line that does NOT
    # raise, or raises something else, fails the example.
    import subprocess as sp
    import sys as _sys
    import tempfile as tf
    from pathlib import Path as P

    for bad in (
        "x = 1  # raises ValueError\n",  # never raises
        "int('a')  # raises KeyError\n",  # raises the WRONG exception
    ):
        hardened = runner._harden_expected_raises(bad)
        with tf.TemporaryDirectory() as tmp:
            f = P(tmp) / "ex.py"
            f.write_text(hardened, encoding="utf-8")
            proc = sp.run([_sys.executable, str(f)], capture_output=True, text=True, timeout=60)
        assert proc.returncode != 0, f"hardened script passed on: {bad!r}"


def test_harden_expected_raises_leaves_plain_lines_alone() -> None:
    plain = "import orders\nprint(orders.order_total([1.0]))\n"
    assert runner._harden_expected_raises(plain).splitlines() == plain.splitlines()


def test_docstring_section_fences_are_not_examples() -> None:
    # Calibration round 2 (2026-08-24 live run): the doc's API-reference
    # section renders Google-style docstring blocks in untagged fences
    # ("Args: ..."), which are prose, not examples — they must not parse
    # and must not be counted as executable examples.
    import ast as _ast

    docstring_block = (
        "Args:\n"
        "    prices: item prices for the orders module.\n"
        "    discount: fractional discount.\n"
    )
    script = runner._harden_expected_raises(runner._fence_to_script(docstring_block))
    try:
        _ast.parse(script)
        parsed = True
    except SyntaxError:
        parsed = False
    assert not parsed, "docstring section block unexpectedly parses as Python"

    real_example = "import orders\nprint(orders.order_total([1.0]))\n"
    _ast.parse(runner._harden_expected_raises(runner._fence_to_script(real_example)))


def test_probe_doc_gen_filters_and_executes_with_mocked_workflow() -> None:
    # Regression for the stripped-import NameError (2026-08-24: a $0
    # billed run died on `ast` because the helper tests never exercised
    # the probe's own fence-filter path). Mocked workflow, no LLM spend:
    # a docstring fence is skipped, the real example runs, probe passes.
    import asyncio

    class _R:
        success = True
        error = None
        metadata = {
            "raw_result_text": (
                "# Documentation\n"
                "order_total and classify_order are documented.\n"
                "```\nArgs:\n    prices: item prices for orders.\n```\n"
                "```python\n"
                "from orders import order_total\n"
                "print(order_total([1.0, 2.0]))\n"
                "```\n"
            )
        }
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    try:
        out = asyncio.run(runner.probe_doc_gen(1.0))
    finally:
        runner._run_workflow = original
    assert out.passed, out.reason
    assert out.evidence["examples_run"] == 1
    assert out.evidence["skipped_unparseable"] == 1


def test_fence_to_script_preserves_repl_body_indentation() -> None:
    # Codex D11 lane (medium): lstripping continuation lines destroyed
    # compound-statement indentation, making valid multiline REPL
    # examples unparseable (and thus silently skipped).
    import ast as _ast

    repl = (
        ">>> from orders import order_total\n"
        ">>> for prices in ([1.0], [2.0]):\n"
        "...     print(order_total(prices))\n"
        "1.0\n"
        "2.0\n"
    )
    script = runner._fence_to_script(repl)
    _ast.parse(script)  # must be valid Python — indentation intact
    assert "    print(order_total(prices))" in script.splitlines()


def test_python_tagged_broken_fence_fails_probe() -> None:
    # Codex D11 lane (high): a ```python fence claims to BE Python; a
    # parse failure there must FAIL the probe, not be skipped as prose —
    # otherwise one valid example masks broken ones.
    import asyncio

    class _R:
        success = True
        error = None
        metadata = {
            "raw_result_text": (
                "order_total and classify_order.\n"
                "```python\nfrom orders import order_total(\n```\n"
                "```python\nfrom orders import order_total\n"
                "print(order_total([1.0]))\n```\n"
            )
        }
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    try:
        out = asyncio.run(runner.probe_doc_gen(1.0))
    finally:
        runner._run_workflow = original
    assert not out.passed
    assert "do not parse" in out.reason


def test_emitted_examples_run_with_scrubbed_env() -> None:
    # Codex D11 lane (critical): LLM-emitted example code must not see
    # the runner's credentials. Canary in the runner env must be
    # invisible to the example subprocess.
    import asyncio
    import os as _os

    class _R:
        success = True
        error = None
        metadata = {
            "raw_result_text": (
                "order_total and classify_order.\n"
                "```python\n"
                "import os, sys\n"
                "sys.exit(1 if os.environ.get('PROBE_ENV_CANARY') else 0)\n"
                "# orders module env check\n"
                "```\n"
            )
        }
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    _os.environ["PROBE_ENV_CANARY"] = "leaked"
    try:
        out = asyncio.run(runner.probe_doc_gen(1.0))
    finally:
        runner._run_workflow = original
        del _os.environ["PROBE_ENV_CANARY"]
    assert out.passed, out.reason


# ---------------------------------------------------------------------------
# Session spend ledger enforcement (docs/specs/session-spend-ledger/)
# The hermetic ledger env comes from this directory's conftest.py.
# ---------------------------------------------------------------------------


def _fake_probe(cost: float, calls: list[str], name: str = "security-audit"):
    async def probe(budget: float):
        calls.append(name)
        return runner.ProbeResult(name=name, passed=True, reason="ok", cost_usd=cost)

    return probe


def test_run_selected_refuses_at_cap_without_launching(monkeypatch) -> None:
    """R2/R3: a probe at the (zero) cap never launches — hard refusal."""
    import asyncio

    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
    calls: list[str] = []
    monkeypatch.setitem(runner.PROBES, "security-audit", _fake_probe(1.0, calls))
    results, refusal = asyncio.run(runner._run_selected(["security-audit"], 1.0))
    assert results == []
    assert calls == []
    assert refusal and "no free first call" in refusal


def test_run_selected_records_actual_probe_cost(monkeypatch) -> None:
    import asyncio
    import json
    import os
    from pathlib import Path

    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "10")
    calls: list[str] = []
    monkeypatch.setitem(runner.PROBES, "security-audit", _fake_probe(1.5, calls))
    results, refusal = asyncio.run(runner._run_selected(["security-audit"], 1.0))
    assert refusal is None and len(results) == 1
    ledger = Path(os.environ["ATTUNE_SESSION_LEDGER_PATH"])
    entries = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert entries[0]["label"] == "probe:security-audit"
    assert abs(entries[0]["cost_usd"] - 1.5) < 1e-9


def test_run_selected_mid_run_crossing_stops_later_probes(monkeypatch) -> None:
    """Crossing the cap mid-run keeps finished results and refuses the rest."""
    import asyncio

    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "2")
    calls: list[str] = []
    monkeypatch.setitem(runner.PROBES, "security-audit", _fake_probe(2.5, calls))
    monkeypatch.setitem(runner.PROBES, "test-gen", _fake_probe(0.5, calls, name="test-gen"))
    results, refusal = asyncio.run(runner._run_selected(["security-audit", "test-gen"], 1.0))
    assert [r.name for r in results] == ["security-audit"]
    assert calls == ["security-audit"]
    assert refusal and "already spent" in refusal


def test_main_exits_2_on_session_refusal(monkeypatch, capsys) -> None:
    """Exit 2 (refused) is distinct from 1 (a probe ran and failed)."""

    async def fake_selected(selected, budget):
        return [], "cap reached"

    monkeypatch.setattr(runner, "_run_selected", fake_selected)
    code = runner.main(["--run", "security-audit", "--no-record"])
    assert code == 2
    assert "SESSION SPEND CAP" in capsys.readouterr().err


def test_run_selected_crashed_probe_records_the_budget_cap(monkeypatch) -> None:
    """D11 lane finding: a probe that crashes mid-workflow may have
    billed before raising; recording $0 would let real spend escape
    the cap. The conservative bound is the per-run budget."""
    import asyncio
    import json
    import os
    from pathlib import Path

    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "10")

    async def crasher(budget: float):
        raise ValueError("boom mid-workflow")

    monkeypatch.setitem(runner.PROBES, "security-audit", crasher)
    results, refusal = asyncio.run(runner._run_selected(["security-audit"], 3.0))
    assert refusal is None
    assert len(results) == 1 and not results[0].passed
    ledger = Path(os.environ["ATTUNE_SESSION_LEDGER_PATH"])
    entries = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert entries[0]["cost_usd"] == 3.0


def test_emitted_tests_run_with_scrubbed_env_files_on_disk() -> None:
    # Codex D11 lane on #2273 (critical), same class as probe_doc_gen's
    # scrub: LLM-emitted test code must not see the runner's
    # credentials. A canary in the runner env must be invisible to the
    # pytest subprocess — the staged test FAILS if it can read it, so
    # a leak fails this test via out.passed.
    import asyncio
    import os as _os
    from pathlib import Path as _Path

    class _R:
        success = True
        error = None
        metadata: dict = {}
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        gen = _Path(kwargs["path"]) / "tests" / "generated"
        gen.mkdir(parents=True)
        (gen / "test_probe_canary.py").write_text(
            "import os\n\n"
            "def test_env_scrubbed():\n"
            "    assert os.environ.get('PROBE_ENV_CANARY') is None\n",
            encoding="utf-8",
        )
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    _os.environ["PROBE_ENV_CANARY"] = "leaked"
    try:
        out = asyncio.run(runner.probe_test_gen(1.0))
    finally:
        runner._run_workflow = original
        del _os.environ["PROBE_ENV_CANARY"]
    assert out.passed, out.reason
    assert out.evidence["files_written"] == 1


def test_emitted_tests_run_with_scrubbed_env_report_fence() -> None:
    # Same canary for the fallback path: fence-extracted test code is
    # executed with the scrubbed env too.
    import asyncio
    import os as _os

    class _R:
        success = True
        error = None
        metadata = {
            "raw_result_text": (
                "```python\n"
                "import os\n\n"
                "def test_env_scrubbed():\n"
                "    assert os.environ.get('PROBE_ENV_CANARY') is None\n"
                "```\n"
            )
        }
        final_output = "x"
        cost_report = None
        summary = ""

    async def fake_run(name, **kwargs):
        return _R()

    original = runner._run_workflow
    runner._run_workflow = fake_run
    _os.environ["PROBE_ENV_CANARY"] = "leaked"
    try:
        out = asyncio.run(runner.probe_test_gen(1.0))
    finally:
        runner._run_workflow = original
        del _os.environ["PROBE_ENV_CANARY"]
    assert out.passed, out.reason
    assert out.evidence["files_written"] == 0
