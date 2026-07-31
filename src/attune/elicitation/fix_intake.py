"""Fix intake — derived scope/probe candidates and the intake form.

Task 4 of docs/specs/outcome-first-fix/: input ergonomics for the
interactive (plugin/skill) surface. Candidates are DERIVED from the
working tree — git-changed paths for scope, matching test files for
probes, and on a clean tree the recently-touched directories from
git history — never from a hand-maintained registry. The CLI
contract (`attune fix`) is composed, not changed.

The module degrades to free-text fields when git is unavailable or
nothing is derivable: the form never blocks intake.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import shlex
import subprocess  # nosec B404 — git plumbing only, fixed argv lists
import sys
from pathlib import Path
from typing import Any

from attune.elicitation.bridge import form_from_dict
from attune.meta_workflows.models import FormSchema

#: Free-text sentinel offered alongside derived options.
OTHER = "other (type a path)"

_SKIP_PARTS = frozenset({"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"})

_TEST_PATTERNS = ("test_*.py", "*_test.py", "*_suite.py")


def _git_changed_files(repo_root: Path) -> list[str]:
    """Changed/untracked files from ``git status --porcelain``, POSIX form.

    Untracked directories are expanded to their contained files (git
    collapses them to one ``dir/`` entry). Missing git degrades to [].
    """
    try:
        proc = subprocess.run(  # nosec B603 B607 — fixed argv, no shell
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    files: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) <= 3:
            continue
        payload = line[3:].strip().strip('"')
        if " -> " in payload:
            payload = payload.partition(" -> ")[2].strip().strip('"')
        target = repo_root / payload
        if target.is_dir():
            for child in sorted(target.rglob("*")):
                if child.is_file():
                    rel = child.relative_to(repo_root).as_posix()
                    if not _SKIP_PARTS.intersection(rel.split("/")):
                        files.append(rel)
        elif target.is_file():
            if not _SKIP_PARTS.intersection(payload.split("/")):
                files.append(payload)
    return files


def _git_recent_file_counts(repo_root: Path, commits: int = 40) -> dict[str, int]:
    """Touch counts per still-existing file over recent commits.

    Missing git, no history, or a timeout all degrade to {}.
    """
    try:
        proc = subprocess.run(  # nosec B603 B607 — fixed argv, no shell
            ["git", "-C", str(repo_root), "log", "--name-only", f"-{commits}", "--pretty=format:"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0:
        return {}
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        path = line.strip()
        if not path or _SKIP_PARTS.intersection(path.split("/")):
            continue
        if (repo_root / path).is_file():
            counts[path] = counts.get(path, 0) + 1
    return counts


def _fallback_scope_candidates(repo_root: Path, limit: int) -> list[str]:
    """Recently-touched directories from git history, most-touched first.

    The clean-tree fallback: with nothing changed, the places work
    recently landed are the likeliest fix targets — still mechanical,
    still registry-free.
    """
    scores: dict[str, int] = {}
    for path, count in _git_recent_file_counts(repo_root).items():
        parent = Path(path).parent.as_posix()
        if parent == "." or not (repo_root / parent).is_dir():
            continue
        scores[parent] = scores.get(parent, 0) + count
    ranked = sorted(scores, key=lambda d: (-scores[d], d))
    return ranked[:limit]


def scope_candidates(repo_root: Path, limit: int = 6) -> list[str]:
    """Likely ``--scope`` values: changed files first, then their parents.

    A fix usually targets where the problem already is — the changed
    set — so changed source files lead, followed by their containing
    directories for wider scopes. On a clean tree, falls back to
    recently-touched directories from git history, so the form keeps
    its picker whenever history exists. Deduplicated, capped at
    ``limit``.
    """
    changed = _git_changed_files(repo_root)
    ordered: dict[str, None] = {}
    for path in changed:
        ordered.setdefault(path, None)
    for path in changed:
        parent = Path(path).parent.as_posix()
        if parent != ".":
            ordered.setdefault(parent, None)
    if not ordered:
        return _fallback_scope_candidates(repo_root, limit)
    return list(ordered)[:limit]


def _is_test_shaped(name: str) -> bool:
    return name.startswith("test_") or name.endswith(("_test.py", "_suite.py"))


def probe_candidates(repo_root: Path, scopes: list[str], limit: int = 4) -> list[str]:
    """Suggested ``--probe`` commands: test files related to the scopes.

    Three derivations, all mechanical and ranked: test-shaped files
    INSIDE a scope directory first (the suite that guards the code
    being fixed), then the mirror test directory for a scope dir
    (``src/pkg/x`` → ``tests/unit/x`` or ``tests/x``), then
    test-shaped files under ``tests/`` whose name contains a scope
    file's stem. Returned as runnable ``pytest <path>`` commands.
    """
    found: dict[str, None] = {}
    tests_root = repo_root / "tests"
    for scope in scopes:
        target = repo_root / scope
        if target.is_dir():
            for pattern in _TEST_PATTERNS:
                for match in sorted(target.rglob(pattern)):
                    found.setdefault(match.relative_to(repo_root).as_posix(), None)
    for scope in scopes:
        name = Path(scope).name
        target = repo_root / scope
        if target.is_dir() and name and not name.startswith("test"):
            for mapped in (f"tests/unit/{name}", f"tests/{name}"):
                if (repo_root / mapped).is_dir():
                    found.setdefault(f"{mapped}/", None)
    for scope in scopes:
        target = repo_root / scope
        stem = Path(scope).stem
        if target.is_file() and tests_root.is_dir() and not stem.startswith("test"):
            for match in sorted(tests_root.rglob(f"*{stem}*.py")):
                if _is_test_shaped(match.name):
                    found.setdefault(match.relative_to(repo_root).as_posix(), None)
    return [f"pytest {path}" for path in list(found)[:limit]]


def build_fix_intake_form(
    scopes: list[str],
    probes: list[str],
) -> FormSchema:
    """The one intake form: request + scope + probes + mode (D21).

    Scope and probe fields render as pickers when candidates exist and
    as free text otherwise — the form is always buildable.
    """
    fields: list[dict[str, Any]] = [
        {
            "id": "request",
            "text": "What should be fixed, in your words?",
            "type": "textarea",
            "required": True,
            "help_text": "Passed verbatim as the fix goal — no inference.",
        }
    ]
    if scopes:
        fields.append(
            {
                "id": "scope",
                "text": "Where must the diff stay confined (--scope)?",
                "type": "single_select",
                "options": [*scopes, OTHER],
                "help_text": "Changed paths first — a fix usually lands where the change is.",
            }
        )
    else:
        fields.append(
            {
                "id": "scope",
                "text": "Where must the diff stay confined (--scope)? (path)",
                "type": "text_input",
                "required": True,
            }
        )
    if probes:
        fields.append(
            {
                "id": "probes",
                "text": "How do we verify the fix (--probe)?",
                "type": "multi_select",
                "options": probes,
                "help_text": "Each probe is verified independently in the receipt.",
            }
        )
    else:
        fields.append(
            {
                "id": "probes",
                "text": "How do we verify the fix? (one command, e.g. pytest tests/x.py)",
                "type": "text_input",
                "required": True,
            }
        )
    fields.append(
        {
            "id": "mode",
            "text": "Run it, or preview only?",
            "type": "single_select",
            "options": ["preview only", "preview then run"],
            "default": "preview only",
            "help_text": "Preview renders the contract and executes nothing.",
        }
    )
    return form_from_dict(
        {
            "title": "Fix intake",
            "description": "Compose an outcome-first fix: goal, scope, verification.",
            "fields": fields,
        }
    )


def compose_fix_command(answers: dict[str, Any]) -> str:
    """Render answers as a copy-safe ``attune fix`` command line.

    Everything is ``shlex.quote``d; the ``--run`` flag appears only
    for the explicit "preview then run" answer.
    """
    request = str(answers.get("request", "")).strip()
    scope = str(answers.get("scope", "")).strip()
    probes_raw = answers.get("probes", [])
    probes = [probes_raw] if isinstance(probes_raw, str) else list(probes_raw)
    parts = ["attune", "fix", shlex.quote(request), "--workflow", "fix"]
    for probe in probes:
        probe_text = str(probe).strip()
        if probe_text:
            parts += ["--probe", shlex.quote(probe_text)]
    if scope and scope != OTHER:
        parts += ["--scope", shlex.quote(scope)]
    if str(answers.get("mode", "")).strip() == "preview then run":
        parts.append("--run")
    return " ".join(parts)


def list_subdirectories(repo_root: Path, raw: str) -> dict[str, Any]:
    """Immediate subdirectories of a repo-relative path, for drill-down.

    Powers the "Other path" folder picker: the skill renders each
    level's directories as pills and drills by re-calling with the
    picked one. The path is validated to stay inside ``repo_root``;
    escapes and non-directories return an ``error`` payload instead
    of raising, so the picker degrades to free text.
    """
    base = (repo_root / raw).resolve()
    try:
        rel = base.relative_to(repo_root.resolve())
    except ValueError:
        return {"error": "path escapes the repository", "path": raw, "dirs": []}
    if not base.is_dir():
        return {"error": "not a directory", "path": raw, "dirs": []}
    dirs = sorted(
        child.name
        for child in base.iterdir()
        if child.is_dir() and child.name not in _SKIP_PARTS and not child.name.startswith(".")
    )
    return {"path": rel.as_posix(), "dirs": dirs}


def _main(argv: list[str]) -> int:
    """CLI seam for the /fix skill.

    Default: print ``{"form": <form dict>, "scopes": [...],
    "probes": [...]}`` for the current repo. With ``--compose``,
    read answers JSON on stdin and print the composed command. With
    ``--list-dirs <path>``, print the drill-down payload for the
    "Other path" folder picker.
    """
    if "--compose" in argv:
        answers = json.load(sys.stdin)
        print(compose_fix_command(answers))
        return 0
    if "--list-dirs" in argv:
        idx = argv.index("--list-dirs")
        raw = argv[idx + 1] if len(argv) > idx + 1 else "."
        print(json.dumps(list_subdirectories(Path.cwd(), raw)))
        return 0
    repo_root = Path.cwd()
    scopes = scope_candidates(repo_root)
    probes = probe_candidates(repo_root, scopes)
    form = build_fix_intake_form(scopes, probes)
    payload = {
        "form": {
            "title": form.title,
            "description": form.description,
            "fields": [
                {
                    "id": q.id,
                    "text": q.text,
                    "type": q.type.value,
                    "options": list(q.options),
                    "default": q.default,
                    "help_text": q.help_text,
                    "required": q.required,
                }
                for q in form.questions
            ],
        },
        "scopes": scopes,
        "probes": probes,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover — thin seam, tested via functions
    raise SystemExit(_main(sys.argv[1:]))
