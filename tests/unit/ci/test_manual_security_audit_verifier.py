"""Exercise real verification code using synthetic GitHub metadata and ZIP bytes.

No network, credential, provider, build or authenticated SDK audit is used.
"""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import struct
import subprocess
import sys
import urllib.error
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".github/scripts/verify_manual_security_audit.py"
PRODUCER = (ROOT / ".github/workflows/security-audit-manual.yml").read_bytes()
spec = importlib.util.spec_from_file_location("manual_audit_verifier", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
REPO, HEAD, CONTROLLER = "owner/repo", "a" * 40, "c" * 40


def complete():
    return {
        "schema_version": "security-audit/v1",
        "workflow": "security-audit",
        "success": True,
        "audit_complete": True,
        "sdk_completion": {"subtype": "success", "is_error": False, "stop_reason": "end_turn"},
        "summary": {"text": "Synthetic fixture; no real audit ran"},
        "findings": [],
        "suggestions": [],
    }


def bundle(report=None, *, change_receipt=None, change_files=None, extra=None):
    identity = {
        "CONTROLLER_SHA": CONTROLLER,
        "RUN_ID": "123",
        "RUN_ATTEMPT": "1",
        "ACTOR": "fixture",
        "PR_NUMBER": "2553",
        "REVIEWED_SHA": HEAD,
        "SPEND_APPROVED": "true",
    }
    files = {
        "run-identity.json": json.dumps(identity).encode(),
        "audited-sha.txt": (HEAD + "\n").encode(),
        "scanner-exit.txt": b"0\n",
        "security_results_raw.txt": b"synthetic raw output",
        "security_results.json": json.dumps(complete() if report is None else report).encode(),
        "security_scan_stderr.log": b"",
    }
    if change_files:
        change_files(files)
    receipt = {
        "schema": "attune/manual-sdk-evidence/v1",
        "repository": REPO,
        "workflow_path": gate.WORKFLOW,
        "identity": identity,
        "steps": dict.fromkeys(("scan", "redact", "verdict", "head"), "success"),
        "files": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
    }
    if change_receipt:
        change_receipt(receipt)
    files["audit-evidence.json"] = json.dumps(receipt).encode()
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
        if extra:
            extra(archive)
    return target.getvalue()


class FakeGitHub:
    def __init__(self, raw=None):
        self.raw = bundle() if raw is None else raw
        self.calls, self.posts = [], []
        self.pr = {
            "state": "open",
            "head": {"sha": HEAD, "repo": {"full_name": REPO}},
            "base": {"ref": "main"},
        }
        self.workflow = {"id": 7, "path": gate.WORKFLOW, "state": "active"}
        self.run = {
            "id": 123,
            "workflow_id": 7,
            "path": gate.WORKFLOW,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "head_sha": CONTROLLER,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": REPO},
            "head_repository": {"full_name": REPO},
            "actor": {"login": "fixture"},
            "display_title": json.dumps({"pr": "2553", "sha": HEAD}),
        }
        self.runs = [self.run]
        self.source = {"content": base64.b64encode(PRODUCER).decode()}
        self.artifact = {
            "id": 456,
            "name": "manual-security-audit-" + HEAD,
            "expired": False,
            "size_in_bytes": len(self.raw),
            "digest": "sha256:" + hashlib.sha256(self.raw).hexdigest(),
            "workflow_run": {"id": 123, "head_sha": CONTROLLER},
        }
        self.artifacts = [self.artifact]
        self.fail_publish = False
        self.pr_reads = 0
        self.move_after_read = False
        self.change_base_after_read = False
        self.fail_get = None
        self.run_list_reads = 0
        self.newer_after_read = False
        self.total_count = None

    def request(self, method, path, payload=None):
        self.calls.append((method, path))
        if method == "POST":
            self.posts.append(copy.deepcopy(payload))
            if self.fail_publish:
                raise gate.Refusal("Synthetic publication failure")
            return {**payload, "id": 789}
        assert method == "GET"
        if self.fail_get and self.fail_get(path, self):
            raise gate.Refusal("Synthetic metadata refusal")
        if path.endswith("/pulls/2553"):
            self.pr_reads += 1
            value = copy.deepcopy(self.pr)
            if self.move_after_read and self.pr_reads > 1:
                value["head"]["sha"] = "b" * 40
            if self.change_base_after_read and self.pr_reads > 1:
                value["base"]["ref"] = "topic"
            return value
        if path.endswith("/workflows/security-audit-manual.yml"):
            return self.workflow
        if "/workflows/security-audit-manual.yml/runs?" in path:
            self.run_list_reads += 1
            if self.newer_after_read and self.run_list_reads > 1:
                newer = {**self.run, "id": 124, "status": "in_progress", "conclusion": None}
                return {"workflow_runs": [*self.runs, newer]}
            return {"workflow_runs": self.runs}
        if "/actions/runs/" in path and path.rsplit("/", 1)[-1].isdigit():
            return next(run for run in self.runs if run["id"] == int(path.rsplit("/", 1)[-1]))
        if "/contents/" in path:
            return self.source
        if path.endswith("/artifacts?per_page=100"):
            return {
                "total_count": (
                    len(self.artifacts) if self.total_count is None else self.total_count
                ),
                "artifacts": self.artifacts,
            }
        raise AssertionError("Unexpected metadata request: " + path)

    def archive(self, repo, artifact):
        assert repo == REPO and artifact["id"] == 456
        self.calls.append(("DOWNLOAD", 456))
        return self.raw


def event(kind="pull_request_target"):
    data = {"repository": {"full_name": REPO}}
    if kind == "pull_request_target":
        return {**data, "number": 2553, "pull_request": {"head": {"sha": HEAD}}}
    return {
        **data,
        "action": "completed",
        "workflow_run": {"id": 123, "display_title": json.dumps({"pr": "2553", "sha": HEAD})},
    }


@pytest.mark.parametrize("kind", ["pull_request_target", "workflow_run"])
@pytest.mark.parametrize("finding", [False, True])
def test_genuine_completed_exact_commit_audit_passes(kind, finding):
    report = complete()
    if finding:
        report["findings"] = [
            {
                "file": "x.py",
                "line": 2,
                "severity": "high",
                "description": "fixture",
                "category": "injection",
                "type": "injection",
            }
        ]
    client = FakeGitHub(bundle(report))
    result = gate.verify_event(client, REPO, kind, event(kind), PRODUCER)
    assert result["accepted"] is True and result["counts"]["high"] == int(finding)
    assert client.posts == [
        {
            "name": "Security Scan",
            "head_sha": HEAD,
            "status": "completed",
            "conclusion": "success",
            "external_id": "manual-sdk-audit:123",
            "output": client.posts[0]["output"],
            "details_url": f"https://github.com/{REPO}/actions/runs/123",
        }
    ]
    assert client.calls.index(("DOWNLOAD", 456)) < next(
        i for i, call in enumerate(client.calls) if call[0] == "POST"
    )


@pytest.mark.parametrize(
    "change",
    [
        {"event": "pull_request"},
        {"head_branch": "topic"},
        {"run_attempt": 2},
        {"run_attempt": True},
        {"workflow_id": 8},
        {"path": "other.yml"},
        {"path": gate.WORKFLOW + "@topic"},
        {"status": "in_progress"},
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"repository": {"full_name": "other/repo"}},
        {"head_repository": {"full_name": "fork/repo"}},
        {"head_sha": "bad"},
        {"display_title": '{"pr":"2553","sha":"' + "b" * 40 + '"}'},
    ],
)
def test_untrusted_or_incomplete_runs_fail(change):
    client = FakeGitHub()
    client.run.update(change)
    kind = "pull_request_target" if "display_title" in change else "workflow_run"
    result = gate.verify_event(client, REPO, kind, event(kind), PRODUCER)
    assert result["accepted"] is False
    assert client.posts[-1]["conclusion"] == "failure"
    assert "zero-findings" in client.posts[-1]["output"]["summary"]


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "duplicate",
        "expired",
        "wrong_run",
        "wrong_controller",
        "wrong_hash",
        "wrong_size",
        "too_large",
        "changed_workflow",
        "missing_workflow",
    ],
)
def test_artifact_provenance_and_lifetime_fail_closed(case):
    client = FakeGitHub()
    if case == "missing":
        client.artifacts = []
    if case == "duplicate":
        client.artifacts.append(copy.deepcopy(client.artifact))
    if case == "expired":
        client.artifact["expired"] = True
    if case == "wrong_run":
        client.artifact["workflow_run"]["id"] = 999
    if case == "wrong_controller":
        client.artifact["workflow_run"]["head_sha"] = "b" * 40
    if case == "wrong_hash":
        client.artifact["digest"] = "sha256:" + "0" * 64
    if case == "wrong_size":
        client.artifact["size_in_bytes"] += 1
    if case == "too_large":
        client.artifact["size_in_bytes"] = gate.MAX_ZIP + 1
    if case == "changed_workflow":
        client.source["content"] = base64.b64encode(b"changed").decode()
    if case == "missing_workflow":
        client.workflow["state"] = "disabled_manually"
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert result["accepted"] is False and client.posts[-1]["conclusion"] == "failure"


