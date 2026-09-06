"""Surface-producer inventory (host-surface-parity Task 1B, R2).

Mechanically discovers every in-tree producer of a host-presented
surface so the parity gate can require exactly one subject record per
producer. Nothing here executes a manifest command or imports a hook;
manifests are parsed as data and Python is read as AST.

Three sources, per design R2:

1. **Shipped Python roots** derived from ``pyproject.toml`` packaging
   metadata (``[tool.setuptools.packages.find]`` plus entry points),
   scanned for calls to a projection target from the attune-forms
   renderer registry and for the closed package host-envelope
   signatures.
2. **Manifest registrations** from ``plugin/hooks/hooks.json`` and
   ``.claude/settings.json``, resolved through the closed shell resolver
   (exact shipped launcher prefix, one ``.py`` token, the two known
   variables, no operators, no escapes). Each resolved script is
   scanned once for renderer calls and the closed event-qualified
   host-envelope signatures.
3. **Host artifacts**: every Markdown command under ``plugin/commands/``
   is an informational subject by construction (``artifact:<path>``);
   its one fenced ``python3 "<path>"`` command resolves to an
   implementation that is scanned like a hook.

Anchors: a Python producer is ``file:qualname``; module-body output is
``repo/path.py:<module>``. A helper reached from a host-exposed root
keeps its own anchor and every root that reached it as a
``root -> helper`` edge; it is provenance, not a subject.

Every "cannot resolve" is a recorded problem, never silence: an unknown
variable, an extra token, a path escape, a missing file, a mapping that
carries a recognized envelope key but cannot be normalized, or a
dynamic sink all fail closed with the registration identity or anchor.

The reviewed ``producer_baseline.json`` fixture is this scan's output on
the execution base; the gate compares a fresh scan to it.
"""

from __future__ import annotations

import ast
import fnmatch
import json
import re
import shlex
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

BASELINE_SCHEMA_VERSION = "attune.surface-inventory.producer-baseline/1"

#: The exact shipped hook launcher. Anything before the tail must equal it.
HOOK_LAUNCHER_PREFIX = 'PY=$(command -v python3 || command -v python) && "$PY"'
#: The one direct command form a Markdown command may carry.
COMMAND_LAUNCHER_PREFIX = "python3"

MANIFESTS: tuple[str, ...] = ("plugin/hooks/hooks.json", ".claude/settings.json")
COMMANDS_DIR = "plugin/commands"

#: Variables the resolver knows; everything else is an unknown variable.
_VARIABLES = {
    "${CLAUDE_PLUGIN_ROOT}": "plugin",
    "$CLAUDE_PLUGIN_ROOT": "plugin",
    "${CLAUDE_PROJECT_DIR}": "",
    "$CLAUDE_PROJECT_DIR": "",
}
_SHELL_OPERATORS = re.compile(r"[|;&<>`]|\$\(")

#: Events whose host contract injects plain stdout into model context.
CONTEXT_STDOUT_EVENTS = frozenset({"SessionStart", "UserPromptSubmit"})
#: Events whose host contract feeds blocking exit-2 stderr back to the model.
EXIT2_STDERR_EVENTS = frozenset({"PreToolUse", "PostToolUse", "Stop", "SubagentStop"})

#: Closed host-envelope signature vocabulary for hook (informational) producers:
#: name -> (subject_kind, destination, qualifying events or None for any).
ENVELOPE_SIGNATURES: dict[str, tuple[str, str, frozenset[str] | None]] = {
    "additional_context": ("informational_delivery", "model_context", None),
    "system_message": ("informational_delivery", "user_notice", None),
    "pretooluse_deny": ("informational_delivery", "model_context", frozenset({"PreToolUse"})),
    "stop_block": ("informational_delivery", "model_context", frozenset({"Stop", "SubagentStop"})),
    "exit2_stderr": ("informational_delivery", "model_context", EXIT2_STDERR_EVENTS),
    "context_stdout": ("informational_delivery", "model_context", CONTEXT_STDOUT_EVENTS),
}
#: Closed package (non-hook) envelope signatures: name -> (subject_kind, marker).
PACKAGE_SIGNATURES: dict[str, tuple[str, str]] = {
    "native_elicit_form": ("interactive_form", "session.elicit_form"),
    "html_response": ("interactive_form", "html|panel_html"),
    "askuserquestion_batches": ("interactive_form", "batches"),
    "workspace_render": ("interactive_workspace", "CommandWorkspaceRender(html, markdown)"),
    "mcp_app_resource": ("interactive_workspace", "ui://"),
}
#: Keys that are control-plane output unless a positive signature also matches.
CONTROL_PLANE_KEYS = frozenset(
    {
        "continue",
        "stopReason",
        "suppressOutput",
        "decision",
        "reason",
        "permissionDecision",
        "permissionDecisionReason",
        "updatedInput",
        "hookEventName",
    }
)
_RECOGNIZED_KEYS = frozenset(
    {"hookSpecificOutput", "additionalContext", "systemMessage", "permissionDecision", "decision"}
)

