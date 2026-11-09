"""Run the static security workflow's actual Bash with finite offline tool stubs.

The sandbox is the existing POSIX fixture object. Its inherited Windows skip is
retained; these controls do not claim native Windows Bash or a real scan.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from tests.unit.ci import test_security_scan_fail_closed as fail_closed

sandbox = fail_closed.sandbox
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def static_steps():
    workflow = yaml.safe_load((ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8"))
    return {step["name"]: step for step in workflow["jobs"]["security"]["steps"] if "name" in step}


_TOOL = r"""
import json
import os
import sys
from pathlib import Path

kind, *args = sys.argv[1:]
Path(kind + "-invocation.json").write_text(json.dumps(args))
Path(kind + "-key-present.json").write_text(json.dumps(bool(os.environ.get("SAFETY_API_KEY"))))
print(kind + " fixture stdout")
print(kind + " fixture stderr", file=sys.stderr)
if kind == "uv":
    output = Path(args[args.index("-o") + 1])
    output.write_text("" if os.environ.get("STATIC_EMPTY_EXPORT") else "locked-project-fixture==1.2.3\n")
    raise SystemExit(int(os.environ.get("STATIC_EXPORT_EXIT", "0")))
if kind == "bandit":
    output = Path(args[args.index("--output") + 1])
    report = {"errors": [], "results": []}
else:
    requirements = Path(args[args.index("--file") + 1])
    Path("safety-input.json").write_text(json.dumps({
        "input_file": str(requirements),
        "files": sorted(p.name for p in requirements.parent.iterdir()),
        "requirements": requirements.read_text(),
    }))
    output = Path(args[args.index("--save-json") + 1])
    report = {
        "report_meta": {"vulnerabilities_found": 0},
        "scanned_packages": {"locked-project-fixture": {"name": "locked-project-fixture", "version": "1.2.3"}},
        "vulnerabilities": [],
    }
mode = os.environ.get("STATIC_REPORT_MODE", "valid")
if mode == "errors":
    report["errors"] = [{"filename": "missing", "reason": "No such file or directory"}]
elif mode == "bad-results":
    report["results"] = None
elif mode == "no-meta":
    report.pop("report_meta")
elif mode == "no-packages":
    report["scanned_packages"] = {}
elif mode == "bad-vulnerabilities":
    report["vulnerabilities"] = None
elif mode == "findings":
    report["report_meta"]["vulnerabilities_found"] = 1
    report["vulnerabilities"] = [{"vulnerability_id": "offline-low-fixture", "severity": "low"}]
if mode != "missing":
    output.write_text("not json" if mode == "malformed" else json.dumps(report))
raise SystemExit(int(os.environ.get("STATIC_TOOL_EXIT", "0")))
"""


@pytest.fixture
def static_tools(sandbox):
    directory, env = sandbox
    tool = directory / "static-tool.py"
    tool.write_text(_TOOL, encoding="utf-8")
    env["STATIC_TOOL_SCRIPT"] = str(tool)
    env["RUNNER_TEMP"] = str(directory / "runner-temp")
    (directory / "runner-temp").mkdir()
    for name in ("bandit", "safety", "uv"):
        executable = directory / "bin" / name
        executable.write_text(
            '#!/bin/sh\nexec python "$STATIC_TOOL_SCRIPT" ' + name + ' "$@"\n',
            encoding="utf-8",
        )
        executable.chmod(0o700)
    return directory, env


def test_static_scans_preserve_policy_and_always_upload(static_steps):
    """Tool errors and artifact absence must not disappear behind green steps."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["security"]
    assert job["env"]["ANTHROPIC_API_KEY"] == ""
    assert job["timeout-minutes"] == 10
    assert job["permissions"] == {"security-events": "write", "contents": "read"}
    install = static_steps["Install dependencies"]["run"]
    assert "'bandit[toml]==1.9.4'" in install
    assert "'safety==3.8.1'" in install and "'uv==0.9.22'" in install
    for name in ("Run Bandit security scan", "Check dependencies for vulnerabilities"):
        step = static_steps[name]
        assert step["if"] == "always()"
        assert step["shell"] == "bash"
        assert not step.get("continue-on-error", False)
        assert "|| true" not in step["run"]
        assert 'exit "$scan_status"' in step["run"]
    for name, prefix in (("Upload Bandit results", "bandit"), ("Upload Safety results", "safety")):
        step = static_steps[name]
        assert step["if"] == "always()"
        assert step["with"]["if-no-files-found"] == "error"
        for leaf in ("report.json", "stdout.log", "stderr.log", "exit-code.txt", "validation.log"):
            assert prefix + "-" + leaf in step["with"]["path"].splitlines()
    text = (ROOT / ".github/workflows/security.yml").read_text(encoding="utf-8")
    assert static_steps["Check dependencies for vulnerabilities"]["env"] == {
        "SAFETY_API_KEY": "${{ secrets.SAFETY_API_KEY }}"
    }
    assert len(re.findall(r"\bsecrets\b", text, flags=re.IGNORECASE)) == 1
    assert "SAFETY_API_KEY" not in job["env"]
    assert all(
        "SAFETY_API_KEY" not in step.get("env", {})
        for step in job["steps"]
        if step.get("name") != "Check dependencies for vulnerabilities"
    )
    safety_run = static_steps["Check dependencies for vulnerabilities"]["run"]
    assert "env -u SAFETY_API_KEY uv export" in safety_run
    assert safety_run.count("SAFETY_API_KEY") == 1
    assert "printenv" not in safety_run and "set -x" not in safety_run
    assert not re.search(r"(?m)^\s*env\s*(?:$|[|>&;])", safety_run)
    assert "attune_llm/" not in text and "coach_wizards/" not in text