@pytest.mark.parametrize(
    "case",
    ["head", "run", "attempt", "actor", "approval", "repo", "steps", "hashes", "scanner_exit"],
)
def test_receipt_cannot_substitute_for_actual_run(case):
    def change(receipt):
        if case in {"head", "run", "attempt", "actor", "approval"}:
            key = {
                "head": "REVIEWED_SHA",
                "run": "RUN_ID",
                "attempt": "RUN_ATTEMPT",
                "actor": "ACTOR",
                "approval": "SPEND_APPROVED",
            }[case]
            receipt["identity"][key] = "wrong"
        if case == "repo":
            receipt["repository"] = "other/repo"
        if case == "steps":
            receipt["steps"]["scan"] = "failure"
        if case == "hashes":
            receipt["files"]["security_results.json"] = "0" * 64

    files = (
        (lambda data: data.update({"scanner-exit.txt": b"3\n"})) if case == "scanner_exit" else None
    )
    client = FakeGitHub(bundle(change_receipt=change, change_files=files))
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"


@pytest.mark.parametrize("member", ["security_results.json", "run-identity.json"])
def test_duplicate_json_key_cannot_hide_an_invalid_earlier_value(member):
    def change(files):
        if member == "security_results.json":
            raw = files[member].replace(b'"success": true', b'"success": false, "success": true')
        else:
            raw = files[member].replace(
                b'"ACTOR": "fixture"', b'"ACTOR": "other", "ACTOR": "fixture"'
            )
        assert raw != files[member]
        files[member] = raw

    client = FakeGitHub(bundle(change_files=change))
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        "not JSON",
        [],
        {},
        {"findings": []},
        {"success": False, "audit_complete": False, "error": "No auth"},
    ],
)
def test_legacy_empty_findings_or_failure_envelope_cannot_pass(invalid):
    with pytest.raises(gate.Refusal):
        gate.report_counts(invalid)


