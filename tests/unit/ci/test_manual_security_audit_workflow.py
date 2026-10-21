"""Offline controls for the exact manual audit workflow scripts.

These exercise local stubs, not GitHub triggers, authentication, or a real SDK
audit. They do not establish that a GitHub check has passed.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/security-audit-manual.yml"


def steps():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["audit"]["steps"]


def step(name):
    return next(s for s in steps() if s["name"] == name)


def _posix_shell():
    if os.name != "posix":
        pytest.skip("This Ubuntu workflow's bash controls require POSIX")


def _node_env():
    env = {"PATH": os.defpath}
    if os.name == "nt":
        env["SystemRoot"] = os.environ["SystemRoot"]
    return env


_NODE_SPAWNS = 0


def _run_node(node: str, script: Path, values: dict, stage: Path):
    """Keep the original child protocol and retain stage evidence on timeout."""
    global _NODE_SPAWNS
    _NODE_SPAWNS += 1
    started = time.monotonic()
    try:
        return subprocess.run(
            [node, str(script), json.dumps(values), str(stage)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            env=_node_env(),
        )
    except subprocess.TimeoutExpired as error:
        stages = (
            stage.read_text(encoding="utf-8", errors="replace") if stage.is_file() else "<absent>"
        )
        pytest.fail(
            "Node control exceeded its original 10-second limit; "
            f"node={node!r}; spawn_ordinal={_NODE_SPAWNS}; "
            f"elapsed={time.monotonic() - started:.3f}s; stages={stages!r}; "
            f"stdout={error.stdout!r}; stderr={error.stderr!r}"
        )


def complete():
    return {
        "schema_version": "security-audit/v1",
        "workflow": "security-audit",
        "success": True,
        "audit_complete": True,
        "sdk_completion": {"subtype": "success", "is_error": False, "stop_reason": "end_turn"},
        "summary": {"text": "Fixture only; no real audit ran"},
        "findings": [],
        "suggestions": [],
    }


def test_manual_trust_and_spend_boundaries():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert set(doc.get("on", doc.get(True))) == {"workflow_dispatch"}
    assert doc["permissions"] == {"contents": "read", "pull-requests": "read"}
    inputs = doc.get("on", doc.get(True))["workflow_dispatch"]["inputs"]
    assert inputs["authorize_spend"]["default"] is False
    assert doc["concurrency"]["cancel-in-progress"] is False
    scan = step("Run one authenticated audit")
    assert scan["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY }}"
    assert scan["env"]["ATTUNE_MAX_BUDGET_USD"] == "10"
    assert scan["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert "--depth standard" in scan["run"]
    assert "--input '{\"max_budget_usd\":10}'" in scan["run"]
    assert "1800s" in scan["run"]
    assert step("Checkout the reviewed source")["with"] == {
        "ref": "${{ steps.identity.outputs.sha }}",
        "persist-credentials": False,
    }
    assert not any("checks: write" in str(s) or "createCheck" in str(s) for s in steps())
    assert not any("cache" in s.get("with", {}) for s in steps())
    assert "permissions" not in doc["jobs"]["audit"]
    assert "environment" not in doc["jobs"]["audit"]
    assert doc["name"] not in {"Run Security Scanner", "Security Scan"}
    assert doc["jobs"]["audit"]["name"] not in {"Run Security Scanner", "Security Scan"}
    assert scan["continue-on-error"] is True
    assert (
        step("Reject incomplete audits and critical findings")["env"]["SCAN_OUTCOME"]
        == "${{ steps.scan.outcome }}"
    )
    assert "steps.redact.outcome == 'success'" in step("Retain audit evidence")["if"]
    install = step("Install the locked noneditable package without model credentials")
    assert install["env"]["UV_NO_CACHE"] == "1"
    assert install["env"]["ANTHROPIC_API_KEY"] == ""
    assert install["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert install["env"]["UV_PROJECT_ENVIRONMENT"] == "${{ runner.temp }}/manual-security-venv"
    for item in steps():
        assert re.search(r"python3 -(?!I -)", item.get("run", "")) is None
        assert "${{" not in item.get("run", "")
        assert "${{" not in item.get("with", {}).get("script", "")
        if "uses" in item:
            assert re.fullmatch(r".+@[0-9a-f]{40}", item["uses"])


@pytest.mark.parametrize(
    "change,approved",
    [
        ({}, True),
        ({"event": "pull_request"}, False),
        ({"ref": "refs/heads/topic"}, False),
        ({"spend": "false"}, False),
        ({"number": "1; touch injected"}, False),
        ({"sha": "a" * 39}, False),
        ({"head": "b" * 40}, False),
        ({"repo": "fork/repo"}, False),
        ({"state": "closed"}, False),
        ({"base": "topic"}, False),
        ({"attempt": "2"}, False),
        ({"null_repo": True}, False),
        ({"api_error": True}, False),
        ({"sha": "A" * 40}, False),
        ({"spend": "TRUE"}, False),
        ({"number": "0"}, False),
        ({"number": "02553"}, False),
    ],
)
def test_exact_identity_script(tmp_path, change, approved):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the offline JavaScript action controls")
    values = {
        "event": "workflow_dispatch",
        "ref": "refs/heads/main",
        "spend": "true",
        "number": "2553",
        "sha": "a" * 40,
        "head": "a" * 40,
        "repo": "owner/repo",
        "state": "open",
        "base": "main",
        "attempt": "1",
    }
    values.update(change)
    script = step("Validate approval and reviewed head")["with"]["script"]
    harness = """
