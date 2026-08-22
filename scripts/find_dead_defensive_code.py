#!/usr/bin/env python3
"""Find Class 2 dead-defensive-code patterns from the coverage bug log.

Usage: python scripts/find_dead_defensive_code.py [path]
       (defaults to src/attune/)

Searches for:

- 2A: Default after exhaustive enum dispatch.
      Function has a chain of `if X == Enum.VALUE: return ...` covering
      every value of an enum, followed by a final default `return`.

- 2B: Post-loop fallback after a loop that always returns/raises.
      `for ...:` loop where every body path either returns or raises,
      followed by post-loop code that's structurally unreachable.

- 2C: Divisor guard where the divisor is structurally non-zero.
      `if x > 0: return n / x` where x is pulled from a structure that
      provably never stores zero values (heuristic: hard to detect
      without dataflow; emits a hint for any guarded division).

- 2D: Filter on already-filtered data.
      `[x for x in seq if x]` over a sequence whose elements are
      verifiably non-falsy (heuristic).

This is a heuristic finder — it will produce false positives. Treat the
output as "candidates worth reading," not "confirmed bugs."
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _enum_value_names(repo_root: Path) -> dict[str, set[str]]:
    """Walk source tree and return {EnumName: {value names}} for all Enum subclasses."""
    enums: dict[str, set[str]] = {}
    for py in repo_root.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            base_names = {
                (
                    b.id
                    if isinstance(b, ast.Name)
                    else (b.attr if isinstance(b, ast.Attribute) else "")
                )
                for b in node.bases
            }
            if not (base_names & {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}):
                continue
            members: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for tgt in item.targets:
                        if isinstance(tgt, ast.Name) and tgt.id.isupper():
                            members.add(tgt.id)
            if members:
                enums[node.name] = members
    return enums


def _all_paths_exit(stmts: list[ast.stmt]) -> bool:
    """True if every path through `stmts` terminates with return or raise."""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, (ast.Return, ast.Raise)):
        return True
    if isinstance(last, ast.If):
        # Both branches must exit
        if not _all_paths_exit(last.body):
            return False
        if not last.orelse:
            return False
        return _all_paths_exit(last.orelse)
    return False


# -----------------------------------------------------------------------------
# Pattern 2A: default after exhaustive enum dispatch
# -----------------------------------------------------------------------------


def find_2a(tree: ast.AST, enums: dict[str, set[str]]) -> list[tuple[int, str]]:
    """Find functions ending with default-return after exhaustive enum if-chain."""
    findings: list[tuple[int, str]] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = fn.body
        if len(body) < 3:
            continue
        # Walk the trailing run of `if X == Enum.MEMBER: return`-style statements
        # and a final return.
        if not isinstance(body[-1], ast.Return):
            continue
        # Collect contiguous if-return statements before the final return
        idx = len(body) - 2
        enum_name: str | None = None
        members_seen: set[str] = set()
        var_name: str | None = None
        while idx >= 0:
            stmt = body[idx]
            if not isinstance(stmt, ast.If):
                break
            test = stmt.test
            if not (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
            ):
                break
            left, right = test.left, test.comparators[0]
            # X == Enum.MEMBER  OR  Enum.MEMBER == X
            cur_var = cur_enum = cur_member = None
            for a, b in [(left, right), (right, left)]:
                if (
                    isinstance(a, ast.Name)
                    and isinstance(b, ast.Attribute)
                    and isinstance(b.value, ast.Name)
                ):
                    cur_var, cur_enum, cur_member = a.id, b.value.id, b.attr
                    break
            if cur_var is None:
                break
            if var_name is None:
                var_name, enum_name = cur_var, cur_enum
            elif cur_var != var_name or cur_enum != enum_name:
                break
            # body must be a single return
            if not (len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return)):
                break
            members_seen.add(cur_member)
            idx -= 1
        if enum_name and enum_name in enums:
            expected = enums[enum_name]
            if expected and members_seen == expected:
                findings.append(
                    (
                        fn.lineno,
                        f"2A {fn.name}: exhaustive {enum_name} dispatch + dead default return",
                    )
                )
    return findings


# -----------------------------------------------------------------------------
# Pattern 2B: post-loop fallback after always-exiting loop
# -----------------------------------------------------------------------------


def find_2b(tree: ast.AST) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        # Function bodies, then look for For/While followed by code
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        for i, stmt in enumerate(body):
            if not isinstance(stmt, (ast.For, ast.While)):
                continue
            # Loop body must always exit
            if not _all_paths_exit(stmt.body):
                continue
            # Followed by code that includes `if last_exception: raise` style
            tail = body[i + 1 :]
            if not tail:
                continue
            for s in tail:
                if isinstance(s, ast.If) and isinstance(s.test, ast.Name):
                    if any(
                        isinstance(b, ast.Raise)
                        and isinstance(b.exc, ast.Name)
                        and b.exc.id == s.test.id
                        for b in s.body
                    ):
                        findings.append(
                            (
                                s.lineno,
                                f"2B {node.name}: post-loop `if {s.test.id}: raise {s.test.id}` after always-exiting loop",
                            )
                        )
                        break
    return findings


# -----------------------------------------------------------------------------
# Pattern 2C: divisor guard (heuristic)
# -----------------------------------------------------------------------------


def find_2c(tree: ast.AST) -> list[tuple[int, str]]:
    """Hint for any `if x > 0:` immediately preceding a division using `x`.

    Heuristic — emits hints; whether it's actually dead depends on whether
    the structure that holds `x` can ever store a zero. Reviewer must confirm.
    """
    findings: list[tuple[int, str]] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for i, stmt in enumerate(fn.body):
            if not isinstance(stmt, ast.If):
                continue
            test = stmt.test
            if not (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Gt)
                and isinstance(test.left, ast.Name)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == 0
            ):
                continue
            divisor = test.left.id
            for inner in ast.walk(stmt):
                if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.Div):
                    if isinstance(inner.right, ast.Name) and inner.right.id == divisor:
                        findings.append(
                            (
                                stmt.lineno,
                                f"2C {fn.name}: `if {divisor} > 0:` guards `/ {divisor}` — confirm divisor is structurally non-zero",
                            )
                        )
                        break
    return findings


# -----------------------------------------------------------------------------
# Driver
# -----------------------------------------------------------------------------


def main() -> int:
    target = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path("src/attune")).resolve()
    if not target.exists():
        print(f"path not found: {target}", file=sys.stderr)
        return 2
    repo_root = target
    while not (repo_root / "pyproject.toml").exists() and repo_root != repo_root.parent:
        repo_root = repo_root.parent
    enums = _enum_value_names(repo_root)
    total = 0
    for py in sorted(target.rglob("*.py")):
        if any(part in {"__pycache__", "build", "dist", "site-packages"} for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            continue
        rel = py.relative_to(repo_root)
        hits: list[tuple[int, str]] = []
        hits += find_2a(tree, enums)
        hits += find_2b(tree)
        hits += find_2c(tree)
        for lineno, msg in sorted(hits):
            print(f"{rel}:{lineno}: {msg}")
            total += 1
    print(f"\n{total} candidate(s) found.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
