"""The class-register rule pack (release-audit-stage R1, Phase 0).

Promotes the machine-local sweep suites (v1 + v2-R7, library review
2026-08-20) into tracked code. Each rule carries its calibration
receipt VERBATIM from the review record — recall and precision are
recorded honestly, never thresholded (Agy#1 declined, dissent
register): a rule is ``calibrated-here`` only when its receipt's repo
matches the current repo's canonical identity, and an uncalibrated
rule is advisory — it never blocks and never clears a class.

Rule provenance:

- R1–R6 came from the attune-forms review's confirmed defect classes.
  Their only suite-level receipt is ~12% recall on the attune-forms
  ground truth; per-rule figures were never recorded, so they ship
  with the attune-forms suite receipt and are uncalibrated-here for
  every other repo — including this one.
- R7a/R7b mechanize the batch-2 class (register C4a/C3): calibrated
  against the 11 confirmed sites fixed in PR #2121 — 8/11 recall,
  zero false positives (r7-calibration-2026-08-20).
- R8/R9 mechanize C10 (phantom read) as the two narrow rules the
  register entry ruled calibratable — the general cross-function
  dataflow form was declined as uncalibratable. They are REPO-level
  rules (:data:`REPO_RULES`), not per-file AST rules: the invariant
  spans producer and consumer files, so they take a repo root, not a
  tree. Calibrated 2026-08-24 against the registered pre-fix shas
  (R8: 9/9 precision on the current tree, fires on the #2213
  instance at ``ac47cfb21^``; R9: 3/3 precision on ``c7c94f33e^``,
  both facets of the entry-point instance, 0 false positives on the
  fixed tree). Class-level recall is 2/7 registered instances by
  design: the workflow-internal reads (#2222, #2223) and the
  semantic probe misreads (severity-vs-category, count-as-gate,
  success semantics) sit outside both seams and would need the
  declined dataflow rule.
"""

from __future__ import annotations

import ast
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Calibration",
    "Hit",
    "RepoRule",
    "Rule",
    "REPO_RULES",
    "RULES",
    "calibrated_here",
    "canonical_repo_id",
    "scan_entry_point_channels",
    "scan_result_key_contract",
    "scan_source",
]


@dataclass(frozen=True)
class Calibration:
    """One calibration receipt (R1 schema) — recorded, not thresholded."""

    repo: str
    recall: float
    precision: float
    date: str
    ground_truth: str


@dataclass(frozen=True)
class Hit:
    """One rule hit at one site."""

    rule_id: str
    path: str
    line: int
    detail: str


@dataclass(frozen=True)
class Rule:
    """One deterministic AST rule plus its metadata."""

    id: str
    invariant: str
    class_ids: tuple[str, ...]
    check: Callable[[ast.AST, str], list[Hit]]
    calibration: Calibration | None = field(default=None)


_FORMS_SUITE_RECEIPT = Calibration(
    repo="smart-ai-memory/attune-forms",
    recall=0.12,
    precision=0.0,  # never measured per-rule; 0.0 = "no figure", not "all wrong"
    date="2026-08-20",
    ground_truth="attune-forms 23 confirmed defects (suite-level only)",
)
_R7_RECEIPT = Calibration(
    repo="smart-ai-memory/attune-ai",
    recall=8 / 11,
    precision=1.0,
    date="2026-08-20",
    ground_truth="11 confirmed sites fixed in PR #2121 (pre-fix origin/main)",
)


def canonical_repo_id(repo_root: Path | None = None) -> str:
    """Current repo identity: normalized origin slug, else dir name.

    The session-start-integrity D1 convention: ``owner/name`` from the
    origin remote, lowercased; directory-name fallback when no remote.
    """
    root = repo_root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return root.name.lower()
    url = result.stdout.strip()
    if result.returncode != 0 or not url:
        return root.name.lower()
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1).lower() if m else root.name.lower()


