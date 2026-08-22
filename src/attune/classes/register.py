"""``attune classes register`` — the DERIVED status column (R2).

The register's status is computed, never authored (unanimous table
finding, roundtable ``q-release-audit-roundtable-stage-001``):

| gate resolves? | calibrated hits | active DEFER | status |
|---|---|---|---|
| yes | 0 | — | CLOSED |
| yes | >0 | — | BROKEN-GATE (loud) |
| no | 0 | no | FIXED-BUT-UNGATED |
| no | >0 | no | OPEN |
| no | any | yes | DEFERRED |

A class with no calibrated rule and no gate derives UNMECHANIZED —
hits are unknowable there, and fabricating a status would make the
register assert something untrue. Advisory (uncalibrated) hits are
reported but never move a status (R1).

Gate identity, not existence (Codex#3): a mapping resolves only when
the gate file exists, defines the named test, AND carries a
``Register-Class: <id>`` tag matching the mapping — a renamed or
reassigned gate goes loud instead of silently preserving CLOSED.
"""

from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from attune.classes.rules import RULES, calibrated_here, canonical_repo_id
from attune.classes.scan import scan_paths

__all__ = ["GateRef", "GATES", "derive_register", "load_defers", "main"]

_REQUIRED_DISPOSITION_KEYS = {"rule_id", "path", "reason"}

_REQUIRED_DEFER_KEYS = {
    "class_id",
    "owner",
    "reason",
    "approved_at",
    "created_sha",
    "expires_after_releases",
    "chair_receipt",
}


@dataclass(frozen=True)
class GateRef:
    """One class -> gate-test mapping (stable node id + identity tag)."""

    class_id: str
    path: str
    test_name: str

    def resolution_problem(self, repo_root: Path) -> str | None:
        """None when the gate resolves; else the drift reason."""
        f = repo_root / self.path
        if not f.is_file():
            return f"gate file missing: {self.path}"
        try:
            source = f.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError) as exc:
            return f"gate file unreadable: {self.path}: {exc}"
        names = {
            n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        if self.test_name not in names:
            return f"gate test renamed away: {self.path}::{self.test_name}"
        if f"Register-Class: {self.class_id}" not in source:
            return (
                f"gate identity tag missing: {self.path} does not carry "
                f"'Register-Class: {self.class_id}'"
            )
        return None


#: The class -> gate mapping. Adding a gate = one row here + the
#: ``Register-Class:`` tag in the gate file; the drift guard
#: (tests/unit/classes/test_register.py) fails on any half-done pair.
GATES: tuple[GateRef, ...] = (
    GateRef(
        "C3",
        "tests/unit/gates/test_external_input_dict_guard.py",
        "test_evaluator_does_not_block_the_chain_on_a_non_object_answer",
    ),
    GateRef(
        "C4a",
        "tests/unit/gates/test_ast_parse_null_byte_guard.py",
        "test_guarded_ast_parse_also_catches_value_error",
    ),
    GateRef(
        "H1",
        "tests/unit/gates/test_reachability_oracle_gate.py",
        "test_no_unresolved_redis_endpoint",
    ),
    GateRef(
        "G1", "tests/unit/gates/test_deterministic_tmp_gate.py", "test_no_deterministic_tmp_publish"
    ),
    GateRef(
        "G2",
        "tests/unit/gates/test_per_record_guard_gate.py",
        "test_no_unguarded_per_record_coercion",
    ),
    GateRef(
        "I-4",
        "tests/unit/gates/test_deserialize_subscript_gate.py",
        "test_no_unguarded_deserialize_into_reconstructor",
    ),
)


def load_dispositions(repo_root: Path) -> tuple[list[dict], list[str]]:
    """Load ``.attune/class-dispositions.yaml`` — dismissed findings.

    The review's dismissed-with-reason discipline, machine-readable:
    each entry ``{rule_id, path, reason}`` subtracts a KNOWN,
    inspected finding from status derivation, so a gate that
    deliberately asserts a subset (C3 group A) is not reported
    BROKEN by hits the review already dismissed. Entries missing
    required keys are problems, never silently applied.
    """
    f = repo_root / ".attune" / "class-dispositions.yaml"
    if not f.is_file():
        return [], []
    try:
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [], [f"class-dispositions.yaml unreadable: {exc}"]
    if data is None:
        return [], []
    if not isinstance(data, list):
        return [], ["class-dispositions.yaml: not a list"]
    valid: list[dict] = []
    problems: list[str] = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict) or _REQUIRED_DISPOSITION_KEYS - set(entry):
            problems.append(
                f"class-dispositions.yaml entry {i}: needs {sorted(_REQUIRED_DISPOSITION_KEYS)}"
            )
            continue
        valid.append(entry)
    return valid, problems


