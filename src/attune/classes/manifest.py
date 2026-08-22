"""The chair manifest — release-audit-stage R7.

What connects the audit to deployment. Without it the stage is
advisory-by-accident: a chair could sit, rule, and then tag something
else entirely. ``release-execute`` verifies a valid manifest exists for
the tag being cut, so a ruling is bound to a release rather than to a
conversation.

Two invariants do the work:

**Completion (R3).** The stage is complete only when EVERY residual item
id carries EXACTLY ONE ruling. A missing ruling means the chair did not
see an item; a duplicate means two rulings disagree. Both reject the
manifest rather than picking a winner.

**Immutability (R7).** A manifest is written once. A re-run writes a new
one — amending in place would let a recorded decision change after the
fact, which is the whole thing the receipt exists to prevent.

``sitting_delta`` (D9) is REQUIRED, not optional: per item, did any seat
amendment change the chair's disposition away from the packet's §7
default? Its release-over-release tally is how the every-release sitting
earns — or loses — its own justification, by measurement rather than
argument.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from attune.classes.packet import DISPOSITIONS, Packet
from attune.security.path_validation import _validate_file_path

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "ManifestError",
    "Manifest",
    "manifest_path",
    "build_manifest",
    "write_manifest",
    "load_manifest",
    "validate_manifest",
    "require_manifest",
]

MANIFEST_SCHEMA_VERSION = 1

_REQUIRED_KEYS = (
    "schema_version",
    "tag",
    "head_sha",
    "baseline_sha",
    "packet_hash",
    "reconcile_receipt",
    "per_item_dispositions",
    "defer_refs",
    "sitting_delta",
    "chair_receipt",
)


class ManifestError(ValueError):
    """A manifest is missing, malformed, or does not rule on the packet."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class Manifest:
    """One chair ruling, bound to one tag and one packet."""

    tag: str
    head_sha: str
    baseline_sha: str
    packet_hash: str
    reconcile_receipt: dict[str, Any]
    per_item_dispositions: dict[str, str]
    defer_refs: tuple[str, ...]
    sitting_delta: dict[str, bool]
    chair_receipt: str
    schema_version: int = MANIFEST_SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tag": self.tag,
            "head_sha": self.head_sha,
            "baseline_sha": self.baseline_sha,
            "packet_hash": self.packet_hash,
            "reconcile_receipt": self.reconcile_receipt,
            "per_item_dispositions": dict(self.per_item_dispositions),
            "defer_refs": list(self.defer_refs),
            "sitting_delta": dict(self.sitting_delta),
            "chair_receipt": self.chair_receipt,
        }

    @property
    def blocked(self) -> tuple[str, ...]:
        """Items the chair did NOT clear — the release stops for these (D4)."""
        return tuple(
            sorted(
                item_id
                for item_id, ruling in self.per_item_dispositions.items()
                if ruling in ("HOLD", "GATE-FIRST")
            )
        )

    @property
    def sitting_changed_anything(self) -> bool:
        """D9: did the sitting move a single disposition this release?"""
        return any(self.sitting_delta.values())


#: A release tag is caller-supplied and lands in a filesystem path, so it
#: is constrained to the characters a tag can legitimately hold. Without
#: this, a "tag" of ``../../../etc/cron.d/x`` would write outside the
#: manifest directory — the path-validation gate flagged exactly this.
_SAFE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def manifest_path(repo_root: Path, tag: str) -> Path:
    """Where a tag's manifest lives.

    The tag is validated and the resolved path is confined to the
    manifest directory: a manifest is a release receipt, so an
    attacker-influenced tag must not be able to place a file anywhere
    else, nor read one from anywhere else.

    Raises:
        ManifestError: The tag is not a plausible tag name, or the
            resolved path escapes ``.attune/release-manifests``.

    """
    if not isinstance(tag, str) or not _SAFE_TAG.match(tag):
        raise ManifestError("bad-tag", f"{tag!r} is not a valid release tag name")

    root = Path(repo_root) / ".attune" / "release-manifests"
    candidate = root / f"{tag}.json"
    try:
        validated = _validate_file_path(str(candidate), allowed_dir=str(root.resolve().parent))
    except ValueError as exc:
        raise ManifestError("unsafe-path", str(exc)) from exc

    if validated.parent.resolve() != root.resolve():
        raise ManifestError("unsafe-path", f"{tag!r} escapes the manifest directory")
    return validated