_MCP_APP_CALLS = frozenset({"mcp_app_result", "mcp_app_resource", "mcp_app_tool_meta"})
_PROJECTION_ROOT_PACKAGE = "attune_forms"
_REEXPORT_MODULE = "attune.elicitation"


# --- records ----------------------------------------------------------------


@dataclass(frozen=True)
class Registration:
    """One manifest hook registration and its resolution."""

    manifest_path: str
    event: str
    matcher: str
    ordinal: int
    raw_command: str
    json_pointer: str
    resolved_repo_path: str | None = None
    error: str | None = None

    @property
    def identity(self) -> str:
        return f"manifest:{self.manifest_path}#{self.json_pointer}"


@dataclass(frozen=True)
class Artifact:
    """A Markdown command or template: an informational subject by construction."""

    anchor: str
    implementation: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class RendererCallAnchor:
    """A resolved call to a registry projection target."""

    anchor: str
    target: str
    syntax: str  # direct | reexport | qualified


@dataclass(frozen=True)
class EnvelopeAnchor:
    """A closed host-envelope signature detected at a producer anchor."""

    anchor: str
    signature: str
    subject_kind: str
    destination: str
    event: str  # "" for package (non-hook) signatures
    sink: str


@dataclass(frozen=True)
class HelperEdge:
    """A host-exposed root reaching a helper that holds an anchor."""

    root_anchor: str
    helper_anchor: str


@dataclass(frozen=True)
class ProducerBaseline:
    """The reviewed execution-base evidence the parity gate compares against."""

    shipped_roots: tuple[str, ...]
    registrations: tuple[Registration, ...]
    artifacts: tuple[Artifact, ...]
    renderer_call_anchors: tuple[RendererCallAnchor, ...]
    package_host_envelope_anchors: tuple[EnvelopeAnchor, ...]
    hook_envelope_anchors: tuple[EnvelopeAnchor, ...]
    helper_edges: tuple[HelperEdge, ...]
    problems: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = BASELINE_SCHEMA_VERSION

    @property
    def unique_resolved_paths(self) -> tuple[str, ...]:
        paths = {r.resolved_repo_path for r in self.registrations if r.resolved_repo_path}
        paths.update(a.implementation for a in self.artifacts if a.implementation)
        return tuple(sorted(paths))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "shipped_roots": list(self.shipped_roots),
            "registrations": [asdict(r) for r in self.registrations],
            "artifacts": [asdict(a) for a in self.artifacts],
            "renderer_call_anchors": [asdict(a) for a in self.renderer_call_anchors],
            "package_host_envelope_anchors": [
                asdict(a) for a in self.package_host_envelope_anchors
            ],
            "hook_envelope_anchors": [asdict(a) for a in self.hook_envelope_anchors],
            "helper_edges": [asdict(e) for e in self.helper_edges],
            "problems": list(self.problems),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProducerBaseline:
        return cls(
            shipped_roots=tuple(data["shipped_roots"]),
            registrations=tuple(Registration(**r) for r in data["registrations"]),
            artifacts=tuple(Artifact(**a) for a in data["artifacts"]),
            renderer_call_anchors=tuple(
                RendererCallAnchor(**a) for a in data["renderer_call_anchors"]
            ),
            package_host_envelope_anchors=tuple(
                EnvelopeAnchor(**a) for a in data["package_host_envelope_anchors"]
            ),
            hook_envelope_anchors=tuple(EnvelopeAnchor(**a) for a in data["hook_envelope_anchors"]),
            helper_edges=tuple(HelperEdge(**e) for e in data["helper_edges"]),
            problems=tuple(data.get("problems", ())),
            schema_version=data.get("schema_version", BASELINE_SCHEMA_VERSION),
        )


# --- shipped roots ----------------------------------------------------------


