"""Tests for PatternScanSource against a known fixture.

The fixture lives in ``tests/fixtures/discovery_sweep/`` and
contains lines that hit each pattern the scanner looks for.
"""

from __future__ import annotations

import textwrap

import pytest

from attune.workflows.discovery_sweep.sources import PatternScanSource


@pytest.mark.asyncio
async def test_pattern_scan_finds_known_patterns(tmp_path) -> None:
    fixture = tmp_path / "demo.py"
    fixture.write_text(
        textwrap.dedent(
            """
            # eval/exec are obvious code-injection vectors:
            def run_eval(text):
                return eval(text)

            def run_exec(text):
                exec(text)

            def loose_handler():
                try:
                    1 / 0
                except:
                    pass

            def broad_handler():
                try:
                    1 / 0
                except Exception:
                    pass

            import subprocess
            def shell_call(cmd):
                subprocess.run(cmd, shell=True)

            # TODO: refactor this later
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    source = PatternScanSource()
    findings = await source.discover(str(tmp_path), budget_usd=0.0)

    pattern_ids = {f.raw["pattern_id"] for f in findings}
    assert {
        "bare_except",
        "broad_exception",
        "dangerous_eval",
        "dangerous_exec",
        "subprocess_shell_true",
        "incomplete_code",
    }.issubset(pattern_ids)

    # Every finding has a file + line (Rule 1 contract from verification.py).
    for f in findings:
        assert f.file is not None
        assert isinstance(f.line, int) and f.line >= 1
        assert f.source == "pattern-scan"


@pytest.mark.asyncio
async def test_pattern_scan_is_non_llm(tmp_path) -> None:
    source = PatternScanSource()
    assert source.is_llm is False


@pytest.mark.asyncio
async def test_pattern_scan_ignores_excluded_dirs(tmp_path) -> None:
    """`__pycache__` and `.venv` should not be scanned."""
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "vendored.py").write_text("eval('1')\n", encoding="utf-8")

    real = tmp_path / "real.py"
    real.write_text("def x():\n    return 1\n", encoding="utf-8")

    source = PatternScanSource()
    findings = await source.discover(str(tmp_path), budget_usd=0.0)
    assert all(".venv" not in (f.file or "") for f in findings)


@pytest.mark.asyncio
async def test_pattern_scan_handles_missing_path(tmp_path) -> None:
    source = PatternScanSource()
    findings = await source.discover(str(tmp_path / "does-not-exist"), budget_usd=0.0)
    assert findings == []
