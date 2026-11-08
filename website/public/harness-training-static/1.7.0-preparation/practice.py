"""Prepare a new offline reporting project; accept and build it separately."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys


def prepare(destination):
    if sys.version_info < (3, 12) or version("attune-harness") != "1.7.0":
        raise ValueError("Select Python 3.12 or later with installed Harness 1.7.0")
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Choose a new practice directory; existing work is preserved")
    if destination.parent.resolve() != destination.parent:
        raise ValueError("Use a canonical parent directory, such as /private/tmp on macOS")
    source = Path(__file__).resolve().parent / "assets" / "example"
    destination.mkdir()
    project = destination / "project"
    project.mkdir()
    for name in ("tests", "data", "expected"):
        shutil.copytree(source / name, project / name,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    shutil.copyfile(source / "pytest.ini", project / "pytest.ini")
    reference = destination / "reference.py"
    shutil.copyfile(source / "report.py", reference)
    reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    (project / "report.py").write_text(
        '"""Unfinished offline practice program."""\n'
        'raise SystemExit("Reporting implementation is not ready")\n', encoding="utf-8"
    )
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
    if len(worker.encode("utf-8")) > 4096:
        raise ValueError("The selected practice path exceeds the command argument bound")
    seat = {
        "adapter": "command", "command": [sys.executable, "-B", "-c", worker],
        "timeout": 30, "tools": [], "max_turns": 1, "max_tool_calls": 0,
        "environment": {"profile": "command-env-v1", "passthrough": []},
    }
    registry = project / "participants.json"
    registry.write_text(json.dumps({"schema_version": 1, "participants": {
        "lead": seat, "reviewer": seat}}, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(project), "-c", "commit.gpgsign=false",
        "-c", "user.name=Offline practice", "-c", "user.email=practice@example.invalid",
        "commit", "-qm", "Prepare the offline reporting fixture\n\n"
        + "Co-Authored-By: GPT-6 (Codex) <codex@openai.com>",
    ], check=True)
    task = destination / "task"
    result = subprocess.run([
        sys.executable, "-I", "-m", "attune_harness", "init", "--for", "plan",
        "--goal", "Complete the activity report", "--project", str(project),
        "--scope", "report.py", "--interpreter", sys.executable,
        "--tests", "tests/test_report.py", "tests/test_html_report.py",
        "--task-dir", str(task),
    ], check=True, capture_output=True, text=True)
    request = destination / "task.work.json"
    content = json.loads(request.read_text(encoding="utf-8"))
    protected = sorted(p.relative_to(project).as_posix()
                       for p in project.rglob("*")
                       if p.is_file() and ".git" not in p.parts and p.name != "report.py")
    content["effects"]["protected"] = protected
    request.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    record = {
        "runtime": version("attune-harness"), "project": str(project),
        "task": str(task), "request": str(request), "registry": str(registry),
        "python": sys.executable, "reference_sha256": reference_hash,
        "protected": protected, "init": json.loads(result.stdout),
        "accepted": False, "build_started": False, "model_calls": 0,
    }
    (destination / "prepared.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    print(json.dumps(prepare(parser.parse_args().destination), indent=2))
