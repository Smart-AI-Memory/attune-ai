"""Tests for the cli-refs check.

Subprocess calls are mocked so tests are deterministic and don't
depend on the installed attune-ai version.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

from attune.authoring.fact_check import cli_refs
from attune.authoring.fact_check.report import CHECK_CLI_REFS


def _write(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "polished.md"
    f.write_text(body, encoding="utf-8")
    return f


def _fake_run(stdout: str, returncode: int = 0) -> Any:
    """Build a fake CompletedProcess."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def test_catches_invented_flag(tmp_path: Path) -> None:
    """The ``--allow-run`` (real: ``--read-only``) regression."""
    help_text = (
        "Usage: attune ops [OPTIONS]\n\n"
        "Options:\n"
        "  --read-only  run in read-only mode\n"
        "  --port INT   port to bind\n"
    )
    body = "Run with `attune ops --allow-run` to enable.\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(cli_refs.subprocess, "run", return_value=_fake_run(help_text)),
    ):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)

    assert any(
        f.check == CHECK_CLI_REFS and f.severity == "error" and "--allow-run" in f.message
        for f in findings
    )


def test_finding_includes_version_coupling_block(tmp_path: Path) -> None:
    """Each CLI-ref finding carries the version + override snippet
    per spec §1.4 and §1.11.1."""
    help_text = "Options:\n  --port INT\n"
    body = "Use `attune ops --bogus` here.\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(cli_refs.subprocess, "run", return_value=_fake_run(help_text)),
        patch.object(cli_refs, "_installed_version", return_value="6.8.0"),
    ):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)

    assert findings, "expected at least one finding"
    message = findings[0].message
    # Version coupling messaging must include the installed version
    # and the per-file override snippet.
    assert "6.8.0" in message
    assert "[tool.attune-author.fact-check.skip]" in message
    assert "check_cli_refs" in message
    assert "--skip-check" in message


def test_accepts_known_flag(tmp_path: Path) -> None:
    help_text = "Options:\n  --read-only  desc\n  --port INT\n"
    body = "Run `attune ops --read-only` to enable.\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(cli_refs.subprocess, "run", return_value=_fake_run(help_text)),
    ):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)
    assert findings == []


def test_handles_subcommand_chain(tmp_path: Path) -> None:
    """``attune workflow run X --flag`` resolves the full chain."""
    help_text = "Options:\n  --path PATH\n  --strict\n"
    body = "Run `attune workflow run security-audit --path src/`.\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(cli_refs.subprocess, "run", return_value=_fake_run(help_text)) as mock_run,
    ):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)
    # Help was probed with the full chain — confirms we route correctly.
    call_args = mock_run.call_args
    assert call_args is not None
    cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
    assert cmd[:4] == ["attune", "workflow", "run", "security-audit"]
    assert findings == []


def test_unknown_subcommand_surfaces_finding(tmp_path: Path) -> None:
    """A nonexistent subcommand chain (--help exits nonzero) is a finding."""
    body = "See `attune ghost --some-flag` for context.\n"
    with (
        patch.object(cli_refs.shutil, "which", return_value="/fake/attune"),
        patch.object(
            cli_refs.subprocess,
            "run",
            return_value=_fake_run("error: no such command", returncode=2),
        ),
        patch.object(cli_refs, "_installed_version", return_value="6.8.0"),
    ):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)
    assert any("subcommand not found" in f.message for f in findings)


def test_missing_cli_short_circuits(tmp_path: Path) -> None:
    """No CLI on PATH → no findings, no crash."""
    body = "Use `attune ops --whatever`.\n"
    with patch.object(cli_refs.shutil, "which", return_value=None):
        findings = cli_refs.check(_write(tmp_path, body), tmp_path)
    # When we can't resolve, treat as ambiguous: no findings raised
    # (we'd be guessing). The version-coupling messaging is still
    # documented for the call sites that do find flags.
    assert findings == []