def calibrated_here(rule: Rule, repo_id: str) -> bool:
    """R1 eligibility: does this rule's receipt bind to THIS repo?"""
    return rule.calibration is not None and rule.calibration.repo == repo_id


# --------------------------------------------------------------------------
# v1 rules (R1–R6) — ported verbatim in behavior from sweep_suite_v1.py
# --------------------------------------------------------------------------

_OS_ERRORS = {"OSError", "IOError", "FileNotFoundError", "PermissionError"}
_REDIS_METHODS = {"get", "set", "hget", "hset", "delete", "exists", "expire", "sadd", "hgetall"}
_REDIS_RECV = {"r", "redis", "client", "conn", "rc", "backend"}
_SUBPROC_FNS = {"run", "check_output", "check_call", "call"}


class _V1Sweep(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.hits: list[Hit] = []
        self.try_depth = 0
        self.func_stack: list[dict] = []

    def _hit(self, rule_id: str, node: ast.AST, detail: str) -> None:
        self.hits.append(Hit(rule_id, self.path, node.lineno, detail))

    def visit_Try(self, node: ast.Try) -> None:
        dumps = [
            n
            for n in ast.walk(node)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr in ("dump", "dumps")
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "json"
        ]
        if dumps and node.handlers:
            names: set[str] = set()
            for h in node.handlers:
                t = h.type
                for x in ([t] if not isinstance(t, ast.Tuple) else t.elts) if t else [None]:
                    if isinstance(x, ast.Name):
                        names.add(x.id)
                    elif isinstance(x, ast.Attribute):
                        names.add(x.attr)
                    else:
                        names.add("?")
            if names and names <= _OS_ERRORS:
                self._hit("R5-narrow-except-jsondump", node, f"handlers={sorted(names)}")
        self.try_depth += 1
        self.generic_visit(node)
        self.try_depth -= 1

    def _visit_func(self, node) -> None:
        kwarg = node.args.kwarg.arg if node.args.kwarg else None
        self.func_stack.append({"kwarg": kwarg, "coalesced": {}})
        self.generic_visit(node)
        self.func_stack.pop()

    visit_FunctionDef = _visit_func  # type: ignore[assignment]
    visit_AsyncFunctionDef = _visit_func  # type: ignore[assignment]

    def visit_Assign(self, node: ast.Assign) -> None:
        if (
            self.func_stack
            and isinstance(node.value, ast.BoolOp)
            and isinstance(node.value.op, ast.Or)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value.values[0], ast.Name)
            and isinstance(node.value.values[-1], ast.Dict | ast.List | ast.Constant | ast.Tuple)
        ):
            frame = self.func_stack[-1]
            frame["coalesced"][node.targets[0].id] = node.lineno
            frame["coalesced"][node.value.values[0].id] = node.lineno
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_r1(node)
        self._check_r2(node)
        self._check_r3(node)
        self._check_r4(node)
        self._check_r6(node)
        self.generic_visit(node)

    def _check_r1(self, node: ast.Call) -> None:
        f = node.func
        if (
            self.try_depth == 0
            and isinstance(f, ast.Attribute)
            and f.attr in ("loads", "load")
            and isinstance(f.value, ast.Name)
            and f.value.id == "json"
        ):
            self._hit("R1-json-loads-unguarded", node, "json parse outside try")

    def _check_r2(self, node: ast.Call) -> None:
        f = node.func
        if (
            self.func_stack
            and isinstance(f, ast.Attribute)
            and f.attr == "update"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == self.func_stack[-1]["kwarg"]
        ):
            self._hit("R2-update-kwargs", node, f"update({node.args[0].id}) clobber risk")

    def _check_r3(self, node: ast.Call) -> None:
        f = node.func
        if (
            self.func_stack
            and isinstance(f, ast.Name)
            and f.id == "isinstance"
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            line = self.func_stack[-1]["coalesced"].get(node.args[0].id)
            if line is not None and node.lineno > line:
                self._hit(
                    "R3-coalesce-before-check",
                    node,
                    f"'{node.args[0].id}' coalesced at :{line} before isinstance",
                )

    def _check_r4(self, node: ast.Call) -> None:
        f = node.func
        if (
            isinstance(f, ast.Attribute)
            and f.attr in _SUBPROC_FNS
            and isinstance(f.value, ast.Name)
            and f.value.id == "subprocess"
        ):
            if not any(k.arg == "timeout" for k in node.keywords):
                self._hit("R4-subprocess-no-timeout", node, f"subprocess.{f.attr} without timeout")

    def _check_r6(self, node: ast.Call) -> None:
        f = node.func
        if (
            isinstance(f, ast.Attribute)
            and f.attr in _REDIS_METHODS
            and isinstance(f.value, ast.Name)
            and f.value.id.lower() in _REDIS_RECV
            and node.args
            and isinstance(node.args[0], ast.JoinedStr)
        ):
            self._hit("R6-redis-fstring-key", node, f"{f.value.id}.{f.attr}(f'...')")


@dataclass(frozen=True)
class _SweepCheck:
    """One rule's slice of a SHARED sweep.

    Every rule in a sweep family sees the same traversal, so running
    the visitor per rule walked each file once per rule (8 walks for
    the 8-rule pack) to keep one rule's hits and discard the rest.
    Carrying the visitor class here lets :func:`scan_source` run each
    distinct sweep once per file and slice it per rule.

    Calling it directly still walks the tree on its own, so a caller
    holding a single ``Rule`` keeps the old standalone behavior.
    """

    visitor: type[ast.NodeVisitor]
    rule_id: str

    def __call__(self, tree: ast.AST, path: str) -> list[Hit]:
        return self.slice(self.sweep(tree, path))

    def sweep(self, tree: ast.AST, path: str) -> list[Hit]:
        """Run the whole family sweep once and return ALL its hits."""
        visitor = self.visitor(path)
        visitor.visit(tree)
        return list(getattr(visitor, "hits", []))

    def slice(self, swept: list[Hit]) -> list[Hit]:
        """Keep only this rule's hits, in traversal order."""
        return [h for h in swept if h.rule_id == self.rule_id]


def _v1_only(rule_id: str) -> Callable[[ast.AST, str], list[Hit]]:
    return _SweepCheck(_V1Sweep, rule_id)


# --------------------------------------------------------------------------
# v2 rules (R7a/R7b) — ported verbatim in behavior from sweep_suite_v2_r7.py
# --------------------------------------------------------------------------

_PARSER_EXPECTS = {
    "safe_load": "YAMLError",
    "ast.parse": "ValueError",
    "fromisoformat": "ValueError",
}
_CATCH_ALL = {"Exception", "BaseException"}


def _call_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Attribute):
        if isinstance(f.value, ast.Name):
            return f"{f.value.id}.{f.attr}"
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _parser_kind(node: ast.Call) -> str | None:
    name = _call_name(node)
    if name is None:
        return None
    if name == "ast.parse":
        return "ast.parse"
    tail = name.rsplit(".", 1)[-1]
    if tail == "safe_load" or (tail == "load" and name.startswith("yaml.")):
        return "safe_load"
    if tail == "fromisoformat":
        return "fromisoformat"
    if tail in ("loads", "load") and name.startswith("json."):
        return "json"
    return None


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    t = handler.type
    if t is None:
        return {"BaseException"}
    parts = t.elts if isinstance(t, ast.Tuple) else [t]
    out: set[str] = set()
    for p in parts:
        if isinstance(p, ast.Name):
            out.add(p.id)
        elif isinstance(p, ast.Attribute):
            out.add(p.attr)
    return out


