"""Tests for `attune.ops.cli` — the `attune ops` CLI entrypoint.

Strategy: real argparse, real `build_config`, real `create_app`.
The two unavoidable patches are:
- `uvicorn.run` — would block the test indefinitely otherwise.
- `webbrowser.open` — would actually open a browser tab.

Covers:
- `add_subparser`: every argument's default, type, action, and
  repeatability. `--allow-run` accepts as a backwards-compat
  no-op. `--specs-root` and `--trusted-host` accumulate via
  `action="append"`.
- `cmd_ops`: missing uvicorn → exit code 2 + stderr message;
  happy path constructs config and invokes uvicorn.run with
  the right host/port; --read-only flips allow_run off;
  --host=0.0.0.0 without --trusted-host triggers the
  middleware warning; --host=0.0.0.0 WITH --trusted-host is
  silent; --no-browser suppresses webbrowser.open;
  webbrowser.open failure is swallowed (best-effort).
- `main`: dispatches to cmd_ops with "ops" injected at argv[0]
  position. Exit code propagates.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.ops import cli as ops_cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_parser() -> argparse.ArgumentParser:
    """Build a fresh ArgumentParser with the ops subparser attached."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    ops_cli.add_subparser(sub)
    return parser


# ---------------------------------------------------------------------------
# add_subparser — argument schema lockdown
# ---------------------------------------------------------------------------


class TestAddSubparser:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Port default reads $PORT; delenv so 8765 is deterministic
        # regardless of the caller's environment (e.g. a Cowork
        # preview manager that exports PORT).
        monkeypatch.delenv("PORT", raising=False)
        parser = _make_parser()
        args = parser.parse_args(["ops"])
        assert args.host == "127.0.0.1"
        assert args.port == 8765
        assert args.project_root is None
        assert args.no_browser is False
        assert args.read_only is False
        assert args.specs_root is None
        assert args.trusted_host is None
        assert args.allow_run is False

    def test_port_coerced_to_int(self) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--port", "9000"])
        assert args.port == 9000
        assert isinstance(args.port, int)

    def test_port_defaults_to_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # A process manager (Cowork preview, container) that exports
        # PORT gets honored without passing --port explicitly.
        monkeypatch.setenv("PORT", "8010")
        parser = _make_parser()
        args = parser.parse_args(["ops"])
        assert args.port == 8010
        assert isinstance(args.port, int)

    def test_explicit_port_flag_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "8010")
        parser = _make_parser()
        args = parser.parse_args(["ops", "--port", "9000"])
        assert args.port == 9000

    def test_project_root_coerced_to_path(self, tmp_path: Path) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--project-root", str(tmp_path)])
        assert args.project_root == tmp_path
        assert isinstance(args.project_root, Path)

    def test_specs_root_repeatable(self, tmp_path: Path) -> None:
        a = tmp_path / "a"
        b = tmp_path / "b"
        parser = _make_parser()
        args = parser.parse_args(["ops", "--specs-root", str(a), "--specs-root", str(b)])
        assert args.specs_root == [a, b]

    def test_trusted_host_repeatable(self) -> None:
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--trusted-host",
                "tunnel.example.com",
                "--trusted-host",
                "other.example.com:9000",
            ]
        )
        assert args.trusted_host == ["tunnel.example.com", "other.example.com:9000"]

    def test_boolean_flags(self) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--read-only", "--allow-run"])
        assert args.no_browser is True
        assert args.read_only is True
        assert args.allow_run is True

    def test_allow_run_is_hidden_in_help(self) -> None:
        # --allow-run kept as a no-op for back-compat; SUPPRESS
        # keeps it out of `--help` output.
        parser = _make_parser()
        help_text = parser.format_help()
        assert "--allow-run" not in help_text


# ---------------------------------------------------------------------------
# cmd_ops — uvicorn dependency handling
# ---------------------------------------------------------------------------


class TestCmdOpsUvicornImport:
    def test_missing_uvicorn_returns_2_and_prints_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Simulate uvicorn missing: monkey-patch the import to
        # raise ImportError when the function body tries it.
        parser = _make_parser()
        args = parser.parse_args(["ops"])

        with patch.dict(sys.modules, {"uvicorn": None}):
            rc = ops_cli.cmd_ops(args)

        assert rc == 2
        err = capsys.readouterr().err
        assert "requires extra dependencies" in err
        assert "attune-ai[ops]" in err


# ---------------------------------------------------------------------------
# cmd_ops — happy path (uvicorn.run patched to no-op)
# ---------------------------------------------------------------------------


