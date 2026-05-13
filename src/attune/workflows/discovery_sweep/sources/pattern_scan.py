"""``PatternScanSource`` — deterministic, LLM-free finding source.

Walks every ``.py`` file under ``path`` and emits ``Finding``
objects for a handful of well-known bug-prone patterns:

- bare ``except:`` clauses          (high)
- broad ``except Exception:``       (medium)
- ``eval(`` / ``exec(`` usage       (high)
- ``subprocess.*(shell=True)``      (high)
- ``# TODO`` / ``# FIXME`` markers  (low)

Implements the :class:`FindingSource` Protocol with
``is_llm = False``, so ``--no-llm`` keeps this adapter in the
sweep while filtering everything else. ``budget_usd`` is
accepted (Protocol contract) but ignored — pattern scanning
is effectively free.

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
    """One regex the scanner looks for."""

    pattern_id: str
    severity: Severity
    title: str
    description: str
    regex: re.Pattern[str]
    confidence: float = 0.9


_PATTERNS: tuple[_PatternSpec, ...] = (
    _PatternSpec(
        pattern_id="bare_except",
        severity="high",
        title="Bare except clause catches KeyboardInterrupt and SystemExit",
        description=(
            "Bare ``except:`` silently swallows control-flow exceptions "
            "(KeyboardInterrupt, SystemExit) along with the error you "
            "meant to handle. Catch specific exception types instead."
        ),
        regex=re.compile(r"^\s*except\s*:"),
    ),
    _PatternSpec(
        pattern_id="broad_exception",
        severity="medium",
        title="Broad except Exception masks specific errors",
        description=(
            "``except Exception:`` may be acceptable for graceful "
            "degradation, but it should be intentional and documented "
            "(see CLAUDE.md exception-handling lesson)."
        ),
        regex=re.compile(r"^\s*except\s+Exception\s*:"),
        confidence=0.7,
    ),
    _PatternSpec(
        pattern_id="dangerous_eval",
        severity="high",
        title="eval() can execute arbitrary code",
        description=(
            "``eval(...)`` of user-controlled input is a code-injection "
            "vector. Prefer ``ast.literal_eval`` for literal data or "
            "``json.loads`` for structured input."
        ),
        regex=re.compile(r"(?<![A-Za-z0-9_.])eval\s*\("),
    ),
    _PatternSpec(
        pattern_id="dangerous_exec",
        severity="high",
        title="exec() can execute arbitrary code",
        description=(
            "``exec(...)`` runs arbitrary Python at runtime. Refactor "
            "to data structures or explicit function dispatch."
        ),
        regex=re.compile(r"(?<![A-Za-z0-9_.])exec\s*\("),
    ),
    _PatternSpec(
        pattern_id="subprocess_shell_true",
        severity="high",
        title="subprocess call with shell=True risks shell injection",
        description=(
            "``shell=True`` lets the OS shell parse the command string. "
            "Pass a list of arguments and leave ``shell`` at its default "
            "to avoid bandit B602/B603 findings."
        ),
        regex=re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True"),
    ),
    _PatternSpec(
        pattern_id="incomplete_code",
        severity="low",
        title="TODO/FIXME marker indicates unfinished work",
        description=(
            "Markers indicate the file has known-unfinished work. "
            "Track in your backlog; not necessarily a bug."
        ),
        regex=re.compile(r"#\s*(?:TODO|FIXME)\b", re.IGNORECASE),
        confidence=0.6,
    ),
)


@dataclass
class PatternScanSource:
    """Regex-based pattern scanner, FindingSource Protocol-conforming."""

    name: str = "pattern-scan"
    is_llm: ClassVar[bool] = False
    exclude_dirs: frozenset[str] = field(default_factory=lambda: _DEFAULT_EXCLUDE_DIRS)
    include_glob: str = "**/*.py"

    async def discover(self, path: str, budget_usd: float) -> list[Finding]:
        """Scan ``path`` for known patterns. ``budget_usd`` is ignored."""
        del budget_usd  # explicit: pattern scanning is free
        root = Path(path)
        if not root.exists():
            logger.warning("PatternScanSource: path does not exist: %s", path)
            return []

        if root.is_file():
            return list(self._scan_file(root, root.parent))

        findings: list[Finding] = []
        for candidate in root.rglob(self.include_glob):
            if not candidate.is_file():
                continue
            if self._is_excluded(candidate, root):
                continue
            findings.extend(self._scan_file(candidate, root))
        return findings

    def _is_excluded(self, path: Path, root: Path) -> bool:
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        return any(part in self.exclude_dirs for part in rel_parts)

    def _scan_file(self, path: Path, root: Path) -> list[Finding]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("PatternScanSource: cannot read %s: %s", path, exc)
            return []

        try:
            display_path = str(path.relative_to(root))
        except ValueError:
            display_path = str(path)

        out: list[Finding] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            for spec in _PATTERNS:
                if spec.regex.search(line):
                    out.append(
                        Finding(
                            source=self.name,
                            severity=spec.severity,
                            title=spec.title,
                            description=spec.description,
                            file=display_path,
                            line=lineno,
                            evidence=line.rstrip(),
                            confidence=spec.confidence,
                            tags=("pattern-scan", spec.pattern_id),
                            raw={"pattern_id": spec.pattern_id},
                        )
                    )
        return out


__all__ = ["PatternScanSource"]
