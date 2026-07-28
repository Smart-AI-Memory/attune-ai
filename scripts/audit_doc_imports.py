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

What it does NOT check (base layer): method/attribute accuracy
(``obj.method()``), runtime behavior. Import resolution is the
high-signal, low-false-positive layer.

G4 deep layer (claim-drift-gates G4, D6 — extends this auditor
rather than adding a parallel one): files opted in via
``.claude/gates/doc-deep-check-allowlist.txt`` (``<path> ::
<reason>`` — the reason is REQUIRED) additionally get:

- **Kwarg/attr resolution** in python fences: keyword arguments on
  calls to fence-imported attune callables are bound against the
  live ``inspect.signature`` (no ``**kwargs`` escape), attribute
  chains rooted at fence-imported modules/classes must resolve, and
  attributes read off constructor-assigned DATACLASS instances must
  be real fields. Non-dataclass instance attrs are deliberately
  unchecked (instance-only attrs would false-positive).
- **MCP-config resolution** in json fences: every ``-m <module>``
  token inside ``args`` lists must be importable
  (``find_spec``), and documented ``mcpServers`` entries are
  diffed against the real ``.claude/mcp.json`` (shared server
  names must match ``command``/``args``; fence-only servers are
  flagged).

Fence bodies are still NEVER executed.

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
import dataclasses
import importlib
import importlib.util
import inspect
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
_JSON_FENCE_RE = re.compile(r"```json\b[^\n]*\n(.*?)```", re.DOTALL)
_IMPORT_LINE_RE = re.compile(r"^\s*(from\s+attune[\w.]*\s+import\s+.+|import\s+attune[\w.]*.*)$")
_SKIP_RE = re.compile(r"<!--\s*doc-import-skip:\s*(?P<reason>.+?)\s*-->")

#: G4 opt-in allowlist — deep checks run ONLY for files listed here.
DEEP_ALLOWLIST = ".claude/gates/doc-deep-check-allowlist.txt"


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
    deep_files: int = 0
    skips: list[str] = field(default_factory=list)


# --- fence + import extraction --------------------------------------------


