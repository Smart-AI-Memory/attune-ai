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
    "Rule",
    "RULES",
    "calibrated_here",
    "canonical_repo_id",
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