require('fs').appendFileSync(process.argv[3], `start pid=${process.pid} node=${process.version}\\n`);
console.error(`identity:start pid=${process.pid} node=${process.version}`);
const v = JSON.parse(process.argv[2]);
const context = {eventName:v.event, ref:v.ref, repo:{owner:'owner',repo:'repo'}};
process.env.PR_NUMBER=v.number;process.env.REVIEWED_SHA=v.sha;
process.env.SPEND_APPROVED=v.spend;
process.env.RUN_ATTEMPT=v.attempt;
const outputs=[], calls=[];
const core={setOutput:(name,value)=>outputs.push([name,value])};
const github={rest:{pulls:{get:async(args)=>{
 calls.push(args);if(v.api_error)throw Error('404');
 return {data:{state:v.state,head:{sha:v.head,repo:v.null_repo?null:{full_name:v.repo}},
 base:{ref:v.base}}};
}}}};
(async()=>{ require("fs").appendFileSync(process.argv[3], "validate\\n"); console.error("identity:validate"); SCRIPT })().catch(e=>{console.error(e.message);process.exitCode=1;})
 .finally(()=>{require("fs").appendFileSync(process.argv[3], "complete\\n");console.error("identity:complete");console.log(JSON.stringify({outputs,calls}));});
""".replace(
        "SCRIPT", script
    )
    test = tmp_path / "identity.js"
    test.write_text(harness, encoding="utf-8")
    result = _run_node(node, test, values, tmp_path / "stage.log")
    assert (result.returncode == 0) is approved, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["outputs"] == ([["sha", values["sha"]]] if approved else [])
    if approved or evidence["calls"]:
        assert evidence["calls"] == [{"owner": "owner", "repo": "repo", "pull_number": 2553}]
    assert not (tmp_path / "injected").exists()


@pytest.mark.parametrize(
    "case",
    [
        "complete",
        "preamble",
        "no_auth",
        "partial",
        "budget",
        "wrong_schema",
        "missing_terminal",
        "missing_finding_fields",
        "trailing",
        "nonzero",
        "finding",
        "failure_one",
        "failure_zero",
        "is_error",
        "bool_line",
        "upper_severity",
        "empty_summary",
        "duplicate",
        "nonfinite",
        "credential_leak",
    ],
)
def test_actual_audit_shell_fails_closed(tmp_path, case):
    _posix_shell()
    payload = complete()
    exit_code = 0
    if case == "partial":
        payload["audit_complete"] = False
    if case == "budget":
        payload["sdk_completion"]["stop_reason"] = "max_tokens"
    if case == "wrong_schema":
        payload["schema_version"] = "other"
    if case == "missing_terminal":
        del payload["sdk_completion"]
    if case == "missing_finding_fields":
        payload["findings"] = [{"severity": "high"}]
    if case in {"finding", "bool_line", "upper_severity"}:
        payload["findings"] = [
            {
                "file": "a.py",
                "line": 3,
                "severity": "high",
                "description": "x",
                "category": "c",
                "type": "c",
            }
        ]
    if case == "bool_line":
        payload["findings"][0]["line"] = True
    if case == "upper_severity":
        payload["findings"][0]["severity"] = "CRITICAL"
    if case == "is_error":
        payload["sdk_completion"]["is_error"] = True
    if case == "empty_summary":
        payload["summary"]["text"] = " "
    if case in {"failure_one", "failure_zero"}:
        payload = {"success": False, "audit_complete": False, "error": "Incomplete SDK audit"}
        exit_code = int(case == "failure_one")
    raw = json.dumps(payload)
    if case == "no_auth":
        raw, exit_code = "No auth found — workflows make LLM calls.\n", 3
    if case == "nonzero":
        exit_code = 7
    if case == "preamble":
        raw = "\n🚀 Running workflow: security-audit\n\n" + raw
    if case == "trailing":
        raw += "\ntrailing text"
    if case == "duplicate":
        raw = raw.replace('"success": true', '"success": false, "success": true')
    if case == "nonfinite":
        raw = raw.replace('"suggestions": []', '"suggestions": [], "extra": NaN')
    evidence = tmp_path / "manual-security-evidence"
    evidence.mkdir()
    binary = tmp_path / "bin"
    binary.mkdir()
    workspace = tmp_path / "source"
    workspace.mkdir()
    venv_bin = tmp_path / "manual-security-venv/bin"
    venv_bin.mkdir(parents=True)
    fixture = tmp_path / "fixture.txt"
    fixture.write_text(raw, encoding="utf-8")
    cli = venv_bin / "attune"
    cli.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$CLI_ARGS"\ncat "$FIXTURE"\nif [ "$LEAK" = yes ]; then printf "%s" "$ANTHROPIC_API_KEY" >&2; fi\nexit "$FIXTURE_EXIT"\n',
        encoding="utf-8",
    )
    cli.chmod(0o700)
    timeout = binary / "timeout"
    timeout.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$TIMEOUT_ARGS"\nshift 3\nexec "$@"\n', encoding="utf-8"
    )
    timeout.chmod(0o700)
    (binary / "python3").symlink_to(sys.executable)
    script = tmp_path / "scan.sh"
    # The suite guard clears Popen credentials. This owned stub receives only
    # a literal synthetic value inside the child; no real inference is invoked.
    script.write_text(
        "export ANTHROPIC_API_KEY=fixture-only\n" + step("Run one authenticated audit")["run"],
        encoding="utf-8",
    )
    env = {
        "PATH": str(binary) + ":/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "FIXTURE": str(fixture),
        "FIXTURE_EXIT": str(exit_code),
        "RUNNER_TEMP": str(tmp_path),
        "CLI_ARGS": str(tmp_path / "cli-args"),
        "TIMEOUT_ARGS": str(tmp_path / "timeout-args"),
        "LEAK": "yes" if case == "credential_leak" else "no",
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=evidence,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    valid = case in {"complete", "preamble", "finding", "nonzero", "credential_leak"}
    assert (result.returncode == 0) is (valid and exit_code == 0), result.stderr
    assert (evidence / "scanner-exit.txt").read_text().strip() == str(exit_code)
    assert (evidence / "security_results_raw.txt").read_bytes() == raw.encode()
    assert f"scan_exit={exit_code}" in (tmp_path / "outputs").read_text()
    exported = json.loads((evidence / "security_results.json").read_text())
    assert exported == (
        payload if valid else {"error": "SDK audit did not produce a completed supported result"}
    )
    argv = [
        "workflow",
        "run",
        "security-audit",
        "--path",
        str(workspace),
        "--depth",
        "standard",
        "--input",
        '{"max_budget_usd":10}',
        "--json",
    ]
    assert (tmp_path / "cli-args").read_text().splitlines() == argv
    assert (tmp_path / "timeout-args").read_text().splitlines() == [
        "--signal=TERM",
        "--kill-after=30s",
        "1800s",
        str(cli),
        *argv,
    ]
    if case == "credential_leak":
        stderr = evidence / "security_scan_stderr.log"
        assert stderr.read_text() == "fixture-only"
        sanitizer = tmp_path / "sanitize.sh"
        sanitizer.write_text(
            "export ANTHROPIC_API_KEY=fixture-only\n"
            + step("Redact credential bytes before artifact upload")["run"],
            encoding="utf-8",
        )
        scrub = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(sanitizer)],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        assert scrub.returncode == 0, scrub.stderr
        assert stderr.read_text() == "[REDACTED]"


@pytest.mark.parametrize(
    "outcome,critical,git_exit,success",
    [
        ("success", False, 0, True),
        ("failure", False, 0, False),
        ("success", True, 0, False),
        ("success", False, 1, False),
        ("skipped", False, 0, False),
        ("cancelled", False, 0, False),
    ],
)
def test_final_verdict_uses_actual_scanner_outcome(tmp_path, outcome, critical, git_exit, success):
    _posix_shell()
    result = complete()
    if critical:
        result["findings"] = [{"severity": "critical"}]
    (tmp_path / "security_results.json").write_text(json.dumps(result), encoding="utf-8")
    binary = tmp_path / "bin"
    binary.mkdir()
    git = binary / "git"
    git.write_text(f"#!/bin/sh\nexit {git_exit}\n", encoding="utf-8")
    git.chmod(0o700)
    (binary / "python3").symlink_to(sys.executable)
    script = tmp_path / "verdict.sh"
    script.write_text(
        step("Reject incomplete audits and critical findings")["run"], encoding="utf-8"
    )
    response = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=tmp_path,
        env={
            "PATH": str(binary) + ":/usr/bin:/bin",
            "SCAN_OUTCOME": outcome,
            "GITHUB_WORKSPACE": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert (response.returncode == 0) is success


@pytest.mark.parametrize("key", ["", " \t\n"])
def test_missing_credential_does_not_start_child(tmp_path, key):
    _posix_shell()
    script = tmp_path / "scan.sh"
    script.write_text(
        f"export ANTHROPIC_API_KEY={shlex.quote(key)}\n"
        + step("Run one authenticated audit")["run"],
        encoding="utf-8",
    )
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode != 0
    assert "no audit was run" in result.stdout
    assert not (tmp_path / "security_results_raw.txt").exists()


@pytest.mark.parametrize("case", ["literal", "symlink", "whitespace", "missing"])
def test_sanitation_gates_artifact_upload(tmp_path, case):
    _posix_shell()
    evidence = tmp_path / "manual-security-evidence"
    evidence.mkdir()
    fake_key = "synthetic-review-only-key" + ("\n" if case == "whitespace" else "")
    for name in ("security_results_raw.txt", "security_scan_stderr.log"):
        (evidence / name).write_text(fake_key.strip(), encoding="utf-8")
    if case == "symlink":
        (evidence / "link").symlink_to(evidence / "security_results_raw.txt")
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "python3").symlink_to(sys.executable)
    for name in ("pathlib.py", "json.py"):
        (tmp_path / name).write_text(
            "open('shadow-imported', 'w').write('bad')\nraise RuntimeError('shadow import')\n",
            encoding="utf-8",
        )
    script = tmp_path / "sanitize.sh"
    script.write_text(
        f"export ANTHROPIC_API_KEY={shlex.quote('' if case == 'missing' else fake_key)}\n"
        + step("Redact credential bytes before artifact upload")["run"],
        encoding="utf-8",
    )
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=tmp_path,
        env={
            "PATH": str(binary) + ":/usr/bin:/bin",
            "RUNNER_TEMP": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert (result.returncode == 0) is (case in {"literal", "whitespace"})
    assert not (tmp_path / "shadow-imported").exists()
    if case in {"literal", "whitespace"}:
        assert all(fake_key.strip().encode() not in p.read_bytes() for p in evidence.iterdir())


@pytest.mark.parametrize(
    "change,success",
    [
        ({}, True),
        ({"head": "b" * 40}, False),
        ({"state": "closed"}, False),
        ({"base": "topic"}, False),
        ({"repo": "fork/repo"}, False),
        ({"repo": None}, False),
    ],
)
def test_post_run_head_script(tmp_path, change, success):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the offline JavaScript action controls")
    values = {"head": "a" * 40, "state": "open", "base": "main", "repo": "owner/repo"}
    values.update(change)
    script = step("Refuse a result for a changed PR head")["with"]["script"]
    harness = """
