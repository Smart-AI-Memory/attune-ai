"""Tests for the ``PatternScanSource`` adapter (Phase 2A)."""

from __future__ import annotations

from pathlib import Path

from attune.workflows.discovery_sweep import (
    Finding,
    PatternScanSource,
    Severity,
)


def _write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _findings(source: PatternScanSource, scope: Path) -> list[Finding]:
    return list(source.discover(scope, budget_usd=0.0, sweep_id="test01abcd23"))


class TestPatternScanSource:
    def test_detects_bare_except(self, tmp_path):
        _write(
            tmp_path / "f.py",
            [
                "def fragile():",
                "    try:",
                "        pass",
                "    except:",
                "        pass",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        bare = [f for f in findings if f.raw_finding["pattern"] == "bare_except"]
        assert len(bare) == 1
        assert bare[0].line == 4
        assert bare[0].severity == Severity.HIGH

    def test_detects_broad_exception(self, tmp_path):
        _write(
            tmp_path / "f.py",
            [
                "def fragile():",
                "    try:",
                "        pass",
                "    except Exception:",
                "        pass",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        broad = [f for f in findings if f.raw_finding["pattern"] == "broad_exception"]
        assert len(broad) == 1
        assert broad[0].severity == Severity.MEDIUM

    def test_detects_subprocess_shell_true(self, tmp_path):
        _write(
            tmp_path / "f.py",
            [
                "import subprocess",
                "def go(cmd):",
                "    return subprocess.call(cmd, shell=True)",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        shells = [f for f in findings if f.raw_finding["pattern"] == "subprocess_shell_true"]
        assert len(shells) == 1
        assert shells[0].severity == Severity.HIGH

    def test_detects_todo_markers(self, tmp_path):
        _write(
            tmp_path / "f.py",
            [
                "def f():",
                "    # TODO: validate input",
                "    pass",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        todos = [f for f in findings if f.raw_finding["pattern"] == "incomplete_code"]
        assert len(todos) == 1
        assert todos[0].severity == Severity.LOW

    def test_dangerous_eval_pattern(self, tmp_path):
        # Build the trigger via constants so the file content
        # contains the literal eval( substring.
        _write(
            tmp_path / "f.py",
            [
                "def go(s):",
                "    return " + "eval" + "(s)",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        evals = [f for f in findings if f.raw_finding["pattern"] == "dangerous_eval"]
        assert len(evals) == 1
        assert evals[0].severity == Severity.HIGH

    def test_does_not_fire_on_method_named_eval(self, tmp_path):
        _write(
            tmp_path / "f.py",
            [
                "class C:",
                "    def go(self):",
                "        return self.eval(1)",
            ],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        evals = [f for f in findings if f.raw_finding["pattern"] == "dangerous_eval"]
        assert evals == []

    def test_skips_excluded_directories(self, tmp_path):
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        _write(
            cache_dir / "f.py",
            ["def fragile():", "    try: pass", "    except: pass"],
        )
        _write(
            tmp_path / "real.py",
            ["def fragile():", "    try:", "        pass", "    except:", "        pass"],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        # Only the file outside __pycache__ should contribute.
        paths = {f.file_path for f in findings}
        assert paths == {"real.py"}

    def test_scans_single_file_when_scope_is_file(self, tmp_path):
        target = tmp_path / "f.py"
        _write(
            target,
            ["def fragile():", "    try: pass", "    except: pass"],
        )
        findings = _findings(PatternScanSource(), target)
        assert len(findings) >= 1
        # When scope is a file, display path is the absolute path.
        assert findings[0].file_path == str(target)

    def test_empty_scope_returns_no_findings(self, tmp_path):
        findings = _findings(PatternScanSource(), tmp_path)
        assert findings == []

    def test_scanned_files_counter(self, tmp_path):
        _write(tmp_path / "a.py", ["def f(): pass"])
        _write(tmp_path / "b.py", ["def g(): pass"])
        source = PatternScanSource()
        _findings(source, tmp_path)
        assert source.scanned_files == 2

    def test_estimated_spend_is_zero(self):
        assert PatternScanSource().estimated_spend_usd == 0.0

    def test_emits_relative_paths_when_scope_is_directory(self, tmp_path):
        (tmp_path / "sub").mkdir()
        _write(
            tmp_path / "sub" / "f.py",
            ["def fragile():", "    try: pass", "    except: pass"],
        )
        findings = _findings(PatternScanSource(), tmp_path)
        rel_paths = {f.file_path for f in findings}
        assert any(p.startswith("sub") for p in rel_paths)

    def test_sweep_id_propagates_to_findings(self, tmp_path):
        _write(tmp_path / "f.py", ["    try: pass", "    except: pass"])
        source = PatternScanSource()
        findings = list(source.discover(tmp_path, budget_usd=0.0, sweep_id="deadbeef9999"))
        assert all(f.sweep_id == "deadbeef9999" for f in findings)