def build_manifest(
    packet: Packet,
    *,
    tag: str,
    head_sha: str,
    baseline_sha: str,
    rulings: dict[str, str],
    chair_receipt: str,
    reconcile_receipt: dict[str, Any] | None = None,
    defer_refs: tuple[str, ...] = (),
    sitting_delta: dict[str, bool] | None = None,
) -> Manifest:
    """Assemble a manifest and validate it against the packet it rules on.

    Raises:
        ManifestError: A ruling is missing, unknown, or names an item the
            packet does not contain. Rather than silently accepting a
            partial ruling set, which would let the stage report complete.

    """
    item_ids = {item.item_id for item in packet.items}
    ruled = set(rulings)

    missing = sorted(item_ids - ruled)
    if missing:
        raise ManifestError("missing-rulings", f"{len(missing)} unruled item(s): {missing[:5]}")

    unknown = sorted(ruled - item_ids)
    if unknown:
        raise ManifestError("unknown-items", f"rulings for items not in the packet: {unknown[:5]}")

    bad = sorted({r for r in rulings.values() if r not in DISPOSITIONS})
    if bad:
        raise ManifestError("bad-disposition", f"{bad} not in {list(DISPOSITIONS)}")

    delta = sitting_delta if sitting_delta is not None else {}
    missing_delta = sorted(item_ids - set(delta))
    if missing_delta:
        raise ManifestError(
            "missing-sitting-delta",
            f"D9 requires a per-item delta; {len(missing_delta)} missing",
        )

    return Manifest(
        tag=tag,
        head_sha=head_sha,
        baseline_sha=baseline_sha,
        packet_hash=packet.packet_hash,
        reconcile_receipt=reconcile_receipt or {},
        per_item_dispositions=dict(rulings),
        defer_refs=tuple(defer_refs),
        sitting_delta=dict(delta),
        chair_receipt=chair_receipt,
    )


def write_manifest(manifest: Manifest, repo_root: Path) -> Path:
    """Write a manifest atomically. Refuses to overwrite (R7 immutability).

    Raises:
        ManifestError: A manifest already exists for this tag. A re-run
            writes a NEW manifest under a new tag; amending in place would
            let a recorded decision change after it was relied on.

    """
    target = manifest_path(repo_root, manifest.tag)
    if target.exists():
        raise ManifestError(
            "already-exists",
            f"{target} — manifests are immutable; a re-run writes a new tag",
        )
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(manifest.as_dict(), indent=2, sort_keys=True) + "\n"
    handle, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(tmp, target)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target


def validate_manifest(data: dict[str, Any]) -> Manifest:
    """Parse and validate a manifest mapping.

    Raises:
        ManifestError: Missing keys, wrong schema version, an unknown
            disposition, or an empty ``sitting_delta`` — D9 makes the
            delta required, so a manifest without it is invalid.

    """
    if not isinstance(data, dict):
        raise ManifestError("not-a-mapping", type(data).__name__)

    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise ManifestError("missing-keys", str(missing))

    if data["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ManifestError(
            "schema-version", f"expected {MANIFEST_SCHEMA_VERSION}, got {data['schema_version']!r}"
        )

    rulings = data["per_item_dispositions"]
    if not isinstance(rulings, dict):
        raise ManifestError("bad-dispositions", "per_item_dispositions must be a mapping")

    bad = sorted({r for r in rulings.values() if r not in DISPOSITIONS})
    if bad:
        raise ManifestError("bad-disposition", f"{bad} not in {list(DISPOSITIONS)}")

    delta = data["sitting_delta"]
    if not isinstance(delta, dict) or (rulings and not delta):
        raise ManifestError("missing-sitting-delta", "D9 requires a per-item sitting delta")

    return Manifest(
        tag=data["tag"],
        head_sha=data["head_sha"],
        baseline_sha=data["baseline_sha"],
        packet_hash=data["packet_hash"],
        reconcile_receipt=data["reconcile_receipt"],
        per_item_dispositions=rulings,
        defer_refs=tuple(data["defer_refs"]),
        sitting_delta=delta,
        chair_receipt=data["chair_receipt"],
    )


def load_manifest(repo_root: Path, tag: str) -> Manifest:
    """Read and validate the manifest for ``tag``."""
    target = manifest_path(repo_root, tag)
    if not target.is_file():
        raise ManifestError("no-manifest", f"no audit manifest for {tag} at {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ManifestError("unreadable", f"{target}: {exc}") from exc
    return validate_manifest(data)


def require_manifest(repo_root: Path, tag: str, head_sha: str) -> Manifest:
    """Gate for ``release-execute``: refuse a tag with no valid manifest.

    Also refuses a manifest recorded against a DIFFERENT commit — a
    ruling on an earlier SHA does not authorize the tag you are cutting
    now, which is the same binding rule the reconcile receipt uses.

    Raises:
        ManifestError: No manifest, an invalid one, one bound to another
            commit, or one whose chair left items blocked.

    """
    manifest = load_manifest(repo_root, tag)
    if manifest.head_sha != head_sha:
        raise ManifestError(
            "sha-mismatch",
            f"manifest rules on {manifest.head_sha[:9]}, tagging {head_sha[:9]}",
        )
    if manifest.blocked:
        raise ManifestError(
            "blocked-items",
            f"chair did not clear {len(manifest.blocked)}: {list(manifest.blocked)[:5]}",
        )
    return manifest
