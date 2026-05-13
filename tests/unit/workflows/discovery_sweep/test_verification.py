"""Verification rule engine + REJECT rules.

Each REJECT rule has a positive fixture (false-positive code
where the rule MUST fire) and a control fixture (real bug with
similar surface where the rule MUST NOT fire).

The control coverage is the regression net for the spec's
asymmetric-cost invariant: a false REJECT is worse than a false
ACCEPT, because REJECTed findings only land in the audit log.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep import (
    Finding,
    Severity,
    VerificationStatus,
)
from attune.workflows.discovery_sweep.rules import (
    DirsSliceAssignmentRule,
    IntentionalBroadExceptRule,
    JsRegexExecRule,
    SecretsPragmaRule,
    StructlogKwargsRule,
    SubprocessExecRule,
    SubprocessInFuzzTargetRule,
    WriteTextEvalFixtureRule,
    default_rules,
)
from attune.workflows.discovery_sweep.verification import VerificationEngine

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "false_positives"


def _find_line(path: Path, needle: str, *, skip_docstring: bool = True) -> int:
    """Return the 1-indexed line containing ``needle``.

    By default skips over lines that look like they live inside the
    module docstring (a common false match because fixtures often
    discuss the trigger pattern in their docstrings).
    """
    in_docstring = False
    docstring_marker = '"""'
    for idx, line in enumerate(path.read_text().splitlines(), start=1):
        if skip_docstring:
            triple_count = line.count(docstring_marker)
            if triple_count == 1:
                in_docstring = not in_docstring
                continue
            if triple_count >= 2:
                # Opens and closes on same line — skip.
                continue
            if in_docstring:
                continue
        if needle in line:
            return idx
    raise AssertionError(f"needle {needle!r} not found in {path}")


def _make_finding(
    *,
    file_path: Path,
    line: int,
    message: str,
    source_workflow: str = "bug_predict",
    severity: Severity = Severity.MEDIUM,
    pattern: str = "scanner",
    relative_to: Path | None = None,
) -> Finding:
    if relative_to is not None:
        try:
            stored_path = str(file_path.relative_to(relative_to))
        except ValueError:
            stored_path = str(file_path)
    else:
        stored_path = str(file_path)
    return Finding(
        source_workflow=source_workflow,
        file_path=stored_path,
        line=line,
        severity=severity,
        message=message,
        raw_finding={"pattern": pattern, "line": line},
        sweep_id="sweepfixture00",
    )


def _engine(rules: Iterable, project_root: Path | None = None) -> VerificationEngine:
    return VerificationEngine(list(rules), project_root=project_root)


# ---------------------------------------------------------------------------
# Rule 1: DirsSliceAssignmentRule
# ---------------------------------------------------------------------------


