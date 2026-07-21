"""Tests for self-healing traps (spec: docs/specs/self-healing-traps/).

Includes the R5 non-mocked round trip: real failing output → real
extraction → real PII gate → real FileStashBackend write → real recall.
"""

from pathlib import Path

from attune.memory.file_stash import FileStashBackend
from attune.memory.session_stash import recall_entries
from attune.telemetry.lessons import (
    extract_trap,
    format_trap,
    process_bash_result,
)

PRECOMMIT_FAILURE = """\
black....................................................................Failed
- hook id: black
- files were modified by this hook

reformatted src/attune/example.py

ruff.....................................................................Passed
- hook id: ruff
- duration: 0.12s
"""

PRECOMMIT_ALL_PASS = """\
black....................................................................Passed
- hook id: black
- duration: 0.30s
trim trailing whitespace.................................................Passed
"""

PYTEST_FAILURE = """\
=================================== FAILURES ===================================
______________________________ test_zone_2_routing _____________________________
AssertionError: assert 'zone_1' == 'zone_2'
=========================== short test summary info ============================
FAILED tests/unit/orchestration/test_friction_matrix.py::TestFrictionMatrix::test_zone_2_routing
============================== 1 failed, 25 passed in 0.53s ====================
"""

PYTEST_GREEN = """\
...........                                                              [100%]
11 passed in 1.24s
"""


class TestExtractTrap:
    """Deterministic signature extraction."""

    def test_precommit_failure_extracted(self) -> None:
        event = extract_trap('git commit -m "x"', PRECOMMIT_FAILURE)
        assert event is not None
        assert event.family == "precommit_rejection"
        assert event.signature == "precommit:black"
        assert "black" in event.detail

    def test_passing_hooks_with_hook_id_lines_do_not_trap(self) -> None:
        # "- hook id:" also appears in passing duration output.
        assert extract_trap('git commit -m "x"', PRECOMMIT_ALL_PASS) is None

    def test_precommit_pattern_requires_commit_command(self) -> None:
        assert extract_trap("ls -la", PRECOMMIT_FAILURE) is None

    def test_pytest_failure_extracted(self) -> None:
        event = extract_trap("pytest tests/unit -q", PYTEST_FAILURE)
        assert event is not None
        assert event.family == "pytest_failure"
        assert event.signature.startswith("pytest:")
        assert "test_zone_2_routing" in event.detail
        assert "1 failed, 25 passed" in event.detail

    def test_pytest_signature_stable_for_same_failures(self) -> None:
        a = extract_trap("pytest -q", PYTEST_FAILURE)
        b = extract_trap("pytest tests/unit -q", PYTEST_FAILURE)
        assert a is not None and b is not None
        assert a.signature == b.signature  # command doesn't change identity

    def test_green_run_no_trap(self) -> None:
        assert extract_trap("pytest tests/unit -q", PYTEST_GREEN) is None

    def test_failed_text_without_pytest_tail_no_trap(self) -> None:
        assert extract_trap("cat log.txt", "FAILED to reach server\n") is None

    def test_empty_inputs(self) -> None:
        assert extract_trap("", PYTEST_FAILURE) is None
        assert extract_trap("pytest", "") is None


class TestFormatTrap:
    """Stash-description formatting."""

    def test_factual_no_boilerplate(self) -> None:
        event = extract_trap('git commit -m "x"', PRECOMMIT_FAILURE)
        assert event is not None
        text = format_trap(event)
        assert text.startswith("Trap: pre-commit rejected the commit")
        assert "git commit" in text
        assert "Prevention" not in text  # no canned advice


class TestRoundTrip:
    """R5: non-mocked write→recall through a real file backend."""

    def test_trap_round_trips_through_real_backend(self, tmp_path: Path) -> None:
        backend = FileStashBackend(base_dir=tmp_path)

        signature = process_bash_result(
            command="pytest tests/unit -q",
            output=PYTEST_FAILURE,
            session_id="sess-rt-1",
            cwd=str(tmp_path),
            backend=backend,
        )
        assert signature is not None and signature.startswith("pytest:")
        assert (tmp_path / "findings.jsonl").exists()  # really on disk

        recalled = recall_entries("test_zone_2_routing failure", backend=backend, cwd=str(tmp_path))
        assert any("test_zone_2_routing" in str(r.get("text", "")) for r in recalled)

    def test_green_output_stashes_nothing(self, tmp_path: Path) -> None:
        backend = FileStashBackend(base_dir=tmp_path)
        assert (
            process_bash_result(
                command="pytest -q",
                output=PYTEST_GREEN,
                session_id="sess-rt-2",
                cwd=str(tmp_path),
                backend=backend,
            )
            is None
        )