def shipped_python_roots(repo: Path) -> tuple[str, ...]:
    """Package roots derived from packaging metadata, never from a hand list."""
    meta = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    find = meta.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})
    excludes = tuple(find.get("exclude", ()))
    wheres = find.get("where", ["."])
    roots: set[str] = set()
    for where in wheres:
        base = repo / where
        for pkg in sorted(p for p in base.iterdir() if p.is_dir() and (p / "__init__.py").exists()):
            if any(fnmatch.fnmatch(pkg.name, pat) for pat in excludes):
                continue
            roots.add(pkg.relative_to(repo).as_posix())
    project = meta.get("project", {})
    entry_values = list(project.get("scripts", {}).values())
    for group in project.get("entry-points", {}).values():
        entry_values.extend(group.values())
    for value in entry_values:
        top = value.split(":", 1)[0].split(".", 1)[0]
        for where in wheres:
            candidate = repo / where / top
            if (candidate / "__init__.py").exists():
                roots.add(candidate.relative_to(repo).as_posix())
    return tuple(sorted(roots))


def _python_files(repo: Path, roots: Iterable[str]) -> Iterator[Path]:
    for root in roots:
        yield from sorted(p for p in (repo / root).rglob("*.py") if "__pycache__" not in p.parts)


# --- manifests and the closed shell resolver ---------------------------------


def resolve_launcher(raw: str, repo: Path, prefix: str) -> tuple[str | None, str | None]:
    """Resolve one manifest command to a repo-relative ``.py`` path, or an error.

    Closed on purpose: the exact launcher prefix, one path token, the
    two known variables, no shell operators, no absolute paths, no
    ``..``, an existing ``.py`` file that stays beneath the repository.
    """
    stripped = raw.strip()
    if not stripped.startswith(prefix):
        return None, f"launcher prefix is not the shipped form {prefix!r}"
    tail = stripped[len(prefix) :].strip()
    if _SHELL_OPERATORS.search(tail):
        return None, "shell operator or command substitution in command tail"
    try:
        tokens = shlex.split(tail)
    except ValueError as exc:
        return None, f"unparseable command tail: {exc}"
    if len(tokens) != 1:
        return None, f"expected exactly one path token, got {len(tokens)}"
    token = tokens[0]
    if token.startswith("/"):
        return None, "absolute path is not repo-relative"
    for name, replacement in _VARIABLES.items():
        if token.startswith(name):
            token = (
                replacement + token[len(name) :].lstrip("/")
                if not replacement
                else replacement + token[len(name) :]
            )
            break
    if "$" in token:
        return None, f"unknown variable in {tokens[0]!r}"
    parts = Path(token.lstrip("/")).parts
    if ".." in parts:
        return None, "path escape ('..')"
    if not token.endswith(".py"):
        return None, "not a Python entrypoint (no .py token)"
    rel = Path(*parts)
    full = (repo / rel).resolve()
    try:
        full.relative_to(repo.resolve())
    except ValueError:
        return None, "resolved path escapes the repository"
    if not full.is_file():
        return None, f"missing file {rel.as_posix()}"
    return rel.as_posix(), None


def manifest_registrations(repo: Path) -> tuple[tuple[Registration, ...], list[str]]:
    """Every hook registration in every manifest, resolved; problems listed."""
    rows: list[Registration] = []
    problems: list[str] = []
    for manifest in MANIFESTS:
        path = repo / manifest
        if not path.exists():
            problems.append(f"manifest:{manifest}: missing")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for event, groups in data.get("hooks", {}).items():
            for gi, group in enumerate(groups):
                for hi, hook in enumerate(group.get("hooks", [])):
                    pointer = f"/hooks/{event}/{gi}/hooks/{hi}/command"
                    raw = hook.get("command", "")
                    resolved, error = resolve_launcher(raw, repo, HOOK_LAUNCHER_PREFIX)
                    reg = Registration(
                        manifest, event, group.get("matcher", ""), hi, raw, pointer, resolved, error
                    )
                    rows.append(reg)
                    count += 1
                    if error:
                        problems.append(f"{reg.identity}: {error}")
        if count == 0:
            problems.append(f"manifest:{manifest}: yields no registration")
    return tuple(rows), problems


_FENCE = re.compile(r"```(?:bash|sh|shell)?\n(.*?)```", re.S)


