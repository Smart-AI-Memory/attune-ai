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

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from ..workflow import Finding, Severity

logger = logging.getLogger(__name__)

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
    exclude_dirs: frozenset[str] = field(default_factory=lambda: _EXCLUDE_DIRS)

    # Surfaced for tests that need to enumerate the supported patterns
    # without parsing the regex tuple themselves.
    PATTERN_NAMES: ClassVar[tuple[str, ...]] = tuple(p.pattern_name for p in _PATTERNS)

    async def discover(self, path: str, budget_usd: float) -> list[Finding]:
        """Walk ``path`` and emit findings. ``budget_usd`` ignored."""
        del budget_usd  # Pattern scanning is free.

        root = Path(path)
        if not root.exists():
            logger.warning("pattern-scan: path does not exist: %s", path)
            return []

        files = self._iter_python_files(root)
        findings: list[Finding] = []
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

        try:
            rel = str(file_path.relative_to(root))
        except ValueError:
            # File outside root (shouldn't happen when root is a dir,
            # but file-root mode lands here).
            rel = str(file_path)

        findings: list[Finding] = []
        for lineno, line in enumerate(content.splitlines(), start=1):
            for spec in _PATTERNS:
                if spec.regex.search(line):
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