class TestDirsSliceAssignmentRule:
    fixture = FIXTURE_ROOT / "dirs_slice_assignment.py"
    control = FIXTURE_ROOT / "dirs_slice_assignment_control.py"

    def test_rejects_dirs_slice_inside_os_walk(self):
        line = _find_line(self.fixture, "dirs[:]")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="memory_leak: large_list_copy on dirs[:]",
        )
        verdict = _engine([DirsSliceAssignmentRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "os.walk" in verdict.verification_reasoning

    def test_does_not_fire_outside_os_walk(self):
        line = _find_line(self.control, "dirs[:]")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="memory_leak: large_list_copy on dirs[:]",
        )
        verdict = _engine([DirsSliceAssignmentRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE

    def test_does_not_fire_on_unrelated_message(self):
        line = _find_line(self.fixture, "dirs[:]")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="style: prefer list comprehension",
        )
        verdict = _engine([DirsSliceAssignmentRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 2: SubprocessExecRule
# ---------------------------------------------------------------------------


class TestSubprocessExecRule:
    fixture = FIXTURE_ROOT / "subprocess_exec.py"
    control = FIXTURE_ROOT / "subprocess_exec_control.py"

    def test_rejects_create_subprocess_exec(self):
        line = _find_line(self.fixture, "create_subprocess_exec")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="dangerous_eval: exec usage detected",
        )
        verdict = _engine([SubprocessExecRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "asyncio" in verdict.verification_reasoning.lower()

    def test_does_not_fire_on_real_eval(self):
        line = _find_line(self.control, "eval(expr)")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="dangerous_eval: eval(",
        )
        verdict = _engine([SubprocessExecRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 3: JsRegexExecRule
# ---------------------------------------------------------------------------


class TestJsRegexExecRule:
    fixture = FIXTURE_ROOT / "js_regex_exec.js"
    control = FIXTURE_ROOT / "js_regex_exec_control.js"

    def test_rejects_js_regex_exec(self):
        line = _find_line(self.fixture, "pattern.exec(")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="dangerous_eval: exec usage",
        )
        verdict = _engine([JsRegexExecRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "regex" in verdict.verification_reasoning.lower()

    def test_does_not_fire_on_real_js_eval(self):
        line = _find_line(self.control, "eval(userInput)")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="dangerous_eval: eval(",
        )
        verdict = _engine([JsRegexExecRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE

    def test_does_not_fire_on_python_file(self):
        # Same .exec() pattern but in a .py file — rule must skip.
        finding = _make_finding(
            file_path=FIXTURE_ROOT / "subprocess_exec.py",
            line=1,
            message="dangerous_eval: exec usage",
        )
        verdict = _engine([JsRegexExecRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 4: WriteTextEvalFixtureRule
# ---------------------------------------------------------------------------


class TestWriteTextEvalFixtureRule:
    fixture = FIXTURE_ROOT / "write_text_eval_fixture.py"
    control = FIXTURE_ROOT / "write_text_eval_fixture_control.py"

    def test_rejects_eval_inside_write_text(self):
        # eval lives inside the .write_text(...) string literal —
        # turn off the docstring skip so the heuristic doesn't
        # treat that triple-quoted block as a docstring.
        line = _find_line(self.fixture, "return eval(code)", skip_docstring=False)
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="dangerous_eval: eval( call",
        )
        verdict = _engine([WriteTextEvalFixtureRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "write_text" in verdict.verification_reasoning.lower()

    def test_does_not_fire_on_real_eval_outside_write_text(self):
        line = _find_line(self.control, "return eval(expr)")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="dangerous_eval: eval( call",
        )
        verdict = _engine([WriteTextEvalFixtureRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 5: IntentionalBroadExceptRule
# ---------------------------------------------------------------------------


class TestIntentionalBroadExceptRule:
    fixture = FIXTURE_ROOT / "intentional_broad_except.py"
    control = FIXTURE_ROOT / "intentional_broad_except_control.py"

    def test_rejects_intentional_broad_except(self):
        line = _find_line(self.fixture, "except Exception:  # noqa: BLE001")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="broad_exception: BLE001 blind exception",
        )
        verdict = _engine([IntentionalBroadExceptRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "intentional" in verdict.verification_reasoning.lower()

    def test_does_not_fire_without_noqa_and_marker(self):
        line = _find_line(self.control, "except Exception")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="broad_exception: BLE001 blind exception",
        )
        verdict = _engine([IntentionalBroadExceptRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 6: SubprocessInFuzzTargetRule
# ---------------------------------------------------------------------------


class TestSubprocessInFuzzTargetRule:
    fixture = FIXTURE_ROOT / "fuzz_target.py"
    control = FIXTURE_ROOT / "normal_subprocess_control.py"

    def test_rejects_subprocess_in_fuzz_path(self, tmp_path):
        # Copy the fixture into a path containing /fuzz_ so the rule's
        # path heuristic engages.
        target_dir = tmp_path / "fuzz_targets"
        target_dir.mkdir()
        target = target_dir / "fuzz_demo.py"
        target.write_text(self.fixture.read_text())
        line = _find_line(target, "subprocess.run(")
        finding = _make_finding(
            file_path=target,
            line=line,
            message="subprocess B603: subprocess without shell injection mitigation",
        )
        verdict = _engine([SubprocessInFuzzTargetRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "fuzz" in verdict.verification_reasoning.lower()

    def test_does_not_fire_on_normal_path(self):
        line = _find_line(self.control, "subprocess.call(cmd, shell=True)")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="subprocess shell injection B602 shell=True",
        )
        verdict = _engine([SubprocessInFuzzTargetRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 7: StructlogKwargsRule
# ---------------------------------------------------------------------------


class TestStructlogKwargsRule:
    fixture = FIXTURE_ROOT / "structlog_kwargs.py"
    control = FIXTURE_ROOT / "structlog_kwargs_control.py"

    def test_rejects_logger_kwargs_in_structlog_file(self):
        line = _find_line(self.fixture, 'logger.info("user.event"')
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="TypeError: logger.info got an unexpected keyword argument",
        )
        verdict = _engine([StructlogKwargsRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "structlog" in verdict.verification_reasoning.lower()

    def test_does_not_fire_in_stdlib_logging_file(self):
        line = _find_line(self.control, "logger.info(")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="TypeError: logger.info got an unexpected keyword argument",
        )
        verdict = _engine([StructlogKwargsRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Rule 8: SecretsPragmaRule
# ---------------------------------------------------------------------------


class TestSecretsPragmaRule:
    fixture = FIXTURE_ROOT / "secrets_pragma.py"
    control = FIXTURE_ROOT / "secrets_pragma_control.py"

    def test_rejects_pragma_allowlisted_line(self):
        line = _find_line(self.fixture, "pragma: allowlist secret")
        finding = _make_finding(
            file_path=self.fixture,
            line=line,
            message="hardcoded credential / api key detected",
        )
        verdict = _engine([SecretsPragmaRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT
        assert "pragma" in verdict.verification_reasoning.lower()

    def test_does_not_fire_without_pragma(self):
        line = _find_line(self.control, "LEAKED_API_KEY")
        finding = _make_finding(
            file_path=self.control,
            line=line,
            message="hardcoded credential / api key detected",
        )
        verdict = _engine([SecretsPragmaRule()]).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


class TestVerificationEngineIntegration:
    def test_unsure_when_no_rule_matches(self):
        finding = _make_finding(
            file_path=FIXTURE_ROOT / "dirs_slice_assignment.py",
            line=1,
            message="totally unfamiliar message",
        )
        verdict = _engine(default_rules()).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE
        assert "no verification rule fired" in verdict.verification_reasoning

    def test_engine_reads_source_only_once_per_path(self):
        engine = _engine(default_rules())
        line = _find_line(FIXTURE_ROOT / "dirs_slice_assignment.py", "dirs[:]")
        finding = _make_finding(
            file_path=FIXTURE_ROOT / "dirs_slice_assignment.py",
            line=line,
            message="memory_leak: large_list_copy",
        )
        engine.classify(finding)
        # Second call should hit the cache; assert the cache populated.
        cached = engine._source_cache.get(str(FIXTURE_ROOT / "dirs_slice_assignment.py"))
        assert cached is not None
        assert len(cached) > 0

    def test_missing_source_file_falls_through_to_unsure(self):
        finding = _make_finding(
            file_path=Path("/nonexistent/path/to/file.py"),
            line=1,
            message="memory_leak: large_list_copy on dirs[:]",
        )
        verdict = _engine(default_rules()).classify(finding)
        assert verdict.verification_status == VerificationStatus.UNSURE

    def test_buggy_rule_does_not_abort_sweep(self):
        class BuggyRule:
            name = "buggy"

            def classify(self, finding, source_lines):
                raise RuntimeError("rule blew up")

        finding = _make_finding(
            file_path=FIXTURE_ROOT / "dirs_slice_assignment.py",
            line=_find_line(FIXTURE_ROOT / "dirs_slice_assignment.py", "dirs[:]"),
            message="memory_leak: large_list_copy",
        )
        engine = _engine([BuggyRule(), DirsSliceAssignmentRule()])
        verdict = engine.classify(finding)
        # Despite the buggy rule, the next rule still fires.
        assert verdict.verification_status == VerificationStatus.REJECT

    def test_classify_many(self):
        line = _find_line(FIXTURE_ROOT / "dirs_slice_assignment.py", "dirs[:]")
        good = _make_finding(
            file_path=FIXTURE_ROOT / "dirs_slice_assignment.py",
            line=line,
            message="memory_leak: large_list_copy",
        )
        unknown = _make_finding(
            file_path=FIXTURE_ROOT / "dirs_slice_assignment.py",
            line=1,
            message="totally unknown",
        )
        verdicts = _engine(default_rules()).classify_many([good, unknown])
        assert verdicts[0].verification_status == VerificationStatus.REJECT
        assert verdicts[1].verification_status == VerificationStatus.UNSURE

    def test_relative_paths_resolved_against_project_root(self, tmp_path):
        target_dir = tmp_path / "src"
        target_dir.mkdir()
        target_file = target_dir / "thing.py"
        target_file.write_text((FIXTURE_ROOT / "dirs_slice_assignment.py").read_text())

        line = _find_line(target_file, "dirs[:]")
        finding = _make_finding(
            file_path=target_file,
            line=line,
            relative_to=tmp_path,
            message="memory_leak: large_list_copy",
        )
        # finding.file_path is now "src/thing.py" — relative.
        assert not Path(finding.file_path).is_absolute()
        verdict = _engine(default_rules(), project_root=tmp_path).classify(finding)
        assert verdict.verification_status == VerificationStatus.REJECT


@pytest.mark.parametrize(
    "rule_cls",
    [
        DirsSliceAssignmentRule,
        SubprocessExecRule,
        JsRegexExecRule,
        WriteTextEvalFixtureRule,
        IntentionalBroadExceptRule,
        SubprocessInFuzzTargetRule,
        StructlogKwargsRule,
        SecretsPragmaRule,
    ],
)
def test_rule_returns_none_on_missing_line(rule_cls):
    """Every rule must gracefully return None when line is missing."""
    rule = rule_cls()
    finding = _make_finding(
        file_path=Path("/tmp/fake.py"),
        line=None if False else 99999,
        message="something",
    )
    out = rule.classify(finding, source_lines=[])
    assert out is None