@pytest.mark.parametrize(
    "path,value",
    [
        (("success",), False),
        (("audit_complete",), False),
        (("schema_version",), "other"),
        (("sdk_completion", "subtype"), "error_max_budget_usd"),
        (("sdk_completion", "is_error"), True),
        (("sdk_completion", "stop_reason"), "max_tokens"),
        (("summary", "text"), " "),
        (("summary", "score"), True),
        (("summary", "score"), 101),
        (("suggestions",), [None]),
        (("findings",), [None]),
    ],
)
def test_partial_error_or_malformed_sdk_result_fails(path, value):
    report = complete()
    target = report
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(gate.Refusal):
        gate.report_counts(report)


@pytest.mark.parametrize(
    "change",
    [
        {"severity": "critical"},
        {"severity": "CRITICAL"},
        {"line": True},
        {"line": 0},
        {"file": ""},
        {"type": "different"},
    ],
)
def test_critical_and_invalid_findings_fail(change):
    report = complete()
    report["findings"] = [
        {
            "file": "x.py",
            "line": 1,
            "severity": "high",
            "description": "x",
            "category": "x",
            "type": "x",
            **change,
        }
    ]
    with pytest.raises(gate.Refusal):
        gate.report_counts(report)


@pytest.mark.parametrize(
    "extra", ["../escape", "/absolute", "script.py", "duplicate", "symlink", "fifo"]
)
def test_zip_is_data_only_and_refuses_unsafe_members(extra):
    # Include every payload member in the hashes, isolating the membership/type guard.
    with zipfile.ZipFile(io.BytesIO(bundle())) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    receipt = json.loads(files.pop("audit-evidence.json"))
    name = "telemetry-usage.jsonl" if extra in {"symlink", "fifo"} else extra
    if extra != "duplicate":
        files[name] = b"synthetic extra member"
    receipt["files"] = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    files["audit-evidence.json"] = json.dumps(receipt).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for member, data in files.items():
            entry = zipfile.ZipInfo(member)
            if member == name and extra in {"symlink", "fifo"}:
                entry.create_system = 3
                entry.external_attr = (
                    (stat.S_IFLNK if extra == "symlink" else stat.S_IFIFO) | 0o600
                ) << 16
            archive.writestr(entry, data)
        if extra == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("security_results.json", files["security_results.json"])
    client = FakeGitHub(output.getvalue())
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"
    reason = (
        "non-file members" if extra in {"symlink", "fifo"} else "Missing, duplicate or unexpected"
    )
    assert reason in client.posts[-1]["output"]["summary"]