require('fs').appendFileSync(process.argv[3], `start pid=${process.pid} node=${process.version}\\n`);
const v=JSON.parse(process.argv[2]);
const context={repo:{owner:'owner',repo:'repo'}};
process.env.PR_NUMBER='2553';process.env.REVIEWED_SHA='a'.repeat(40);
const calls=[];
const github={rest:{pulls:{get:async(args)=>{calls.push(args);return {data:{state:v.state,
head:{sha:v.head,repo:v.repo===null?null:{full_name:v.repo}},base:{ref:v.base}}};}}}};
(async()=>{require("fs").appendFileSync(process.argv[3], "validate\\n"); SCRIPT })().catch(e=>{console.error(e.message);process.exitCode=1;})
 .finally(()=>{require("fs").appendFileSync(process.argv[3], "complete\\n");console.log(JSON.stringify(calls));});
""".replace(
        "SCRIPT", script
    )
    target = tmp_path / "post.js"
    target.write_text(harness, encoding="utf-8")
    result = _run_node(node, target, values, tmp_path / "stage.log")
    assert (result.returncode == 0) is success, result.stderr
    assert json.loads(result.stdout) == [{"owner": "owner", "repo": "repo", "pull_number": 2553}]


@pytest.mark.parametrize("matches", [True, False])
def test_install_identity_bindings_without_installing(tmp_path, matches):
    _posix_shell()
    item = step("Install the locked noneditable package without model credentials")
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "python3").symlink_to(sys.executable)
    stubs = {
        "python": '#!/bin/sh\nprintf "%s\\n" "$@" > "$PIP_ARGS"\n',
        "uv": '#!/bin/sh\nprintf "%s\\n" "$@" > "$UV_ARGS"\nprintf "%s\\n" "$UV_PROJECT_ENVIRONMENT" "$UV_NO_CACHE" "$ANTHROPIC_API_KEY" > "$UV_ENV"\n',
        "git": '#!/bin/sh\nif [ "$1" = rev-parse ]; then printf "%s\\n" "$FAKE_HEAD"; fi\n',
    }
    for name, text in stubs.items():
        p = binary / name
        p.write_text(text, encoding="utf-8")
        p.chmod(0o700)
    values = {
        "CONTROLLER_SHA": "c" * 40,
        "RUN_ID": "123",
        "RUN_ATTEMPT": "1",
        "ACTOR": "fixture-actor",
        "PR_NUMBER": "2553",
        "REVIEWED_SHA": "a" * 40,
        "SPEND_APPROVED": "true",
    }
    env = {
        **values,
        "PATH": str(binary) + ":/usr/bin:/bin",
        "RUNNER_TEMP": str(tmp_path),
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_CODE_OAUTH_TOKEN": "",
        "UV_NO_CACHE": "1",
        "UV_PROJECT_ENVIRONMENT": str(tmp_path / "manual-security-venv"),
        "FAKE_HEAD": ("a" if matches else "b") * 40,
        "PIP_ARGS": str(tmp_path / "pip-args"),
        "UV_ARGS": str(tmp_path / "uv-args"),
        "UV_ENV": str(tmp_path / "uv-env"),
    }
    script = tmp_path / "install.sh"
    script.write_text(item["run"], encoding="utf-8")
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert (result.returncode == 0) is matches, result.stderr
    receipt = tmp_path / "manual-security-evidence/run-identity.json"
    if matches:
        assert json.loads(receipt.read_text()) == values
        assert (receipt.parent / "audited-sha.txt").read_text().strip() == values["REVIEWED_SHA"]
    else:
        assert not receipt.exists()
    assert (tmp_path / "pip-args").read_text().splitlines() == [
        "-m",
        "pip",
        "install",
        "--no-cache-dir",
        "uv==0.9.22",
    ]
    assert (tmp_path / "uv-args").read_text().splitlines() == [
        "sync",
        "--locked",
        "--no-dev",
        "--no-editable",
    ]
    assert (tmp_path / "uv-env").read_text().splitlines() == [
        str(tmp_path / "manual-security-venv"),
        "1",
        "",
    ]
