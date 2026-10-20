"""Verify trusted manual SDK evidence; never run audited code or a model.

Artifacts are read as bounded ZIP data, without extraction or imports. Acceptance
means the approved commit's scanner reported supported SDK completion under the
trusted producer. It is not independent provider attestation or model-quality proof.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

WORKFLOW = ".github/workflows/security-audit-manual.yml"
CHECK = "Security Scan"
SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_ZIP = 32 * 1024 * 1024
MAX_CONTENT = 64 * 1024 * 1024
REQUIRED = {
    "audited-sha.txt",
    "run-identity.json",
    "scanner-exit.txt",
    "security_results_raw.txt",
    "security_results.json",
    "security_scan_stderr.log",
}
OPTIONAL = {"telemetry-usage.jsonl", "telemetry-summary.json"}


class Refusal(ValueError):
    """Evidence cannot substantiate an accepted audit."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise Refusal("Non-finite JSON token")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise Refusal("Malformed evidence JSON") from exc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    """One attempt per request; never forward authentication to artifact hosts."""

    def __init__(self, token):
        require(bool(token), "GitHub job authentication is unavailable")
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, path, payload=None):
        require(path.startswith("/repos/"), "Unsupported GitHub API path")
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            "https://api.github.com" + path,
            data=body,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "attune-audit-verifier",
            },
        )
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
            require(len(raw) <= 2 * 1024 * 1024, "Oversized GitHub metadata")
            return strict_json(raw)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise Refusal("GitHub metadata request failed; no retry performed") from exc

    def archive(self, repo, artifact):
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact['id']}/zip",
            headers={
                "Authorization": "Bearer " + self.token,
                "User-Agent": "attune-audit-verifier",
            },
        )
        try:
            for attempt in range(4):
                try:
                    with self.opener.open(request, timeout=30) as response:
                        require(attempt > 0, "Artifact API did not return a signed download")
                        raw = response.read(MAX_ZIP + 1)
                    require(len(raw) <= MAX_ZIP, "Oversized artifact download")
                    return raw
                except urllib.error.HTTPError as exc:
                    require(exc.code in (301, 302, 303, 307, 308), "Artifact download failed")
                    target = exc.headers.get("Location", "")
                    exc.close()
                    parsed = urllib.parse.urlsplit(target)
                    require(
                        parsed.scheme == "https"
                        and parsed.hostname
                        and not parsed.username
                        and not parsed.password
                        and parsed.port in (None, 443),
                        "Unsafe artifact download redirect",
                    )
                    # A fresh request carries no Authorization header to the signed host.
                    request = urllib.request.Request(
                        target, headers={"User-Agent": "attune-audit-verifier"}
                    )
            raise Refusal("Too many artifact download redirects")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise Refusal("Artifact download failed; no credentials or URL logged") from exc


def title_identity(title):
    value = strict_json(title)
    require(isinstance(value, dict) and set(value) == {"pr", "sha"}, "Unsupported audit run title")
    require(
        isinstance(value["pr"], str)
        and re.fullmatch(r"[1-9][0-9]{0,9}", value["pr"])
        and isinstance(value["sha"], str)
        and SHA.fullmatch(value["sha"]),
        "Invalid audit target identity",
    )
    return int(value["pr"]), value["sha"]


def report_counts(report):
    require(
        isinstance(report, dict)
        and set(report)
        == {
            "schema_version",
            "workflow",
            "success",
            "audit_complete",
            "sdk_completion",
            "summary",
            "findings",
            "suggestions",
        },
        "Incomplete SDK report",
    )
    require(
        report["schema_version"] == "security-audit/v1"
        and report["workflow"] == "security-audit"
        and report["success"] is True
        and report["audit_complete"] is True,
        "SDK audit did not affirm completion",
    )
    terminal = report["sdk_completion"]
    require(
        isinstance(terminal, dict)
        and set(terminal) == {"subtype", "is_error", "stop_reason"}
        and terminal["subtype"] == "success"
        and terminal["is_error"] is False
        and terminal["stop_reason"] in (None, "end_turn"),
        "SDK terminal result is incomplete",
    )
    summary = report["summary"]
    require(
        isinstance(summary, dict)
        and set(summary) <= {"text", "score"}
        and isinstance(summary.get("text"), str)
        and bool(summary["text"].strip()),
        "Malformed SDK summary",
    )
    require(
        "score" not in summary or (type(summary["score"]) is int and 0 <= summary["score"] <= 100),
        "Malformed SDK score",
    )
    counts = {name: 0 for name in ("critical", "high", "medium", "low")}
    require(isinstance(report["findings"], list), "Missing SDK findings list")
    for finding in report["findings"]:
        require(
            isinstance(finding, dict)
            and set(finding) == {"file", "line", "severity", "description", "category", "type"},
            "Malformed SDK finding",
        )
        require(
            all(
                isinstance(finding[key], str) and finding[key].strip()
                for key in ("file", "description", "category", "type")
            )
            and type(finding["line"]) is int
            and finding["line"] > 0
            and isinstance(finding["severity"], str)
            and finding["severity"] in counts
            and finding["type"] == finding["category"],
            "Invalid SDK finding fields",
        )
        counts[finding["severity"]] += 1
    require(isinstance(report["suggestions"], list), "Malformed SDK suggestions")
    for item in report["suggestions"]:
        require(
            isinstance(item, dict)
            and set(item) <= {"description", "priority"}
            and isinstance(item.get("description"), str)
            and item["description"].strip()
            and ("priority" not in item or item["priority"] in ("high", "medium", "low")),
            "Malformed SDK suggestion",
        )
    require(counts["critical"] == 0, "Critical findings block this audit")
    return counts


def verify_archive(raw, artifact, run, repo, number, sha):
    require(
        len(raw) == artifact["size_in_bytes"] and len(raw) <= MAX_ZIP,
        "Artifact byte count differs from GitHub metadata",
    )
    require(
        artifact.get("digest") == "sha256:" + hashlib.sha256(raw).hexdigest(),
        "Artifact SHA-256 differs from GitHub metadata",
    )
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            require(
                0 < len(entries) <= 16 and sum(x.file_size for x in entries) <= MAX_CONTENT,
                "Oversized audit artifact contents",
            )
            names = [x.filename for x in entries]
            require(
                len(set(names)) == len(names)
                and set(names) <= REQUIRED | OPTIONAL | {"audit-evidence.json"}
                and REQUIRED | {"audit-evidence.json"} <= set(names),
                "Missing, duplicate or unexpected audit artifact members",
            )
            require(
                not any(
                    x.is_dir() or stat.S_IFMT(x.external_attr >> 16) not in (0, stat.S_IFREG)
                    for x in entries
                ),
                "Audit artifact contains non-file members",
            )
            files = {name: archive.read(name) for name in names}
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise Refusal("Audit artifact ZIP is invalid") from exc
    receipt = strict_json(files.pop("audit-evidence.json"))
    require(
        isinstance(receipt, dict)
        and set(receipt) == {"schema", "repository", "workflow_path", "identity", "steps", "files"},
        "Malformed audit evidence receipt",
    )
    require(
        receipt["schema"] == "attune/manual-sdk-evidence/v1"
        and receipt["repository"] == repo
        and receipt["workflow_path"] == WORKFLOW,
        "Audit receipt provenance differs",
    )
    expected = {
        "CONTROLLER_SHA": run["head_sha"],
        "RUN_ID": str(run["id"]),
        "RUN_ATTEMPT": "1",
        "ACTOR": run["actor"]["login"],
        "PR_NUMBER": str(number),
        "REVIEWED_SHA": sha,
        "SPEND_APPROVED": "true",
    }
    require(
        receipt["identity"] == expected and strict_json(files["run-identity.json"]) == expected,
        "Audit receipt identity differs from GitHub run",
    )
    require(
        receipt["steps"] == dict.fromkeys(("scan", "redact", "verdict", "head"), "success"),
        "An audit step did not succeed",
    )
    require(
        receipt["files"]
        == {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "Audit payload hashes differ",
    )
    require(
        files["scanner-exit.txt"] == b"0\n" and files["audited-sha.txt"] == (sha + "\n").encode(),
        "Scanner exit or audited source identity differs",
    )
    return report_counts(strict_json(files["security_results.json"]))


def verify_run(client, repo, run_id, number, sha, producer):
    prefix = f"/repos/{repo}"
    workflow = client.request("GET", prefix + "/actions/workflows/security-audit-manual.yml")
    require(
        type(workflow.get("id")) is int
        and workflow["id"] > 0
        and workflow.get("path") == WORKFLOW
        and workflow.get("state") == "active",
        "Manual audit workflow is unavailable",
    )
    run = client.request("GET", prefix + f"/actions/runs/{run_id}")
    require(
        run.get("id") == run_id
        and run.get("workflow_id") == workflow.get("id")
        and run.get("path") in (WORKFLOW, WORKFLOW + "@main")
        and run.get("event") == "workflow_dispatch"
        and run.get("head_branch") == "main"
        and type(run.get("run_attempt")) is int
        and run["run_attempt"] == 1
        and run.get("repository", {}).get("full_name") == repo
        and run.get("head_repository", {}).get("full_name") == repo,
        "Audit did not come from the expected main-branch first dispatch",
    )
    require(
        run.get("status") == "completed" and run.get("conclusion") == "success",
        "Manual audit has not completed successfully",
    )
    require(
        title_identity(run.get("display_title")) == (number, sha),
        "Manual run targets another commit",
    )
    controller = run.get("head_sha", "")
    require(
        isinstance(controller, str) and SHA.fullmatch(controller), "Invalid controller source SHA"
    )
    source = client.request("GET", prefix + f"/contents/{WORKFLOW}?ref={controller}")
    try:
        encoded = "".join(source.get("content", "").split())
        actual = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise Refusal("Manual workflow source is unavailable") from exc
    require(actual == producer, "Manual workflow changed; a fresh audit is required")
    listing = client.request("GET", prefix + f"/actions/runs/{run_id}/artifacts?per_page=100")
    require(listing.get("total_count", 101) <= 100, "Too many audit artifacts")
    matches = [
        x for x in listing.get("artifacts", []) if x.get("name") == "manual-security-audit-" + sha
    ]
    require(len(matches) == 1, "A unique audit artifact is unavailable")
    artifact = matches[0]
    require(
        artifact.get("expired") is False
        and type(artifact.get("id")) is int
        and artifact["id"] > 0
        and type(artifact.get("size_in_bytes")) is int
        and 0 < artifact["size_in_bytes"] <= MAX_ZIP
        and artifact.get("workflow_run", {}).get("id") == run_id
        and artifact.get("workflow_run", {}).get("head_sha") == controller,
        "Audit artifact provenance or lifetime differs",
    )
    return verify_archive(client.archive(repo, artifact), artifact, run, repo, number, sha)


def latest_target_run(client, prefix, number, sha):
    runs = client.request(
        "GET",
        prefix + "/actions/workflows/security-audit-manual.yml/runs"
        "?event=workflow_dispatch&branch=main&per_page=100",
    )
    candidates = []
    for run in runs.get("workflow_runs", []):
        try:
            identity = title_identity(run.get("display_title"))
        except Refusal:
            continue
        if identity == (number, sha) and type(run.get("id")) is int and run["id"] > 0:
            candidates.append(run["id"])
    require(bool(candidates), "No manual audit found for this commit among the latest 100 runs")
    return max(candidates)


def verify_event(client, repo, event_name, event, producer):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "Invalid repository identity")
    require(
        event.get("repository", {}).get("full_name") == repo, "Event belongs to another repository"
    )
    run_id = None
    if event_name == "pull_request_target":
        number, sha = event["number"], event["pull_request"]["head"]["sha"]
        require(
            type(number) is int and number > 0 and isinstance(sha, str) and SHA.fullmatch(sha),
            "Invalid PR event identity",
        )
    elif event_name == "workflow_run":
        require(
            event["action"] in ("requested", "in_progress", "completed"), "Unexpected audit event"
        )
        run_id = event["workflow_run"]["id"]
        require(type(run_id) is int and run_id > 0, "Invalid audit run ID")
        # The authenticated event supplies a failure target even if run metadata is unavailable.
        # A success still requires fresh API provenance and the full payload below.
        number, sha = title_identity(event["workflow_run"].get("display_title"))
    else:
        raise Refusal("Unsupported verification event")
    prefix = f"/repos/{repo}"
    counts, failure, pr = None, None, None
    try:
        pr = client.request("GET", prefix + f"/pulls/{number}")
        if pr.get("state") != "open" or pr.get("head", {}).get("sha") != sha:
            return {
                "accepted": False,
                "ignored": True,
                "reason": "Outdated PR context; no check published",
            }
        require(
            pr.get("base", {}).get("ref") == "main"
            and (pr.get("head", {}).get("repo") or {}).get("full_name") == repo,
            "Manual audit requires a same-repository PR targeting main",
        )
        if event_name == "workflow_run":
            metadata = client.request("GET", prefix + f"/actions/runs/{run_id}")
            require(
                title_identity(metadata.get("display_title")) == (number, sha),
                "Audit event and actual run identity differ",
            )
        # Reconcile both event types. An old callback cannot choose an old successful run.
        run_id = latest_target_run(client, prefix, number, sha)
        counts = verify_run(client, repo, run_id, number, sha, producer)
    # Unexpected data errors must publish failure rather than reuse a pass.
    except Exception as exc:  # noqa: BLE001
        failure = str(exc) if isinstance(exc, Refusal) else "Audit metadata is incomplete"
        counts = None
    if pr is not None:
        try:
            current = client.request("GET", prefix + f"/pulls/{number}")
            if current.get("state") != "open" or current.get("head", {}).get("sha") != sha:
                return {
                    "accepted": False,
                    "ignored": True,
                    "reason": "PR moved; no check published",
                }
            require(
                current.get("base", {}).get("ref") == "main"
                and (current.get("head", {}).get("repo") or {}).get("full_name") == repo,
                "PR target changed during verification",
            )
            if counts is not None:
                require(
                    latest_target_run(client, prefix, number, sha) == run_id,
                    "A newer audit started during verification; completion is unverified",
                )
        # A known target gets one failed-check attempt after a freshness error.
        except Exception as exc:  # noqa: BLE001
            failure = failure or (
                str(exc) if isinstance(exc, Refusal) else "PR freshness is unavailable"
            )
            counts = None
    accepted = failure is None and counts is not None
    summary = (
        (
            f"The approved commit's scanner reported completion for `{sha}`. Findings: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if accepted
        else (
            "Manual audit not accepted; this is not a zero-findings result.\n\n"
            + (failure or "Missing evidence")
        )
    )
    payload = {
        "name": CHECK,
        "head_sha": sha,
        "status": "completed",
        "conclusion": "success" if accepted else "failure",
        "external_id": "manual-sdk-audit:" + str(run_id) if run_id else "",
        "output": {
            "title": "Security Scan Completed" if accepted else "Security Scan Incomplete",
            "summary": summary,
        },
    }
    if run_id:
        payload["details_url"] = f"https://github.com/{repo}/actions/runs/{run_id}"
    # One attempt, including failures. A transport error or differing response remains an error.
    created = client.request("POST", prefix + "/check-runs", payload)
    require(
        created.get("head_sha") == sha
        and created.get("conclusion") == payload["conclusion"]
        and created.get("name") == CHECK,
        "Check publication outcome differs; inspect without retry",
    )
    return {
        "accepted": accepted,
        "ignored": False,
        "head_sha": sha,
        "run_id": run_id,
        "counts": counts,
        "reason": failure,
    }


def main():
    try:
        require(os.environ.get("GITHUB_REF") == "refs/heads/main", "Verifier must run from main")
        event = strict_json(Path(os.environ["GITHUB_EVENT_PATH"]).read_bytes())
        producer = (
            Path(__file__).resolve().parents[1] / "workflows/security-audit-manual.yml"
        ).read_bytes()
        result = verify_event(
            GitHub(os.environ.get("GITHUB_TOKEN", "")),
            os.environ["GITHUB_REPOSITORY"],
            os.environ["GITHUB_EVENT_NAME"],
            event,
            producer,
        )
        print(json.dumps(result, sort_keys=True))
        # Delivery succeeded even when the SDK gate was correctly published as failure.
        # Only the custom Security Scan conclusion represents audit acceptance.
        return 0
    except (Refusal, KeyError, OSError, TypeError, AttributeError) as exc:
        print(
            "Security audit verification failed: "
            + (str(exc) if isinstance(exc, Refusal) else "Missing controller context"),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
