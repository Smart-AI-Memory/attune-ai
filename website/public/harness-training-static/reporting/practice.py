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
import tempfile
import time


_MAX_WORKER_BYTES = 4096
_COURSE_OPTIONS = {
    "init": ("--for", "--goal", "--project", "--scope", "--interpreter", "--tests", "--task-dir"),
    "plan": ("--request", "--project", "--config", "--task-dir", "--accept", "--checkpoint"),
    "build": ("--allow-external",),
    "status": ("--format",),
}
_COURSE_CHOICES = {"init": ("--for", "plan"), "status": ("--format", "markdown")}
_OPTION_DECLARATION = re.compile(r"^  (--[a-z][a-z-]*)(?=[ \t,]|$)([^\n]*)", re.MULTILINE)


class PreparationCommandError(ValueError):
    """A failed setup command with its original output, before text decoding."""

    def __init__(self, message, receipt, stdout=b"", stderr=b""):
        super().__init__(message)
        self.receipt = receipt
        self.stdout = stdout or b""
        self.stderr = stderr or b""


def _text(data):
    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _refusal_detail(stdout):
    """Show bounded structured Harness errors, never arbitrary terminal output."""
    try:
        result = json.loads(_text(stdout))
    except (ValueError, TypeError):
        return ""
    if not isinstance(result, dict) or result.get("status") != "failed":
        return ""
    error = result.get("error")
    if not isinstance(error, dict) or not isinstance(error.get("detail"), str):
        return ""
    detail = " ".join(error["detail"].split())
    return "".join(character for character in detail if character.isprintable())[:600]


def _run(command, failure, *, step, timeout=10):
    started = time.monotonic()
    receipt = {"step": step, "python": sys.executable, "timeout_seconds": timeout,
               "exit_code": None}
    stdout = stderr = b""
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        receipt.update(outcome="timeout", exception=type(exc).__name__)
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        explanation = f"The preparation command exceeded its {timeout:g}-second limit; partial effects are unknown."
    except OSError as exc:
        receipt.update(outcome="launch_failure", exception=type(exc).__name__, errno=exc.errno)
        explanation = f"The preparation command could not start ({type(exc).__name__})."
    else:
        if result.returncode == 0:
            return _text(result.stdout)
        stdout, stderr = result.stdout, result.stderr
        receipt.update(outcome="nonzero_exit", exit_code=result.returncode)
        explanation = f"The preparation command exited with code {result.returncode}."
        detail = _refusal_detail(stdout)
        if detail:
            explanation += f" Harness reported: {detail}"
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 6)
    raise PreparationCommandError(f"{failure}. {explanation}", receipt, stdout, stderr)


def _save_failure(destination, error):
    # A sibling cannot enter the project's frozen effects or overwrite an attempt.
    directory = Path(tempfile.mkdtemp(prefix="practice-diagnostics-", dir=destination.parent))
    (directory / "stdout.bin").write_bytes(error.stdout)
    (directory / "stderr.bin").write_bytes(error.stderr)
    artifacts = ("project", "project/.git", "task.work.json", "task", "task/record.json", "prepared.json")
    receipt = {**error.receipt, "destination": str(destination),
               "partial_artifacts": {name: (destination / name).exists() for name in artifacts},
               "accepted": False, "build_started": False, "model_calls": 0}
    (directory / "failure.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return directory


def _check_runtime():
    if sys.version_info < (3, 12):
        raise ValueError(
            f"Select Python 3.12 or later using the course setup instructions. Selected Python: {sys.executable}"
        )
    try:
        installed = version("attune-harness")
    except PackageNotFoundError as exc:
        raise ValueError(
            "Install Harness in this Python environment using the course setup instructions. "
            f"Selected Python: {sys.executable}"
        ) from exc

    python = [sys.executable, "-I", "-B", "-X", "utf8"]
    _run([*python, "-c", "import pytest"],
         "Install pytest in this Python environment using the course setup instructions", step="check-pytest")
    _run(["git", "--version"], "Install Git and make it available on PATH before starting the course",
         step="check-git")
    for command, required_options in _COURSE_OPTIONS.items():
        help_text = _run(
            [*python, "-m", "attune_harness", command, "--help"],
            f"Harness {installed} could not show {command} help. Select a compatible Harness environment",
            step=f"help-{command}",
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
    try:
        return _prepare(destination)
    except PreparationCommandError as exc:
        try:
            directory = _save_failure(destination, exc)
            diagnostic = f"Inspect the local diagnostics in {directory} before trying a new directory."
        except OSError as save_error:
            diagnostic = f"Diagnostics could not be saved ({type(save_error).__name__})."
        raise ValueError(
            f"{exc} Selected Python: {sys.executable}. "
            f"Existing files were kept; no plan was accepted or BUILD requested. {diagnostic}"
        ) from exc


def _prepare(destination):
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
         "Could not initialize the practice Git repository. Check Git", step="git-init")
    _run(["git", "-C", str(project), "add", "."],
         "Could not stage the practice files. Check Git", step="git-add")
    _run([
        "git", "-C", str(project), "-c", "commit.gpgsign=false",
        "-c", "user.name=Offline practice", "-c", "user.email=practice@example.invalid",
        "commit", "-qm", "Prepare the offline reporting fixture\n\n"
        + "Co-Authored-By: GPT-6 (Codex) <codex@openai.com>",
    ], "Could not commit the practice files. Check Git", step="git-commit")
    task = destination / "task"
    result = _run([
        sys.executable, "-I", "-B", "-X", "utf8", "-m", "attune_harness", "init", "--for", "plan",
        "--goal", "Complete the activity report", "--project", str(project),
        "--scope", "report.py", "--interpreter", sys.executable,
        "--tests", "tests/test_report.py", "tests/test_html_report.py",
        "--task-dir", str(task),
    ], "Harness could not prepare the practice request", step="prepare-request", timeout=30)
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
