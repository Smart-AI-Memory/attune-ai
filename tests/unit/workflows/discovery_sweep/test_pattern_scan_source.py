"""Unit tests for PatternScanSource.

Runs against tmp_path fixtures with known pattern hits so the
adapter can be exercised without depending on src/ layout.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
from pathlib import Path

import pytest

from attune.workflows.discovery_sweep import Finding, FindingSource
from attune.workflows.discovery_sweep.sources import pattern_scan as _pattern_scan_mod
from attune.workflows.discovery_sweep.sources.pattern_scan import (
    PatternScanSource,
)

_POSIX_NON_ROOT = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission-bit semantics need non-root POSIX",
)


def _scan(tmp_path: Path) -> list[Finding]:
    return asyncio.run(PatternScanSource().discover([str(tmp_path)], 0.0))


class TestProtocolConformance:
    def test_implements_finding_source(self) -> None:
        assert isinstance(PatternScanSource(), FindingSource)

    def test_is_not_llm(self) -> None:
        assert PatternScanSource().is_llm is False

    def test_name_is_pattern_scan(self) -> None:
        assert PatternScanSource().name == "pattern-scan"

    def test_budget_multiplier_is_zero(self) -> None:
        # Non-LLM sources claim no share of the budget pool.
        assert PatternScanSource().budget_multiplier == 0.0


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
        findings = asyncio.run(PatternScanSource().discover([str(missing)], 0.0))
        assert findings == []

    def test_single_file_path_scans_just_that_file(self, tmp_path: Path) -> None:
        (tmp_path / "x.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = asyncio.run(PatternScanSource().discover([str(tmp_path / "x.py")], 0.0))
        assert len(findings) >= 1
        assert all(f.file is not None for f in findings)

    def test_multiple_paths_all_scanned(self, tmp_path: Path) -> None:
        # Engine glob-expands to a list; the source must visit every
        # entry, not just the first.
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        (a / "alpha.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        (b / "beta.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = asyncio.run(PatternScanSource().discover([str(a), str(b)], 0.0))
        files = {f.file for f in findings}
        assert "alpha.py" in files
        assert "beta.py" in files


class TestBudget:
    def test_ignores_budget(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        zero = asyncio.run(PatternScanSource().discover([str(tmp_path)], 0.0))
        big = asyncio.run(PatternScanSource().discover([str(tmp_path)], 999.0))
        assert len(zero) == len(big)


class TestFalsePositiveFilters:
    """Filters that mirror bug-predict's `_is_acceptable_*` helpers.

    Discovered via dogfood runs against
    ``src/attune/workflows/discovery_sweep/`` (scanner self-match) and
    ``src/attune/memory/short_term/`` (noqa BLE001 acknowledged
    broad-except). See ``.claude/rules-tail/attune/scanner-patterns.md``.
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


