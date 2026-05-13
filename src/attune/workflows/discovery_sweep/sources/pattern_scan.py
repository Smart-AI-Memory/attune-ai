"""``PatternScanSource`` — non-LLM regex scanner adapter.

Walks ``.py`` files under the given path and emits ``Finding`` objects
for canonical bug patterns:

- ``bare_except`` — bare ``except:`` clause (HIGH)
- ``broad_exception`` — bare ``except Exception:`` (MEDIUM)
- ``dangerous_eval`` — ``eval(`` / ``exec(`` call (HIGH)
- ``subprocess_shell_true`` — ``subprocess.*(shell=True)`` (HIGH)
- ``incomplete_code`` — ``TODO`` / ``FIXME`` marker (LOW)

Spend is always $0.00 — the adapter ignores ``budget_usd``.

The verification engine's REJECT and QUESTION rules handle false-
positive triage downstream (LOW-severity ``incomplete_code`` falls
below the severity threshold and lands in ``rejected``), so the
scanner doesn't need its own allow-list logic.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from ..workflow import Finding, Severity

logger = logging.getLogger(__name__)

_QUOTE_CHARS: frozenset[str] = frozenset({'"', "'", "`"})
_NOQA_BLE001_RE = re.compile(r"#\s*noqa\s*:\s*[^#\n]*\bBLE001\b", re.IGNORECASE)

# (start_line, start_col, end_line, end_col) — all 1-indexed lines,
# 0-indexed columns, matching CPython's ``ast`` convention.
_StringSpan = tuple[int, int, int, int]


def _collect_string_spans(content: str) -> list[_StringSpan] | None:
    """Return spans of every string literal in ``content`` via :mod:`ast`.

    Each span is ``(start_line, start_col, end_line, end_col)`` using the
    same indexing as :mod:`ast` (lines 1-indexed, cols 0-indexed). The
    spans include single-line and multi-line strings, docstrings,
    bytes-literals, and the literal fragments of f-strings (CPython
    emits each f-string fragment as its own :class:`ast.Constant` child).

    Returns ``None`` when ``content`` fails to parse. Callers should fall
    back to the line-local quote walk in that case so files with syntax
    errors still get pattern-scanned.
    """
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return None
    spans: list[_StringSpan] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str | bytes):
            continue
        if (
            node.lineno is None
            or node.col_offset is None
            or node.end_lineno is None
            or node.end_col_offset is None
        ):
            continue
        spans.append((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset))
    return spans


def _is_inside_string_span(spans: list[_StringSpan], line: int, col: int) -> bool:
    """True if ``(line, col)`` falls inside any string span.

    Linear scan over ``spans`` — fine for typical modules (a few hundred
    string nodes at most). Lines strictly between ``start_line`` and
    ``end_line`` of a span are always inside.
    """
    for start_line, start_col, end_line, end_col in spans:
        if start_line < line < end_line:
            return True
        if start_line == line and end_line == line:
            if start_col <= col < end_col:
                return True
        elif start_line == line:
            if col >= start_col:
                return True
        elif end_line == line:
            if col < end_col:
                return True
    return False


def _is_inside_quoted_region(line: str, match_start: int) -> bool:
    """True if ``match_start`` falls inside a quoted region on ``line``.

    Treats maximal runs of ``"`` / ``'`` / `` ` `` as single toggles so
    Python triple-quoted strings (``\"\"\"``) and Markdown double-backtick
    code-spans (``...``) flip state correctly. Catches scanner self-match
    false positives where a pattern (e.g. ``eval(``) appears inside a
    docstring or a Python string literal on the same line.
    """
    state: str | None = None
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch in _QUOTE_CHARS:
            run = ch
            j = i
            while j < n and line[j] == run:
                j += 1
            if j > match_start >= i:
                # The match position lands inside the quote run itself
                # (unlikely for our patterns but safe to call it
                # quoted).
                return True
            if i >= match_start:
                break
            if state is None:
                state = run
            elif state == run:
                state = None
            i = j
            continue
        i += 1
        if i > match_start:
            break
    return state is not None


def _has_noqa_ble001(line: str) -> bool:
    """True if ``line`` carries an explicit ``# noqa: BLE001`` waiver.

    The project's coding standards require this annotation on every
    intentional ``except Exception:`` block (paired with an
    ``# INTENTIONAL:`` comment). When the annotation is present, the
    broad-except pattern is acknowledged team policy rather than a
    finding.
    """
    return bool(_NOQA_BLE001_RE.search(line))


_EXCLUDE_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".git",
        "build",
        "dist",
        ".eggs",
        "site-packages",
    }
)


@dataclass(frozen=True)
class _PatternSpec:
    """One regex the scanner looks for."""

    pattern_name: str
    severity: Severity
    regex: re.Pattern[str]
    title: str


# Anchored line-level patterns. Each one is intentionally narrow:
# we'd rather miss a finding than flood the queue with false
# positives that verification rules can't filter (severity threshold
# only filters LOW/INFO; medium/high noise gets through).
_PATTERNS: tuple[_PatternSpec, ...] = (
    _PatternSpec(
        pattern_name="bare_except",
        severity="high",
        regex=re.compile(r"^\s*except\s*:"),
        title="Bare except: clause catches KeyboardInterrupt and SystemExit",
    ),
    _PatternSpec(
        pattern_name="broad_exception",
        severity="medium",
        regex=re.compile(r"^\s*except\s+Exception\s*:"),
        title="Broad except Exception: clause may mask specific errors",
    ),
    _PatternSpec(
        pattern_name="dangerous_eval",
        severity="high",
        regex=re.compile(r"(?<![A-Za-z0-9_.])eval\s*\("),
        title="Use of eval() — may execute arbitrary code",
    ),
    _PatternSpec(
        pattern_name="dangerous_exec",
        severity="high",
        regex=re.compile(r"(?<![A-Za-z0-9_.])exec\s*\("),
        title="Use of exec() — may execute arbitrary code",
    ),
    _PatternSpec(
        pattern_name="subprocess_shell_true",
        severity="high",
        regex=re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
        title="subprocess call with shell=True — shell injection risk",
    ),
    _PatternSpec(
        pattern_name="incomplete_code",
        severity="low",
        regex=re.compile(r"#\s*(?:TODO|FIXME)\b", re.IGNORECASE),
        title="TODO/FIXME marker — incomplete code",
    ),
)


@dataclass
class PatternScanSource:
    """Deterministic line-level pattern scanner.

    Implements :class:`FindingSource` structurally — no inheritance
    needed thanks to :func:`runtime_checkable`.

    The ``confidence`` per finding is fixed at ``0.7``: high enough to
    clear the verification confidence threshold (0.5) so legitimate
    findings reach the queue, but not so high that genuinely uncertain
    matches push out higher-confidence LLM findings during dedup.
    """

    name: str = "pattern-scan"
    is_llm: bool = False
    # Non-LLM sources don't consume budget; the engine still includes
    # them in fan-out but allocates $0 from the total budget pool.
    budget_multiplier: float = 0.0
    exclude_dirs: frozenset[str] = field(default_factory=lambda: _EXCLUDE_DIRS)

    # Surfaced for tests that need to enumerate the supported patterns
    # without parsing the regex tuple themselves.
    PATTERN_NAMES: ClassVar[tuple[str, ...]] = tuple(p.pattern_name for p in _PATTERNS)

    async def discover(self, paths: list[str], budget_usd: float) -> list[Finding]:
        """Walk each path in ``paths`` and emit findings.

        ``budget_usd`` is ignored — pattern scanning is free. The engine
        glob-expands the user's ``--path`` upstream so every entry in
        ``paths`` is a concrete file or directory.
        """
        del budget_usd  # Pattern scanning is free.

        findings: list[Finding] = []
        for path in paths:
            root = Path(path)
            if not root.exists():
                logger.warning("pattern-scan: path does not exist: %s", path)
                continue
            files = self._iter_python_files(root)
            for file_path in files:
                findings.extend(self._scan_file(file_path, root))
        return findings

    def _iter_python_files(self, root: Path) -> list[Path]:
        """Yield ``.py`` files under ``root``, skipping vendor/cache trees.

        ``root`` may be a single file (returned as-is if it's a .py)
        or a directory (walked recursively).
        """
        if root.is_file():
            return [root] if root.suffix == ".py" else []

        if not root.is_dir():
            return []

        out: list[Path] = []
        for path in root.rglob("*.py"):
            # Skip any path under an excluded directory.
            if any(part in self.exclude_dirs for part in path.parts):
                continue
            out.append(path)
        return out

    def _scan_file(self, file_path: Path, root: Path) -> list[Finding]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.debug("pattern-scan: cannot read %s: %s", file_path, exc)
            return []

        # Render the file's display path. When the input was a single
        # file (root == file_path), ``relative_to`` returns ``.``; fall
        # back to the bare filename so output shows ``foo.py:42`` rather
        # than ``.:42``.
        if file_path == root:
            rel = file_path.name
        else:
            try:
                rel = str(file_path.relative_to(root))
            except ValueError:
                rel = str(file_path)

        # Build a whole-file string-span map via ``ast`` so pattern tokens
        # mentioned inside multi-line docstrings (the dominant false-
        # positive shape from the 2026-05-13 dogfood audit) are filtered.
        # ``None`` when the file fails to parse — the line-local fallback
        # still applies in that case via the OR below.
        spans = _collect_string_spans(content)

        findings: list[Finding] = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            for spec in _PATTERNS:
                match = spec.regex.search(line)
                if not match:
                    continue
                # Skip if EITHER the AST says the token is inside a real
                # string literal (catches multi-line docstrings) OR the
                # line-local quote walk says it's inside a quoted region
                # on this line (catches same-line literals AND prose
                # inside ``# "..."`` comment text, which AST never sees).
                # OR semantics preserve Phase 1's comment-text filtering.
                in_ast_string = spans is not None and _is_inside_string_span(
                    spans, lineno, match.start()
                )
                if in_ast_string or _is_inside_quoted_region(line, match.start()):
                    continue
                if spec.pattern_name == "broad_exception" and _has_noqa_ble001(line):
                    # Project coding standards waive `except Exception:`
                    # when the line carries an explicit `# noqa: BLE001`
                    # annotation (paired with an `# INTENTIONAL:`
                    # comment).
                    continue
                findings.append(
                    Finding(
                        source=self.name,
                        severity=spec.severity,
                        title=spec.title,
                        description=(
                            f"Pattern `{spec.pattern_name}` matched at " f"{rel}:{lineno}."
                        ),
                        file=rel,
                        line=lineno,
                        evidence=line.strip()[:200],
                        confidence=0.7,
                        tags=(spec.pattern_name,),
                    )
                )
        return findings
