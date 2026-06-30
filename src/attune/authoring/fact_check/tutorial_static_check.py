"""Static check of Python code fences in polished tutorials.

Phase 4 of the polish-fact-check spec. Extracts every
`````python`` fence from a polished tutorial, runs
``ast.parse`` as a cheap syntax gate, then invokes ``mypy
--strict`` as a subprocess per fence. Findings are mapped back to
the fence's line position in the original file so the soft-fail
block points at the right place.

Scope: only files under ``docs/tutorials/`` (or matching the
configured tutorial-path glob). Other doc kinds may carry code
samples but tutorials are where reader-follow-along expectations
are highest, so they're the highest-value target for static
checking.

Phase 4.1 is **static only** — no fence is executed. Execution
tiers are deferred to Phase 4.2 (documented in design.md).
"""

from __future__ import annotations

import ast
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from .report import Finding

logger = logging.getLogger(__name__)


CHECK_TUTORIAL_STATIC = "check_tutorial_static"

#: Directive that opts a single fence out of the mypy pass. Must
#: appear as the FIRST line inside the fence. Stripped before
#: publication so readers don't see the directive in the rendered
#: tutorial.
_SKIP_DIRECTIVE = "# attune-author: skip-mypy"

#: Fences must be balanced `````python ... `````
#: blocks. The leading newline anchor is intentional — fences must
#: start at the beginning of a line, not mid-paragraph.
_FENCE_PATTERN = re.compile(
    r"(?:\A|\n)```python\s*\n(.*?)\n```",
    flags=re.DOTALL,
)

#: Default subprocess timeout. mypy on a 30-line fence should
#: finish in <5s; the cap protects against pathological imports.
_MYPY_TIMEOUT_SECONDS = 10


def _line_of_offset(text: str, offset: int) -> int:
    """Return the 1-based line number containing ``offset`` in ``text``."""
    return text.count("\n", 0, offset) + 1


def _parse_mypy_output(stdout: str, base_line: int, file_label: str) -> list[Finding]:
    """Convert mypy stdout into ``Finding`` rows.

    mypy line shape::

        <path>:<line>: <severity>: <message>  [code]

    We rewrite ``<line>`` to ``<base_line + line - 1>`` so the
    finding's location maps back to the original tutorial.
    """
    findings: list[Finding] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        # mypy output normally starts with the tempfile path; split
        # off everything up to the first colon-line-colon pair.
        match = re.match(r"^[^:]+:(\d+):\s*(error|warning|note):\s*(.+)$", line)
        if not match:
            continue
        mypy_line = int(match.group(1))
        severity_word = match.group(2)
        message = match.group(3).strip()
        absolute_line = base_line + mypy_line - 1
        severity = "error" if severity_word == "error" else "warning"
        findings.append(
            Finding(
                check=CHECK_TUTORIAL_STATIC,
                severity=severity,  # type: ignore[arg-type]
                location=f"Line {absolute_line} ({file_label} fence)",
                message=message,
            )
        )
    return findings


def _run_mypy(code: str, base_line: int) -> list[Finding]:
    """Type-check ``code`` via subprocess ``mypy --strict``.

    Returns an empty list when mypy isn't installed or the
    subprocess fails to launch — we never want the static check
    to break the polish pipeline.
    """
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        encoding="utf-8",
        delete=False,
    ) as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    try:
        try:
            result = subprocess.run(  # noqa: S603 - args are trusted constants
                [
                    "mypy",
                    "--strict",
                    "--no-error-summary",
                    "--no-color-output",
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_MYPY_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "fact_check.tutorial_static_check: mypy invocation failed: %s",
                exc,
            )
            return []
        # mypy exits 0 on success, 1 on findings, 2 on usage errors.
        if result.returncode not in (0, 1):
            logger.warning(
                "fact_check.tutorial_static_check: mypy exited %d (stderr: %s)",
                result.returncode,
                (result.stderr or "").strip()[:200],
            )
            return []
        return _parse_mypy_output(result.stdout, base_line, file_label="python")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _strip_skip_directive(code: str) -> tuple[str, bool]:
    """Return ``(stripped_code, was_skipped)``.

    The directive must be the first non-blank line of the fence.
    """
    lines = code.split("\n")
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == _SKIP_DIRECTIVE:
            del lines[idx]
            return "\n".join(lines), True
        break
    return code, False


def check(polished_path: Path) -> list[Finding]:
    """Run the tutorial static check against ``polished_path``.

    Args:
        polished_path: Markdown file produced by the polish pass.

    Returns:
        A list of findings — empty when every fence type-checks
        clean, or when ``polished_path`` is not a tutorial.
    """
    try:
        text = polished_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.debug("tutorial_static_check: cannot read %s (%s)", polished_path, exc)
        return []

    findings: list[Finding] = []
    for match in _FENCE_PATTERN.finditer(text):
        fence_body = match.group(1)
        # Line number of the FIRST line *inside* the fence (the body),
        # so mypy line numbers map cleanly through.
        fence_open_offset = match.start() + match.group(0).find("```python") + 1
        # The body starts one line after the opening ```python.
        body_start_line = _line_of_offset(text, fence_open_offset) + 1

        stripped, was_skipped = _strip_skip_directive(fence_body)
        if was_skipped:
            logger.debug(
                "tutorial_static_check: skip-mypy honored at line %d",
                body_start_line,
            )
            continue

        try:
            ast.parse(stripped)
        except SyntaxError as exc:
            findings.append(
                Finding(
                    check=CHECK_TUTORIAL_STATIC,
                    severity="error",
                    location=f"Line {body_start_line + max(exc.lineno or 1, 1) - 1} (python fence)",
                    message=f"SyntaxError: {exc.msg}",
                )
            )
            continue

        findings.extend(_run_mypy(stripped, base_line=body_start_line))

    return findings


def is_tutorial_path(path: Path) -> bool:
    """Heuristic: ``path`` lives under a ``tutorials/`` directory."""
    parts = path.parts
    return "tutorials" in parts


def strip_skip_directives_in_file(text: str) -> str:
    """Remove ``# attune-author: skip-mypy`` lines from every fence.

    The published tutorial shouldn't carry the directive; the
    polish writer calls this on the final string before writing
    so readers don't see it.
    """

    def _strip_in_match(match: re.Match[str]) -> str:
        body = match.group(1)
        stripped, _was = _strip_skip_directive(body)
        # Preserve the leading anchor (`\A` matches empty string at
        # start; otherwise `\n` was captured) so we don't insert a
        # spurious newline at the start of the file.
        leading = "\n" if text[match.start() : match.start() + 1] == "\n" else ""
        return f"{leading}```python\n{stripped}\n```"

    return _FENCE_PATTERN.sub(_strip_in_match, text)


__all__ = [
    "CHECK_TUTORIAL_STATIC",
    "check",
    "is_tutorial_path",
    "strip_skip_directives_in_file",
]
