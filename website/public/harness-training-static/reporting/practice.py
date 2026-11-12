"""Prepare a new offline reporting project; accept and build it separately."""

import argparse
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


_MAX_WORKER_BYTES = 4096
_COURSE_OPTIONS = {
    "init": ("--for", "--goal", "--project", "--scope", "--interpreter", "--tests", "--task-dir"),
    "plan": ("--request", "--project", "--config", "--task-dir", "--accept", "--checkpoint"),
    "build": ("--allow-external",),
    "status": ("--format",),
}
_COURSE_CHOICES = {"init": ("--for", "plan"), "status": ("--format", "markdown")}
_OPTION_DECLARATION = re.compile(r"^  (--[a-z][a-z-]*)(?=[ \t,]|$)([^\n]*)", re.MULTILINE)


def _run(command, failure, *, timeout=10):
    try:
        return subprocess.run(
            command, check=True, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=timeout,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(failure) from exc


def _check_runtime():
    if sys.version_info < (3, 12):
        raise ValueError("Select Python 3.12 or later using the course setup instructions")
    try:
        installed = version("attune-harness")
    except PackageNotFoundError as exc:
        raise ValueError("Install Harness in this Python environment using the course setup instructions") from exc

    python = [sys.executable, "-I", "-B"]
    _run([*python, "-c", "import pytest"],
         "Install pytest in this Python environment using the course setup instructions")
    _run(["git", "--version"], "Install Git and make it available on PATH before starting the course")
    for command, required_options in _COURSE_OPTIONS.items():
        help_text = _run(
            [*python, "-m", "attune_harness", command, "--help"],
            f"Harness {installed} could not show {command} help. Select a compatible Harness environment",
        )
        declarations = dict(_OPTION_DECLARATION.findall(help_text))
        for option in required_options:
            if option not in declarations:
                raise ValueError(
                    f"Harness {installed} does not expose {command} {option}. "
                    "Select a compatible Harness environment"
                )
        if command in _COURSE_CHOICES:
            option, required_choice = _COURSE_CHOICES[command]
            choices = re.match(r"\s*\{([^}]+)\}", declarations[option])
            if not choices or required_choice not in choices[1].split(","):
                raise ValueError(
                    f"Harness {installed} does not expose {command} {option} {required_choice}. "
                    "Select a compatible Harness environment"
                )
        if command in ("build", "status") and not re.search(r"(?m)^  task_dir(?:[ \t]|$)", help_text):
            raise ValueError(
                f"Harness {installed} does not expose the {command} task directory argument. "
                "Select a compatible Harness environment"
            )
    return installed


def prepare(destination):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Choose a new practice directory; existing work is preserved")
    if destination.parent.resolve() != destination.parent:
        raise ValueError("Use a canonical parent directory, such as /private/tmp on macOS")
    installed = _check_runtime()
    source = Path(__file__).resolve().parent / "assets" / "example"
    try:
        reference_bytes = (source / "report.py").read_bytes()
    except OSError as exc:
        raise ValueError("Extract the complete reporting practice bundle and try again") from exc
    reference = destination / "reference.py"
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    worker = f'''import hashlib, json, pathlib, sys
request = json.load(sys.stdin)
turn = request["turn"]
if turn["role"] == "worker":
    data = pathlib.Path({str(reference)!r}).read_bytes()
    if hashlib.sha256(data).hexdigest() != {reference_hash!r}:
        raise SystemExit("The fixed practice reference changed")
    selected = turn["output_schema"]["files"][0]
    result = {{"schema_version": 2, "files": [{{
        "path": selected["path"], "before_sha256": selected["before_sha256"],
        "text": data.decode("utf-8")}}]}}
else:
    result = {{"kind": "critique", "findings": [], "notes": [
        "Deterministic protocol witness; no substantive review performed."]}}
print(json.dumps({{"schema_version": 1,
    "request_digest": request["request_digest"],
    "action": {{"kind": "final", "text": json.dumps(result)}}}}))
'''
    if len(worker.encode("utf-8")) > _MAX_WORKER_BYTES:
        raise ValueError("The selected practice path exceeds the command argument bound")
    try:
        destination.mkdir()
    except FileExistsError as exc:
        raise ValueError("Choose a new practice directory; existing work is preserved") from exc
    project = destination / "project"
    project.mkdir()
    for name in ("tests", "data", "expected"):
        shutil.copytree(source / name, project / name,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    shutil.copyfile(source / "pytest.ini", project / "pytest.ini")
    reference.write_bytes(reference_bytes)
    (project / "report.py").write_text(
        '\"\"\"Unfinished offline practice program.\"\"\"\n'
        'raise SystemExit("Reporting implementation is not ready")\n', encoding="utf-8",
    )
    seat = {
        "adapter": "command", "command": [sys.executable, "-B", "-c", worker],
        "timeout": 30, "tools": [], "max_turns": 1, "max_tool_calls": 0,
        "environment": {"profile": "command-env-v1", "passthrough": []},
    }
    registry = project / "participants.json"
    registry.write_text(json.dumps({"schema_version": 1, "participants": {
        "lead": seat, "reviewer": seat}}, indent=2) + "\n", encoding="utf-8")
    _run(["git", "init", "-q", str(project)],
         "Could not initialize the practice Git repository. Check Git and choose a new practice directory")
    _run(["git", "-C", str(project), "add", "."],
         "Could not stage the practice files. Check Git and choose a new practice directory")
    _run([
        "git", "-C", str(project), "-c", "commit.gpgsign=false",
        "-c", "user.name=Offline practice", "-c", "user.email=practice@example.invalid",
        "commit", "-qm", "Prepare the offline reporting fixture\n\n"
        + "Co-Authored-By: GPT-6 (Codex) <codex@openai.com>",
    ], "Could not commit the practice files. Check Git and choose a new practice directory")
    task = destination / "task"
    result = _run([
        sys.executable, "-I", "-B", "-m", "attune_harness", "init", "--for", "plan",
        "--goal", "Complete the activity report", "--project", str(project),
        "--scope", "report.py", "--interpreter", sys.executable,
        "--tests", "tests/test_report.py", "tests/test_html_report.py",
        "--task-dir", str(task),
    ], "Harness could not prepare the practice request. Check the selected environment and choose a new practice directory",
        timeout=30)
    request = destination / "task.work.json"
    try:
        content = json.loads(request.read_text(encoding="utf-8"))
        init = json.loads(result)
        if not isinstance(content, dict) or not isinstance(content.get("effects"), dict):
            raise ValueError("The work request did not include an effect manifest")
        if not isinstance(init, dict) or init.get("status") != "created":
            raise ValueError("The init receipt did not report a created request")
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"Harness {installed} did not prepare a usable practice request. "
            "Select a compatible Harness environment and choose a new practice directory"
        ) from exc
    protected = sorted(p.relative_to(project).as_posix()
                       for p in project.rglob("*")
                       if p.is_file() and ".git" not in p.parts and p.name != "report.py")
    content["effects"]["protected"] = protected
    request.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    record = {
        "runtime": installed, "project": str(project),
        "task": str(task), "request": str(request), "registry": str(registry),
        "python": sys.executable, "reference_sha256": reference_hash,
        "protected": protected, "init": init,
        "accepted": False, "build_started": False, "model_calls": 0,
    }
    (destination / "prepared.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    try:
        print(json.dumps(prepare(parser.parse_args().destination), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Practice setup failed: {exc}\n")