class TestCmdOpsHappyPath:
    def test_default_run_invokes_uvicorn_with_config(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--project-root", str(tmp_path)])

        with patch("uvicorn.run") as mock_run:
            rc = ops_cli.cmd_ops(args)

        assert rc == 0
        mock_run.assert_called_once()
        # Positional `app` plus host/port kwargs.
        kwargs = mock_run.call_args.kwargs
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8765
        assert kwargs["log_level"] == "info"

        # Banner emits the URL + config details on stdout.
        out = capsys.readouterr().out
        assert "http://127.0.0.1:8765" in out
        assert "allow-run: on" in out

    def test_read_only_flips_allow_run_off(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--read-only",
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run"):
            rc = ops_cli.cmd_ops(args)
        assert rc == 0
        assert "allow-run: off" in capsys.readouterr().out

    def test_custom_host_and_port(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--host",
                "127.0.0.1",
                "--port",
                "9999",
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run") as mock_run:
            ops_cli.cmd_ops(args)
        assert mock_run.call_args.kwargs["port"] == 9999
        assert "http://127.0.0.1:9999" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cmd_ops — 0.0.0.0 warning
# ---------------------------------------------------------------------------


class TestCmdOpsBindWarning:
    def test_zero_zero_zero_zero_without_trusted_host_warns(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--host",
                "0.0.0.0",  # nosec B104
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        err = capsys.readouterr().err
        assert "WARNING" in err
        assert "0.0.0.0" in err
        assert "--trusted-host" in err

    def test_zero_zero_zero_zero_with_trusted_host_silent(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--host",
                "0.0.0.0",  # nosec B104
                "--trusted-host",
                "example.com",
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        err = capsys.readouterr().err
        # No bind warning — user opted in by naming an external host.
        assert "WARNING" not in err

    def test_loopback_host_no_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Default 127.0.0.1 should never emit the 0.0.0.0 warning,
        # regardless of trusted-host presence.
        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        assert "WARNING" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# cmd_ops — browser launch
# ---------------------------------------------------------------------------


class TestCmdOpsBrowser:
    def test_no_browser_flag_suppresses_open(self, tmp_path: Path) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"), patch("webbrowser.open") as mock_open:
            ops_cli.cmd_ops(args)
        mock_open.assert_not_called()

    def test_default_opens_browser(self, tmp_path: Path) -> None:
        parser = _make_parser()
        args = parser.parse_args(["ops", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"), patch("webbrowser.open") as mock_open:
            ops_cli.cmd_ops(args)
        mock_open.assert_called_once()
        # URL passed matches the printed banner shape.
        assert "127.0.0.1:8765" in mock_open.call_args.args[0]

    def test_browser_failure_is_swallowed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # `webbrowser.open` can raise on headless systems or with
        # broken X11. The function catches Exception broadly and
        # continues — documented as best-effort.
        parser = _make_parser()
        args = parser.parse_args(["ops", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"), patch("webbrowser.open", side_effect=RuntimeError("no DISPLAY")):
            rc = ops_cli.cmd_ops(args)
        # Crucially: function still returns 0 and reaches uvicorn.run.
        assert rc == 0


# ---------------------------------------------------------------------------
# main() — standalone entry
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_dispatches_to_cmd_ops(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # main() injects "ops" before sys.argv[1:]. Patch sys.argv
        # to drive the dispatch.
        monkeypatch.setattr(
            sys,
            "argv",
            ["attune-ops", "--no-browser", "--project-root", str(tmp_path)],
        )
        with patch("uvicorn.run") as mock_run:
            rc = ops_cli.main()
        assert rc == 0
        mock_run.assert_called_once()

    def test_main_propagates_exit_code(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # When uvicorn is missing, cmd_ops returns 2 — main()
        # must surface that exit code, not swallow it.
        monkeypatch.setattr(sys, "argv", ["attune-ops"])
        with patch.dict(sys.modules, {"uvicorn": None}):
            rc = ops_cli.main()
        assert rc == 2


# ---------------------------------------------------------------------------
# cmd_ops — --specs-candidates flag (T3 integration with persistence)
# ---------------------------------------------------------------------------


class TestCmdOpsSpecsCandidates:
    """End-to-end: CLI flag → resolver → build_config → banner."""

    def test_flag_on_persists_and_shows_on_in_banner(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Redirect ATTUNE_HOME so the resolver writes into tmp_path.
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--specs-candidates",
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run"):
            rc = ops_cli.cmd_ops(args)
        assert rc == 0
        assert "specs-candidates: on" in capsys.readouterr().out

        # Persisted to disk under the redirected ATTUNE_HOME.
        from attune.ops import ops_config_store

        assert ops_config_store.load_settings(tmp_path) == {"specs_candidates_enabled": True}

    def test_no_flag_reads_persisted_true(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # Pre-seed persisted state.
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        from attune.ops import ops_config_store

        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", True)

        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        assert "specs-candidates: on" in capsys.readouterr().out

    def test_flag_off_persists_false_after_prior_true(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        from attune.ops import ops_config_store

        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", True)

        parser = _make_parser()
        args = parser.parse_args(
            [
                "ops",
                "--no-browser",
                "--no-specs-candidates",
                "--project-root",
                str(tmp_path),
            ]
        )
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        assert "specs-candidates: off" in capsys.readouterr().out
        assert ops_config_store.load_settings(tmp_path) == {"specs_candidates_enabled": False}

    def test_default_off_when_no_persistence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
        parser = _make_parser()
        args = parser.parse_args(["ops", "--no-browser", "--project-root", str(tmp_path)])
        with patch("uvicorn.run"):
            ops_cli.cmd_ops(args)
        assert "specs-candidates: off" in capsys.readouterr().out
        # No write happened on the read-only path.
        from attune.ops import ops_config_store

        assert not ops_config_store.settings_path(tmp_path).exists()
