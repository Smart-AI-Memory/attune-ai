#!/usr/bin/env python3
"""Documentation import gate — verify every ``attune`` import in a doc
code fence actually resolves against the installed package.

This is the FINAL guard for the recurring "feature removed in PR X, but
the docs still ``from attune import <gone>``" failure that produced the
``orchestration-doc-fiction-cleanup`` and ``empathy-doc-fiction-cleanup``
specs. A reader who copies a fence should never hit ``ImportError``.

What it checks:

- Every fenced ``python`` / ``py`` code block in the in-scope docs.
- Each ``from attune... import ...`` / ``import attune...`` line in those
  fences. Non-``attune`` imports (stdlib, third-party) are IGNORED — we
  only guarantee our own symbols resolve.
- Resolution is IMPORT-ONLY and IN-PROCESS: the module is imported and
  each name checked with ``hasattr``. Fence BODIES are never executed
  (no side effects, no network, no API keys).

What it does NOT check: method/attribute accuracy (``obj.method()``),
runtime behavior. Import resolution is the high-signal, low-false-
positive layer; deeper checking is intentionally out of scope.

Scope (published surfaces only):

- INCLUDE: ``docs/**``, ``content/features/**``, ``content/blog/**``.
- EXCLUDE: ``docs/specs/**`` and any ``**/archive/**`` (history
  legitimately names removed symbols), and generated bundles
  (``plugin/help/generated/**`` — checked at their source instead).

Escape hatch: a fence preceded (within 3 lines, blanks allowed) by an
HTML comment ``<!-- doc-import-skip: <reason> -->`` is skipped. Use it
ONLY for fences that intentionally show removed/old code (a migration
"before:" block) — the reason is required and reported.

Run:

    python scripts/audit_doc_imports.py                 # human report
    python scripts/audit_doc_imports.py --format json   # CI-shaped
    python scripts/audit_doc_imports.py --paths docs/reference  # subset

Exit codes:
    0  — every attune import in scope resolves (or was skipped w/ reason).
    1  — one or more imports do not resolve (CI fails).
    2  — bad invocation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --- scope ----------------------------------------------------------------

INCLUDE_GLOBS = (
    "docs/**/*.md",
    "content/features/**/*.md",
    "content/blog/**/*.md",
)
EXCLUDE_SUBSTRINGS = (
    "/specs/",
    "/archive/",
    "/generated/",
)

_FENCE_RE = re.compile(r"```(?:python|py)\b[^\n]*\n(.*?)```", re.DOTALL)
_IMPORT_LINE_RE = re.compile(r"^\s*(from\s+attune[\w.]*\s+import\s+.+|import\s+attune[\w.]*.*)$")
_SKIP_RE = re.compile(r"<!--\s*doc-import-skip:\s*(?P<reason>.+?)\s*-->")


@dataclass
class Finding:
    file: str
    line: int
    statement: str
    message: str
    severity: str = "error"


@dataclass
class Stats:
    files: int = 0
    fences: int = 0
    imports_checked: int = 0
    skipped_fences: int = 0
    skips: list[str] = field(default_factory=list)


# --- fence + import extraction --------------------------------------------


def _iter_python_fences(text: str):
    """Yield (start_line, body, skipped, skip_reason) for each python fence.

    ``skipped`` is True when a ``doc-import-skip`` marker sits within the
    3 lines preceding the fence opener (blank lines allowed between).
    """
    lines = text.splitlines()
    # Map character offset of each fence match to its 1-based start line.
    for m in _FENCE_RE.finditer(text):
        start_line = text.count("\n", 0, m.start()) + 1
        # Look back up to 3 non-blank-significant lines for a skip marker.
        skip_reason = None
        i = start_line - 2  # line just above the ``` opener (0-based index)
        looked = 0
        while i >= 0 and looked < 3:
            raw = lines[i].strip()
            if raw:
                sm = _SKIP_RE.search(raw)
                if sm:
                    skip_reason = sm.group("reason")
                break  # first non-blank line above decides
            i -= 1
            looked += 1
        body_start_line = start_line + 1  # first line inside the fence
        yield body_start_line, m.group(1), skip_reason is not None, skip_reason


def _import_statements(body: str) -> list[tuple[int, str]]:
    """Return (offset_within_body, statement) for each attune import.

    Prefers AST (handles multi-line parenthesized imports); falls back to
    a line scan for snippet fences that are not parseable modules.
    """
    out: list[tuple[int, str]] = []
    try:
        tree = ast.parse(body)
    except SyntaxError:
        for idx, ln in enumerate(body.splitlines()):
            if _IMPORT_LINE_RE.match(ln) and "(" not in ln:
                out.append((idx, ln.strip()))
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("attune"):
                names = ", ".join(
                    a.name + (f" as {a.asname}" if a.asname else "") for a in node.names
                )
                out.append((node.lineno - 1, f"from {mod} import {names}"))
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("attune"):
                    stmt = f"import {a.name}" + (f" as {a.asname}" if a.asname else "")
                    out.append((node.lineno - 1, stmt))
    return out


# --- resolution -----------------------------------------------------------


def _resolve(statement: str) -> str | None:
    """Return an error message if the import does not resolve, else None.

    Import-only and in-process: imports the module and checks each name
    with ``hasattr``. Never executes fence bodies.
    """
    try:
        if statement.startswith("import "):
            mod = statement[len("import ") :].split(" as ")[0].strip()
            importlib.import_module(mod)
            return None
        # from MOD import A, B as C, ...
        head, _, tail = statement.partition(" import ")
        mod = head[len("from ") :].strip()
        module = importlib.import_module(mod)
        missing = []
        for piece in tail.split(","):
            name = piece.strip().split(" as ")[0].strip()
            if name and name != "*" and not hasattr(module, name):
                missing.append(name)
        if missing:
            return f"{mod} has no attribute(s): {', '.join(missing)}"
        return None
    except ModuleNotFoundError as e:
        return f"ModuleNotFoundError: {e}"
    except ImportError as e:
        return f"ImportError: {e}"
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: a doc import that blows up any other way (e.g. a
        # module-level error) is still a broken fence the reader would hit.
        return f"{type(e).__name__}: {e}"


# --- driver ---------------------------------------------------------------


def _in_scope(path: Path, repo: Path) -> bool:
    rel = "/" + str(path.relative_to(repo)).replace("\\", "/")
    return not any(sub in rel for sub in EXCLUDE_SUBSTRINGS)


def audit(repo: Path, paths: list[str] | None) -> tuple[list[Finding], Stats]:
    findings: list[Finding] = []
    stats = Stats()
    if paths:
        files = []
        for p in paths:
            fp = repo / p
            files.extend(fp.rglob("*.md") if fp.is_dir() else [fp])
    else:
        files = []
        for g in INCLUDE_GLOBS:
            files.extend(repo.glob(g))
    for f in sorted(set(files)):
        if not f.is_file() or f.suffix != ".md" or not _in_scope(f, repo):
            continue
        text = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(repo))
        had_fence = False
        for body_line, body, skipped, reason in _iter_python_fences(text):
            stmts = _import_statements(body)
            if not stmts:
                continue
            had_fence = True
            stats.fences += 1
            if skipped:
                stats.skipped_fences += 1
                stats.skips.append(f"{rel}:{body_line} ({reason})")
                continue
            for off, stmt in stmts:
                stats.imports_checked += 1
                err = _resolve(stmt)
                if err:
                    findings.append(Finding(rel, body_line + off, stmt, err))
        if had_fence:
            stats.files += 1
    return findings, stats


def _format_markdown(findings: list[Finding], stats: Stats) -> str:
    lines = [
        "# Doc import audit",
        "",
        f"Checked {stats.imports_checked} attune import(s) across "
        f"{stats.fences} fence(s) in {stats.files} file(s); "
        f"{stats.skipped_fences} fence(s) skipped.",
        "",
    ]
    if findings:
        lines.append(f"## {len(findings)} unresolved import(s)")
        lines.append("")
        for fn in findings:
            lines.append(f"- `{fn.file}:{fn.line}` — `{fn.statement}`")
            lines.append(f"  - {fn.message}")
    else:
        lines.append("All attune imports resolve. ✅")
    if stats.skips:
        lines.append("")
        lines.append("## Skipped (doc-import-skip)")
        lines.append("")
        lines.extend(f"- {s}" for s in stats.skips)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--paths", nargs="*", help="Limit to these files/dirs (repo-relative).")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    # Make in-repo ``src`` importable for local runs (CI installs the pkg).
    src = repo / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    findings, stats = audit(repo, args.paths)

    if args.format == "json":
        print(
            json.dumps(
                {
                    "findings": [vars(f) for f in findings],
                    "stats": vars(stats),
                },
                indent=2,
            )
        )
    else:
        print(_format_markdown(findings, stats))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