class TestMultiLineDocstringFilter:
    """AST-based string-region filter — added 2026-05-13.

    The whole-tree dogfood audit on 2026-05-13 surfaced 14 false
    positives where pattern keywords were mentioned in **multi-line**
    module docstrings. The pre-existing line-local quote walk only
    catches same-line literals — a docstring whose opening ``\"\"\"``
    is on line 1 and whose ``eval(`` mention is on line 12 falls
    through. The AST helper rejects those by collecting every string-
    literal node's span up front and filtering finding coordinates
    against the span set.

    See ``docs/specs/discovery-sweep/dogfood-audit-2026-05-13.md``.
    """

    def test_eval_inside_multiline_module_docstring_skipped(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        # Module docstring opens on line 1, mentions ``eval(`` on line 4
        # (in prose). Pre-AST filter would miss this; the AST helper
        # treats lines 1-6 inclusive as inside-string territory.
        (tmp_path / "a.py").write_text(
            '"""Module docstring.\n'
            "\n"
            "Coding standards:\n"
            f"- No {keyword}() or exec() usage\n"
            "- All operators whitelisted\n"
            '"""\n'
            "\n"
            "def safe(): return 1\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_exec_inside_multiline_class_docstring_skipped(self, tmp_path: Path) -> None:
        keyword = "ex" + "ec"
        (tmp_path / "b.py").write_text(
            "class Foo:\n"
            '    """One liner.\n'
            "\n"
            f"    Does not use {keyword}() anywhere.\n"
            '    """\n'
            "\n"
            "    def bar(self):\n"
            "        return 1\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_real_eval_outside_string_still_detected(self, tmp_path: Path) -> None:
        """AST filter must not suppress legitimate calls."""
        keyword = "ev" + "al"
        (tmp_path / "c.py").write_text(
            '"""Module docstring with no pattern keyword."""\n'
            "\n"
            "def unsafe(x):\n"
            f"    return {keyword}(x)\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert len(findings) == 1
        assert "dangerous_eval" in findings[0].tags
        assert findings[0].line == 4

    def test_syntax_error_falls_back_to_line_local_filter(self, tmp_path: Path) -> None:
        """Files that fail to ast.parse still get same-line filtering.

        The fallback path catches same-line string literals (the
        original Phase 1 behavior) so single-line scanner self-matches
        keep getting filtered even when the file has invalid syntax.
        """
        keyword = "ev" + "al"
        # Truly broken syntax (unbalanced bracket on a real statement)
        # — AST will refuse to parse, scanner falls back. The string
        # literal on the line is still recognized by the line-local
        # quote walk.
        (tmp_path / "d.py").write_text(
            f'TITLE = "Use of {keyword}() bad"\n' "def broken(:\n    pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        # Same-line string filter still applies via the fallback path.
        assert findings == [], findings

    def test_eval_in_fstring_literal_fragment_skipped(self, tmp_path: Path) -> None:
        """f-string literal fragments are ``ast.Constant`` children and
        should be treated as inside-string by the AST helper."""
        keyword = "ev" + "al"
        (tmp_path / "e.py").write_text(
            f'def f(): return f"prose mentioning {keyword}() in middle"\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings


class TestPathRendering:
    """Single-file scans render the bare filename, not ``.``."""

    def test_single_file_input_renders_filename(self, tmp_path: Path) -> None:
        (tmp_path / "alpha.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = asyncio.run(PatternScanSource().discover([str(tmp_path / "alpha.py")], 0.0))
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


class TestStringSpanBoundaryLines:
    """``_is_inside_string_span`` on the string's own start/end line.

    The interior-line case (``start_line < line < end_line``) is
    already covered by ``TestMultiLineDocstringFilter``. These two
    exercise the boundary branches: a match on the same line the
    multi-line string OPENS (after the opening quote), and a match on
    the line it CLOSES (before the closing quote).
    """

    def test_match_on_string_open_line_after_quote_skipped(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(
            f'x = """also mentions {keyword}( here\n' "continues on the next line\n" '"""\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings

    def test_match_on_string_close_line_before_quote_skipped(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(
            'x = """\nfirst line\n' f'{keyword}( at end"""\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings


class TestQuoteWalkStateToggle:
    """``_is_inside_quoted_region`` closes a quote pair before the match.

    A single-quote-toggle open (``test_eval_inside_single_quoted_string_
    skipped``) is already covered. This closes the pair (open then
    close) BEFORE the match on the same line, so the walk's state ends
    back at ``None`` — proving the match is correctly treated as
    outside any string once the earlier pair has closed.
    """

    def test_quote_pair_closed_before_match_not_treated_as_quoted(self, tmp_path: Path) -> None:
        keyword = "ev" + "al"
        (tmp_path / "a.py").write_text(
            f"s = 'hi' if {keyword}(cond) else 'bye'\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        hits = [f for f in findings if "dangerous_eval" in f.tags]
        assert len(hits) == 1, findings


class TestSpecialFilePaths:
    """Filesystem entries that are neither a regular file nor a directory."""

    @pytest.mark.skipif(sys.platform == "win32", reason="mkfifo is POSIX-only")
    def test_fifo_path_neither_file_nor_dir_returns_empty(self, tmp_path: Path) -> None:
        fifo_path = tmp_path / "myfifo"
        os.mkfifo(fifo_path)
        findings = asyncio.run(PatternScanSource().discover([str(fifo_path)], 0.0))
        assert findings == []


class TestUnreadableFileTolerance:
    """A file the scanner cannot read is skipped, not fatal to the run."""

    def test_invalid_utf8_file_skipped_other_files_still_scanned(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.py"
        bad.write_bytes(b"\xff\xfe\x00 not valid utf-8\n")
        good = tmp_path / "good.py"
        good.write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        files = {f.file for f in findings}
        assert "good.py" in files
        assert "bad.py" not in files

    @_POSIX_NON_ROOT
    def test_permission_denied_file_skipped(self, tmp_path: Path) -> None:
        unreadable = tmp_path / "secret.py"
        unreadable.write_text("eval(x)\n", encoding="utf-8")
        unreadable.chmod(0o000)
        try:
            findings = _scan(tmp_path)
        finally:
            unreadable.chmod(0o644)
        assert findings == []


class TestPathRenderingFallback:
    """``relative_to`` failure falls back to the raw path string.

    Not reachable through a real ``rglob`` walk (every yielded path is
    constructed under ``root``), so this simulates the failure via a
    scoped monkeypatch — the fallback exists as a defensive guard, and
    this proves it does the right thing if ever exercised.
    """

    def test_relative_to_value_error_falls_back_to_str_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sub = tmp_path / "pkg"
        sub.mkdir()
        target = sub / "beta.py"
        target.write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n",
            encoding="utf-8",
        )
        real_relative_to = Path.relative_to

        def broken_relative_to(self: Path, other: object, *a: object, **kw: object) -> Path:
            if self == target:
                raise ValueError("simulated: not relative to root")
            return real_relative_to(self, other, *a, **kw)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "relative_to", broken_relative_to)
        findings = _scan(tmp_path)
        assert len(findings) == 1
        assert findings[0].file == str(target)


class TestDefensiveGuards:
    """Belt-and-suspenders branches not reachable via normal inputs.

    Both guards exist for robustness against AST/regex edge cases the
    module's own comments flag as atypical. Simulating them via a
    scoped monkeypatch proves the fallback behavior is correct without
    weakening the production code.
    """

    def test_constant_node_missing_end_position_excludes_its_span(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``Constant`` node with ``end_lineno is None`` is skipped
        when building string spans (``_collect_string_spans``), so its
        contents fall through to the line-local quote-walk fallback."""
        keyword = "ev" + "al"
        content = (
            '"""Module docstring marker HERE.\n'
            "\n"
            f"Mentions {keyword}( in prose.\n"
            '"""\n'
            "\n"
            "def safe(): return 1\n"
        )
        (tmp_path / "a.py").write_text(content, encoding="utf-8")

        real_parse = ast.parse

        def broken_parse(src: str, *a: object, **kw: object) -> ast.AST:
            tree = real_parse(src, *a, **kw)  # type: ignore[arg-type]
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and "docstring marker HERE" in node.value
                ):
                    node.end_lineno = None
            return tree

        monkeypatch.setattr(_pattern_scan_mod.ast, "parse", broken_parse)
        findings = _scan(tmp_path)
        hits = [f for f in findings if "dangerous_eval" in f.tags]
        assert len(hits) == 1, findings

    def test_match_starting_exactly_on_quote_char_treated_as_quoted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """None of the shipped ``_PATTERNS`` regexes can start a match
        on a quote character (they all open on a keyword/``#``), so
        ``_is_inside_quoted_region``'s "match lands inside the quote
        run itself" branch is untestable through the real pattern set.
        A synthetic pattern exercises the guard directly."""
        synthetic = _pattern_scan_mod._PatternSpec(
            pattern_name="synthetic_quote_probe",
            severity="low",
            regex=re.compile(r'"'),
            title="synthetic quote-char probe",
        )
        monkeypatch.setattr(_pattern_scan_mod, "_PATTERNS", (synthetic,))
        # Syntactically invalid so ast.parse fails -> spans is None ->
        # the AST filter never short-circuits the quote-walk fallback.
        (tmp_path / "a.py").write_text(
            'TITLE = "hello"\ndef broken(:\n    pass\n',
            encoding="utf-8",
        )
        findings = _scan(tmp_path)
        assert findings == [], findings