class _R7Visitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.hits: list[Hit] = []

    def visit_Try(self, node: ast.Try) -> None:
        caught: set[str] = set()
        for h in node.handlers:
            caught |= _handler_names(h)
        if node.handlers and not (caught & _CATCH_ALL):
            seen: set[str] = set()
            for sub in node.body:
                for n in ast.walk(sub):
                    if not isinstance(n, ast.Call):
                        continue
                    kind = _parser_kind(n)
                    expected = _PARSER_EXPECTS.get(kind or "")
                    if expected and expected not in caught and kind not in seen:
                        seen.add(kind or "")
                        self.hits.append(
                            Hit(
                                "R7a-parse-under-narrow-except",
                                self.path,
                                n.lineno,
                                f"{kind} needs {expected}; handlers={sorted(caught)}",
                            )
                        )
        self.generic_visit(node)

    @staticmethod
    def _collect_bindings(node) -> tuple[dict[str, int], set[str]]:
        """Names bound from parser calls, and names isinstance-guarded."""
        parsed: dict[str, int] = {}
        guarded: set[str] = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                if _parser_kind(n.value) and len(n.targets) == 1:
                    tgt = n.targets[0]
                    if isinstance(tgt, ast.Name):
                        parsed.setdefault(tgt.id, n.lineno)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                if n.func.id == "isinstance" and n.args and isinstance(n.args[0], ast.Name):
                    guarded.add(n.args[0].id)
        return parsed, guarded

    @staticmethod
    def _access_target(n: ast.AST) -> str | None:
        """The Name a ``.get(...)`` or subscript reads from, if any."""
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "get"
            and isinstance(n.func.value, ast.Name)
        ):
            return n.func.value.id
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name):
            return n.value.id
        return None

    def _scan_function(self, node) -> None:
        parsed, guarded = self._collect_bindings(node)
        for n in ast.walk(node):
            target = self._access_target(n)
            if target and target in parsed and target not in guarded:
                self.hits.append(
                    Hit(
                        "R7b-parse-then-unguarded-access",
                        self.path,
                        n.lineno,
                        f"'{target}' parsed at :{parsed[target]}, used without isinstance guard",
                    )
                )
                parsed.pop(target, None)
        self.generic_visit(node)

    visit_FunctionDef = _scan_function  # type: ignore[assignment]
    visit_AsyncFunctionDef = _scan_function  # type: ignore[assignment]


