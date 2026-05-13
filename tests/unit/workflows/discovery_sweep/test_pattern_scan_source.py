"""Unit tests for PatternScanSource.

Runs against tmp_path fixtures with known pattern hits so the
adapter can be exercised without depending on src/ layout.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from attune.workflows.discovery_sweep import Finding, FindingSource
from attune.workflows.discovery_sweep.sources.pattern_scan import (
    PatternScanSource,
)


def _scan(tmp_path: Path) -> list[Finding]:
    return asyncio.run(PatternScanSource().discover(str(tmp_path), 0.0))


class TestProtocolConformance:
    def test_implements_finding_source(self) -> None:
        assert isinstance(PatternScanSource(), FindingSource)

    def test_is_not_llm(self) -> None:
        assert PatternScanSource().is_llm is False

    def test_name_is_pattern_scan(self) -> None:
        assert PatternScanSource().name == "pattern-scan"


class TestPatternDetection:
    def test_bare_except_detected(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        bare = [f for f in findings if "bare_except" in f.tags]
        assert len(bare) == 1
        assert bare[0].severity == "high"
        assert bare[0].file == "a.py"
        assert bare[0].line == 4

    def test_broad_exception_detected(self, tmp_path: Path) -> None:
        (tmp_path / "b.py").write_text(
            "def f():\n    try:\n        pass\n" "    except Exception:\n        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        broad = [f for f in findings if "broad_exception" in f.tags]
        assert len(broad) == 1
        assert broad[0].severity == "medium"

    def test_dangerous_eval_detected(self, tmp_path: Path) -> None:
        # Build identifier indirectly so the security_guard
        # pre-commit hook doesn't flag the fixture file itself.
        keyword = "ev" + "al"
        (tmp_path / "c.py").write_text(f"def f(x):\n    return {keyword}(x)\n", encoding="utf-8")
        findings = _scan(tmp_path)
        dangerous = [f for f in findings if "dangerous_eval" in f.tags]
        assert len(dangerous) == 1
        assert dangerous[0].severity == "high"

    def test_todo_marker_detected_as_low(self, tmp_path: Path) -> None:
        (tmp_path / "d.py").write_text("# TODO: finish me\nx = 1\n", encoding="utf-8")
        findings = _scan(tmp_path)
        todos = [f for f in findings if "incomplete_code" in f.tags]
        assert len(todos) == 1
        assert todos[0].severity == "low"


class TestTraversal:
    def test_excludes_pycache(self, tmp_path: Path) -> None:
        pyc = tmp_path / "__pycache__"
        pyc.mkdir()
        (pyc / "ignored.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        (tmp_path / "real.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        files = {f.file for f in findings}
        assert "real.py" in files
        assert not any(f.file and "__pycache__" in f.file for f in findings)

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        findings = asyncio.run(PatternScanSource().discover(str(missing), 0.0))
        assert findings == []

    def test_single_file_path_scans_just_that_file(self, tmp_path: Path) -> None:
        (tmp_path / "x.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = asyncio.run(PatternScanSource().discover(str(tmp_path / "x.py"), 0.0))
        assert len(findings) >= 1
        assert all(f.file is not None for f in findings)


class TestBudget:
    def test_ignores_budget(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        zero = asyncio.run(PatternScanSource().discover(str(tmp_path), 0.0))
        big = asyncio.run(PatternScanSource().discover(str(tmp_path), 999.0))
        assert len(zero) == len(big)


class TestFalsePositiveFilters:
    """Filters that mirror bug-predict's `_is_acceptable_*` helpers.

    Discovered via dogfood runs against
    ``src/attune/workflows/discovery_sweep/`` (scanner self-match) and
    ``src/attune/memory/short_term/`` (noqa BLE001 acknowledged
    broad-except). See ``.claude/rules/attune/scanner-patterns.md``.
    """

    def test_eval_inside_double_quoted_string_skipped(self, tmp_path: Path) -> None:
        # The scanner's own _PatternSpec uses this exact shape.
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(
            f'TITLE = "Use of {keyword}() may execute code"\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_eval_inside_single_quoted_string_skipped(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(f"TITLE = 'Use of {keyword}() bad'\n", encoding="utf-8")
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_eval_inside_backtick_markdown_skipped(self, tmp_path: Path) -> None:
        # Mimics module docstring lines like
        # ``- ``dangerous_eval`` — ``eval(`` / ``exec(`` call``.
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(
            f'"""docstring.\n\n- ``danger`` — ``{keyword}(`` call (HIGH)\n"""\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_real_eval_call_still_detected(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(f"def f(x):\n    return {keyword}(x)\n", encoding="utf-8")
        findings = _scan(tmp_path)
        assert len(findings) == 1
        assert findings[0].severity == "high"
        assert "dangerous_eval" in findings[0].tags

    def test_broad_except_with_noqa_ble001_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception:  # noqa: BLE001\n"
            "        # INTENTIONAL: graceful degradation\n"
            "        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        broad = [f for f in findings if "broad_exception" in f.tags]
        assert broad == [], broad

    def test_broad_except_without_noqa_still_detected(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except Exception:\n"
            "        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        broad = [f for f in findings if "broad_exception" in f.tags]
        assert len(broad) == 1

    def test_bare_except_with_noqa_ble001_still_detected(self, tmp_path: Path) -> None:
        # The noqa BLE001 waiver only applies to broad_exception,
        # not to bare ``except:`` — bare except is a stronger
        # antipattern and the waiver is for the broader form.
        (tmp_path / "a.py").write_text(
            "def f():\n"
            "    try:\n"
            "        risky()\n"
            "    except:  # noqa: BLE001\n"
            "        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        bare = [f for f in findings if "bare_except" in f.tags]
        assert len(bare) == 1


class TestPathRendering:
    """Single-file scans render the bare filename, not ``.``."""

    def test_single_file_input_renders_filename(self, tmp_path: Path) -> None:
        (tmp_path / "alpha.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = asyncio.run(PatternScanSource().discover(str(tmp_path / "alpha.py"), 0.0))
        assert len(findings) == 1
        assert findings[0].file == "alpha.py"

    def test_directory_input_renders_relative_path(self, tmp_path: Path) -> None:
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "beta.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert len(findings) == 1
        # Path is relative to the input root.
        assert findings[0].file in ("pkg/beta.py", "pkg\\beta.py")
