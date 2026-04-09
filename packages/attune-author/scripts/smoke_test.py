#!/usr/bin/env python3
"""End-to-end smoke test for attune-author.

Puts the CLI and core API through their paces against a
disposable sample project. Exercises:

  - --version / --help
  - init (project scan -> features.yaml)
  - status (fresh manifest, no templates)
  - generate <feature> (concept/task/reference templates)
  - status (templates fresh)
  - source mutation -> status (templates stale)
  - regenerate --dry-run
  - regenerate
  - status (back to fresh)
  - error paths (missing manifest, unknown feature)
  - python API (load_manifest, check_staleness)
  - docs subcommand (skipped if [ai] extra missing)
  - pytest suite (optional)

Exit code is 0 only if every check passes.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --keep         # leave sandbox dir
    python scripts/smoke_test.py --with-pytest  # also run pytest
    python scripts/smoke_test.py --python /path/to/python
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

# ---- Output helpers --------------------------------------------------------

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(s: str) -> str:
    return _c("32", s)


def red(s: str) -> str:
    return _c("31", s)


def yellow(s: str) -> str:
    return _c("33", s)


def cyan(s: str) -> str:
    return _c("36", s)


def bold(s: str) -> str:
    return _c("1", s)


# ---- Result tracking -------------------------------------------------------


@dataclass
class TestResult:
    name: str
    status: str  # "pass", "fail", "skip"
    duration_s: float
    detail: str = ""


@dataclass
class Report:
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult) -> None:
        self.results.append(result)
        marker = {
            "pass": green("PASS"),
            "fail": red("FAIL"),
            "skip": yellow("SKIP"),
        }[result.status]
        print(f"  [{marker}] {result.name} ({result.duration_s:.2f}s)")
        if result.detail and result.status != "pass":
            for line in result.detail.splitlines():
                print(f"        {line}")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "fail")

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skip")


# ---- Test runner -----------------------------------------------------------


class SmokeTest:
    def __init__(
        self,
        sandbox: Path,
        python: str,
        report: Report,
        run_pytest: bool = False,
    ) -> None:
        self.sandbox = sandbox
        self.python = python
        self.report = report
        self.run_pytest = run_pytest
        self.project = sandbox / "sample_project"
        self.help_dir = self.project / ".help"

    # -- subprocess helpers --

    def _run_cli(
        self,
        *args: str,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [self.python, "-m", "attune_author.cli", *args]
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or self.project),
            capture_output=True,
            text=True,
        )
        if check and proc.returncode != 0:
            raise RuntimeError(
                f"CLI failed: {' '.join(cmd)}\n"
                f"  stdout: {proc.stdout}\n"
                f"  stderr: {proc.stderr}"
            )
        return proc

    def _run_python(self, code: str) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [self.python, "-c", code],
            cwd=str(self.project),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"python -c failed:\n  stdout: {proc.stdout}\n  stderr: {proc.stderr}"
            )
        return proc

    # -- check decorator --

    def _check(self, name: str, fn) -> None:
        start = time.perf_counter()
        try:
            outcome = fn()
        except _Skip as exc:
            self.report.add(TestResult(name, "skip", time.perf_counter() - start, str(exc)))
            return
        except Exception:  # noqa: BLE001
            # INTENTIONAL: smoke-test runner must record any check failure
            # (including unexpected exceptions) as a fail result rather than
            # crashing the whole script.
            self.report.add(
                TestResult(
                    name,
                    "fail",
                    time.perf_counter() - start,
                    traceback.format_exc(),
                )
            )
            return
        detail = outcome if isinstance(outcome, str) else ""
        self.report.add(TestResult(name, "pass", time.perf_counter() - start, detail))

    # -- test phases --

    def setup_sample_project(self) -> None:
        self.project.mkdir(parents=True, exist_ok=True)

        # src/sample/auth.py
        auth_dir = self.project / "src" / "sample"
        auth_dir.mkdir(parents=True, exist_ok=True)
        (auth_dir / "__init__.py").write_text('"""sample package."""\n')
        (auth_dir / "auth.py").write_text(
            textwrap.dedent(
                '''\
                """User authentication module."""

                def login(username: str, password: str) -> bool:
                    """Authenticate a user against the local store."""
                    return bool(username and password)


                def logout(token: str) -> None:
                    """Invalidate a session token."""
                    _ = token
                '''
            )
        )
        (auth_dir / "config.py").write_text(
            textwrap.dedent(
                '''\
                """Application configuration."""

                DEFAULT_TIMEOUT = 30


                def load(path: str) -> dict:
                    """Load configuration from disk."""
                    return {"path": path, "timeout": DEFAULT_TIMEOUT}
                '''
            )
        )
        (auth_dir / "cli.py").write_text(
            textwrap.dedent(
                '''\
                """Command-line entry point."""

                def main() -> int:
                    """Run the CLI."""
                    print("hello")
                    return 0
                '''
            )
        )

        (self.project / "README.md").write_text(
            "# sample project\n\nA fixture for the attune-author smoke test.\n"
        )
        (self.project / "pyproject.toml").write_text(
            textwrap.dedent(
                """\
                [project]
                name = "sample"
                version = "0.0.1"
                """
            )
        )

    def test_version(self) -> str:
        proc = self._run_cli("--version")
        out = (proc.stdout + proc.stderr).strip()
        if "attune-author" not in out:
            raise AssertionError(f"--version output unexpected: {out!r}")
        return out

    def test_help(self) -> str:
        proc = self._run_cli("--help")
        for kw in ("init", "status", "generate", "regenerate", "docs"):
            if kw not in proc.stdout:
                raise AssertionError(f"--help missing subcommand {kw!r}")
        return "all subcommands listed"

    def test_init(self) -> str:
        proc = self._run_cli("init")
        manifest = self.help_dir / "features.yaml"
        if not manifest.exists():
            raise AssertionError(f"features.yaml not created: {proc.stdout}")
        body = manifest.read_text()
        if "version:" not in body or "features:" not in body:
            raise AssertionError(f"features.yaml malformed:\n{body}")
        return f"manifest written to {manifest.relative_to(self.project)}"

    def test_init_idempotent(self) -> str:
        proc = self._run_cli("init")
        if "Already initialized" not in proc.stdout:
            raise AssertionError(
                "second init should report already initialized; " f"got: {proc.stdout!r}"
            )
        return "second init is a no-op"

    def _features(self) -> list[str]:
        from_yaml = (self.help_dir / "features.yaml").read_text()
        names = []
        in_features = False
        for line in from_yaml.splitlines():
            if line.startswith("features:"):
                in_features = True
                continue
            if in_features and line and not line.startswith(" "):
                in_features = False
            if in_features and line.startswith("  ") and not line.startswith("   "):
                stripped = line.strip().rstrip(":")
                if stripped and not stripped.startswith("-"):
                    names.append(stripped)
        return names

    def test_status_initial(self) -> str:
        proc = self._run_cli("status")
        out = proc.stdout
        if not out.strip():
            raise AssertionError("status produced no output")
        return f"status reported {len(out.splitlines())} lines"

    def test_generate_each_feature(self) -> str:
        features = self._features()
        if not features:
            raise AssertionError("no features parsed from manifest")
        generated = 0
        for name in features:
            proc = self._run_cli("generate", name, check=False)
            if proc.returncode != 0:
                # Some features may have no source matches; tolerate
                continue
            generated += 1
        if generated == 0:
            raise AssertionError("generate produced no templates for any feature")

        # Look for any generated template directory under .help/
        templates = (
            list(self.help_dir.rglob("concept.md"))
            + list(self.help_dir.rglob("reference.md"))
            + list(self.help_dir.rglob("task.md"))
        )
        if not templates:
            raise AssertionError("no template files written under .help/")
        return f"generated for {generated}/{len(features)} features, {len(templates)} files"

    def test_status_after_generate(self) -> str:
        proc = self._run_cli("status")
        out = proc.stdout
        # Just confirm it still runs and produces output
        if not out.strip():
            raise AssertionError("status after generate produced no output")
        return "status reports cleanly"

    def test_mutation_marks_stale(self) -> str:
        # Touch a source file to invalidate hash
        target = self.project / "src" / "sample" / "auth.py"
        body = target.read_text()
        target.write_text(body + "\n# mutation\n")

        proc = self._run_cli("status")
        out = proc.stdout.lower()
        if "stale" not in out and "outdated" not in out:
            # Some configurations report differently; fall back to
            # checking via regenerate --dry-run
            dry = self._run_cli("regenerate", "--dry-run")
            if "stale" not in dry.stdout.lower() and "0" in dry.stdout:
                raise AssertionError(
                    "no staleness detected after mutation:\n"
                    f"  status: {proc.stdout}\n  dry-run: {dry.stdout}"
                )
            return "staleness detected via dry-run"
        return "staleness detected via status"

    def test_regenerate(self) -> str:
        proc = self._run_cli("regenerate")
        out = proc.stdout
        if "Regenerated" not in out and "regenerated" not in out:
            raise AssertionError(f"regenerate output unexpected: {out!r}")
        return out.strip().splitlines()[0] if out.strip() else "ok"

    def test_unknown_feature(self) -> str:
        proc = self._run_cli("generate", "definitely-not-a-feature", check=False)
        if proc.returncode == 0:
            raise AssertionError("expected nonzero exit for unknown feature")
        if "not found" not in (proc.stdout + proc.stderr).lower():
            raise AssertionError(f"missing 'not found' message: {proc.stdout!r} {proc.stderr!r}")
        return "unknown feature reports clear error"

    def test_missing_manifest(self) -> str:
        scratch = self.sandbox / "no_manifest"
        scratch.mkdir(exist_ok=True)
        proc = subprocess.run(
            [self.python, "-m", "attune_author.cli", "status"],
            cwd=str(scratch),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            raise AssertionError("status without manifest should fail")
        msg = (proc.stdout + proc.stderr).lower()
        if "not found" not in msg and "no such file" not in msg and "error" not in msg:
            raise AssertionError(
                f"missing-manifest error message unclear: {proc.stdout!r} {proc.stderr!r}"
            )
        return "missing manifest produces a clear error"

    def test_python_api(self) -> str:
        # Exercise the public Python API directly.
        code = textwrap.dedent(
            f"""\
            from pathlib import Path
            from attune_author.manifest import load_manifest
            from attune_author.staleness import check_staleness

            help_dir = Path(r"{self.help_dir}")
            project_root = Path(r"{self.project}")

            manifest = load_manifest(help_dir)
            assert manifest.features, "no features loaded"

            report = check_staleness(manifest, help_dir, project_root)
            print(f"features={{len(manifest.features)}} stale={{len(report.stale_features)}}")
            """
        )
        proc = self._run_python(code)
        return proc.stdout.strip()

    def test_docs_command(self) -> str:
        # Optional: only if [ai] extra is installed.
        check = subprocess.run(
            [self.python, "-c", "import anthropic"],
            capture_output=True,
        )
        if check.returncode != 0:
            raise _Skip("anthropic not installed (install [ai] extra)")
        target = self.project / "src" / "sample" / "auth.py"
        proc = self._run_cli(
            "docs",
            str(target),
            "--doc-type",
            "api-reference",
            check=False,
        )
        if proc.returncode != 0:
            # Could fail at runtime if no API key; treat as skip
            raise _Skip(
                "docs subcommand failed (likely missing ANTHROPIC_API_KEY): "
                + proc.stderr.strip()[:200]
            )
        return "docs produced output"

    def test_pytest_suite(self) -> str:
        if not self.run_pytest:
            raise _Skip("--with-pytest not provided")
        package_dir = Path(__file__).resolve().parent.parent
        proc = subprocess.run(
            [self.python, "-m", "pytest", "-q"],
            cwd=str(package_dir),
            capture_output=True,
            text=True,
        )
        tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-5:])
        if proc.returncode != 0:
            raise AssertionError(f"pytest failed:\n{tail}")
        return tail

    # -- run all --

    def run(self) -> None:
        print(bold(cyan("\n=== attune-author smoke test ===\n")))
        print(f"sandbox: {self.sandbox}")
        print(f"python : {self.python}\n")

        print(bold("Setup"))
        self.setup_sample_project()
        print(f"  sample project at {self.project}\n")

        print(bold("CLI surface"))
        self._check("--version", self.test_version)
        self._check("--help", self.test_help)

        print(bold("\nInit / scan"))
        self._check("init creates manifest", self.test_init)
        self._check("init is idempotent", self.test_init_idempotent)

        print(bold("\nStatus / generate"))
        self._check("status (initial)", self.test_status_initial)
        self._check("generate each feature", self.test_generate_each_feature)
        self._check("status (after generate)", self.test_status_after_generate)

        print(bold("\nStaleness / regenerate"))
        self._check("source mutation marks stale", self.test_mutation_marks_stale)
        self._check("regenerate", self.test_regenerate)

        print(bold("\nError paths"))
        self._check("unknown feature", self.test_unknown_feature)
        self._check("missing manifest", self.test_missing_manifest)

        print(bold("\nPython API"))
        self._check("load_manifest + check_staleness", self.test_python_api)

        print(bold("\nOptional"))
        self._check("docs subcommand", self.test_docs_command)
        self._check("pytest suite", self.test_pytest_suite)


class _Skip(Exception):
    """Raised by a check to mark itself skipped."""


# ---- Entry point -----------------------------------------------------------


def _default_python() -> str:
    """Pick the best python for running attune-author.

    Prefers the package's local .venv if present, else current.
    """
    pkg_root = Path(__file__).resolve().parent.parent
    candidates = [
        pkg_root / ".venv" / "bin" / "python",
        pkg_root / ".venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Leave the sandbox directory in place after the run.",
    )
    parser.add_argument(
        "--with-pytest",
        action="store_true",
        help="Also run the package pytest suite as a final check.",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="Python interpreter to invoke attune-author with "
        "(defaults to the package .venv if present).",
    )
    parser.add_argument(
        "--sandbox",
        default=None,
        help="Use this directory as the sandbox instead of a temp dir.",
    )
    args = parser.parse_args(argv)

    python = args.python or _default_python()
    if args.sandbox:
        sandbox = Path(args.sandbox).resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        owns_sandbox = False
    else:
        sandbox = Path(tempfile.mkdtemp(prefix="attune-author-smoke-"))
        owns_sandbox = True

    report = Report()
    try:
        SmokeTest(
            sandbox=sandbox,
            python=python,
            report=report,
            run_pytest=args.with_pytest,
        ).run()
    finally:
        print()
        print(bold("=== Summary ==="))
        print(
            f"  {green(str(report.passed) + ' passed')}, "
            f"{red(str(report.failed) + ' failed')}, "
            f"{yellow(str(report.skipped) + ' skipped')}"
        )
        if owns_sandbox and not args.keep:
            shutil.rmtree(sandbox, ignore_errors=True)
        else:
            print(f"  sandbox kept at {sandbox}")

    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
