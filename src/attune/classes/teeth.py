"""Teeth — the R5 blocking decision (release-audit-stage Phase 2).

Computes, never enforces: given a baseline and HEAD, decide which
findings BLOCK, WARN, or ride an active DEFER. Enforcement (wiring
the non-zero exit into /release) arms ONLY on a chair-recorded
promotion naming the validated rule-pack version, after Phase 1 has
produced a clean dry-run manifest (R5, Codex#16). Until then the CLI
reports and exits 0 unless ``--armed``.

Re-exposure is operational, not vibes (Codex#10): a finding is
RE-EXPOSED when its stable identity exists at HEAD and not at the
baseline. Identity = (rule id, posix path rename-tracked to the
baseline name, nearest enclosing symbol) — line numbers are not
identity, so formatting moves don't re-block, and a pre-existing
finding is register debt, not a release block.

The block rule: a NEW calibrated-rule finding whose class derives
FIXED-BUT-UNGATED (or OPEN) blocks until the class gets its gate —
unless an active, valid DEFER covers the class. An expired DEFER
does not suppress; the block resuming is the convergence mechanism
(D6).
"""

from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from attune.classes.register import derive_register
from attune.classes.rules import RULES, calibrated_here, canonical_repo_id, scan_source

__all__ = ["FindingIdentity", "finding_identities", "re_exposed", "decide", "main"]

_BLOCKING_STATUSES = {"FIXED-BUT-UNGATED", "OPEN"}


@dataclass(frozen=True)
class FindingIdentity:
    """Stable identity for one finding (line numbers excluded)."""

    rule_id: str
    path: str
    anchor: str


def _enclosing_anchors(source: str) -> list[tuple[int, int, str]]:
    """(start, end, dotted-name) spans for defs/classes, innermost last."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    spans: list[tuple[int, int, str]] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                name = f"{prefix}{child.name}"
                spans.append((child.lineno, child.end_lineno or child.lineno, name))
                walk(child, f"{name}.")
            else:
                walk(child, prefix)

    walk(tree, "")
    return spans


def finding_identities(source: str, path: str) -> set[FindingIdentity]:
    """Calibration-agnostic identities for every rule hit in ``source``."""
    anchors = _enclosing_anchors(source)
    out: set[FindingIdentity] = set()
    for hit in scan_source(source, path):
        if hit.rule_id == "PARSE-ERROR":
            continue
        anchor = "<module>"
        for start, end, name in anchors:
            if start <= hit.line <= end:
                anchor = name  # innermost wins (walk order is outer->inner)
        out.add(FindingIdentity(hit.rule_id, Path(path).as_posix(), anchor))
    return out


def _rename_map(repo_root: Path, baseline_sha: str) -> dict[str, str]:
    """HEAD path -> baseline path for renamed files."""
    diff = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--find-renames",
            "--name-status",
            f"{baseline_sha}..HEAD",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    renames: dict[str, str] = {}
    for line in diff.stdout.splitlines():
        parts = line.split("\t")
        if parts and parts[0].startswith("R") and len(parts) == 3:
            renames[parts[2]] = parts[1]  # new -> old
    return renames


def re_exposed(
    repo_root: Path, baseline_sha: str, changed_files: list[str]
) -> list[FindingIdentity]:
    """Findings present at HEAD and absent at the baseline (Codex#10)."""
    renames = _rename_map(repo_root, baseline_sha)
    new_findings: list[FindingIdentity] = []
    for f in changed_files:
        head_src = (repo_root / f).read_text(encoding="utf-8", errors="replace")
        base_path = renames.get(f, f)
        show = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{baseline_sha}:{base_path}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        base_ids = finding_identities(show.stdout, f) if show.returncode == 0 else set()
        head_ids = finding_identities(head_src, f)
        new_findings.extend(sorted(head_ids - base_ids, key=lambda i: (i.path, i.anchor)))
    return new_findings


def decide(
    *,
    repo_root: Path | None = None,
    baseline_sha: str,
    changed_files: list[str],
) -> dict:
    """The R5 decision for one release diff.

    Returns:
        ``{"blocks": [...], "deferred": [...], "warns": [...]}`` —
        each entry a finding identity plus its class and reason.
    """
    root = repo_root or Path.cwd()
    repo_id = canonical_repo_id(root)
    register = derive_register(repo_root=root)
    status_by_class = {r["class_id"]: r["status"] for r in register["rows"]}
    deferred_classes = {r["class_id"] for r in register["rows"] if r["status"] == "DEFERRED"}
    calibrated_rules = {r.id: r for r in RULES if calibrated_here(r, repo_id)}

    blocks: list[dict] = []
    deferred: list[dict] = []
    warns: list[dict] = []
    for finding in re_exposed(root, baseline_sha, changed_files):
        rule = calibrated_rules.get(finding.rule_id)
        entry = {
            "rule_id": finding.rule_id,
            "path": finding.path,
            "anchor": finding.anchor,
        }
        if rule is None:
            warns.append({**entry, "reason": "advisory rule (uncalibrated-here) — never blocks"})
            continue
        classes = [c for c in rule.class_ids if status_by_class.get(c) in _BLOCKING_STATUSES]
        covered = [c for c in rule.class_ids if c in deferred_classes]
        if classes:
            blocks.append(
                {
                    **entry,
                    "classes": classes,
                    "reason": f"new calibrated finding; class(es) {classes} ungated — gate-first (D4)",
                }
            )
        elif covered:
            deferred.append(
                {
                    **entry,
                    "classes": covered,
                    "reason": "active DEFER covers the class; block resumes at expiry (D6)",
                }
            )
        else:
            warns.append({**entry, "reason": "class gated or closed — informational"})
    return {"blocks": blocks, "deferred": deferred, "warns": warns}


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.teeth --baseline <sha> [--armed]``."""
    import argparse

    from attune.classes.baseline import BaselineError, resolve_baseline

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--armed",
        action="store_true",
        help="non-zero exit on blocks — ONLY under a chair-recorded promotion (R5)",
    )
    args = parser.parse_args(argv)
    root = args.repo_root or Path.cwd()
    try:
        baseline = resolve_baseline(root, override=args.baseline)
    except BaselineError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    result = decide(
        repo_root=root,
        baseline_sha=baseline.baseline_sha,
        changed_files=[f for f in baseline.changed if f.endswith(".py")],
    )
    print(json.dumps(result, indent=2))
    if result["blocks"] and args.armed:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