def test_bandit_positive_scans_current_paths_at_original_threshold(static_steps, static_tools):
    directory, _ = static_tools
    result = fail_closed._bash(static_steps["Run Bandit security scan"]["run"], static_tools)
    assert result.returncode == 0, result.stderr
    assert json.loads((directory / "bandit-invocation.json").read_text()) == [
        "-c",
        ".bandit",
        "-r",
        "src/",
        "attune_software/",
        "--format",
        "json",
        "--output",
        "bandit-report.json",
        "--severity-level",
        "medium",
        "--confidence-level",
        "medium",
    ]
    assert (directory / "bandit-exit-code.txt").read_text() == "0\n"
    assert "bandit fixture stdout" in (directory / "bandit-stdout.log").read_text()
    assert "bandit fixture stderr" in (directory / "bandit-stderr.log").read_text()


@pytest.mark.parametrize(
    "tool_exit,mode",
    [
        (1, "valid"),
        (2, "missing"),
        (0, "missing"),
        (0, "malformed"),
        (0, "errors"),
        (0, "bad-results"),
    ],
)
def test_bandit_errors_and_missing_reports_fail_with_evidence(
    static_steps, static_tools, tool_exit, mode
):
    directory, env = static_tools
    env.update(STATIC_TOOL_EXIT=str(tool_exit), STATIC_REPORT_MODE=mode)
    result = fail_closed._bash(static_steps["Run Bandit security scan"]["run"], static_tools)
    assert result.returncode == (tool_exit or 1)
    assert (directory / "bandit-exit-code.txt").read_text() == str(tool_exit) + "\n"
    assert "bandit fixture stdout" in (directory / "bandit-stdout.log").read_text()
    assert "bandit fixture stderr" in (directory / "bandit-stderr.log").read_text()
    if tool_exit == 0:
        assert (directory / "bandit-validation.log").read_text()


def test_safety_positive_scans_only_the_locked_project_export(static_steps, static_tools):
    directory, env = static_tools
    env["SAFETY_API_KEY"] = "offline-safety-fixture"
    result = fail_closed._bash(
        static_steps["Check dependencies for vulnerabilities"]["run"], static_tools
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((directory / "uv-key-present.json").read_text()) is False
    assert json.loads((directory / "safety-key-present.json").read_text()) is True
    export = json.loads((directory / "uv-invocation.json").read_text())
    assert export[:6] == [
        "export",
        "--locked",
        "--all-extras",
        "--no-emit-project",
        "--no-hashes",
        "-o",
    ]
    invocation = json.loads((directory / "safety-invocation.json").read_text())
    input_file = invocation[invocation.index("--file") + 1]
    assert invocation == [
        "--stage",
        "cicd",
        "check",
        "--file",
        input_file,
        "--output",
        "json",
        "--save-json",
        "safety-report.json",
        "--exit-code",
    ]
    assert export[6] == input_file
    scanned = json.loads((directory / "safety-input.json").read_text())
    assert scanned["files"] == ["requirements.txt"]
    assert scanned["requirements"] == "locked-project-fixture==1.2.3\n"
    assert (directory / "safety-requirements.txt").read_text() == scanned["requirements"]
    assert (directory / "safety-exit-code.txt").read_text() == "0\n"


@pytest.mark.parametrize(
    "tool_exit,mode",
    [
        (1, "missing"),
        (64, "findings"),
        (0, "missing"),
        (0, "malformed"),
        (0, "no-meta"),
        (0, "no-packages"),
        (0, "bad-vulnerabilities"),
        (0, "findings"),
    ],
)
def test_safety_auth_tool_and_report_failures_keep_original_evidence(
    static_steps, static_tools, tool_exit, mode
):
    directory, env = static_tools
    env.update(STATIC_TOOL_EXIT=str(tool_exit), STATIC_REPORT_MODE=mode)
    result = fail_closed._bash(
        static_steps["Check dependencies for vulnerabilities"]["run"], static_tools
    )
    assert result.returncode == (tool_exit or 1)
    assert (directory / "safety-exit-code.txt").read_text() == str(tool_exit) + "\n"
    assert (directory / "safety-requirements.txt").read_text() == "locked-project-fixture==1.2.3\n"
    assert "safety fixture stdout" in (directory / "safety-stdout.log").read_text()
    assert "safety fixture stderr" in (directory / "safety-stderr.log").read_text()
    if tool_exit == 0:
        assert (directory / "safety-validation.log").read_text()


@pytest.mark.parametrize("export_exit,empty", [(7, False), (0, True)])
def test_lock_export_failure_never_scans_a_tool_environment(
    static_steps, static_tools, export_exit, empty
):
    directory, env = static_tools
    env["STATIC_EXPORT_EXIT"] = str(export_exit)
    if empty:
        env["STATIC_EMPTY_EXPORT"] = "1"
    result = fail_closed._bash(
        static_steps["Check dependencies for vulnerabilities"]["run"], static_tools
    )
    assert result.returncode == (export_exit or 1)
    assert not (directory / "safety-invocation.json").exists()
    assert (directory / "safety-export-exit-code.txt").read_text() == str(export_exit) + "\n"
    assert "uv fixture stdout" in (directory / "safety-export-stdout.log").read_text()
    assert "uv fixture stderr" in (directory / "safety-export-stderr.log").read_text()
