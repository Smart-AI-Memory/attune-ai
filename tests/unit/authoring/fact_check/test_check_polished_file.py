"""Integration tests for the top-level ``check_polished_file`` entry."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

from attune.authoring.fact_check import (
    apply_soft_fail,
    check_polished_file,
    cli_refs,
)
from attune.authoring.fact_check.report import (
    CHECK_CLI_REFS,
    CHECK_MD_LINKS,
    CHECK_PYTHON_REFS,
    FactCheckConfig,
    FactCheckError,
)


def _write(tmp_path: Path, body: str, name: str = "polished.md") -> Path:
    f = tmp_path / name
    f.write_text(body, encoding="utf-8")
    return f


def _fake_run(stdout: str, returncode: int = 0) -> Any:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def test_check_polished_file_aggregates_findings_across_checks(
    tmp_path: Path,
) -> None:
    """End-to-end: a file with three error classes surfaces them all."""
    body = (
        "# Polished\n\n"
        "```python\n"
        "from attune.ops._readers import Bad\n"
        "```\n\n"
        "Run `attune ops --allow-run` to enable.\n\n"
        "See [details](missing.md) for more.\n"
    )
    help_text = "Options:\n  --read-only\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(cli_refs.subprocess, "run", return_value=_fake_run(help_text)),
        patch.object(cli_refs, "_installed_version", return_value="6.8.0"),
    ):
        report = check_polished_file(_write(tmp_path, body), project_root=tmp_path)

    checks_hit = {f.check for f in report.findings}
    assert CHECK_PYTHON_REFS in checks_hit
    assert CHECK_CLI_REFS in checks_hit
    assert CHECK_MD_LINKS in checks_hit
    assert report.has_errors()


def test_apply_soft_fail_appends_block(tmp_path: Path) -> None:
    """Soft-fail mode rewrites the file with the unresolved block."""
    body = "# Polished\n\nSee [x](nope.md).\n"
    file = _write(tmp_path, body)
    report = check_polished_file(file, project_root=tmp_path)
    assert report.has_errors()

    appended = apply_soft_fail(file, report)
    assert appended is True

    text = file.read_text(encoding="utf-8")
    assert "## Unresolved references" in text
    assert "nope.md" in text


def test_apply_soft_fail_noop_on_empty_report(tmp_path: Path) -> None:
    """Empty report → file untouched, returns False."""
    body = "# Polished\n\nAll good.\n"
    file = _write(tmp_path, body)
    report = check_polished_file(file, project_root=tmp_path)
    assert not report.has_errors()

    assert apply_soft_fail(file, report) is False
    assert file.read_text(encoding="utf-8") == body


def test_strict_mode_raises_via_explicit_check(tmp_path: Path) -> None:
    """Callers gate on ``report.has_errors()`` to raise ``FactCheckError``."""
    body = "See [x](nope.md).\n"
    file = _write(tmp_path, body)
    report = check_polished_file(file, project_root=tmp_path)

    raised = False
    try:
        if report.has_errors():
            raise FactCheckError(f"{len(report.findings)} unresolved refs")
    except FactCheckError as exc:
        raised = True
        assert "unresolved" in str(exc)
    assert raised is True


def test_config_disabled_skips_all_checks(tmp_path: Path) -> None:
    """``enabled = False`` short-circuits before any check runs."""
    body = "See [x](nope.md).\n"
    file = _write(tmp_path, body)
    cfg = FactCheckConfig(enabled=False)
    report = check_polished_file(file, project_root=tmp_path, config=cfg)
    assert report.findings == []


def test_per_file_skip_disables_specific_check(tmp_path: Path) -> None:
    """``skip`` opts a single file out of one check while keeping others."""
    body = "```python\nfrom attune.ops._readers import X\n```\n[y](nope.md)\n"
    (tmp_path / "docs").mkdir()
    file = tmp_path / "docs" / "x.md"
    file.write_text(body, encoding="utf-8")

    cfg = FactCheckConfig(skip={"docs/x.md": [CHECK_MD_LINKS]})
    report = check_polished_file(file, project_root=tmp_path, config=cfg)
    checks_hit = {f.check for f in report.findings}
    # python_refs still fires, md_links suppressed.
    assert CHECK_PYTHON_REFS in checks_hit
    assert CHECK_MD_LINKS not in checks_hit
