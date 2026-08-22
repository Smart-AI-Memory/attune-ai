"""The residual packet — release-audit-stage R4, schema v1.

What the seats sit on. The packet is a small, normative artifact: eight
sections, hard caps, and **no diff hunks or file contents**. Its job is
to make an every-release sitting payable (D2) by keeping the reading
cost near zero when the residual is empty, and bounded when it is not.

**Over-cap is a refusal, never a truncation** (R4/Agy#4). A packet that
silently dropped its 13th item would let the chair rule on a subset
while believing they ruled on the whole — so :func:`build_packet`
raises :class:`PacketOverCap` carrying structured diagnostics, and the
chair splits the release (R4 split semantics: the chair splits, the
tool re-runs).

Section map::

    §0 header        tag range, baseline SHA, files, packages, symbol delta
    §1 reconcile     CI run id, workflow, HEAD SHA, conclusion
    §2 sweep hits    class, file:line, excerpt, recall/precision, SCAN-ERROR
    §3 exposure      fixed-but-ungated classes x changed surface (matrix)
    §4 boundaries    new boundary kind + two program points each
    §5 open classes  open class x file
    §6 NULL          what this diff does NOT introduce
    §7 dispositions  one pre-filled default per residual item

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from attune.classes.baseline import SWEEP_ROOTS, Baseline

__all__ = [
    "DISPOSITIONS",
    "PacketOverCap",
    "Packet",
    "ResidualItem",
    "build_packet",
]

#: R3 disposition vocabulary — exactly these, no synonyms.
DISPOSITIONS = ("SHIP", "HOLD", "GATE-FIRST", "DEFER")

#: R4 hard caps. Exceeding any of them is a refusal, not a trim.
MAX_WORDS = 1500
MAX_ITEMS = 12
MAX_SWEEP_ROWS = 20

#: D5 — a calibrated HIT blocks, surface EXPOSURE only warns. These are
#: PRE-FILLED defaults the seats amend and the chair rules on (R4 §7);
#: they are never the final word.
_DEFAULT_DISPOSITION = {
    "hit": "GATE-FIRST",
    "advisory-hit": "SHIP",
    "exposure": "SHIP",
    "open-class": "SHIP",
    "boundary": "SHIP",
}


class PacketOverCap(RuntimeError):
    """The residual does not fit schema v1 — the chair splits the release."""

    def __init__(self, diagnostics: dict[str, Any]) -> None:
        self.diagnostics = diagnostics
        super().__init__(json.dumps(diagnostics, indent=2, sort_keys=True))

    #: Process exit code reserved for an over-cap refusal (R4).
    exit_code = 2


@dataclass(frozen=True)
class ResidualItem:
    """One thing the chair must rule on.

    ``item_id`` is stable for a given (kind, class, locus) so a manifest
    ruling can be matched back to what it ruled on.
    """

    item_id: str
    kind: str
    class_id: str
    locus: str
    detail: str
    default_disposition: str

    def as_dict(self) -> dict[str, str]:
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "class_id": self.class_id,
            "locus": self.locus,
            "detail": self.detail,
            "default_disposition": self.default_disposition,
        }


@dataclass(frozen=True)
class Packet:
    """A schema-v1 residual packet."""

    sections: dict[str, Any]
    items: tuple[ResidualItem, ...] = field(default=())
    schema_version: int = 1

    @property
    def packet_hash(self) -> str:
        """Content hash the manifest binds to (R7 ``packet_hash``)."""
        payload = json.dumps(self.as_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @property
    def blocking(self) -> tuple[ResidualItem, ...]:
        """Items whose default is to stop the release (D4/D5 teeth)."""
        return tuple(i for i in self.items if i.default_disposition in ("HOLD", "GATE-FIRST"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "sections": self.sections,
            "items": [i.as_dict() for i in self.items],
        }

    def word_count(self) -> int:
        return len(json.dumps(self.as_dict(), ensure_ascii=False).split())


def _public_symbols(source: str) -> set[str]:
    """Top-level public names a module exports."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)
    return names


