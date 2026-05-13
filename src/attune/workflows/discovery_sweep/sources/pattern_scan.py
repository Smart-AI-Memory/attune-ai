"""``PatternScanSource`` — deterministic line-level pattern scanner.

Walks ``.py`` files under a scope and emits ``Finding`` objects
for canonical bug patterns:

- bare ``except:`` clauses
- broad ``except Exception:`` clauses
- ``eval(`` / ``exec(`` usage
- ``subprocess.*`` with ``shell=True``
- TODO/FIXME markers (low severity)

Zero LLM cost. The verification engine's REJECT rules filter
the obvious false positives (intentional broad excepts,
write_text fixtures, JS regex.exec, fuzz-target subprocess) so
this adapter's raw output is already triaged before it reaches
the queue.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from ..schema import Finding, Severity

_DEFAULT_INCLUDE_GLOB = "**/*.py"
_DEFAULT_EXCLUDE_DIRS = frozenset(
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
    """One pattern the scanner looks for."""

    name: str
    severity: Severity
    regex: re.Pattern[str]
    message_template: str


_PATTERNS: tuple[_PatternSpec, ...] = (
    _PatternSpec(
        name="bare_except",
        severity=Severity.HIGH,
        regex=re.compile(r"^\s*except\s*:"),
        message_template="bare_except: catches KeyboardInterrupt and SystemExit",
    ),
    _PatternSpec(
        name="broad_exception",
        severity=Severity.MEDIUM,
        regex=re.compile(r"^\s*except\s+Exception\s*:"),
        message_template=("broad_exception: BLE001 blind exception — masks specific errors"),
    ),
    _PatternSpec(
        name="dangerous_eval",
        severity=Severity.HIGH,
        regex=re.compile(r"(?<![A-Za-z0-9_.])eval\s*\("),
        message_template="dangerous_eval: eval( call may execute arbitrary code",
    ),
    _PatternSpec(
        name="dangerous_exec",
        severity=Severity.HIGH,
        regex=re.compile(r"(?<![A-Za-z0-9_.])exec\s*\("),
        message_template="dangerous_eval: exec usage may execute arbitrary code",
    ),
    _PatternSpec(
        name="subprocess_shell_true",
        severity=Severity.HIGH,
        regex=re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
        message_template=("subprocess shell injection B602: shell=True with user input is risky"),
    ),
    _PatternSpec(
        name="incomplete_code",
        severity=Severity.LOW,
        regex=re.compile(r"#\s*(?:TODO|FIXME)\b", re.IGNORECASE),
        message_template="incomplete_code: TODO/FIXME marker",
    ),
)


@dataclass
class PatternScanSource:
    """Deterministic line-level pattern scanner.

    No LLM round-trips. ``estimated_spend_usd`` is always 0.0.
    Set ``include_glob`` to restrict scope further (default
    matches all .py files); ``exclude_dirs`` to skip vendor /
    cache trees in addition to the built-in defaults.
    """

    name: str = "pattern_scan"
    include_glob: str = _DEFAULT_INCLUDE_GLOB
    exclude_dirs: frozenset[str] = _DEFAULT_EXCLUDE_DIRS
    estimated_spend_usd: float = 0.0
    _scanned_files: int = field(default=0, init=False, repr=False)

    def discover(
        self,
        scope: Path,
        budget_usd: float,
        sweep_id: str,
    ) -> Iterable[Finding]:
        """Walk ``scope`` and yield Findings for matching lines.

        ``budget_usd`` is honored as an advisory hint only — this
        scanner has no real spend, so we ignore it.
        """
        scope_path = Path(scope).resolve()
        if scope_path.is_file():
            yield from self._scan_file(scope_path, sweep_id)
            return
        if not scope_path.is_dir():
            return

        for candidate in scope_path.rglob(self.include_glob):
            if not candidate.is_file():
                continue
            if self._is_excluded(candidate, scope_path):
                continue
            yield from self._scan_file(candidate, sweep_id, scope_root=scope_path)

    def _is_excluded(self, path: Path, scope_root: Path) -> bool:
        try:
            rel_parts = path.relative_to(scope_root).parts
        except ValueError:
            rel_parts = path.parts
        return any(part in self.exclude_dirs for part in rel_parts)

    def _scan_file(
        self,
        path: Path,
        sweep_id: str,
        scope_root: Path | None = None,
    ) -> Iterable[Finding]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        self._scanned_files += 1

        display_path = str(path.relative_to(scope_root)) if scope_root is not None else str(path)

        for lineno, line in enumerate(text.splitlines(), start=1):
            for spec in _PATTERNS:
                if spec.regex.search(line):
                    yield Finding(
                        source_workflow=self.name,
                        file_path=display_path,
                        line=lineno,
                        severity=spec.severity,
                        message=spec.message_template,
                        raw_finding={
                            "pattern": spec.name,
                            "matched_line": line.rstrip(),
                        },
                        sweep_id=sweep_id,
                    )

    @property
    def scanned_files(self) -> int:
        """Number of files this scanner processed in its lifetime."""
        return self._scanned_files


__all__ = ["PatternScanSource"]
