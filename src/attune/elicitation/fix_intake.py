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

from attune.elicitation.intake_template import (
    PROVIDERS,
    TEMPLATES,
    FieldSlot,
    FormTemplate,
    ProviderContext,
    build_form,
)
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


def _is_production_path(rel: str) -> bool:
    """True for paths under a top-level ``src/`` with no ``tests`` part.

    Production packages legitimately contain modules with test-shaped
    NAMES (``test_gen_parallel.py`` is a workflow, not a suite), so a
    name match under ``src/`` is not probe material unless it sits in
    an embedded ``tests`` directory.
    """
    parts = rel.split("/")
    return parts[0] == "src" and "tests" not in parts


def probe_candidates(repo_root: Path, scopes: list[str], limit: int = 4) -> list[str]:
    """Suggested ``--probe`` commands: test files related to the scopes.

    Three derivations, all mechanical and ranked: test-shaped files
    INSIDE a scope directory first (the suite that guards the code
    being fixed — production paths under ``src/`` are excluded, since
    a workflow module named ``test_*.py`` is not a suite), then the
    mirror test directory for a scope dir
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
                    rel = match.relative_to(repo_root).as_posix()
                    if not _is_production_path(rel):
                        found.setdefault(rel, None)
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


def _provider_fix_scopes(ctx: ProviderContext) -> list[str]:
    """Registered provider: scope candidates for the fix intake."""
    return scope_candidates(ctx.repo_root)


def _provider_fix_probes(ctx: ProviderContext) -> list[str]:
    """Registered provider: probe candidates for the fix intake."""
    return probe_candidates(ctx.repo_root, scope_candidates(ctx.repo_root))


PROVIDERS["fix_scopes"] = _provider_fix_scopes
PROVIDERS["fix_probes"] = _provider_fix_probes

#: The fix intake, declaratively (Phase 2a). Slot keys are CLI
#: composition keys (request/scope/probes/mode), not the fix
#: workflow's input_schema keys, so the template is standalone
#: (unbound) by design — recorded in the Phase 2 execution notes.
FIX_TEMPLATE = FormTemplate(
    title="Fix intake",
    description="Compose an outcome-first fix: goal, scope, verification.",
    fields=[
        FieldSlot(
            key="request",
            text="What should be fixed, in your words?",
            control="textarea",
            required=True,
            help_text="Passed verbatim as the fix goal — no inference.",
        ),
        FieldSlot(
            key="scope",
            text="Where must the diff stay confined (--scope)?",
            provider="fix_scopes",
            other=OTHER,
            fallback_text="Where must the diff stay confined (--scope)? (path)",
            help_text="Changed paths first — a fix usually lands where the change is.",
        ),
        FieldSlot(
            key="probes",
            text="How do we verify the fix (--probe)?",
            provider="fix_probes",
            control="multi_select",
            fallback_text="How do we verify the fix? (one command, e.g. pytest tests/x.py)",
            help_text="Each probe is verified independently in the receipt.",
        ),
        FieldSlot(
            key="mode",
            text="Run it, or preview only?",
            options=["preview only", "preview then run"],
            default="preview only",
            help_text="Preview renders the contract and executes nothing.",
        ),
    ],
)

TEMPLATES["fix"] = FIX_TEMPLATE


def build_fix_intake_form(
    scopes: list[str],
    probes: list[str],
) -> FormSchema:
    """The one intake form: request + scope + probes + mode (D21).

    Phase 2a: built from :data:`FIX_TEMPLATE` with the pre-derived
    candidates as overrides — the hand-written construction this
    function used to contain is deleted (same-PR rule, spec D2).
    The structural-equality gate pins the output against the
    shipped hand shape.
    """
    return build_form(
        FIX_TEMPLATE,
        ProviderContext(repo_root=Path.cwd()),
        candidates_override={"scope": scopes, "probes": probes},
    )


def compose_fix_command(answers: dict[str, Any]) -> str:
    """Render answers as a copy-safe ``attune fix`` command line.

    Everything is ``shlex.quote``d; the ``--run`` flag appears only
    for the explicit "preview then run" answer.
    """
    request = str(answers.get("request", "")).strip()
    scope = str(answers.get("scope", "")).strip()
    probes_raw = answers.get("probes", [])
    if isinstance(probes_raw, str):
        probes: list[Any] = [probes_raw]
    elif isinstance(probes_raw, list | tuple):
        probes = list(probes_raw)
    else:
        # A dict used to be iterated to its KEYS, silently emitting a
        # wrong --probe at exit 0; a scalar raised TypeError. Neither
        # is a probe list (library-review E2).
        probes = []
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


def _read_answers() -> dict[str, Any] | None:
    """Read the answers object from stdin, or None when unusable.

    Mirrors ``spec_intake._read_answers``: unparseable input, or valid
    JSON that is not an object, previously crashed the ``.get`` chain
    with a traceback against a documented return-0 contract
    (library-review E2).
    """
    try:
        answers = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        print(f"error: could not parse answers JSON: {exc}", file=sys.stderr)
        return None
    if not isinstance(answers, dict):
        print(
            f"error: answers must be a JSON object, got {type(answers).__name__}",
            file=sys.stderr,
        )
        return None
    return answers


def _main(argv: list[str]) -> int:
    """CLI seam for the /fix skill.

    Default: print ``{"form": <form dict>, "scopes": [...],
    "probes": [...]}`` for the current repo. With ``--compose``,
    read answers JSON on stdin and print the composed command. With
    ``--list-dirs <path>``, print the drill-down payload for the
    "Other path" folder picker.
    """
    if "--compose" in argv:
        answers = _read_answers()
        if answers is None:
            return 2
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