def _show(repo_root: Path, ref: str, path: str) -> str:
    """File contents at a ref, or "" when absent there."""
    result = subprocess.run(  # noqa: S603 — fixed argv, no shell
        ["git", "-C", str(repo_root), "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


#: Only these paths carry the PACKAGE's public surface. A test class
#: named ``TestValidationError`` disappearing is not an API removal, and
#: letting it into §0 buries the removals that actually break a caller.
_PACKAGE_ROOTS = ("src/",)


def _is_package_surface(path: str) -> bool:
    return path.startswith(_PACKAGE_ROOTS)


def _symbol_delta(repo_root: Path, baseline: Baseline) -> dict[str, list[str]]:
    """Public symbols added/removed across the range (R4 §0).

    A public-surface change is what makes a release breaking, so the
    header states it rather than leaving the chair to infer it.

    DELETED modules are included deliberately. The sweep skips them —
    there is nothing left to scan — but every public name a deleted
    module exported is removed, and that is the clearest breaking change
    a release can contain. Reading only the changed set would have made
    14.0.0's own breaking removal invisible here.
    """
    added: set[str] = set()
    removed: set[str] = set()

    for path in baseline.changed:
        if not _is_package_surface(path):
            continue
        before = _public_symbols(_show(repo_root, baseline.baseline_sha, path))
        after = _public_symbols(_show(repo_root, baseline.head_sha, path))
        added |= after - before
        removed |= before - after

    for path in baseline.deleted:
        if not _is_package_surface(path):
            continue
        removed |= _public_symbols(_show(repo_root, baseline.baseline_sha, path))

    return {"added": sorted(added), "removed": sorted(removed)}


def _packages_touched(changed: tuple[str, ...]) -> list[str]:
    """Distinct top-level package paths in the changed set (R4 §0)."""
    packages = set()
    for path in changed:
        parts = Path(path).parts
        packages.add("/".join(parts[:2]) if len(parts) > 1 else parts[0])
    return sorted(packages)


def build_packet(
    baseline: Baseline,
    sweep: dict[str, Any],
    register: dict[str, Any],
    *,
    repo_root: Path | None = None,
    reconcile: dict[str, Any] | None = None,
    boundaries: tuple[dict[str, Any], ...] = (),
) -> Packet:
    """Assemble the schema-v1 residual packet.

    Args:
        baseline: The resolved audit range (R3 step 0).
        sweep: :func:`attune.classes.scan.scan_paths` output over
            ``baseline.changed`` (R3 step 2).
        register: :func:`attune.classes.register.derive_register` output.
        repo_root: Repo to read file contents from for the §0 symbol delta.
        reconcile: The §1 receipt, or None when reconcile has not run.
        boundaries: §4 new-boundary inventory entries.

    Returns:
        A :class:`Packet` whose items each carry a pre-filled disposition.

    Raises:
        PacketOverCap: Any R4 cap exceeded. Carries diagnostics naming
            which cap and by how much; the caller exits 2 and the chair
            splits the release. Nothing is truncated.

    """
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    rows = register.get("rows", [])
    by_status: dict[str, list[dict]] = {}
    for row in rows:
        by_status.setdefault(row["status"], []).append(row)

    rule_meta = sweep.get("rules", {})
    items: list[ResidualItem] = []

    # -- §2 sweep hits ----------------------------------------------------
    sweep_rows: list[dict[str, Any]] = []
    for hit in sweep.get("hits", []):
        meta = rule_meta.get(hit["rule_id"], {})
        calibration = meta.get("calibration") or {}
        calibrated = bool(meta.get("calibrated_here"))
        locus = f"{hit['path']}:{hit['line']}"
        sweep_rows.append(
            {
                "class_ids": meta.get("class_ids", []),
                "rule_id": hit["rule_id"],
                "locus": locus,
                "excerpt": str(hit.get("detail", ""))[:120],
                "recall": calibration.get("recall"),
                "precision": calibration.get("precision"),
                "calibrated_here": calibrated,
            }
        )
        # Only a CALIBRATED hit becomes a residual item. An uncalibrated
        # rule is advisory here (R1: "never blocks, never clears"), so it
        # is reported as a sweep row and NOT given a chair ruling — it
        # would consume the item cap with something unrulable.
        if not calibrated:
            continue
        class_id = (meta.get("class_ids") or ["?"])[0]
        items.append(
            ResidualItem(
                item_id=f"hit:{hit['rule_id']}:{locus}",
                kind="hit",
                class_id=class_id,
                locus=locus,
                detail=str(hit.get("detail", ""))[:120],
                default_disposition=_DEFAULT_DISPOSITION["hit"],
            )
        )

    # -- §3 ungated exposure: a MATRIX, never severity rows (D5) ----------
    ungated = [r["class_id"] for r in by_status.get("FIXED-BUT-UNGATED", [])]
    exposure_matrix = [
        {"class_id": class_id, "changed_surface": bool(baseline.changed)} for class_id in ungated
    ]
    # D5: exposure WARNS through this matrix and nothing else. Minting a
    # residual item per ungated class would put warning-severity rows in
    # competition with hits for the item cap — the precise thing D5
    # forbids, because a noisy gate gets allowlisted into uselessness.

    # -- §5 open-class exposure -------------------------------------------
    open_rows = []
    for row in by_status.get("OPEN", []):
        open_rows.append({"class_id": row["class_id"], "hits": row.get("calibrated_hits", 0)})
        items.append(
            ResidualItem(
                item_id=f"open-class:{row['class_id']}",
                kind="open-class",
                class_id=row["class_id"],
                locus="register",
                detail="confirmed class with no gate",
                default_disposition=_DEFAULT_DISPOSITION["open-class"],
            )
        )

    # -- §4 new boundaries -------------------------------------------------
    for boundary in boundaries:
        items.append(
            ResidualItem(
                item_id=f"boundary:{boundary.get('kind')}:{boundary.get('locus')}",
                kind="boundary",
                class_id=str(boundary.get("class_id", "-")),
                locus=str(boundary.get("locus", "")),
                detail=str(boundary.get("kind", "")),
                default_disposition=_DEFAULT_DISPOSITION["boundary"],
            )
        )

    # -- §6 explicit NULL: stating what is ABSENT is the point -------------
    null_section = {
        "no_calibrated_hits": not any(i.kind == "hit" for i in items),
        "no_scan_errors": not sweep.get("scan_errors"),
        "no_public_symbols_removed": True,  # replaced below once computed
        "no_new_boundaries": not boundaries,
    }

    symbol_delta = _symbol_delta(root, baseline)
    null_section["no_public_symbols_removed"] = not symbol_delta["removed"]

    sections = {
        "0_header": {
            "tag_range": baseline.tag_range,
            "baseline_sha": baseline.baseline_sha,
            "head_sha": baseline.head_sha,
            "baseline_source": baseline.source,
            "files_changed": len(baseline.changed),
            # D10: the sweep is package-scoped. Stating what was NOT
            # looked at keeps a narrowed sweep from reading like a clean
            # one — an empty residual must never be ambiguous between
            # "no defects here" and "did not look here".
            "files_swept": len(baseline.to_sweep),
            "files_not_swept": len(baseline.not_swept),
            "sweep_scope": list(SWEEP_ROOTS),
            "packages_touched": _packages_touched(baseline.changed),
            "public_symbols": symbol_delta,
        },
        "1_reconcile": reconcile,
        "2_sweep_hits": sweep_rows,
        "3_ungated_exposure": exposure_matrix,
        "4_new_boundaries": list(boundaries),
        "5_open_class_exposure": open_rows,
        "6_null": null_section,
        "7_default_dispositions": [
            {"item_id": i.item_id, "disposition": i.default_disposition} for i in items
        ],
        "scan_errors": sweep.get("scan_errors", []),
    }

    packet = Packet(sections=sections, items=tuple(items))

    breaches = []
    if len(items) > MAX_ITEMS:
        breaches.append({"cap": "items", "limit": MAX_ITEMS, "actual": len(items)})
    if len(sweep_rows) > MAX_SWEEP_ROWS:
        breaches.append({"cap": "sweep_rows", "limit": MAX_SWEEP_ROWS, "actual": len(sweep_rows)})
    words = packet.word_count()
    if words > MAX_WORDS:
        breaches.append({"cap": "words", "limit": MAX_WORDS, "actual": words})

    if breaches:
        raise PacketOverCap(
            {
                "error": "residual-over-cap",
                "remedy": "split the release; each partition re-runs baseline -> sweep -> exposure",
                "tag_range": baseline.tag_range,
                "breaches": breaches,
            }
        )

    return packet
