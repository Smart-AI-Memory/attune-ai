"""Tests for RealArchitectureAnalyzer.

Covers: analyze(), _build_import_graph(), _extract_imports(),
_find_circular_imports(), _path_to_module(), and edge cases.
"""

from attune.orchestration.tools.architecture import (
    ArchitectureReport,
    RealArchitectureAnalyzer,
)


class TestAnalyzeValidProject:
    """Tests for analyze() with valid Python projects."""

    def test_analyze_returns_report(self, tmp_path):
        """Given valid Python files, analyze returns ArchitectureReport."""
        (tmp_path / "mod_a.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "mod_b.py").write_text("import sys\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert isinstance(report, ArchitectureReport)
        assert report.total_modules == 2
        assert report.score >= 0.0
        assert report.score <= 10.0

    def test_analyze_perfect_score_no_issues(self, tmp_path):
        """Given clean project with no circulars, score is 10."""
        (tmp_path / "a.py").write_text("import os\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("import sys\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.score == 10.0
        assert report.passed is True
        assert report.circular_imports == []
        assert report.high_coupling == []

    def test_analyze_counts_packages(self, tmp_path):
        """Given nested packages, counts packages correctly."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "core.py").write_text("import os\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.total_packages == 1
        assert report.total_modules == 2  # __init__.py + core.py


class TestAnalyzeEdgeCases:
    """Tests for edge cases in analyze()."""

    def test_analyze_empty_directory(self, tmp_path):
        """Given empty directory, returns perfect score with zero modules."""
        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.score == 10.0
        assert report.total_modules == 0
        assert report.passed is True

    def test_analyze_nonexistent_path(self, tmp_path):
        """Given nonexistent target path, returns default report."""
        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze("does_not_exist")

        assert report.score == 5.0
        assert report.total_modules == 0

    def test_analyze_syntax_error_file_skipped(self, tmp_path):
        """Given file with syntax error, skips it gracefully."""
        (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
        (tmp_path / "good.py").write_text("import os\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.total_modules == 2  # Both counted as files
        # bad.py contributes no imports but doesn't crash

    def test_analyze_binary_file_skipped(self, tmp_path):
        """Given non-UTF8 .py file, skips it gracefully."""
        (tmp_path / "binary.py").write_bytes(b"\xff\xfe\x00\x01")
        (tmp_path / "good.py").write_text("import os\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        # Should not crash — binary file skipped during import extraction
        assert isinstance(report, ArchitectureReport)


class TestCircularImportDetection:
    """Tests for _find_circular_imports()."""

    def test_detect_direct_circular(self, tmp_path):
        """Given A imports B and B imports A, detects circular."""
        (tmp_path / "mod_a.py").write_text("import mod_b\n", encoding="utf-8")
        (tmp_path / "mod_b.py").write_text("import mod_a\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert len(report.circular_imports) == 1
        pair = report.circular_imports[0]
        assert set(pair) == {"mod_a", "mod_b"}

    def test_no_circular_when_clean(self, tmp_path):
        """Given one-way imports, no circulars detected."""
        (tmp_path / "mod_a.py").write_text("import mod_b\n", encoding="utf-8")
        (tmp_path / "mod_b.py").write_text("import os\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.circular_imports == []

    def test_circular_penalizes_score(self, tmp_path):
        """Given circular import, score is reduced and passed is False."""
        (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("import a\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.score < 10.0
        assert report.passed is False


class TestHighCouplingDetection:
    """Tests for high coupling detection."""

    def test_high_coupling_over_threshold(self, tmp_path):
        """Given module importing >15 others, flagged as high coupling."""
        imports = "\n".join(f"import mod_{i}" for i in range(20))
        (tmp_path / "hub.py").write_text(imports, encoding="utf-8")
        for i in range(20):
            (tmp_path / f"mod_{i}.py").write_text("# stub\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert len(report.high_coupling) >= 1
        assert any(item["module"] == "hub" for item in report.high_coupling)
        assert report.score < 10.0

    def test_no_coupling_under_threshold(self, tmp_path):
        """Given module importing <15, no high coupling flagged."""
        imports = "\n".join(f"import mod_{i}" for i in range(5))
        (tmp_path / "hub.py").write_text(imports, encoding="utf-8")
        for i in range(5):
            (tmp_path / f"mod_{i}.py").write_text("# stub\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        report = analyzer.analyze(".")

        assert report.high_coupling == []


class TestExtractImports:
    """Tests for _extract_imports()."""

    def test_extracts_import_statement(self, tmp_path):
        """Given 'import os', extracts 'os'."""
        f = tmp_path / "test.py"
        f.write_text("import os\nimport sys\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        imports = analyzer._extract_imports(f)

        assert "os" in imports
        assert "sys" in imports

    def test_extracts_from_import(self, tmp_path):
        """Given 'from pathlib import Path', extracts 'pathlib'."""
        f = tmp_path / "test.py"
        f.write_text("from pathlib import Path\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        imports = analyzer._extract_imports(f)

        assert "pathlib" in imports

    def test_skips_relative_imports(self, tmp_path):
        """Given relative import, does not include it."""
        f = tmp_path / "test.py"
        f.write_text("from . import sibling\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        imports = analyzer._extract_imports(f)

        assert len(imports) == 0

    def test_returns_empty_on_syntax_error(self, tmp_path):
        """Given syntax error, returns empty set."""
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n", encoding="utf-8")

        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        imports = analyzer._extract_imports(f)

        assert imports == set()


class TestPathToModule:
    """Tests for _path_to_module()."""

    def test_simple_file(self, tmp_path):
        """Given 'module.py', returns 'module'."""
        f = tmp_path / "module.py"
        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        assert analyzer._path_to_module(f, tmp_path) == "module"

    def test_init_file(self, tmp_path):
        """Given 'pkg/__init__.py', returns 'pkg'."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        f = pkg / "__init__.py"
        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        assert analyzer._path_to_module(f, tmp_path) == "pkg"

    def test_nested_module(self, tmp_path):
        """Given 'pkg/sub/mod.py', returns 'pkg.sub.mod'."""
        sub = tmp_path / "pkg" / "sub"
        sub.mkdir(parents=True)
        f = sub / "mod.py"
        analyzer = RealArchitectureAnalyzer(str(tmp_path))
        assert analyzer._path_to_module(f, tmp_path) == "pkg.sub.mod"