def test_no_manual_run_and_publish_error_stay_failed():
    client = FakeGitHub()
    client.runs = []
    client.fail_publish = True
    with pytest.raises(gate.Refusal):
        gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert len(client.posts) == 1 and client.posts[0]["conclusion"] == "failure"


@pytest.mark.parametrize("kind", ["pull_request_target", "workflow_run"])
@pytest.mark.parametrize("state", ["failure", "cancelled", "in_progress"])
def test_newer_failed_or_pending_audit_cannot_fall_back_to_older_success(kind, state):
    client = FakeGitHub()
    newer = copy.deepcopy(client.run)
    newer.update(
        id=124,
        status="in_progress" if state == "in_progress" else "completed",
        conclusion=None if state == "in_progress" else state,
    )
    client.runs.append(newer)
    result = gate.verify_event(client, REPO, kind, event(kind), PRODUCER)
    assert not result["accepted"] and result["run_id"] == 124
    assert client.posts[-1]["conclusion"] == "failure"
    assert not any(call[0] == "DOWNLOAD" for call in client.calls)


@pytest.mark.parametrize("when", ["before", "after"])
def test_audit_does_not_write_to_changed_pr_head(when):
    client = FakeGitHub()
    if when == "before":
        client.pr["head"]["sha"] = "b" * 40
    else:
        client.move_after_read = True
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and result["ignored"] and not client.posts


def test_changed_pr_base_cannot_receive_a_success_for_the_same_head():
    client = FakeGitHub()
    client.change_base_after_read = True
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"


