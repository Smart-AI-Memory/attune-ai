"""AST-based post-generation fact-check for polished docs.

Phase 1 of the polish-fact-check spec
(``docs/specs/polish-fact-check``). Each check module surfaces
findings into a shared :class:`FactCheckReport`; the caller
decides whether to soft-fail (append an ``## Unresolved
references`` block to the polished file) or strict-fail (raise
:class:`FactCheckError`).
"""

from __future__ import annotations

from pathlib import Path

from . import cli_refs, doc_examples, md_links, numeric_refs, python_refs, tutorial_static_check
from .config import load_config
from .report import (
    CHECK_CLI_REFS,
    CHECK_DOC_EXAMPLES,
    CHECK_MD_LINKS,
    CHECK_NUMERIC_REFS,
    CHECK_PYTHON_REFS,
    FactCheckConfig,
    FactCheckError,
    FactCheckReport,
    Finding,
    Severity,
    format_unresolved_block,
)
from .tutorial_static_check import CHECK_TUTORIAL_STATIC


def check_polished_file(
    polished_path: Path,
    *,
    project_root: Path,
    config: FactCheckConfig | None = None,
) -> FactCheckReport:
    """Run all enabled fact-check passes against ``polished_path``.

    Args:
        polished_path: Markdown file produced by the polish pass.
        project_root: Consumer project root. Used to resolve CLI
            ``--help`` output, ``.help/features.yaml``, and to
            match per-file skip entries from configuration.
        config: Optional explicit config; ``None`` means load
            from the project's ``pyproject.toml``.

    Returns:
        A :class:`FactCheckReport` with zero or more findings.
        Callers gate on ``report.has_errors()`` for strict mode
        and feed ``report.findings`` to
        :func:`format_unresolved_block` for soft-fail.
    """
    cfg = config if config is not None else load_config(project_root)
    report = FactCheckReport()
    if not cfg.enabled:
        return report

    try:
        rel_path = polished_path.relative_to(project_root).as_posix()
    except ValueError:
        rel_path = polished_path.name

    if cfg.is_check_enabled(CHECK_PYTHON_REFS, rel_path):
        report.extend(python_refs.check(polished_path))
    if cfg.is_check_enabled(CHECK_CLI_REFS, rel_path):
        report.extend(cli_refs.check(polished_path, project_root))
    if cfg.is_check_enabled(CHECK_MD_LINKS, rel_path):
        report.extend(md_links.check(polished_path))
    if cfg.is_check_enabled(CHECK_NUMERIC_REFS, rel_path):
        report.extend(numeric_refs.check(polished_path, project_root))
    if cfg.is_check_enabled(CHECK_DOC_EXAMPLES, rel_path):
        report.extend(doc_examples.check(polished_path))
    if cfg.is_check_enabled(
        CHECK_TUTORIAL_STATIC, rel_path
    ) and tutorial_static_check.is_tutorial_path(polished_path):
        report.extend(tutorial_static_check.check(polished_path))

    return report


def apply_soft_fail(polished_path: Path, report: FactCheckReport) -> bool:
    """Append the unresolved-references block to ``polished_path``.

    Returns True if the block was appended, False if there was
    nothing to append (empty report).
    """
    block = format_unresolved_block(report.findings)
    if not block:
        return False
    existing = polished_path.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    polished_path.write_text(existing + block + "\n", encoding="utf-8")
    return True


__all__ = [
    "CHECK_CLI_REFS",
    "CHECK_DOC_EXAMPLES",
    "CHECK_MD_LINKS",
    "CHECK_NUMERIC_REFS",
    "CHECK_PYTHON_REFS",
    "CHECK_TUTORIAL_STATIC",
    "FactCheckConfig",
    "FactCheckError",
    "FactCheckReport",
    "Finding",
    "Severity",
    "apply_soft_fail",
    "check_polished_file",
    "format_unresolved_block",
    "load_config",
]