def _iter_python_fences(text: str, fence_re: re.Pattern = _FENCE_RE):
    """Yield (start_line, body, skipped, skip_reason) for each python fence.

    ``skipped`` is True when a ``doc-import-skip`` marker sits within the
    3 lines preceding the fence opener (blank lines allowed between).
    """
    lines = text.splitlines()
    # Map character offset of each fence match to its 1-based start line.
    for m in fence_re.finditer(text):
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

    Delegates to the shared authoritative resolver
    (``attune.authoring.fact_check.imports``, #1586) so this gate and
    the master fact-check produce one import verdict. Imported lazily:
    ``main()`` puts the in-repo ``src`` on ``sys.path`` first, so the
    script keeps working in a checkout where the package isn't
    installed. Never executes fence bodies.
    """
    from attune.authoring.fact_check.imports import resolve_import_statement

    return resolve_import_statement(statement)


# --- G4 deep checks (kwargs/attrs + MCP module paths) ----------------------


def _load_deep_allowlist(repo: Path) -> tuple[dict[str, str], list[Finding]]:
    """Load the opt-in deep-check allowlist: ``<path> :: <reason>``.

    A line without a reason is a FINDING (the reason string is
    required by the G4 contract), never silently accepted.
    """
    entries: dict[str, str] = {}
    findings: list[Finding] = []
    fp = repo / DEEP_ALLOWLIST
    if not fp.exists():
        return entries, findings
    for idx, ln in enumerate(fp.read_text(encoding="utf-8").splitlines(), start=1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        path, sep, reason = s.partition("::")
        if not sep or not reason.strip():
            findings.append(
                Finding(DEEP_ALLOWLIST, idx, s, "allowlist entry needs '<path> :: <reason>'")
            )
            continue
        entries[path.strip()] = reason.strip()
    return entries, findings


def _fence_objects(tree: ast.AST) -> dict[str, object]:
    """Resolve a fence's attune imports to live objects (name -> object).

    Unresolvable imports are silently skipped here — the BASE layer
    already reports them; the deep layer only checks what resolves.
    """
    objects: dict[str, object] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("attune"):
            try:
                module = importlib.import_module(node.module or "")
            except Exception:  # noqa: BLE001 — base layer owns this report
                continue
            for a in node.names:
                obj = getattr(module, a.name, None)
                if obj is not None:
                    objects[a.asname or a.name] = obj
        elif isinstance(node, ast.Import):
            for a in node.names:
                if not a.name.startswith("attune"):
                    continue
                try:
                    importlib.import_module(a.name)
                except Exception:  # noqa: BLE001 — base layer owns this report
                    continue
                if a.asname:
                    objects[a.asname] = sys.modules[a.name]
                else:
                    root = a.name.split(".")[0]
                    objects[root] = sys.modules[root]
    return objects


def _resolve_chain(node: ast.AST, objects: dict[str, object]) -> tuple[object | None, str | None]:
    """Resolve a ``Name``/``Attribute`` chain to a live object.

    Returns ``(object, None)`` on success, ``(None, message)`` when a
    link in a rooted chain is missing, ``(None, None)`` when the chain
    is not rooted at a fence-imported name (not ours to judge).
    """
    parts: list[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name) or cur.id not in objects:
        return None, None
    obj = objects[cur.id]
    dotted = cur.id
    for attr in reversed(parts):
        if not hasattr(obj, attr):
            return None, f"{dotted} has no attribute {attr!r}"
        dotted += "." + attr
        obj = getattr(obj, attr)
    return obj, None


def _deep_check_python(body: str) -> list[tuple[int, str, str]]:
    """G4(a): kwarg + attribute resolution for one python fence.

    Returns ``(line_offset, expression, message)`` triples. Checks:

    - attribute chains rooted at fence-imported names resolve;
    - keyword args on resolved callables bind against the live
      signature (callables taking ``**kwargs`` are skipped);
    - attributes read off constructor-assigned DATACLASS instances
      are real fields/methods. Non-dataclass instances are skipped
      (instance-only attrs set in ``__init__`` would false-positive).
    """
    out: list[tuple[int, str, str]] = []
    try:
        tree = ast.parse(body)
    except SyntaxError:
        return out
    objects = _fence_objects(tree)
    if not objects:
        return out

    instances: dict[str, type] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            target_obj, _err = _resolve_chain(node.value.func, objects)
            if target_obj is not None and inspect.isclass(target_obj):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        instances[tgt.id] = target_obj

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_obj, err = _resolve_chain(node.func, objects)
            if err:
                out.append((node.lineno - 1, ast.unparse(node.func), err))
                continue
            if func_obj is None or not callable(func_obj):
                continue
            kwargs = [kw.arg for kw in node.keywords if kw.arg]
            if not kwargs:
                continue
            try:
                sig = inspect.signature(func_obj)
            except (TypeError, ValueError):
                continue
            if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                continue
            unknown = [k for k in kwargs if k not in sig.parameters]
            if unknown:
                out.append(
                    (
                        node.lineno - 1,
                        ast.unparse(node.func),
                        f"unexpected kwarg(s): {', '.join(unknown)} (signature {sig})",
                    )
                )
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            cls = instances.get(node.value.id)
            if cls is None or not dataclasses.is_dataclass(cls):
                continue
            attr = node.attr
            field_names = {f.name for f in dataclasses.fields(cls)}
            if attr not in field_names and not hasattr(cls, attr):
                out.append(
                    (
                        node.lineno - 1,
                        f"{node.value.id}.{attr}",
                        f"{cls.__module__}.{cls.__qualname__} has no field/attr {attr!r}",
                    )
                )
    return out


def _check_json_fence(
    body: str, repo: Path, compare_real: bool = False
) -> list[tuple[int, str, str]]:
    """G4(b): MCP module paths + ``.claude/mcp.json`` drift for one fence.

    Module importability applies to every json fence. The
    ``mcpServers`` diff against the real ``.claude/mcp.json`` runs
    only with ``compare_real=True`` — i.e. when the surrounding doc
    is documenting THAT file; a Claude Desktop config example
    legitimately differs and must not be flagged.
    """
    out: list[tuple[int, str, str]] = []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return out

    modules: list[str] = []

    def walk(obj: object) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "args" and isinstance(value, list):
                    strs = [s for s in value if isinstance(s, str)]
                    for i, tok in enumerate(strs[:-1]):
                        if tok == "-m":
                            modules.append(strs[i + 1])
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    for mod in modules:
        try:
            found = importlib.util.find_spec(mod)
        except (ImportError, ModuleNotFoundError, ValueError):
            found = None
        if found is None:
            out.append((0, f"-m {mod}", f"module {mod!r} is not importable"))

    servers = data.get("mcpServers") if isinstance(data, dict) else None
    real_path = repo / ".claude" / "mcp.json"
    if compare_real and isinstance(servers, dict) and real_path.exists():
        try:
            real = json.loads(real_path.read_text(encoding="utf-8")).get("mcpServers", {})
        except (OSError, json.JSONDecodeError):
            return out
        for name, cfg in servers.items():
            if name not in real:
                out.append(
                    (0, f"mcpServers.{name}", "server not present in the real .claude/mcp.json")
                )
                continue
            if not isinstance(cfg, dict):
                continue
            for key in ("command", "args"):
                if key in cfg and cfg.get(key) != real[name].get(key):
                    out.append(
                        (
                            0,
                            f"mcpServers.{name}.{key}",
                            f"drifts from .claude/mcp.json: doc {cfg.get(key)!r} "
                            f"vs real {real[name].get(key)!r}",
                        )
                    )
    return out


# --- driver ---------------------------------------------------------------


def _section_block(text: str, key: str) -> str:
    """Return the indented block under a top-level ``key:`` in YAML text.

    Reads every line after ``key:`` (or ``key: |``) until the next
    non-indented line. Used to lift ``nav:`` and ``exclude_docs:`` out of
    ``mkdocs.yml`` without a full YAML parse (which mkdocs custom tags can
    break).
    """
    out: list[str] = []
    in_block = False
    for ln in text.splitlines():
        if not in_block:
            if re.match(rf"^{re.escape(key)}\s*(\|.*)?$", ln):
                in_block = True
            continue
        if ln and not ln[0].isspace():  # next top-level key/comment
            break
        out.append(ln)
    return "\n".join(out)


def _mkdocs_doc_scope(repo: Path):
    """Predicate over docs-relative paths: is this page PUBLISHED?

    Scopes the gate to served surfaces. A ``docs/`` page is published if
    it is referenced in mkdocs ``nav`` OR not matched by ``exclude_docs``
    (nav wins the occasional nav-vs-exclude conflict). Returns ``None``
    when ``mkdocs.yml`` is unavailable, so the caller falls back to the
    coarse ``EXCLUDE_SUBSTRINGS`` only. ``content/**`` is always in scope
    (it's the website source, not governed by mkdocs).
    """
    mk = repo / "mkdocs.yml"
    if not mk.exists():
        return None
    text = mk.read_text(encoding="utf-8")
    nav_paths = set(re.findall(r"([A-Za-z0-9_][\w./-]*\.md)", _section_block(text, "nav:")))
    exc_lines = [
        s
        for s in (ln.strip() for ln in _section_block(text, "exclude_docs:").splitlines())
        if s and not s.startswith("#")
    ]
    try:
        import pathspec  # mkdocs's own exclude_docs matcher

        spec = pathspec.PathSpec.from_lines("gitwildmatch", exc_lines)
        excluded = spec.match_file
    except Exception:  # noqa: BLE001
        # INTENTIONAL: pathspec is optional. If absent, don't exclude
        # anything (over-check rather than silently skip a real fence).
        def excluded(_rel: str) -> bool:
            return False

    def is_published(rel: str) -> bool:
        return rel in nav_paths or not excluded(rel)

    return is_published


def _in_scope(path: Path, repo: Path, published) -> bool:
    rel = str(path.relative_to(repo)).replace("\\", "/")
    if any(sub in "/" + rel for sub in EXCLUDE_SUBSTRINGS):
        return False
    # docs/ pages are scoped to served surfaces; content/** is always in.
    if published is not None and rel.startswith("docs/"):
        return published(rel[len("docs/") :])
    return True


def audit(repo: Path, paths: list[str] | None) -> tuple[list[Finding], Stats]:
    findings: list[Finding] = []
    stats = Stats()
    published = _mkdocs_doc_scope(repo)
    deep_allow, allow_findings = _load_deep_allowlist(repo)
    findings.extend(allow_findings)
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
        if not f.is_file() or f.suffix != ".md" or not _in_scope(f, repo, published):
            continue
        text = f.read_text(encoding="utf-8")
        rel = str(f.relative_to(repo)).replace("\\", "/")
        deep = rel in deep_allow
        if deep:
            stats.deep_files += 1
        had_fence = False
        for body_line, body, skipped, reason in _iter_python_fences(text):
            stmts = _import_statements(body)
            if not stmts and not deep:
                continue
            if skipped:
                if stmts:
                    had_fence = True
                    stats.fences += 1
                    stats.skipped_fences += 1
                    stats.skips.append(f"{rel}:{body_line} ({reason})")
                continue
            if stmts:
                had_fence = True
                stats.fences += 1
            for off, stmt in stmts:
                stats.imports_checked += 1
                err = _resolve(stmt)
                if err:
                    findings.append(Finding(rel, body_line + off, stmt, err))
            if deep:
                for off, expr, msg in _deep_check_python(body):
                    findings.append(Finding(rel, body_line + off, expr, msg))
        if deep:
            text_lines = text.splitlines()
            for body_line, body, skipped, reason in _iter_python_fences(
                text, fence_re=_JSON_FENCE_RE
            ):
                if skipped:
                    stats.skips.append(f"{rel}:{body_line} ({reason})")
                    continue
                # The real-file diff applies only when the fence is
                # documenting .claude/mcp.json itself (named within
                # the 10 lines above the fence opener).
                context = "\n".join(text_lines[max(0, body_line - 11) : body_line - 1])
                compare_real = ".claude/mcp.json" in context
                for off, expr, msg in _check_json_fence(body, repo, compare_real=compare_real):
                    findings.append(Finding(rel, body_line + off, expr, msg))
        if had_fence:
            stats.files += 1
    return findings, stats


def _format_markdown(findings: list[Finding], stats: Stats) -> str:
    lines = [
        "# Doc import audit",
        "",
        f"Checked {stats.imports_checked} attune import(s) across "
        f"{stats.fences} fence(s) in {stats.files} file(s); "
        f"{stats.skipped_fences} fence(s) skipped; "
        f"{stats.deep_files} file(s) deep-checked (G4).",
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