def _r7_only(rule_id: str) -> Callable[[ast.AST, str], list[Hit]]:
    return _SweepCheck(_R7Visitor, rule_id)


#: The pack. Class ids map to the 2026-08-20 register; a rule with no
#: confirmed register class carries an empty tuple (honest, not padded).
RULES: tuple[Rule, ...] = (
    Rule(
        "R1-json-loads-unguarded",
        "json parse outside any try",
        (),
        _v1_only("R1-json-loads-unguarded"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R2-update-kwargs",
        "reserved-key clobber via **kwargs splat",
        ("C1",),
        _v1_only("R2-update-kwargs"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R3-coalesce-before-check",
        "coalesce-to-default before the isinstance seam",
        (),
        _v1_only("R3-coalesce-before-check"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R4-subprocess-no-timeout",
        "un-timeouted subprocess",
        ("C8",),
        _v1_only("R4-subprocess-no-timeout"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R5-narrow-except-jsondump",
        "never-raises contract with a too-narrow except",
        ("C2",),
        _v1_only("R5-narrow-except-jsondump"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R6-redis-fstring-key",
        "unvalidated interpolation into a Redis key",
        (),
        _v1_only("R6-redis-fstring-key"),
        _FORMS_SUITE_RECEIPT,
    ),
    Rule(
        "R7a-parse-under-narrow-except",
        "parser raises outside the caught set",
        ("C4a", "C4b"),
        _r7_only("R7a-parse-under-narrow-except"),
        _R7_RECEIPT,
    ),
    Rule(
        "R7b-parse-then-unguarded-access",
        "parsed non-dict reaching a .get/[] chain",
        ("C3",),
        _r7_only("R7b-parse-then-unguarded-access"),
        _R7_RECEIPT,
    ),
)


def scan_source(source: str, path: str, rules: tuple[Rule, ...] = RULES) -> list[Hit]:
    """Run the pack over one file's source.

    Args:
        source: Python source text.
        path: Path used in hit reports.
        rules: The rules to run; defaults to the full pack.

    Returns:
        All hits, rule order then line order. Unparseable source
        returns a single ``PARSE-ERROR`` hit rather than raising —
        the scan must not die on one bad file (SCAN-ERROR semantics
        live one level up, in the stage).
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        lineno = getattr(exc, "lineno", 0) or 0
        return [Hit("PARSE-ERROR", path, lineno, str(exc))]
    # One traversal per distinct sweep, not one per rule. Rules that
    # share a visitor (all of RULES does) would otherwise walk the
    # file once each -- 8 walks where 2 suffice, on every scanned file
    # in every CI run.
    swept: dict[type[ast.NodeVisitor], list[Hit]] = {}
    hits: list[Hit] = []
    for rule in rules:
        check = rule.check
        if not isinstance(check, _SweepCheck):
            hits.extend(check(tree, path))  # custom rule: unchanged
            continue
        family = swept.get(check.visitor)
        if family is None:
            family = check.sweep(tree, path)
            swept[check.visitor] = family
        hits.extend(check.slice(family))
    return hits


# --------------------------------------------------------------------------
# Repo-level rules (R8/R9) — class C10, phantom read (2026-08-24)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoRule:
    """A rule whose invariant spans files, so it scans a repo root.

    Same metadata shape as :class:`Rule`; the check takes the repo
    root instead of one file's tree. These do NOT join :data:`RULES`
    (the per-file sweep) — their enforcement surface is the C10 gate
    (``tests/unit/gates/test_phantom_read_gate.py``).
    """

    id: str
    invariant: str
    class_ids: tuple[str, ...]
    check: Callable[[Path], list[Hit]]
    calibration: Calibration | None = field(default=None)


_R8_RECEIPT = Calibration(
    repo="smart-ai-memory/attune-ai",
    recall=1 / 1,
    precision=1.0,
    date="2026-08-24",
    ground_truth=(
        "registered #2213 instance at ac47cfb21^ (fires); current tree "
        "9 hits, all hand-triaged real (adapter-built producers whose "
        "picks can only return defaults), 0 false positives; "
        "fixtures pinned in tests/unit/gates/test_phantom_read_gate.py"
    ),
)
_R9_RECEIPT = Calibration(
    repo="smart-ai-memory/attune-ai",
    recall=1 / 1,
    precision=1.0,
    date="2026-08-24",
    ground_truth=(
        "registered entry-point instance at c7c94f33e^ (3/3 facets fire: "
        "the unmarked legacy-group workflow read, plus the unread "
        "attune.workflows and legacy plugin-group registrations); fixed "
        "tree 0 hits across 8 reads + 4 registered groups"
    ),
)

#: Pick names ``_report_fields`` serves from the parsed report — the
#: mirror of ``attune.mcp.workflow_handlers._FINDINGS_KEYS`` and
#: ``_is_score_key``. Everything else on the report path resolves to
#: the pick's static default.
_SERVABLE_FINDINGS_KEYS = frozenset({"findings", "predictions", "checks"})

#: MCP handler files whose ``_workflow_response`` picks R8 audits.
_R8_HANDLER_FILES = (
    Path("src/attune/mcp/workflow_handlers.py"),
    Path("src/attune/mcp/server.py"),
)
_R8_WORKFLOWS_ROOT = Path("src/attune/workflows")


def _is_score_name(name: str) -> bool:
    return name == "score" or name.endswith("_score")


def _dict_literal_keys(node: ast.Dict) -> set[str]:
    return {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}


def _call_tail(node: ast.Call) -> str:
    fn = node.func
    return fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")


def _parse_file(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return None


def _collect_name_keys(tree: ast.AST) -> dict[str, set[str]]:
    """Names assigned dict literals or extended by constant-key subscript."""
    name_keys: dict[str, set[str]] = {}
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1):
            continue
        tgt = n.targets[0]
        if isinstance(tgt, ast.Name) and isinstance(n.value, ast.Dict):
            name_keys.setdefault(tgt.id, set()).update(_dict_literal_keys(n.value))
        if (
            isinstance(tgt, ast.Subscript)
            and isinstance(tgt.value, ast.Name)
            and isinstance(tgt.slice, ast.Constant)
            and isinstance(tgt.slice.value, str)
        ):
            name_keys.setdefault(tgt.value.id, set()).add(tgt.slice.value)
    return name_keys


def _final_output_arg(call: ast.Call) -> ast.expr | None:
    """The ``final_output`` argument of a ``WorkflowResult(...)`` call."""
    for kw in call.keywords:
        if kw.arg == "final_output":
            return kw.value
    return call.args[2] if len(call.args) >= 3 else None


def _producer_contract(files: list[Path]) -> tuple[set[str], bool, bool]:
    """(dict_keys, adapter, resolvable) for one workflow module's files.

    ``dict_keys`` are the string keys of every plain-dict
    ``final_output`` a ``WorkflowResult(...)`` site can carry (dict
    literals, plus names assigned dict literals or extended by
    constant-key subscript assignment anywhere in the module).
    ``adapter`` marks a ``from_agent_output`` producer, whose
    final_output is a serialized report (or raw text) — servable picks
    there are ONLY findings-like and score-like names. A module with
    neither form is unresolvable and must not be judged.
    """
    dict_keys: set[str] = set()
    adapter = False
    resolvable = False
    for f in files:
        tree = _parse_file(f)
        if tree is None:
            continue
        name_keys = _collect_name_keys(tree)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            tail = _call_tail(n)
            if tail == "from_agent_output":
                adapter = True
                resolvable = True
            if tail != "WorkflowResult":
                continue
            fo = _final_output_arg(n)
            if isinstance(fo, ast.Dict):
                dict_keys.update(_dict_literal_keys(fo))
                resolvable = True
            elif isinstance(fo, ast.Name) and fo.id in name_keys:
                dict_keys.update(name_keys[fo.id])
                resolvable = True
    return dict_keys, adapter, resolvable


def _workflow_module_files(workflows_root: Path, module: str) -> list[Path]:
    single = workflows_root / f"{module}.py"
    if single.is_file():
        return [single]
    pkg = workflows_root / module
    if pkg.is_dir():
        return sorted(p for p in pkg.glob("*.py") if "__pycache__" not in p.parts)
    return []


def _pick_source_key(value: ast.expr) -> str | None:
    """The final_output key a ``_workflow_response`` pick reads."""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Tuple) and value.elts:
        first = value.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def scan_result_key_contract(
    repo_root: Path,
    *,
    handler_paths: tuple[Path, ...] = _R8_HANDLER_FILES,
    workflows_root: Path = _R8_WORKFLOWS_ROOT,
) -> list[Hit]:
    """R8: an MCP field pick must read a key its workflow can emit.

    For each handler method that imports a workflow class from
    ``attune.workflows.<mod>`` and calls ``_workflow_response`` with
    field picks, the pick's source key must be servable: present in
    the producer's plain-dict ``final_output`` keys (legacy path), or
    — on an adapter-built producer — a findings-like or score-like
    name, the only picks ``_report_fields`` resolves from the report.
    Any other pick can only ever return its static default: the
    consumer reads what no producer emits, and the response renders
    healthy (class C10, the #2213 shape).

    Hit details are ``<handler>:<response_key><-<source_key>`` so the
    gate's baseline can name known sites stably.
    """
    hits: list[Hit] = []
    for rel in handler_paths:
        tree = _parse_file(repo_root / rel)
        if tree is None:
            continue
        # TOP-LEVEL workflow imports count for EVERY handler in the
        # file — a handler importing its workflow at module scope must
        # not silently evade the seam (codex cross-review, #2271).
        # Direct body statements only: walking the whole tree would
        # union every handler's nested imports into every other's.
        module_imports = [
            stmt.module.removeprefix("attune.workflows.")
            for stmt in tree.body
            if isinstance(stmt, ast.ImportFrom)
            and stmt.module
            and stmt.module.startswith("attune.workflows.")
        ]
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                hits.extend(
                    _judge_handler(node, rel.as_posix(), repo_root / workflows_root, module_imports)
                )
    return hits


def _handler_workflow_modules(node: ast.AST) -> list[str]:
    return [
        imp.module.removeprefix("attune.workflows.")
        for imp in ast.walk(node)
        if isinstance(imp, ast.ImportFrom)
        and imp.module
        and imp.module.startswith("attune.workflows.")
    ]


def _servable(pick: str, src: str, dict_keys: set[str], adapter: bool) -> bool:
    if src in dict_keys:
        return True
    return adapter and (
        pick in _SERVABLE_FINDINGS_KEYS
        or src in _SERVABLE_FINDINGS_KEYS
        or _is_score_name(pick)
        or _is_score_name(src)
    )


def _judge_handler(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    rel: str,
    workflows_root: Path,
    module_imports: list[str] | None = None,
) -> list[Hit]:
    """R8 hits for one handler method's ``_workflow_response`` picks."""
    modules = _handler_workflow_modules(node) + list(module_imports or [])
    calls = [
        c
        for c in ast.walk(node)
        if isinstance(c, ast.Call) and _call_tail(c) == "_workflow_response"
    ]
    if not modules or not calls:
        return []
    dict_keys: set[str] = set()
    adapter = False
    resolvable = False
    for m in modules:
        keys, has_adapter, is_resolvable = _producer_contract(
            _workflow_module_files(workflows_root, m)
        )
        dict_keys |= keys
        adapter = adapter or has_adapter
        resolvable = resolvable or is_resolvable
    if not resolvable:
        return []  # unknown contract — never judged (precision over recall)
    hits: list[Hit] = []
    for call in calls:
        for kw in call.keywords:
            if kw.arg is None or kw.arg in ("raw_output", "include_provider"):
                continue
            src = _pick_source_key(kw.value)
            if src is None or _servable(kw.arg, src, dict_keys, adapter):
                continue
            hits.append(
                Hit(
                    "R8-phantom-result-key",
                    rel,
                    kw.value.lineno,
                    f"{node.name}:{kw.arg}<-{src} "
                    f"(modules={sorted(modules)}, emits={sorted(dict_keys)}, "
                    f"adapter={adapter})",
                )
            )
    return hits


_GROUP_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z0-9_]+)+$")
_EP_SECTION_RE = re.compile(r'^\[project\.entry-points\.(?:"([^"]+)"|([\w.-]+))\]', re.M)

#: Registered groups whose consumer is legitimately outside src/
#: (pytest reads pytest11 itself). Extend only with a recorded reason.
_EXTERNAL_CONSUMER_GROUPS = frozenset({"pytest11"})


def _group_literals(values: list[ast.expr], marked: bool) -> list[tuple[str, int, bool]]:
    """Group-shaped string constants among ``values``."""
    return [
        (v.value, v.lineno, marked)
        for v in values
        if isinstance(v, ast.Constant) and isinstance(v.value, str) and _GROUP_RE.match(v.value)
    ]


def _groups_from_assign(node: ast.Assign) -> list[tuple[str, int, bool]]:
    """Groups bound by a ``*GROUP*`` constant (str or tuple of str)."""
    if len(node.targets) != 1:
        return []
    tgt = node.targets[0]
    if not (isinstance(tgt, ast.Name) and "GROUP" in tgt.id.upper()):
        return []
    values = node.value.elts if isinstance(node.value, ast.Tuple) else [node.value]
    return _group_literals(values, marked="LEGACY" in tgt.id.upper())


def _groups_from_call(node: ast.Call) -> list[tuple[str, int, bool]]:
    """Group literals at an entry-point-ish call site."""
    if "entry_point" not in _call_tail(node).lower():
        return []
    marked = any(
        k.arg == "legacy" and isinstance(k.value, ast.Constant) and bool(k.value.value)
        for k in node.keywords
    )
    return _group_literals([*node.args, *[k.value for k in node.keywords]], marked)


def _entry_point_reads(tree: ast.AST) -> list[tuple[str, int, bool]]:
    """(group, lineno, deliberately_marked) reads in one module.

    A group is collected from (a) module-level ``*GROUP*`` constant
    assignments (str or tuple of str), marked when the binding name
    contains ``LEGACY``, and (b) group-shaped string literals at calls
    whose name contains ``entry_point`` (``entry_points`` itself and
    local helpers like ``_load_entry_point_workflows``), marked when
    the call carries ``legacy=True``.
    """
    out: list[tuple[str, int, bool]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            out.extend(_groups_from_assign(node))
        elif isinstance(node, ast.Call):
            out.extend(_groups_from_call(node))
    return out


def scan_entry_point_channels(
    repo_root: Path,
    *,
    src_root: Path = Path("src"),
    pyproject_name: str = "pyproject.toml",
    external_consumers: frozenset[str] = _EXTERNAL_CONSUMER_GROUPS,
) -> list[Hit]:
    """R9: entry-point channel identity must resolve in both directions.

    Read side: every group a ``src/`` module reads must be named in
    pyproject.toml (a registration section, or the deliberate
    third-party comment) or carry an explicit legacy marker (LEGACY in
    the binding name, or ``legacy=True`` at the call). Write side:
    every group pyproject registers must be read by ``src/`` unless
    its consumer is external (``external_consumers``). An empty read
    is a legal state, so nothing else distinguishes "no producers"
    from "wrong channel" (class C10 instance 7, #2259: both directions
    drifted at once).
    """
    hits: list[Hit] = []
    pyproject = repo_root / pyproject_name
    py_text = pyproject.read_text(encoding="utf-8") if pyproject.is_file() else ""
    read_groups: set[str] = set()
    for path in sorted((repo_root / src_root).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Singular substring: the collector matches helper calls like
        # ``_load_entry_point_workflows`` too, so the prefilter must
        # not demand the plural form (codex cross-review, #2271).
        if "entry_point" not in text:
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        rel = path.relative_to(repo_root)
        for group, lineno, marked in _entry_point_reads(tree):
            read_groups.add(group)
            mentioned = re.search(rf"(?<![\w.]){re.escape(group)}(?![\w.])", py_text)
            if not marked and not mentioned:
                hits.append(
                    Hit(
                        "R9-entry-point-channel",
                        rel.as_posix(),
                        lineno,
                        f"reads group '{group}' that pyproject never names "
                        "and no legacy marker claims",
                    )
                )
    for match in _EP_SECTION_RE.finditer(py_text):
        group = match.group(1) or match.group(2)
        if group in external_consumers or group in read_groups:
            continue
        lineno = py_text.count("\n", 0, match.start()) + 1
        hits.append(
            Hit(
                "R9-entry-point-channel",
                pyproject_name,
                lineno,
                f"registers group '{group}' that nothing in {src_root} reads",
            )
        )
    return hits


#: The C10 pack. Enforcement surface: the phantom-read gate; these do
#: not join the per-file RULES sweep because their invariant is
#: cross-file by construction.
REPO_RULES: tuple[RepoRule, ...] = (
    RepoRule(
        "R8-phantom-result-key",
        "an MCP field pick reads a key its workflow can emit",
        ("C10",),
        scan_result_key_contract,
        _R8_RECEIPT,
    ),
    RepoRule(
        "R9-entry-point-channel",
        "entry-point groups resolve read-to-registration in both directions",
        ("C10",),
        scan_entry_point_channels,
        _R9_RECEIPT,
    ),
)