def test_trusted_workflow_has_no_model_or_pr_code_execution():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/security-scan.yml").read_text(encoding="utf-8")
    )
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"pull_request_target", "workflow_run"}
    assert triggers["pull_request_target"]["branches"] == ["main"]
    assert triggers["workflow_run"]["workflows"] == ["Security audit (approved manual run)"]
    assert workflow["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
        "actions": "read",
        "checks": "write",
    }
    assert workflow["concurrency"]["cancel-in-progress"] is False
    group = workflow["concurrency"]["group"]
    assert "github.event.pull_request.head.sha" in group
    assert "github.event.workflow_run.display_title" in group
    steps = workflow["jobs"]["security-scan"]["steps"]
    assert steps[0]["with"] == {"ref": "${{ github.workflow_sha }}", "persist-credentials": False}
    verify = steps[-1]
    assert verify["run"] == "python3 -I .github/scripts/verify_manual_security_audit.py"
    assert verify["env"]["ANTHROPIC_API_KEY"] == verify["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert "secrets." not in str(workflow) and "continue-on-error" not in str(verify)


def test_github_artifact_redirect_does_not_forward_authorization():
    client = gate.GitHub("synthetic-job-token")
    requests = []

    class Response(io.BytesIO):
        pass

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert timeout == 30
            if len(requests) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    302,
                    "redirect",
                    {"Location": "https://fixture.example/artifact?synthetic-signature=1"},
                    None,
                )
            return Response(b"synthetic archive")

    client.opener = Opener()
    assert client.archive(REPO, {"id": 456}) == b"synthetic archive"
    assert requests[0].get_header("Authorization") == "Bearer synthetic-job-token"
    assert requests[1].get_header("Authorization") is None


@pytest.mark.parametrize(
    "location",
    [
        "http://fixture.example/file",
        "file:///tmp/file",
        "https://user:pass@fixture.example/file",
        "https://fixture.example:444/file",
    ],
)
def test_unsafe_download_redirect_is_refused(location):
    client = gate.GitHub("synthetic-job-token")

    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 302, "redirect", {"Location": location}, None
            )

    client.opener = Opener()
    with pytest.raises(gate.Refusal):
        client.archive(REPO, {"id": 456})


def test_unexpected_verifier_error_still_publishes_failure():
    client = FakeGitHub()

    def unexpected(*args):
        raise RuntimeError("synthetic decoding defect")

    client.archive = unexpected
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"


def test_actual_manual_manifest_round_trip(tmp_path):
    if os.name != "posix":
        pytest.skip("The actual Ubuntu workflow heredoc requires POSIX")
    directory = tmp_path / "manual-security-evidence"
    directory.mkdir()
    with zipfile.ZipFile(io.BytesIO(bundle())) as archive:
        for name in archive.namelist():
            if name != "audit-evidence.json":
                (directory / name).write_bytes(archive.read(name))
    workflow = yaml.safe_load(PRODUCER)
    script = next(
        s["run"]
        for s in workflow["jobs"]["audit"]["steps"]
        if s["name"] == "Bind audit payload to its run"
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "python3").symlink_to(sys.executable)
    source = tmp_path / "bind.sh"
    source.write_text(script, encoding="utf-8")
    env = {
        "PATH": str(binary) + ":/usr/bin:/bin",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_REPOSITORY": REPO,
        **dict.fromkeys(
            ("SCAN_OUTCOME", "REDACT_OUTCOME", "VERDICT_OUTCOME", "HEAD_OUTCOME"), "success"
        ),
    }
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-eo", "pipefail", str(source)],
        cwd=directory,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(directory.iterdir()):
            archive.writestr(p.name, p.read_bytes())
    client = FakeGitHub(raw.getvalue())
    verified = gate.verify_event(client, REPO, "workflow_run", event("workflow_run"), PRODUCER)
    assert verified["accepted"] is True and client.posts[-1]["head_sha"] == HEAD