def command_artifacts(repo: Path) -> tuple[tuple[Artifact, ...], list[str]]:
    """Markdown commands as artifact subjects, each with its resolved implementation."""
    out: list[Artifact] = []
    problems: list[str] = []
    for md in sorted((repo / COMMANDS_DIR).glob("*.md")):
        anchor = f"artifact:{md.relative_to(repo).as_posix()}"
        commands = [
            line.strip()
            for block in _FENCE.findall(md.read_text(encoding="utf-8"))
            for line in block.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not commands:
            out.append(Artifact(anchor))
            continue
        if len(commands) != 1:
            error = f"{len(commands)} fenced commands; expected one"
            out.append(Artifact(anchor, error=error))
            problems.append(f"{anchor}: {error}")
            continue
        resolved, error = resolve_launcher(commands[0], repo, COMMAND_LAUNCHER_PREFIX)
        out.append(Artifact(anchor, resolved, error))
        if error:
            problems.append(f"{anchor}: {error}")
    return tuple(out), problems


# --- projection-target vocabulary -------------------------------------------


def projection_targets() -> dict[str, str]:
    """``name -> qualname`` for every attune-forms registry target."""
    from attune_forms.renderer_registry import iter_targets

    return {t.name: t.qualname for t in iter_targets()}


def _reexported_targets(repo: Path, targets: dict[str, str]) -> set[str]:
    """Registry target names that ``attune.elicitation`` re-exports from attune_forms."""
    init = repo / "src" / "attune" / "elicitation" / "__init__.py"
    if not init.exists():
        return set()
    names: set[str] = set()
    for node in ast.parse(init.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] == _PROJECTION_ROOT_PACKAGE:
                names.update(a.name for a in node.names if a.name in targets)
    return names


# --- per-module AST index ---------------------------------------------------


@dataclass
class _ModuleScan:
    rel: str
    tree: ast.Module
    functions: dict[str, ast.AST]  # qualname -> def node (methods as Class.method)
    target_aliases: dict[str, tuple[str, str]]  # bare name -> (target qualname, syntax)
    module_aliases: dict[str, str]  # bare name -> dotted module
    helper_imports: dict[str, tuple[str, str]]  # bare name -> (repo file, qualname)

    def node(self, qual: str) -> ast.AST:
        if qual == "<module>":
            body = [
                s
                for s in self.tree.body
                if not isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            ]
            return ast.Module(body=body, type_ignores=[])
        return self.functions[qual]


def _index_functions(tree: ast.Module) -> dict[str, ast.AST]:
    """``qualname -> def`` for module-level functions and class methods."""
    functions: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    functions[f"{node.name}.{item.name}"] = item
    return functions


@dataclass
class _Bindings:
    target_aliases: dict[str, tuple[str, str]] = field(default_factory=dict)
    module_aliases: dict[str, str] = field(default_factory=dict)
    helper_imports: dict[str, tuple[str, str]] = field(default_factory=dict)


def _bind_import(node: ast.Import, b: _Bindings) -> None:
    for a in node.names:
        if a.asname:
            b.module_aliases[a.asname] = a.name
        else:
            b.module_aliases[a.name] = a.name
            b.module_aliases.setdefault(a.name.split(".")[0], a.name.split(".")[0])


def _bind_import_from(
    node: ast.ImportFrom,
    rel: str,
    path: Path,
    repo: Path,
    targets: dict[str, str],
    reexports: set[str],
    roots: tuple[str, ...],
    b: _Bindings,
) -> None:
    module = _absolute_module(node, rel)
    top = module.split(".")[0]
    for a in node.names:
        bound = a.asname or a.name
        if top == _PROJECTION_ROOT_PACKAGE and a.name in targets:
            owner = targets[a.name].rsplit(".", 1)[0]
            if module in (_PROJECTION_ROOT_PACKAGE, owner):
                b.target_aliases[bound] = (targets[a.name], "direct")
                continue
        if module == _REEXPORT_MODULE and a.name in reexports:
            b.target_aliases[bound] = (targets[a.name], "reexport")
            continue
        sub = f"{module}.{a.name}"
        if _module_file(sub, repo, roots) is not None:
            b.module_aliases[bound] = sub
        elif (helper := _helper_file(module, a.name, repo, roots, path)) is not None:
            b.helper_imports[bound] = helper
        elif top in (_PROJECTION_ROOT_PACKAGE, "attune"):
            b.module_aliases[bound] = sub


def _index_module(
    path: Path, repo: Path, targets: dict[str, str], reexports: set[str], roots: tuple[str, ...]
) -> _ModuleScan:
    rel = path.relative_to(repo).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    b = _Bindings()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            _bind_import(node, b)
        elif isinstance(node, ast.ImportFrom) and node.module:
            _bind_import_from(node, rel, path, repo, targets, reexports, roots, b)
    return _ModuleScan(
        rel, tree, _index_functions(tree), b.target_aliases, b.module_aliases, b.helper_imports
    )


def _absolute_module(node: ast.ImportFrom, rel: str) -> str:
    if not node.level:
        return node.module or ""
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    package = parts[:-1]  # the module's own package
    if node.level > 1:
        package = package[: len(package) - (node.level - 1)]
    return ".".join(package + ([node.module] if node.module else []))


def _module_file(module: str, repo: Path, roots: tuple[str, ...]) -> Path | None:
    parts = module.split(".")
    for root in roots:
        base = repo / root
        if base.name != parts[0]:
            continue
        candidate = base.parent.joinpath(*parts)
        if candidate.with_suffix(".py").is_file():
            return candidate.with_suffix(".py")
        if (candidate / "__init__.py").is_file():
            return candidate / "__init__.py"
    return None


def _helper_file(
    module: str, name: str, repo: Path, roots: tuple[str, ...], importer: Path | None = None
) -> tuple[str, str] | None:
    """(repo file, qualname) for a function imported from a repo-local module.

    Resolves inside shipped roots first, then — the way a script's own
    directory sits first on ``sys.path`` — as a sibling of the importer.
    """
    file = _module_file(module, repo, roots)
    if file is None and importer is not None:
        sibling = importer.parent.joinpath(*module.split(".")).with_suffix(".py")
        if sibling.is_file() and sibling.resolve().is_relative_to(repo.resolve()):
            file = sibling
    if file is None:
        return None
    rel = file.relative_to(repo).as_posix()
    for node in ast.parse(file.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return rel, name
    return None


def _dotted(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _resolve_call_target(
    func: ast.expr, scan: _ModuleScan, targets: dict[str, str]
) -> tuple[str, str] | None:
    """(target qualname, syntax) when a call resolves to a registry target."""
    dotted = _dotted(func)
    if dotted is None:
        return None
    if dotted in scan.target_aliases:
        return scan.target_aliases[dotted]
    if "." in dotted:
        head, name = dotted.rsplit(".", 1)
        if name in targets:
            module = scan.module_aliases.get(head, head)
            if module == _REEXPORT_MODULE or module.split(".")[0] == _PROJECTION_ROOT_PACKAGE:
                return targets[name], "qualified"
    return None


# --- envelope normalization -------------------------------------------------


@dataclass
class _Facts:
    """What one function's body does, as far as bounded static analysis sees."""

    stdout_sink: str | None = None
    stderr_sink: str | None = None
    exit2: bool = False
    mappings: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    returns_mapping: bool = False


_UNRESOLVED = object()


def _normalize_mapping(node: ast.expr, depth: int = 0) -> dict[str, Any] | None | object:
    """A dict literal / ``dict(...)`` with constant keys -> {key: normalized value}.

    ``None`` when the node is not a mapping; ``_UNRESOLVED`` when it is a
    mapping whose shape cannot be established statically.
    """
    if depth > 4:
        return _UNRESOLVED
    items: list[tuple[str, ast.expr]] = []
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            if key is None or not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                return _UNRESOLVED
            items.append((key.value, value))
    elif isinstance(node, ast.Call) and _dotted(node.func) == "dict" and not node.args:
        for kw in node.keywords:
            if kw.arg is None:
                return _UNRESOLVED
            items.append((kw.arg, kw.value))
    else:
        return None
    out: dict[str, Any] = {}
    for key, value in items:
        inner = _normalize_mapping(value, depth + 1)
        if inner is _UNRESOLVED:
            return _UNRESOLVED
        if inner is not None:
            out[key] = inner
        elif isinstance(value, ast.Constant):
            out[key] = value.value
        else:
            out[key] = "<expr>"
    return out


def _function_facts(node: ast.AST) -> _Facts:
    facts = _Facts()
    assigned: dict[str, dict[str, Any]] = {}
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            _record_call(sub, facts, assigned)
        elif isinstance(sub, ast.Raise) and isinstance(sub.exc, ast.Call):
            if _dotted(sub.exc.func) == "SystemExit" and _const_is(sub.exc.args, 2):
                facts.exit2 = True
        elif isinstance(sub, ast.Return) and sub.value is not None:
            _record_return(sub.value, facts, assigned)
        elif isinstance(sub, ast.Assign) and len(sub.targets) == 1:
            _record_assign(sub, facts, assigned)
    for sub in ast.walk(node):
        if isinstance(sub, ast.Dict | ast.Call):
            norm = _normalize_mapping(sub)
            if isinstance(norm, dict) and norm and norm not in facts.mappings:
                facts.mappings.append(norm)
    facts.mappings.extend(m for m in assigned.values() if m not in facts.mappings)
    return facts


def _const_is(args: list[ast.expr], value: Any) -> bool:
    return bool(args) and isinstance(args[0], ast.Constant) and args[0].value == value


def _record_call(sub: ast.Call, facts: _Facts, assigned: dict[str, dict[str, Any]]) -> None:
    dotted = _dotted(sub.func) or ""
    facts.calls.append(dotted)
    if dotted == "print":
        file_kw = [k for k in sub.keywords if k.arg == "file"]
        if not file_kw:
            facts.stdout_sink = "print"
        elif _dotted(file_kw[0].value) == "sys.stderr":
            facts.stderr_sink = "print(file=sys.stderr)"
        elif _dotted(file_kw[0].value) == "sys.stdout":
            facts.stdout_sink = "print(file=sys.stdout)"
        else:
            facts.unresolved.append("print(file=<dynamic>)")
    elif dotted in ("sys.stdout.write", "sys.stdout.buffer.write"):
        facts.stdout_sink = dotted
    elif dotted in ("sys.stderr.write", "sys.stderr.buffer.write"):
        facts.stderr_sink = dotted
    elif dotted == "sys.exit" and _const_is(sub.args, 2):
        facts.exit2 = True
    elif dotted.endswith(".update") and sub.args and isinstance(sub.func, ast.Attribute):
        base = _dotted(sub.func.value)
        norm = _normalize_mapping(sub.args[0])
        if base in assigned and isinstance(norm, dict):
            assigned[base].update(norm)
        elif norm is _UNRESOLVED and _mentions_recognized_key(sub.args[0]):
            facts.unresolved.append("mapping.update(<unresolved mapping with a recognized key>)")


def _record_return(value: ast.expr, facts: _Facts, assigned: dict[str, dict[str, Any]]) -> None:
    if isinstance(value, ast.Constant) and value.value == 2:
        facts.exit2 = True
        return
    norm = _normalize_mapping(value)
    if isinstance(norm, dict):
        facts.mappings.append(norm)
        facts.returns_mapping = True
    elif norm is _UNRESOLVED and _mentions_recognized_key(value):
        facts.unresolved.append("returned mapping with a recognized key cannot be normalized")
    elif isinstance(value, ast.Name) and value.id in assigned:
        facts.mappings.append(assigned[value.id])
        facts.returns_mapping = True


def _record_assign(sub: ast.Assign, facts: _Facts, assigned: dict[str, dict[str, Any]]) -> None:
    target = sub.targets[0]
    norm = _normalize_mapping(sub.value)
    if isinstance(target, ast.Name):
        if isinstance(norm, dict):
            assigned[target.id] = dict(norm)
        elif norm is _UNRESOLVED and _mentions_recognized_key(sub.value):
            facts.unresolved.append(f"{target.id} = <mapping with a recognized key, unresolvable>")
        return
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
        key = target.slice
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            holds = assigned.get(target.value.id, {})
            if _RECOGNIZED_KEYS & set(holds) or _mentions_recognized_key(sub.value):
                facts.unresolved.append(f"{target.value.id}[<dynamic key>] on an envelope mapping")
            return
        if norm is _UNRESOLVED:
            facts.unresolved.append(f"{target.value.id}[{key.value!r}] = <unresolved mapping>")
            return
        value = (
            norm
            if norm is not None
            else (sub.value.value if isinstance(sub.value, ast.Constant) else "<expr>")
        )
        assigned.setdefault(target.value.id, {})[key.value] = value


def _mentions_recognized_key(node: ast.AST) -> bool:
    """True when a mapping KEY (never a bare string value) is a recognized envelope key."""
    for n in ast.walk(node):
        keys: list[ast.expr | None] = []
        if isinstance(n, ast.Dict):
            keys = list(n.keys)
        elif isinstance(n, ast.Call) and _dotted(n.func) == "dict":
            if any(kw.arg in _RECOGNIZED_KEYS for kw in n.keywords):
                return True
        elif isinstance(n, ast.Subscript):
            keys = [n.slice]
        if any(isinstance(k, ast.Constant) and k.value in _RECOGNIZED_KEYS for k in keys):
            return True
    return False


def _mapping_signatures(mapping: dict[str, Any], event: str) -> set[str]:
    """Structured (mapping-based) signatures one normalized mapping satisfies for ``event``."""
    found: set[str] = set()
    hso = mapping.get("hookSpecificOutput")
    hso = hso if isinstance(hso, dict) else {}
    if "additionalContext" in hso and hso.get("hookEventName") == event:
        found.add("additional_context")
    if "systemMessage" in mapping:
        found.add("system_message")
    deny = hso.get("permissionDecision") == "deny" and "permissionDecisionReason" in hso
    if deny and event == "PreToolUse":
        found.add("pretooluse_deny")
    block = mapping.get("decision") == "block" and "reason" in mapping
    if block and event in ("Stop", "SubagentStop"):
        found.add("stop_block")
    return found


def _envelope_signatures(facts: _Facts, event: str) -> list[tuple[str, str]]:
    """(signature, sink) pairs a function's facts satisfy for one hook event."""
    found: set[tuple[str, str]] = set()
    emits = facts.stdout_sink or ("return" if facts.returns_mapping else None)
    if emits:
        for mapping in facts.mappings:
            found.update((sig, emits) for sig in _mapping_signatures(mapping, event))
    if facts.stderr_sink and facts.exit2 and event in EXIT2_STDERR_EVENTS:
        found.add(("exit2_stderr", facts.stderr_sink))
    structured = {s for s, _ in found if s != "exit2_stderr"}
    if facts.stdout_sink and event in CONTEXT_STDOUT_EVENTS and not structured:
        found.add(("context_stdout", facts.stdout_sink))
    return sorted(found)


# --- reachability -----------------------------------------------------------


def _reachable(
    scan: _ModuleScan, start: str, lookup: Callable[[str], _ModuleScan | None]
) -> list[tuple[_ModuleScan, str]]:
    """Cycle-safe closure of repo-local callables reachable from ``start`` in ``scan``."""
    seen: set[tuple[str, str]] = set()
    order: list[tuple[_ModuleScan, str]] = []
    stack: list[tuple[_ModuleScan, str]] = [(scan, start)]
    while stack:
        current, qual = stack.pop()
        if (current.rel, qual) in seen:
            continue
        seen.add((current.rel, qual))
        order.append((current, qual))
        for sub in ast.walk(current.node(qual)):
            if not isinstance(sub, ast.Call):
                continue
            dotted = _dotted(sub.func)
            if dotted is None:
                continue
            if dotted in current.functions:
                stack.append((current, dotted))
            elif dotted.startswith("self.") and "." in qual:
                method = f"{qual.split('.')[0]}.{dotted[5:]}"
                if method in current.functions:
                    stack.append((current, method))
            elif dotted in current.helper_imports:
                file, name = current.helper_imports[dotted]
                other = lookup(file)
                if other is not None:
                    stack.append((other, name))
    return order


def _anchor(scan: _ModuleScan, qual: str) -> str:
    return f"{scan.rel}:{qual}"


# --- the scan ---------------------------------------------------------------


def _renderer_calls(
    scan: _ModuleScan, qual: str, targets: dict[str, str]
) -> list[RendererCallAnchor]:
    found = []
    for sub in ast.walk(scan.node(qual)):
        if isinstance(sub, ast.Call):
            resolved = _resolve_call_target(sub.func, scan, targets)
            if resolved:
                found.append(RendererCallAnchor(_anchor(scan, qual), resolved[0], resolved[1]))
    return found


def _package_envelopes(anchor: str, facts: _Facts) -> set[EnvelopeAnchor]:
    """Closed package host-envelope signatures one callable's facts satisfy."""
    found: set[EnvelopeAnchor] = set()
    for call in facts.calls:
        if call.endswith(".elicit_form"):
            found.add(
                EnvelopeAnchor(
                    anchor, "native_elicit_form", "interactive_form", "session", "", call
                )
            )
        if call.endswith("CommandWorkspaceRender"):
            found.add(
                EnvelopeAnchor(
                    anchor, "workspace_render", "interactive_workspace", "host", "", call
                )
            )
        if call.rsplit(".", 1)[-1] in _MCP_APP_CALLS:
            found.add(
                EnvelopeAnchor(
                    anchor, "mcp_app_resource", "interactive_workspace", "host", "", "mcp_app"
                )
            )
    if not facts.returns_mapping:
        return found
    for mapping in facts.mappings:
        if "html" in mapping or "panel_html" in mapping:
            found.add(
                EnvelopeAnchor(anchor, "html_response", "interactive_form", "host", "", "return")
            )
        if "batches" in mapping:
            found.add(
                EnvelopeAnchor(
                    anchor, "askuserquestion_batches", "interactive_form", "host", "", "return"
                )
            )
    return found


@dataclass
class _Findings:
    renderer_calls: set[RendererCallAnchor] = field(default_factory=set)
    package_envelopes: set[EnvelopeAnchor] = field(default_factory=set)
    hook_envelopes: set[EnvelopeAnchor] = field(default_factory=set)
    helper_edges: set[HelperEdge] = field(default_factory=set)
    problems: list[str] = field(default_factory=list)


def _scan_package_roots(
    indexes: dict[str, _ModuleScan], roots: tuple[str, ...], targets: dict[str, str], out: _Findings
) -> None:
    """Shipped roots: renderer calls + package envelopes at every callable."""
    for rel, scan in list(indexes.items()):
        if not any(rel.startswith(root + "/") for root in roots):
            continue
        for qual in [*scan.functions, "<module>"]:
            out.renderer_calls.update(_renderer_calls(scan, qual, targets))
            facts = _function_facts(scan.node(qual))
            out.package_envelopes.update(_package_envelopes(_anchor(scan, qual), facts))


def _scan_hook_script(
    scan: _ModuleScan,
    events: list[str],
    lookup: Callable[[str], _ModuleScan | None],
    targets: dict[str, str],
    out: _Findings,
) -> None:
    """A manifest-resolved script: event-qualified envelopes over its reachable graph."""
    root_anchor = _anchor(scan, "<module>")
    for other, qual in _reachable(scan, "<module>", lookup):
        anchor = _anchor(other, qual)
        calls = _renderer_calls(other, qual, targets)
        out.renderer_calls.update(calls)
        facts = _function_facts(other.node(qual))
        out.problems.extend(f"{anchor}: {u} (fails closed)" for u in facts.unresolved)
        envelopes = {
            EnvelopeAnchor(anchor, sig, *ENVELOPE_SIGNATURES[sig][:2], event, sink)
            for event in events
            for sig, sink in _envelope_signatures(facts, event)
        }
        out.hook_envelopes.update(envelopes)
        if anchor != root_anchor and (calls or envelopes):
            out.helper_edges.add(HelperEdge(root_anchor, anchor))


def scan_repository(repo: Path) -> ProducerBaseline:
    """Discover every surface producer in ``repo``. Never executes anything."""
    repo = repo.resolve()
    roots = shipped_python_roots(repo)
    targets = projection_targets()
    reexports = _reexported_targets(repo, targets)
    registrations, reg_problems = manifest_registrations(repo)
    artifacts, art_problems = command_artifacts(repo)
    out = _Findings(problems=[*reg_problems, *art_problems])
    hook_events: dict[str, set[str]] = {}
    for reg in registrations:
        if reg.resolved_repo_path:
            hook_events.setdefault(reg.resolved_repo_path, set()).add(reg.event)
    scripts = sorted(set(hook_events) | {a.implementation for a in artifacts if a.implementation})
    indexes: dict[str, _ModuleScan] = {}

    def lookup(rel: str) -> _ModuleScan | None:
        """Index a repo-local file on demand (hooks import siblings off sys.path)."""
        if rel not in indexes:
            file = repo / rel
            if not file.is_file():
                return None
            indexes[rel] = _index_module(file, repo, targets, reexports, roots)
        return indexes[rel]

    for path in _python_files(repo, roots):
        lookup(path.relative_to(repo).as_posix())
    _scan_package_roots(indexes, roots, targets, out)
    for rel in scripts:
        scan = lookup(rel)
        if scan is not None:
            _scan_hook_script(scan, sorted(hook_events.get(rel, set())), lookup, targets, out)
    return ProducerBaseline(
        shipped_roots=roots,
        registrations=registrations,
        artifacts=artifacts,
        renderer_call_anchors=tuple(sorted(out.renderer_calls, key=lambda a: (a.anchor, a.target))),
        package_host_envelope_anchors=tuple(
            sorted(out.package_envelopes, key=lambda a: (a.anchor, a.signature))
        ),
        hook_envelope_anchors=tuple(
            sorted(out.hook_envelopes, key=lambda a: (a.anchor, a.event, a.signature))
        ),
        helper_edges=tuple(
            sorted(out.helper_edges, key=lambda e: (e.root_anchor, e.helper_anchor))
        ),
        problems=tuple(sorted(set(out.problems))),
    )


def write_baseline(repo: Path, out: Path) -> ProducerBaseline:
    """Scan and write the reviewed fixture (pretty, sorted, trailing newline).

    The output path is validated to stay beneath ``repo`` — the fixture
    is spec evidence and never lands outside the tree that produced it.
    """
    from attune.security.path_validation import _validate_file_path

    baseline = scan_repository(repo)
    out = _validate_file_path(str(out), allowed_dir=str(repo.resolve()))
    out.write_text(
        json.dumps(baseline.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return baseline


def load_baseline(path: Path) -> ProducerBaseline:
    """Read a fixture written by :func:`write_baseline`; a non-object file is rejected."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: producer baseline must be a JSON object")
    return ProducerBaseline.from_dict(data)