def load_defers(repo_root: Path) -> tuple[list[dict], list[str]]:
    """Load and validate ``.attune/defers/*.yaml`` (R5 schema).

    Returns:
        (valid_records, problems). A record missing required keys or
        unparseable is a PROBLEM, never silently active — an invalid
        DEFER must not suppress a block.
    """
    defer_dir = repo_root / ".attune" / "defers"
    records: list[dict] = []
    problems: list[str] = []
    if not defer_dir.is_dir():
        return records, problems
    for f in sorted(defer_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            problems.append(f"{f.name}: unreadable ({exc})")
            continue
        if not isinstance(data, dict):
            problems.append(f"{f.name}: not a mapping")
            continue
        missing = _REQUIRED_DEFER_KEYS - set(data)
        if missing:
            problems.append(f"{f.name}: missing keys {sorted(missing)}")
            continue
        records.append(data)
    return records, problems


def _defer_expired(record: dict, repo_root: Path) -> bool:
    """A DEFER expires after N releases (tags) contain its creation SHA."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "tag", "--contains", str(record["created_sha"])],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False  # cannot prove expiry -> record stays active (fail toward blocking later, not silence)
    if result.returncode != 0:
        return False
    releases_since = len([t for t in result.stdout.splitlines() if t.strip()])
    try:
        allowed = int(record["expires_after_releases"])
    except (TypeError, ValueError):
        return False
    return releases_since >= allowed


def _subtract_dispositions(hits: list[dict], dispositions: list[dict], root: Path) -> list[dict]:
    """Drop hits the review dismissed with a recorded reason."""
    dismissed = {(d["rule_id"], d["path"]) for d in dispositions}

    def _rel(path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(root.resolve()))
        except ValueError:
            return path

    return [h for h in hits if (h["rule_id"], _rel(h["path"])) not in dismissed]


def _count_hits_per_class(hits: list[dict], repo_id: str) -> tuple[dict[str, int], dict[str, int]]:
    """Per-class hit counts, split calibrated vs advisory (R1)."""
    calibrated: dict[str, int] = {}
    advisory: dict[str, int] = {}
    for rule in RULES:
        n = sum(1 for h in hits if h["rule_id"] == rule.id)
        bucket = calibrated if calibrated_here(rule, repo_id) else advisory
        for class_id in rule.class_ids:
            bucket[class_id] = bucket.get(class_id, 0) + n
    return calibrated, advisory


def _derive_status(*, gate_ok: bool, hits: int, deferred: bool, mechanized: bool) -> str:
    """The R2 status table, one decision per row."""
    if gate_ok:
        return "BROKEN-GATE" if hits > 0 else "CLOSED"
    if deferred:
        return "DEFERRED"
    if not mechanized:
        return "UNMECHANIZED"
    return "OPEN" if hits > 0 else "FIXED-BUT-UNGATED"


def _class_row(
    class_id: str,
    *,
    gate: GateRef | None,
    root: Path,
    repo_id: str,
    calibrated_hits: int,
    advisory_hits: int,
    defer: dict | None,
) -> dict:
    """One derived-register row."""
    gate_problem = gate.resolution_problem(root) if gate else None
    mechanized = any(class_id in r.class_ids and calibrated_here(r, repo_id) for r in RULES)
    status = _derive_status(
        gate_ok=gate is not None and gate_problem is None,
        hits=calibrated_hits,
        deferred=defer is not None,
        mechanized=mechanized,
    )
    return {
        "class_id": class_id,
        "status": status,
        "gate": f"{gate.path}::{gate.test_name}" if gate else None,
        "gate_problem": gate_problem,
        "calibrated_hits": calibrated_hits,
        "advisory_hits": advisory_hits,
        "defer": (defer or {}).get("chair_receipt"),
    }


def derive_register(
    *,
    repo_root: Path | None = None,
    scan_roots: list[Path] | None = None,
) -> dict:
    """Compute the derived register for this repo.

    Args:
        repo_root: Repository root; default cwd.
        scan_roots: Paths for the FULL-REPO scan (status must derive
            from whole-tree hits, never a changed-file sweep —
            Codex#4). Default ``src``.

    Returns:
        JSON-ready dict: per-class status rows plus defer problems
        and scan errors.
    """
    root = repo_root or Path.cwd()
    repo_id = canonical_repo_id(root)
    roots = scan_roots or [root / "src"]
    scan = scan_paths(roots, repo_root=root)

    dispositions, disposition_problems = load_dispositions(root)
    kept_hits = _subtract_dispositions(scan["hits"], dispositions, root)
    calibrated_hits, advisory_hits = _count_hits_per_class(kept_hits, repo_id)

    defers, defer_problems = load_defers(root)
    active_defers = {str(d["class_id"]): d for d in defers if not _defer_expired(d, root)}

    gate_by_class = {g.class_id: g for g in GATES}
    universe = (
        set(gate_by_class)
        | set(calibrated_hits)
        | set(advisory_hits)
        | set(active_defers)
        | {cid for r in RULES for cid in r.class_ids}
    )

    rows = [
        _class_row(
            class_id,
            gate=gate_by_class.get(class_id),
            root=root,
            repo_id=repo_id,
            calibrated_hits=calibrated_hits.get(class_id, 0),
            advisory_hits=advisory_hits.get(class_id, 0),
            defer=active_defers.get(class_id),
        )
        for class_id in sorted(universe)
    ]
    return {
        "repo": repo_id,
        "rows": rows,
        "defer_problems": defer_problems,
        "disposition_problems": disposition_problems,
        "dispositions_applied": len(dispositions),
        "scan_errors": scan["scan_errors"],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.register [--repo-root .]``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--scan-roots", nargs="*", type=Path, default=None)
    args = parser.parse_args(argv)
    result = derive_register(repo_root=args.repo_root, scan_roots=args.scan_roots)
    print(json.dumps(result, indent=2))
    broken = [r for r in result["rows"] if r["status"] == "BROKEN-GATE"]
    problems = result["defer_problems"] + result["disposition_problems"]
    return 1 if (broken or problems or result["scan_errors"]) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
