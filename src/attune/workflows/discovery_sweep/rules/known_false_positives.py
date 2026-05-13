"""REJECT rules grounded in documented CLAUDE.md false positives.

Each rule targets a specific historical false positive. Paired
control tests (see ``tests/unit/workflows/discovery_sweep/
test_verification.py``) ensure each rule does NOT fire on
similar-looking REAL bugs.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from ..schema import Finding, VerificationStatus

_REJECT = VerificationStatus.REJECT


def _line_at(source_lines: list[str], line: int | None) -> str | None:
    """Return the 1-indexed line, or None if out of range."""
    if line is None or line < 1 or line > len(source_lines):
        return None
    return source_lines[line - 1]


def _context_window(
    source_lines: list[str],
    line: int | None,
    *,
    before: int,
    after: int,
) -> list[str]:
    """Return a window of lines around ``line`` (1-indexed)."""
    if line is None:
        return []
    start = max(0, line - 1 - before)
    end = min(len(source_lines), line + after)
    return source_lines[start:end]


def _find_open_call_above(
    source_lines: list[str],
    line: int | None,
    *,
    needles: tuple[str, ...],
    max_lookback: int = 20,
) -> int | None:
    """Find a line above ``line`` containing any ``needles`` whose
    enclosing call has not closed by the target line.

    Returns the 1-indexed line of the matching open call, or None.

    The "not closed" heuristic counts parentheses: if the number
    of '(' from the candidate line through (line - 1) exceeds the
    number of ')' in the same range, we treat the call as still
    open at ``line``.
    """
    if line is None or line < 2:
        return None
    start_idx = max(0, line - 1 - max_lookback)
    for candidate_idx in range(line - 2, start_idx - 1, -1):
        candidate = source_lines[candidate_idx]
        if not any(n in candidate for n in needles):
            continue
        between = source_lines[candidate_idx : line - 1]
        opens = sum(s.count("(") for s in between)
        closes = sum(s.count(")") for s in between)
        if opens > closes:
            return candidate_idx + 1
    return None


# ---------------------------------------------------------------------------
# Rule 1: os.walk dirs[:] = [...] pattern
# ---------------------------------------------------------------------------


class DirsSliceAssignmentRule:
    """REJECT memory-leak / large-list-copy findings on the
    ``dirs[:] = [...]`` pattern inside an ``os.walk`` loop.

    Lesson: this pattern is REQUIRED for in-place dirs filtering;
    rebinding ``dirs = [...]`` would silently fail to filter.
    """

    name = "dirs_slice_assignment"
    _TRIGGER_TOKENS = ("dirs[:]",)
    _SUSPECT_MESSAGES = (
        "memory_leak",
        "large_list_copy",
        "list_copy",
        "unnecessary copy",
    )

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None

        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None
        if not any(t in line_text for t in self._TRIGGER_TOKENS):
            return None

        # Confirm the dirs[:] is inside an os.walk loop above.
        lookback = _context_window(source_lines, finding.line, before=10, after=0)
        if not any("os.walk(" in line for line in lookback):
            return None

        return (
            _REJECT,
            "dirs[:] inside os.walk loop is required for in-place "
            "filtering, not a memory leak (see CLAUDE.md "
            "os-walk-dirs-pattern lesson).",
        )


# ---------------------------------------------------------------------------
# Rule 2: create_subprocess_exec flagged as eval/exec
# ---------------------------------------------------------------------------


class SubprocessExecRule:
    """REJECT eval/exec findings whose source line uses
    ``create_subprocess_exec`` (substring match on 'exec' triggered
    the scanner, but this is asyncio's safe spawn helper)."""

    name = "subprocess_exec_false_eval"
    _SAFE_TOKENS = ("create_subprocess_exec", "asyncio.subprocess.exec")
    _SUSPECT_MESSAGES = ("dangerous_eval", "exec usage", "eval(")

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None

        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None
        if not any(t in line_text for t in self._SAFE_TOKENS):
            return None
        # Sanity: must not actually contain raw eval(/exec( calls.
        # Strip the safe token first so 'subprocess_exec' doesn't
        # match 'exec(' below.
        stripped = line_text
        for token in self._SAFE_TOKENS:
            stripped = stripped.replace(token, "")
        if "eval(" in stripped or "exec(" in stripped:
            return None

        return (
            _REJECT,
            "create_subprocess_exec is asyncio's safe spawn helper, "
            "not Python eval/exec (CLAUDE.md scanner-patterns lesson).",
        )


# ---------------------------------------------------------------------------
# Rule 3: JavaScript regex.exec() flagged as exec
# ---------------------------------------------------------------------------


class JsRegexExecRule:
    """REJECT exec findings in .js/.ts/.tsx files where the call is
    a regex ``.exec(...)`` method, not Python exec."""

    name = "js_regex_exec"
    _JS_EXTENSIONS = (".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs")
    _SUSPECT_MESSAGES = ("dangerous_eval", "exec usage", "eval(")

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        if not finding.file_path.endswith(self._JS_EXTENSIONS):
            return None
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None

        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None
        # `.exec(` on a regex object — not standalone exec(
        if ".exec(" not in line_text:
            return None
        # Reject if the line actually has a bare eval(/exec( call too.
        # Look for tokens not preceded by '.': i.e. eval( at start of token.
        cleaned = line_text.replace(".exec(", " ").replace(".eval(", " ")
        if "eval(" in cleaned or " exec(" in cleaned or cleaned.lstrip().startswith("exec("):
            return None

        return (
            _REJECT,
            "JavaScript regex.exec() is a safe method call, not "
            "Python exec (CLAUDE.md scanner-patterns lesson).",
        )


# ---------------------------------------------------------------------------
# Rule 4: eval/exec inside .write_text() / .write_bytes() fixtures
# ---------------------------------------------------------------------------


class WriteTextEvalFixtureRule:
    """REJECT eval/exec findings where the line is inside a still-
    open ``.write_text(`` or ``.write_bytes(`` call — fixture data,
    not executable code."""

    name = "write_text_eval_fixture"
    _WRITE_CALLS = (".write_text(", ".write_bytes(", "write_text(", "write_bytes(")
    _SUSPECT_MESSAGES = ("dangerous_eval", "exec usage", "eval(", "exec(")

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None
        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None
        if "eval(" not in line_text and "exec(" not in line_text:
            return None

        open_call = _find_open_call_above(
            source_lines,
            finding.line,
            needles=self._WRITE_CALLS,
            max_lookback=25,
        )
        if open_call is None:
            return None

        return (
            _REJECT,
            f"eval/exec appears inside an open .write_text/.write_bytes "
            f"call starting at line {open_call} — fixture content, not "
            f"executable code (CLAUDE.md scanner-patterns lesson).",
        )


# ---------------------------------------------------------------------------
# Rule 5: Intentional broad except with # noqa: BLE001 + INTENTIONAL: marker
# ---------------------------------------------------------------------------


class IntentionalBroadExceptRule:
    """REJECT broad-exception findings on lines paired with
    ``# noqa: BLE001`` AND an ``# INTENTIONAL:`` comment within 3
    lines (the documented graceful-degradation pattern)."""

    name = "intentional_broad_except"
    _SUSPECT_MESSAGES = ("broad_exception", "blind exception", "ble001", "broad except")
    _NOQA = "noqa: ble001"
    _MARKER = "intentional"

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None
        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None

        window = _context_window(source_lines, finding.line, before=0, after=3)
        window_lower = [line.lower() for line in window]

        has_noqa = self._NOQA in line_text.lower() or any(
            self._NOQA in line for line in window_lower
        )
        has_marker = any(self._MARKER in line for line in window_lower)

        if not (has_noqa and has_marker):
            return None

        return (
            _REJECT,
            "broad except is paired with # noqa: BLE001 and an "
            "INTENTIONAL: comment — documented graceful-degradation "
            "pattern (CLAUDE.md coding-standards-index lesson).",
        )


# ---------------------------------------------------------------------------
# Rule 6: subprocess.run inside fuzz targets / clusterfuzzlite scaffolding
# ---------------------------------------------------------------------------


class SubprocessInFuzzTargetRule:
    """REJECT shell-injection / subprocess findings inside fuzz
    target files and clusterfuzzlite scaffolding — these execute
    in an isolated build container, not in the production app."""

    name = "subprocess_in_fuzz_target"
    _SUSPECT_MESSAGES = (
        "shell injection",
        "subprocess",
        "command injection",
        "b602",
        "b603",
        "shell=true",
    )
    _FUZZ_PATH_TOKENS = (
        ".clusterfuzzlite/",
        "/fuzz_",
        "/fuzzing/",
        "fuzz_targets/",
    )

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None
        path_lower = finding.file_path.lower()
        if not any(token in path_lower for token in self._FUZZ_PATH_TOKENS):
            return None

        return (
            _REJECT,
            "subprocess call inside a fuzz target / clusterfuzzlite "
            "scaffold runs in an isolated build container — not a "
            "shell-injection risk in this context.",
        )


# ---------------------------------------------------------------------------
# Rule 7: structlog kwargs flagged as TypeError on stdlib Logger
# ---------------------------------------------------------------------------


class StructlogKwargsRule:
    """REJECT findings that flag ``logger.info("msg", key=value)``
    as a TypeError when the file is using structlog (where kwargs
    are the documented syntax)."""

    name = "structlog_kwargs"
    _SUSPECT_MESSAGES = (
        "unexpected keyword argument",
        "got an unexpected keyword",
        "logger.info(",
        "typeerror",
    )

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None

        # File must import or configure structlog.
        has_structlog = any(
            "import structlog" in line
            or "from structlog" in line
            or "structlog.get_logger" in line
            or "structlog.stdlib" in line
            for line in source_lines[:120]
        )
        if not has_structlog:
            return None

        # Line must be a logger call with kwargs.
        line_text = _line_at(source_lines, finding.line)
        if line_text is None or "logger." not in line_text:
            return None
        if "=" not in line_text:
            return None

        return (
            _REJECT,
            "logger.<level>(msg, key=value) is valid structlog "
            "syntax — the file uses structlog (CLAUDE.md scanner-"
            "patterns lesson on structlog kwargs).",
        )


# ---------------------------------------------------------------------------
# Rule 8: Pragma-allowlisted secret strings
# ---------------------------------------------------------------------------


class SecretsPragmaRule:
    """REJECT secret findings on lines tagged
    ``# pragma: allowlist secret`` (the detect-secrets escape
    hatch)."""

    name = "secrets_pragma_allowlist"
    _SUSPECT_MESSAGES = (
        "hardcoded",
        "secret",
        "credential",
        "password",
        "api key",
        "detect-secrets",
    )
    _PRAGMA = "pragma: allowlist secret"

    def classify(
        self,
        finding: Finding,
        source_lines: list[str],
    ) -> tuple[VerificationStatus, str] | None:
        message = finding.message.lower()
        if not any(s in message for s in self._SUSPECT_MESSAGES):
            return None
        line_text = _line_at(source_lines, finding.line)
        if line_text is None:
            return None
        if self._PRAGMA not in line_text.lower():
            return None

        return (
            _REJECT,
            "line carries # pragma: allowlist secret — documented "
            "detect-secrets escape hatch (CLAUDE.md secrets lessons).",
        )


__all__ = [
    "DirsSliceAssignmentRule",
    "IntentionalBroadExceptRule",
    "JsRegexExecRule",
    "SecretsPragmaRule",
    "StructlogKwargsRule",
    "SubprocessExecRule",
    "SubprocessInFuzzTargetRule",
    "WriteTextEvalFixtureRule",
]
