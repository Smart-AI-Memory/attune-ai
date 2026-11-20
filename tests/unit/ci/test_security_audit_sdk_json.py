"""Exercise the real security CLI, SDK result collector, and workflow consumer offline.

The child process replaces only the SDK query and non-target host services.
It never runs the real provider or reads host authentication. These controls
are source proposals until independently reviewed, applied, and executed.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.ci import test_security_scan_fail_closed as fail_closed
from tests.unit.ci.test_security_scan_fail_closed import (  # noqa: F401
    _check,
    _pipeline,
)

sandbox = fail_closed.sandbox
steps = fail_closed.steps

ROOT = Path(__file__).resolve().parents[3]

_CLI_RUNNER = """\
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime

import claude_agent_sdk
from claude_agent_sdk.types import DeferredToolUse
from attune import cli_minimal
from attune.cli_commands import workflow_commands
from attune.telemetry import usage_ping
from attune.workflows import security_audit, security_audit_json

fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
boundary = {"query_calls": 0, "auth_calls": 0, "spend_calls": 0}

def no_host_notice(*args, **kwargs):
    return None

cli_minimal.first_run_memory_notice = no_host_notice
usage_ping.maybe_prompt_consent = no_host_notice
security_audit.SecurityAuditWorkflow._track_sdk_run_telemetry = no_host_notice
security_audit.SecurityAuditWorkflow._emit_workflow_telemetry = no_host_notice
if fixture.get("freeze_clock"):
    fixed_time = datetime(2026, 1, 1, 0, 0, 0)
    security_audit.datetime = SimpleNamespace(now=lambda: fixed_time)

async def no_transcript_read(session_id):
    return {}

security_audit.collect_subagent_transcripts = no_transcript_read

async def local_query(*args, **kwargs):
    boundary["query_calls"] += 1
    boundary["schema"] = kwargs["options"].output_format
    for result in fixture.get("results", []):
        yield claude_agent_sdk.ResultMessage(
            subtype=result.get("subtype", "success"),
            duration_ms=1,
            duration_api_ms=1,
            is_error=result.get("is_error", False),
            num_turns=1,
            session_id="offline-sdk-fixture",
            total_cost_usd=0.0,
            usage={"input_tokens": 0, "output_tokens": 0},
            result="## Summary\\nA human report",
            structured_output=result.get("structured_output"),
            stop_reason=result.get("stop_reason"),
            errors=result.get("errors"),
            terminal_reason=result.get("terminal_reason", "completed"),
            origin=result.get("origin"),
            api_error_status=result.get("api_error_status"),
            deferred_tool_use=(
                DeferredToolUse(**result["deferred_tool_use"])
                if result.get("deferred_tool_use") is not None
                else None
            ),
        )
    if fixture.get("connection_error"):
        raise ConnectionError("Offline SDK connection failure")

security_audit.claude_agent_sdk.query = local_query

if not fixture.get("no_auth"):
    def offline_auth():
        boundary["auth_calls"] += 1
        return None

    def offline_spend(*args, **kwargs):
        boundary["spend_calls"] += 1
        return (3, False) if fixture.get("spend_refused") else (None, False)

    workflow_commands._auth_preflight = offline_auth
    workflow_commands._spend_gate_check = offline_spend

if fixture.get("serialization_failure"):
    def refuse_serialization(*args, **kwargs):
        raise TypeError("offline serialization failure")

    security_audit_json.json = SimpleNamespace(dumps=refuse_serialization)

try:
    argv = ["workflow", "run", "security-audit", "--path", "."]
    if not fixture.get("human"):
        argv.append("--json")
    exit_code = cli_minimal.main(argv)
finally:
    Path("boundary.json").write_text(json.dumps(boundary), encoding="utf-8")
