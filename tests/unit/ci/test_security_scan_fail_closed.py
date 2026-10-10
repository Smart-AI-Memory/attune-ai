"""Execute the security workflow boundary with local CLI and GitHub API stubs.

No SDK/auth/provider call is made. The bash step runs with Actions' -e/pipefail
semantics; the real analyzer and check JavaScript run as subprocesses.
SECURITY_SCAN_WORKFLOW permits local negative-control/mutation receipts without
editing the checked-in workflow. It is a read-only YAML input override.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = Path(
    os.environ.get("SECURITY_SCAN_WORKFLOW", ROOT / ".github/workflows/security-scan.yml")
)
NO_AUTH = (
    "\n🔑 No auth found — workflows make LLM calls and need one of these:\n"
    "   - Claude Code (subscription): install it (npm install -g @anthropic-ai/claude-code), "
    "run `claude` once to log in, then re-run this workflow.\n"
    "   - API key: export ANTHROPIC_API_KEY=... and re-run.\n"
    "   For guided configuration: attune auth setup\n"
    "   Setup fight you? https://github.com/Smart-AI-Memory/attune-ai/discussions/1325\n"
)


@pytest.fixture
def steps():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return {step["name"]: step for step in workflow["jobs"]["security-scan"]["steps"]}


@pytest.fixture
def sandbox(tmp_path):
    """Expose only the stub CLI and known local runtimes, with no inherited auth."""
    if os.name != "posix":
        pytest.skip("This ubuntu-latest workflow's bash execution harness requires POSIX")
    node = shutil.which("node")
    assert node, "Node is needed to execute actions/github-script's actual JavaScript"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("python", "python3"):
        (bindir / name).symlink_to(sys.executable)
    (bindir / "node").symlink_to(node)
    cli = bindir / "attune"
    cli.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" > "$STUB_INVOCATION"\n'
        'cat "$STUB_STDOUT"\ncat "$STUB_STDERR" >&2\nexit "$STUB_EXIT"\n',
        encoding="utf-8",
    )
    cli.chmod(0o700)
    env = {
        "PATH": f"{bindir}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GITHUB_OUTPUT": str(tmp_path / "github-output.txt"),
        "STUB_INVOCATION": str(tmp_path / "stub-invocation.txt"),
        "STUB_STDOUT": str(tmp_path / "stub-stdout.txt"),
        "STUB_STDERR": str(tmp_path / "stub-stderr.txt"),
        "STUB_EXIT": "0",
    }
    # Fixed tmp_path descendants; no user-controlled write destination.
    (tmp_path / "stub-stdout.txt").write_text("", encoding="utf-8")
    (tmp_path / "stub-stderr.txt").write_text("", encoding="utf-8")
    (tmp_path / "github-output.txt").touch()
    return tmp_path, env


def _bash(script, sandbox):
    directory, env = sandbox
    script_file = directory / "workflow-step.sh"
    script_file.write_text(script, encoding="utf-8")
    return subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(script_file)],
        cwd=directory,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )


def _check(
    steps,
    sandbox,
    *,
    scan_outcome="success",
    scan_status="success",
    scan_exit="0",
    analysis_outcome="success",
    api_error=False,
):
    directory, env = sandbox
    script = steps["Create check run"]["with"]["script"]
    harness = directory / "check-harness.js"
    harness.write_text(
        "const state = {payload: null, failures: []};\n"
        "const core = {setFailed: message => {state.failures.push(message); process.exitCode = 1;}};\n"
        "const context = {repo: {owner: 'stub', repo: 'stub'}, sha: 'local-fixture'};\n"
        "const github = {rest: {checks: {create: async payload => {\n"
        "  state.payload = payload;\n"
        "  if (process.env.STUB_API_ERROR === '1') throw new Error('Stub HTTP 500');\n"
        "}}}};\n"
        "async function main() {\n" + script + "\n}\n"
        "main().catch(error => {state.error = error.message; process.exitCode = 1;})\n"
        ".finally(() => console.log(JSON.stringify(state)));\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["node", str(harness)],
        cwd=directory,
        env={
            **env,
            "SCAN_OUTCOME": scan_outcome,
            "SCAN_STATUS": scan_status,
            "SCAN_EXIT": scan_exit,
            "ANALYSIS_OUTCOME": analysis_outcome,
            "STUB_API_ERROR": "1" if api_error else "0",
        },
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.stdout.strip(), result.stderr
    return result, json.loads(result.stdout)


def _pipeline(steps, sandbox, output, exit_code=0, *, api_error=False):
    directory, env = sandbox
    (directory / "stub-stdout.txt").write_text(output, encoding="utf-8")
    env["STUB_EXIT"] = str(exit_code)
    scan = _bash(steps["Run security audit"]["run"], sandbox)
    assert (directory / "stub-invocation.txt").read_text().strip() == (
        "workflow run security-audit --json"
    )
    outputs = dict(
        line.split("=", 1) for line in (directory / "github-output.txt").read_text().splitlines()
    )
    ensured = _bash(steps["Ensure results file exists"]["run"], sandbox)
    assert ensured.returncode == 0, ensured.stderr
    analyze = subprocess.run(
        [
            sys.executable,
            str(ROOT / ".github/scripts/analyze_security_results.py"),
            "--input",
            "security_results.json",
            "--output",
            "analysis.json",
            "--github-output",
            env["GITHUB_OUTPUT"],
        ],
        cwd=directory,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    check, state = _check(
        steps,
        sandbox,
        scan_outcome="success" if scan.returncode == 0 else "failure",
        scan_status=outputs.get("scan_status", ""),
        scan_exit=outputs.get("scan_exit", ""),
        analysis_outcome="success" if analyze.returncode == 0 else "failure",
        api_error=api_error,
    )
    return scan, outputs, check, state


@pytest.mark.parametrize("exit_code", [1, 2, 3, 127])
def test_nonzero_scan_with_valid_empty_findings_fails(steps, sandbox, exit_code):
    scan, outputs, check, state = _pipeline(steps, sandbox, '{"findings": []}', exit_code)
    assert outputs.get("scan_exit") == str(exit_code)
    assert scan.returncode != 0
    assert check.returncode != 0
    assert state["failures"]
    assert state["payload"]["conclusion"] == "failure"
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


@pytest.mark.parametrize(
    "output",
    [
        "",
        "not JSON",
        '{"findings":',
        "null",
        "[]",
        "{}",
        '{"findings": {}}',
        '{"findings": [null]}',
        '{"findings": [], "error": "No auth"}',
        '{"findings": [{"severity": "critical"}], "error": ""}',
        '{"findings": [{"severity": "critical"}], "error": null}',
        '{"findings": [], "scan_skipped": true}',
        '{"findings": [], "success": false}',
        '{"findings": [], "exit_code": 3}',
        '{"exit_code": 0, "success": true, "result": "WorkflowResult(...)"}',
        'Progress\n{"success":false,"result":{"findings":[]}',
        'Progress\n{"success":false,"result":\n{"findings":[]}',
        '{"findings": []} trailing text',
        '{"findings": [{"severity": "unsupported"}]}',
    ],
    ids=[
        "empty",
        "text",
        "truncated",
        "null",
        "array",
        "missing-findings",
        "wrong-findings",
        "bad-finding",
        "error",
        "empty-error-with-critical",
        "null-error-with-critical",
        "skipped",
        "unsuccessful",
        "exit-mismatch",
        "sdk-envelope",
        "truncated-outer-object",
        "truncated-outer-multiline",
        "trailing-data",
        "unsupported-severity",
    ],
)
def test_invalid_output_with_zero_exit_fails(steps, sandbox, output):
    _, _, check, state = _pipeline(steps, sandbox, output)
    assert check.returncode != 0
    assert state["payload"]["conclusion"] == "failure"
    assert "Findings are unavailable" in state["payload"]["output"]["summary"]
    directory, _ = sandbox
    assert not (directory / "pr_comment.md").exists()


def test_retained_no_auth_exit_three_fails_even_if_posting_fails(steps, sandbox):
    scan, outputs, check, state = _pipeline(steps, sandbox, NO_AUTH, 3, api_error=True)
    assert state["payload"]["conclusion"] == "failure"
    assert outputs.get("scan_exit") == "3"
    assert scan.returncode != 0 and check.returncode != 0
    assert state["failures"]
    assert state["error"] == "Stub HTTP 500"
    assert "No blocking issues" not in state["payload"]["output"]["summary"]


@pytest.mark.parametrize("prefix", ["", "Progress {panel}\n"])
def test_completed_zero_findings_is_explicit(steps, sandbox, prefix):
    scan, outputs, check, state = _pipeline(steps, sandbox, prefix + '{"findings": []}')
    assert scan.returncode == check.returncode == 0
    assert outputs.get("scan_exit") == "0"
    assert state["failures"] == []
    assert state["payload"]["conclusion"] == "success"
    assert state["payload"]["output"]["title"] == "Security Scan Completed — No Findings"


@pytest.mark.parametrize(
    "severity, conclusion", [("low", "success"), ("medium", "success"), ("critical", "failure")]
)
def test_existing_finding_policy_survives(steps, sandbox, severity, conclusion):
    output = "Progress\n" + json.dumps(
        {
            "findings": [
                {"severity": severity, "file": "é.py", "type": "fixture", "match": "a } b { c"},
            ]
        }
    )
    scan, _, check, state = _pipeline(steps, sandbox, output)
    assert scan.returncode == check.returncode == 0
    assert state["payload"]["conclusion"] == conclusion
    if severity == "critical":
        block = steps["Block on critical findings"]
        assert block["if"] == (
            "steps.analyze.outputs.has_critical == 'true' && "
            "steps.check_bypass.outputs.has_bypass != 'true'"
        )
        assert (
            _bash(
                block["run"].replace("${{ steps.analyze.outputs.critical_count }}", "1"), sandbox
            ).returncode
            == 1
        )


@pytest.mark.parametrize(
    "analysis",
    [
        None,
        "not JSON",
        "null",
        "[]",
        "{}",
        '{"total_findings": 0, "critical_count": 0, "medium_count": 0, "low_count": 0, '
        '"has_critical": false, "has_bypass": true, "scan_skipped": true}',
    ],
)
def test_missing_or_invalid_analysis_fails_even_with_bypass(steps, sandbox, analysis):
    directory, _ = sandbox
    if analysis is not None:
        (directory / "analysis.json").write_text(analysis, encoding="utf-8")
    check, state = _check(steps, sandbox)
    assert check.returncode != 0
    assert state["failures"]
    assert state["payload"]["conclusion"] == "failure"


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"error": "Provider failure"},
        {"error": ""},
        {"error": None},
        {"error": False},
        {"error": 0},
        {"critical_count": -1},
        {"total_findings": None},
        {"has_critical": "false"},
        {"has_bypass": "true"},
        {"has_critical": True},
        {"critical_count": 1},
        {"medium_count": 1},
        {"total_findings": 1},
    ],
)
def test_invalid_analysis_contract_fails(steps, sandbox, invalid_fields):
    directory, _ = sandbox
    analysis = {
        "total_findings": 0,
        "critical_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "has_critical": False,
        "has_bypass": True,
        **invalid_fields,
    }
    (directory / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    check, state = _check(steps, sandbox)
    assert check.returncode != 0
    assert state["payload"]["conclusion"] == "failure"


@pytest.mark.parametrize(
    "overrides",
    [
        {"scan_outcome": "failure"},
        {"scan_outcome": "skipped"},
        {"scan_outcome": "cancelled"},
        {"scan_status": ""},
        {"scan_exit": ""},
        {"scan_exit": "3"},
        {"analysis_outcome": "failure"},
        {"analysis_outcome": "skipped"},
    ],
)
def test_failed_or_missing_step_metadata_cannot_pass(steps, sandbox, overrides):
    _pipeline(steps, sandbox, '{"findings": []}')
    check, state = _check(steps, sandbox, **overrides)
    assert check.returncode != 0
    assert state["payload"]["conclusion"] == "failure"


def test_check_observes_raw_outcome_not_masked_conclusion(steps):
    """Platform-independent guard: continue-on-error cannot erase failure evidence."""
    check = steps["Create check run"]
    assert check["if"] == "always()"
    assert check["env"] == {
        "SCAN_OUTCOME": "${{ steps.security_scan.outcome }}",
        "SCAN_STATUS": "${{ steps.security_scan.outputs.scan_status }}",
        "SCAN_EXIT": "${{ steps.security_scan.outputs.scan_exit }}",
        "ANALYSIS_OUTCOME": "${{ steps.analyze.outcome }}",
    }
    comment_condition = steps["Post results to PR"]["if"]
    assert "steps.security_scan.outcome == 'success'" in comment_condition
    assert "steps.security_scan.outputs.scan_status == 'success'" in comment_condition