@pytest.mark.parametrize("case", ["entries", "declared_content", "artifact_count"])
def test_archive_and_metadata_bounds_refuse_before_payload_use(case):
    raw = bundle()
    if case == "entries":
        output = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(output, "w") as archive:
            files = {name: source.read(name) for name in source.namelist()}
            for index in range(17):
                files[f"extra-{index}"] = b"x"
            receipt = json.loads(files["audit-evidence.json"])
            receipt["files"] = {
                name: hashlib.sha256(data).hexdigest()
                for name, data in files.items()
                if name != "audit-evidence.json"
            }
            files["audit-evidence.json"] = json.dumps(receipt).encode()
            for name, data in files.items():
                archive.writestr(name, data)
        raw = output.getvalue()
    if case == "declared_content":
        data = bytearray(raw)
        central = data.index(b"PK\x01\x02")
        struct.pack_into("<I", data, central + 24, gate.MAX_CONTENT + 1)
        raw = bytes(data)
    client = FakeGitHub(raw)
    if case == "artifact_count":
        client.total_count = 101
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"]
    reason = (
        "Too many audit artifacts"
        if case == "artifact_count"
        else "Oversized audit artifact contents"
    )
    assert reason in client.posts[-1]["output"]["summary"]


def test_actual_download_read_limit_is_bounded(monkeypatch):
    assert gate.MAX_ZIP == 32 * 1024 * 1024
    monkeypatch.setattr(gate, "MAX_ZIP", 8)
    client = gate.GitHub("synthetic-job-token")
    requests, sizes = [], []

    class Response(io.BytesIO):
        def read(self, size=-1):
            sizes.append(size)
            return super().read(size)

    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            if len(requests) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    302,
                    "redirect",
                    {"Location": "https://fixture.example/file"},
                    None,
                )
            return Response(b"123456789")

    client.opener = Opener()
    with pytest.raises(gate.Refusal, match="Artifact download failed"):
        client.archive(REPO, {"id": 456})
    assert sizes == [9] and len(requests) == 2


@pytest.mark.parametrize("case", ["fork", "missing_repo", "closed"])
def test_unsupported_or_closed_pr_cannot_receive_success(case):
    client = FakeGitHub()
    if case == "fork":
        client.pr["head"]["repo"]["full_name"] = "fork/repo"
    if case == "missing_repo":
        client.pr["head"]["repo"] = None
    if case == "closed":
        client.pr["state"] = "closed"
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"]
    if case == "closed":
        assert result["ignored"] and not client.posts
    else:
        assert client.posts[-1]["conclusion"] == "failure"
        assert "same-repository" in client.posts[-1]["output"]["summary"]