raise SystemExit(exit_code)
"""


def _structured(findings=None):
    return {
        "audit_complete": True,
        "summary": {"text": "Completed offline fixture", "score": 90},
        "findings": {} if findings is None else findings,
        "suggestions": [],
    }


def _finding(severity="high"):
    return {
        "file": "src/é.py",
        "line": 42,
        "severity": severity,
        "description": "Complete {braces} finding with Unicode é.",
    }


def _run_cli(tmp_path, fixture):
    """Run the actual CLI main/exit path with a local SDK query replacement."""
    directory = tmp_path / "cli"
    directory.mkdir()
    (directory / "home").mkdir()
    (directory / "runner.py").write_text(_CLI_RUNNER, encoding="utf-8")
    config = directory / "fixture.json"
    config.write_text(json.dumps(fixture), encoding="utf-8")
    env = {
        "PATH": os.defpath,
        "HOME": str(directory / "home"),
        "USERPROFILE": str(directory / "home"),
        "TMPDIR": str(directory),
        "TEMP": str(directory),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_CODE_OAUTH_TOKEN": "",
        "CI": "true",
    }
    if os.name == "nt":
        env["SystemRoot"] = os.environ["SystemRoot"]
    result = subprocess.run(
        [sys.executable, str(directory / "runner.py"), str(config)],
        cwd=directory,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )
    boundary = json.loads((directory / "boundary.json").read_text(encoding="utf-8"))
    return result, boundary


def _payload(stdout):
    start = stdout.find("\n{")
    assert start >= 0, stdout
    return json.loads(stdout[start + 1 :])


def test_completed_empty_sdk_audit_crosses_real_cli_and_consumer(tmp_path, steps, sandbox):
    result, boundary = _run_cli(tmp_path, {"results": [{"structured_output": _structured()}]})
    assert result.returncode == 0, result.stderr
    data = _payload(result.stdout)
    assert data["findings"] == [] and data["audit_complete"] is True
    assert data["exit_code"] == 0 and data["success"] is True
    assert boundary["query_calls"] == boundary["auth_calls"] == boundary["spend_calls"] == 1
    scan, outputs, check, state = _pipeline(steps, sandbox, result.stdout, result.returncode)
    assert scan.returncode == check.returncode == 0
    assert outputs["scan_exit"] == "0"
    assert state["payload"]["output"]["title"] == "Security Scan Completed — No Findings"


@pytest.mark.parametrize("severity,conclusion", [("HIGH", "success"), ("critical", "failure")])
def test_sdk_severity_details_survive_to_analysis_and_check(
    tmp_path, steps, sandbox, severity, conclusion
):
    finding = _finding(severity)
    result, _ = _run_cli(
        tmp_path, {"results": [{"structured_output": _structured({"security": [finding]})}]}
    )
    assert result.returncode == 0, result.stderr
    data = _payload(result.stdout)
    expected = {**finding, "severity": severity.lower(), "category": "security", "type": "security"}
    assert data["findings"] == [expected]
    _, _, check, state = _pipeline(steps, sandbox, result.stdout, result.returncode)
    assert check.returncode == 0
    assert state["payload"]["conclusion"] == conclusion
    directory, _ = sandbox
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["findings"] == [expected]
    assert analysis["total_findings"] == 1
    assert analysis["high_count"] == (1 if severity == "HIGH" else 0)
    assert analysis["critical_count"] == (1 if severity == "critical" else 0)
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    assert finding["description"] in comment and "src/é.py:42" in comment


@pytest.mark.parametrize(
    "structured",
    [
        None,
        "markdown is not structured findings",
        {},
        {**_structured(), "audit_complete": False},
        {key: value for key, value in _structured().items() if key != "audit_complete"},
        {**_structured(), "findings": []},
        {**_structured(), "findings": {"security": None}},
        {**_structured(), "findings": {"security": [None]}},
        {
            **_structured(),
            "findings": {
                "security": [{key: value for key, value in _finding().items() if key != "severity"}]
            },
        },
        {**_structured(), "findings": {"security": [_finding("unknown")]}},
        {**_structured(), "findings": {"security": [{**_finding(), "line": True}]}},
        {**_structured(), "findings": {"security": [{**_finding(), "line": 0}]}},
        {**_structured(), "findings": {"security": [{**_finding(), "description": ""}]}},
        {**_structured(), "summary": {"text": ""}},
        {**_structured(), "summary": {"text": "Incomplete", "score": float("nan")}},
        {**_structured(), "error": "A partial audit is not complete"},
        {**_structured(), "partial": True},
    ],
)
def test_malformed_or_partial_sdk_output_returns_process_failure(tmp_path, structured):
    result, boundary = _run_cli(tmp_path, {"results": [{"structured_output": structured}]})
    assert boundary["query_calls"] == 1
    assert result.returncode == 1, result.stderr
    data = _payload(result.stdout)
    assert data["success"] is False and data["audit_complete"] is False
    assert data["exit_code"] == 1 and data["error"]


@pytest.mark.parametrize(
    "signals",
    [
        {"subtype": None},
        {"subtype": "error_max_turns"},
        {"subtype": "error_max_budget_usd", "is_error": True},
        {"is_error": True},
        {"errors": ["SDK provider error"]},
        {"stop_reason": "max_tokens"},
        {"terminal_reason": "aborted_streaming"},
        {"terminal_reason": "aborted_tools"},
        {"terminal_reason": "max_turns"},
        {"terminal_reason": None},
        {"terminal_reason": "future_value"},
        {"origin": {"kind": "task-notification"}},
        {"origin": {}},
        {"api_error_status": 529},
        {"api_error_status": 0},
        {"deferred_tool_use": {"id": "offline-deferred", "name": "Read", "input": {}}},
    ],
)
def test_non_success_sdk_terminal_result_never_reports_completed(tmp_path, signals):
    result, _ = _run_cli(tmp_path, {"results": [{"structured_output": _structured(), **signals}]})
    assert result.returncode == 1, result.stderr
    assert _payload(result.stdout)["success"] is False


@pytest.mark.parametrize("count", [0, 2])
def test_missing_or_multiple_terminal_results_fail(tmp_path, count):
    result, _ = _run_cli(tmp_path, {"results": [{"structured_output": _structured()}] * count})
    assert result.returncode == 1, result.stderr
    assert _payload(result.stdout)["audit_complete"] is False


def test_serialization_failure_is_not_a_repr_success(tmp_path):
    result, _ = _run_cli(
        tmp_path,
        {"results": [{"structured_output": _structured()}], "serialization_failure": True},
    )
    assert result.returncode == 1, result.stderr
    assert _payload(result.stdout)["success"] is False
    assert "WorkflowResult(" not in result.stdout


def test_sdk_connection_failure_cannot_become_a_completed_audit(tmp_path, steps, sandbox):
    result, boundary = _run_cli(tmp_path, {"results": [], "connection_error": True})
    assert boundary["query_calls"] == 1
    assert result.returncode == 1, result.stderr
    _, _, check, state = _pipeline(steps, sandbox, result.stdout, result.returncode)
    assert check.returncode != 0
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


def test_actual_no_auth_preflight_stops_before_sdk_query(tmp_path):
    result, boundary = _run_cli(tmp_path, {"results": [], "no_auth": True})
    assert result.returncode == 3, result.stderr
    assert boundary["query_calls"] == boundary["spend_calls"] == 0
    assert "No auth found" in result.stdout


def test_high_does_not_disappear_when_critical_is_present(tmp_path, steps, sandbox):
    findings = [_finding("high"), {**_finding("critical"), "line": 77}]
    result, _ = _run_cli(
        tmp_path, {"results": [{"structured_output": _structured({"security": findings})}]}
    )
    assert result.returncode == 0, result.stderr
    _, _, _, state = _pipeline(steps, sandbox, result.stdout, result.returncode)
    directory, _ = sandbox
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["high_count"] == analysis["critical_count"] == 1
    assert analysis["total_findings"] == len(analysis["findings"]) == 2
    assert state["payload"]["conclusion"] == "failure"


def test_consumer_refuses_missing_severity_even_with_zero_process_exit(steps, sandbox):
    finding = {key: value for key, value in _finding().items() if key != "severity"}
    _, _, check, state = _pipeline(steps, sandbox, json.dumps({"findings": [finding]}))
    assert check.returncode != 0
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


@pytest.mark.parametrize("field", ["audit_complete", "sdk_completion"])
def test_consumer_refuses_damaged_security_contract(tmp_path, steps, sandbox, field):
    result, _ = _run_cli(tmp_path, {"results": [{"structured_output": _structured()}]})
    assert result.returncode == 0, result.stderr
    payload = _payload(result.stdout)
    payload.pop(field)
    _, _, check, state = _pipeline(steps, sandbox, json.dumps(payload))
    assert check.returncode != 0
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


def test_refused_spend_gate_stops_before_sdk_query(tmp_path):
    result, boundary = _run_cli(tmp_path, {"results": [], "spend_refused": True})
    assert result.returncode == 3, result.stderr
    assert boundary["query_calls"] == 0 and boundary["spend_calls"] == 1


def test_human_output_keeps_the_original_schema_and_report(tmp_path):
    structured = copy.deepcopy(_structured())
    structured.pop("audit_complete")
    structured["summary"]["text"] = "A human report"
    result, boundary = _run_cli(
        tmp_path, {"results": [{"structured_output": structured}], "human": True}
    )
    assert result.returncode == 0, result.stderr
    assert "A human report" in result.stdout
    assert "security-audit/v1" not in result.stdout
    assert "audit_complete" not in boundary["schema"]["schema"]["properties"]


def test_negative_high_count_refuses_even_when_total_sum_balances(steps, sandbox):
    directory, _ = sandbox
    analysis = {
        "total_findings": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "has_critical": False,
        "has_bypass": False,
    }
    target = directory / "analysis.json"
    target.write_text(json.dumps(analysis), encoding="utf-8")
    check, state = _check(steps, sandbox)
    assert check.returncode == 0 and state["payload"]["conclusion"] == "success"
    analysis.update(high_count=-1, medium_count=1)
    target.write_text(json.dumps(analysis), encoding="utf-8")
    check, state = _check(steps, sandbox)
    assert check.returncode != 0
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


def test_finding_comment_escapes_injection_and_bounds_legacy_match(steps, sandbox):
    attack = "</details><script>x</script>@team`[link](u)"
    legacy_match = "legacy evidence " * 20 + "FULL-LEGACY-TAIL"
    findings = [
        {**_finding("high"), "description": attack, "file": "</code>@file[link]"},
        {**_finding("critical"), "description": attack, "type": "</b>@kind[link]"},
        {
            "severity": "critical",
            "file": "legacy.py",
            "type": "legacy",
            "match": legacy_match,
        },
    ]
    _, _, _, state = _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    assert state["payload"]["conclusion"] == "failure"
    directory, _ = sandbox
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["findings"] == findings
    assert "<script>" not in comment and "@team" not in comment
    assert "@file" not in comment and "[link](u)" not in comment
    assert "&lt;script&gt;" in comment and "&#64;team" in comment and "&#96;" in comment
    assert "FULL-LEGACY-TAIL" not in comment
    assert "**Match:** <code>" in comment
    assert "truncated to 60 characters" in comment
    assert "`analysis.json`" in comment


def test_high_comment_counts_omitted_findings_and_links_full_artifact(steps, sandbox):
    directory, env = sandbox
    env.update(
        GITHUB_SERVER_URL="https://github.com",
        GITHUB_REPOSITORY="Smart-AI-Memory/attune-ai",
        GITHUB_RUN_ID="123",
    )
    findings = [
        {**_finding("high"), "description": "x" * 200 + "FULL-HIGH-DESCRIPTION-TAIL"}
        for _ in range(80)
    ]
    _, _, check, state = _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    assert check.returncode == 0 and state["payload"]["conclusion"] == "success"
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    assert analysis["findings"] == findings and analysis["high_count"] == 80
    assert comment.count("- <code>") == 10
    assert "70 more HIGH findings" in comment
    assert "10 displayed finding descriptions were truncated to 60 characters" in comment
    assert "FULL-HIGH-DESCRIPTION-TAIL" not in comment
    assert "https://github.com/Smart-AI-Memory/attune-ai/actions/runs/123" in comment
    assert len(comment) < 10000


def test_high_details_character_budget_counts_every_omitted_item(steps, sandbox):
    findings = [
        {
            **_finding("high"),
            "category": "<" * 80,
            "file": "<" * 160,
            "description": "<" * 60,
        }
        for _ in range(10)
    ]
    _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    directory, _ = sandbox
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    details = comment.split("### 🟠 High Severity Issues (Non-Blocking)", 1)[1]
    details = details.split("### 🛠️ Need Help?", 1)[0]
    displayed = comment.count("- <code>")
    assert 0 < displayed < 10
    assert len(details) <= 6000
    assert f"{10 - displayed} more HIGH findings" in details
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["findings"] == findings and analysis["high_count"] == 10


def test_invalid_public_run_identity_uses_plain_artifact_note(steps, sandbox):
    directory, env = sandbox
    env.update(
        GITHUB_SERVER_URL="https://untrusted.example",
        GITHUB_REPOSITORY="../..",
        GITHUB_RUN_ID="123",
    )
    finding = {**_finding("high"), "description": "x" * 80}
    _pipeline(steps, sandbox, json.dumps({"findings": [finding]}))
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    assert "untrusted.example" not in comment
    assert "See `analysis.json` in the `security-scan-results` artifact." in comment


def test_completed_and_aborted_own_prompt_results_have_opposite_json_outcomes(tmp_path):
    for reason, expected_exit in [("completed", 0), ("aborted_tools", 1)]:
        directory = tmp_path / reason
        directory.mkdir()
        result, boundary = _run_cli(
            directory,
            {"results": [{"structured_output": _structured(), "terminal_reason": reason}]},
        )
        assert boundary["query_calls"] == 1
        assert result.returncode == expected_exit, result.stderr
        payload = _payload(result.stdout)
        assert payload["success"] is (expected_exit == 0)
        assert payload["audit_complete"] is (expected_exit == 0)
        assert payload["exit_code"] == expected_exit
        assert "WorkflowResult(" not in result.stdout
        if expected_exit:
            assert "no successful, error-free terminal result" in payload["error"]


def test_aborted_sdk_result_is_incomplete_through_real_consumer(tmp_path, steps, sandbox):
    result, boundary = _run_cli(
        tmp_path,
        {"results": [{"structured_output": _structured(), "terminal_reason": "aborted_streaming"}]},
    )
    assert boundary["query_calls"] == 1 and result.returncode == 1
    payload = _payload(result.stdout)
    assert payload["success"] is False and payload["audit_complete"] is False
    _, _, check, state = _pipeline(steps, sandbox, result.stdout, result.returncode)
    assert check.returncode != 0
    assert state["payload"]["output"]["title"] == "Security Scan Incomplete"


def test_human_terminal_fields_preserve_baseline_output_and_exit(tmp_path):
    outputs = []
    structured = copy.deepcopy(_structured())
    structured.pop("audit_complete")
    structured["summary"]["text"] = "A human report"
    for reason in ["completed", "aborted_streaming"]:
        directory = tmp_path / reason
        directory.mkdir()
        result, boundary = _run_cli(
            directory,
            {
                "human": True,
                "freeze_clock": True,
                "results": [{"structured_output": structured, "terminal_reason": reason}],
            },
        )
        assert result.returncode == 0, result.stderr
        assert boundary["query_calls"] == boundary["auth_calls"] == boundary["spend_calls"] == 1
        assert "A human report" in result.stdout
        assert "security-audit/v1" not in result.stdout
        assert "audit_complete" not in boundary["schema"]["schema"]["properties"]
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_original_invalid_contract_base_with_bypass_is_valid(steps, sandbox):
    directory, _ = sandbox
    analysis = {
        "total_findings": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "has_critical": False,
        "has_bypass": True,
    }
    (directory / "analysis.json").write_text(json.dumps(analysis), encoding="utf-8")
    check, state = _check(steps, sandbox)
    assert check.returncode == 0
    assert state["payload"]["conclusion"] == "success"


@pytest.mark.parametrize(
    "server,repository,run_id",
    [
        ("https://untrusted.example", "Smart-AI-Memory/attune-ai", "123"),
        ("https://github.com", "../..", "123"),
        ("https://github.com", "Smart-AI-Memory/attune-ai", "123/../../untrusted"),
    ],
)
def test_each_invalid_public_run_identity_field_refuses_link(
    steps, sandbox, server, repository, run_id
):
    directory, env = sandbox
    env.update(GITHUB_SERVER_URL=server, GITHUB_REPOSITORY=repository, GITHUB_RUN_ID=run_id)
    finding = {**_finding("high"), "description": "x" * 80}
    _pipeline(steps, sandbox, json.dumps({"findings": [finding]}))
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    assert "See `analysis.json` in the `security-scan-results` artifact." in comment
    assert "/actions/runs/" not in comment and "untrusted.example" not in comment


def test_medium_and_low_groups_escape_fields_and_count_omissions(steps, sandbox):
    attack = "</code><script>x</script>@team`[link](u)"
    findings = [
        {
            **_finding(severity),
            "type": f"{severity}-{index}-{attack}",
            "file": f"{attack}.py",
            "description": "Retained full description " * 20,
        }
        for severity in ["medium", "low"]
        for index in range(20)
    ]
    _, _, check, state = _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    assert check.returncode == 0 and state["payload"]["conclusion"] == "success"
    directory, _ = sandbox
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["findings"] == findings
    assert analysis["medium_count"] == analysis["low_count"] == 20
    assert "@team" not in comment and "@Team" not in comment and "<script>" not in comment
    assert "[link](u)" not in comment and "[Link](U)" not in comment
    assert "&#64;" in comment and "&#96;" in comment and "&lt;" in comment
    assert "10 MEDIUM groups and 10 MEDIUM finding locations omitted" in comment
    assert "10 LOW groups with 10 LOW findings omitted" in comment
    assert "See `analysis.json`" in comment
    assert len(comment) < 15000


def test_medium_group_character_budget_counts_hidden_locations(steps, sandbox):
    findings = [
        {
            **_finding("medium"),
            "type": "<" * 80 + str(index),
            "file": "<" * 160,
        }
        for index in range(10)
        for _ in range(5)
    ]
    _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    directory, _ = sandbox
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    details = comment.split("### 🟡 Medium Severity Issues (Non-Blocking)", 1)[1]
    details = details.split("### 🛠️ Need Help?", 1)[0]
    displayed = details.count(" occurrences):")
    assert 0 < displayed < 10
    assert len(details) <= 6000
    assert (
        f"{10 - displayed} MEDIUM groups and {50 - 3 * displayed} MEDIUM finding locations omitted"
        in details
    )
    assert f"{4 * displayed} displayed fields truncated" in details
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert analysis["findings"] == findings and analysis["medium_count"] == 50


def test_low_labels_are_clipped_with_full_analysis_preserved(steps, sandbox):
    findings = [{**_finding("low"), "type": "x" * 200 + "FULL-LOW-TYPE-TAIL"}]
    _pipeline(steps, sandbox, json.dumps({"findings": findings}))
    directory, _ = sandbox
    comment = (directory / "pr_comment.md").read_text(encoding="utf-8")
    analysis = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    assert "full-low-type-tail" not in comment.casefold()
    assert "1 displayed fields truncated" in comment
    assert "0 LOW groups with 0 LOW findings omitted" in comment
    assert analysis["findings"] == findings and analysis["low_count"] == 1