@pytest.mark.parametrize("action", ["requested", "in_progress"])
def test_new_pending_event_revokes_prior_success(action):
    client = FakeGitHub()
    client.run.update(status="in_progress", conclusion=None)
    payload = event("workflow_run")
    payload["action"] = action
    result = gate.verify_event(client, REPO, "workflow_run", payload, PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"
    assert "not completed successfully" in client.posts[-1]["output"]["summary"]


@pytest.mark.parametrize("stage", ["initial_pr", "event_metadata", "post_pr", "final_runs"])
def test_known_target_metadata_error_attempts_one_failed_publication(stage):
    client = FakeGitHub()

    def refuse(path, obj):
        if stage == "initial_pr":
            return path.endswith("/pulls/2553")
        if stage == "event_metadata":
            return path.endswith("/actions/runs/123")
        if stage == "post_pr":
            return path.endswith("/pulls/2553") and obj.pr_reads == 1
        return (
            stage == "final_runs"
            and "/workflows/security-audit-manual.yml/runs?" in path
            and obj.run_list_reads == 1
        )

    client.fail_get = refuse
    result = gate.verify_event(client, REPO, "workflow_run", event("workflow_run"), PRODUCER)
    assert not result["accepted"] and len(client.posts) == 1
    assert client.posts[0]["head_sha"] == HEAD and client.posts[0]["conclusion"] == "failure"
    assert "Synthetic metadata refusal" in client.posts[0]["output"]["summary"]


def test_new_dispatch_between_verification_and_publication_prevents_success():
    client = FakeGitHub()
    client.newer_after_read = True
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"
    assert "newer audit started" in client.posts[-1]["output"]["summary"]


@pytest.mark.parametrize(
    "case,code", [("accepted", 0), ("failure_published", 0), ("ignored", 0), ("publish_error", 1)]
)
def test_main_exit_describes_controller_delivery_not_sdk_acceptance(
    tmp_path, monkeypatch, capsys, case, code
):
    client = FakeGitHub()
    if case == "failure_published":
        client.runs = []
    if case == "ignored":
        client.pr["head"]["sha"] = "b" * 40
    if case == "publish_error":
        client.fail_publish = True
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event()), encoding="utf-8")
    for name, value in {
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_PATH": str(path),
        "GITHUB_REPOSITORY": REPO,
        "GITHUB_EVENT_NAME": "pull_request_target",
        "GITHUB_TOKEN": "synthetic-job-token",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(gate, "GitHub", lambda token: client)
    assert gate.main() == code
    captured = capsys.readouterr()
    if case == "failure_published":
        assert json.loads(captured.out)["accepted"] is False
        assert client.posts[-1]["conclusion"] == "failure"
    if case == "publish_error":
        assert len(client.posts) == 1 and "failed" in captured.err


def test_producer_consumer_handoff_is_bound_to_actual_yaml():
    producer = yaml.safe_load(PRODUCER)
    consumer = yaml.safe_load(
        (ROOT / ".github/workflows/security-scan.yml").read_text(encoding="utf-8")
    )
    rendered = (
        producer["run-name"]
        .replace("${{ inputs.pull_request }}", "2553")
        .replace("${{ inputs.reviewed_sha }}", HEAD)
    )
    assert gate.title_identity(rendered) == (2553, HEAD)
    trigger = consumer.get("on", consumer.get(True))["workflow_run"]
    assert trigger["workflows"] == [producer["name"]] and trigger["branches"] == ["main"]
    assert trigger["types"] == ["requested", "in_progress", "completed"]
    steps = producer["jobs"]["audit"]["steps"]
    retain = next(s for s in steps if s["name"] == "Retain audit evidence")
    assert (
        retain["with"]["name"].replace("${{ steps.identity.outputs.sha }}", HEAD)
        == "manual-security-audit-" + HEAD
    )
    bind = next(s for s in steps if s["name"] == "Bind audit payload to its run")
    assert bind["id"] == "bind" and "steps.bind.outcome == 'success'" in retain["if"]
    ids = {s.get("id") for s in steps}
    for name in ("scan", "redact", "verdict", "head"):
        assert (
            name in ids
            and bind["env"][name.upper() + "_OUTCOME"] == "${{ steps." + name + ".outcome }}"
        )
    heredoc = bind["run"].split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    assignments = {
        node.targets[0].id: node.value
        for node in ast.parse(heredoc).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    assert ast.literal_eval(assignments["required"]) == gate.REQUIRED
    assert isinstance(assignments["allowed"], ast.BinOp)
    assert ast.literal_eval(assignments["allowed"].right) == gate.OPTIONAL


@pytest.mark.parametrize("path", [gate.WORKFLOW, gate.WORKFLOW + "@main"])
def test_documented_main_workflow_run_path_forms_are_accepted(path):
    client = FakeGitHub()
    client.run["path"] = path
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert result["accepted"] is True and client.posts[-1]["conclusion"] == "success"


def test_first_specific_refusal_survives_a_later_freshness_error():
    client = FakeGitHub()
    client.run["conclusion"] = "failure"
    client.fail_get = lambda path, obj: path.endswith("/pulls/2553") and obj.pr_reads == 1
    result = gate.verify_event(client, REPO, "pull_request_target", event(), PRODUCER)
    assert not result["accepted"] and client.posts[-1]["conclusion"] == "failure"
    summary = client.posts[-1]["output"]["summary"]
    assert "Manual audit has not completed successfully" in summary
    assert "Synthetic metadata refusal" not in summary
