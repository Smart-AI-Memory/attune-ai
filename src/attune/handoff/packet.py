"""Handoff packet assembly, rendering, parsing, and caps.

Design D1/D4 (docs/specs/cross-provider-session-handoff/design.md):
the packet file is the contract template's markdown body (ASSERTED,
caller-supplied) under a machine-readable frontmatter block
(VERIFIED, git-derived). Caps reject oversize input with the limit
named — never silent truncation (R5).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

#: D4 caps — reject-with-reason, never truncate.
PACKET_CAP_BYTES = 8192
FIELD_CAP_BYTES = 2048

_FRONTMATTER_MARK = "---"

#: (field key, template heading) in contract-template order. Only
#: sections with content render (R5).
SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("goal", "Goal"),
    ("acceptance_criteria", "Acceptance criteria"),
    ("scope_assumptions", "Scope and assumptions"),
    ("current_state", "Current state"),
    ("verification", "Verification"),
    ("next_action", "Next action"),
)

_ASSERTED_TEXT_FIELDS = (
    "goal",
    "acceptance_criteria",
    "scope_assumptions",
    "current_state",
    "next_action",
)


class PacketError(ValueError):
    """Invalid packet input (caps, bad slug, malformed file)."""


def check_caps(fields: dict[str, Any]) -> dict[str, Any] | None:
    """Return an ``{ok: False}`` rejection dict when a cap is hit."""
    for name in _ASSERTED_TEXT_FIELDS:
        value = fields.get(name) or ""
        if len(value.encode("utf-8")) > FIELD_CAP_BYTES:
            return {
                "ok": False,
                "reason": "field_over_cap",
                "field": name,
                "limit": FIELD_CAP_BYTES,
            }
    return None


def _normalize_verification(rows: Any) -> list[dict[str, str]]:
    """R1: rows record only probes actually run; default is ``not run``."""
    normalized: list[dict[str, str]] = []
    for row in rows or []:
        normalized.append(
            {
                "claim": str(row.get("claim", "")),
                "probe": str(row.get("probe", "")),
                "result": str(row.get("result") or "not run"),
            }
        )
    return normalized


def render(meta: dict[str, Any], sections: dict[str, Any]) -> str:
    """Render frontmatter + template-shaped markdown body."""
    lines: list[str] = [_FRONTMATTER_MARK]
    for key in sorted(meta):
        lines.append(f"{key}: {json.dumps(meta[key], ensure_ascii=False)}")
    lines.append(_FRONTMATTER_MARK)
    lines.append("")
    lines.append("# Agent work handoff")
    for key, heading in SECTION_ORDER:
        value = sections.get(key)
        if not value:
            continue
        lines.append("")
        lines.append(f"## {heading}")
        lines.append("")
        if key == "verification":
            lines.append("| Claim | Failure-sensitive probe | Result |")
            lines.append("| --- | --- | --- |")
            for row in value:
                lines.append(f"| {row['claim']} | {row['probe']} | {row['result']} |")
        else:
            lines.append(str(value).rstrip())
    return "\n".join(lines) + "\n"


def parse(text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse a packet file into (meta, sections).

    Raises:
        PacketError: when the frontmatter block is missing or a
            line is malformed.

    """
    lines = text.splitlines()
    if not lines or lines[0] != _FRONTMATTER_MARK:
        raise PacketError("missing frontmatter")
    meta: dict[str, Any] = {}
    body_start = None
    for i, line in enumerate(lines[1:], start=1):
        if line == _FRONTMATTER_MARK:
            body_start = i + 1
            break
        key, sep, raw = line.partition(": ")
        if not sep:
            raise PacketError(f"malformed frontmatter line: {line!r}")
        try:
            meta[key] = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PacketError(f"malformed frontmatter value for {key!r}") from exc
    if body_start is None:
        raise PacketError("unterminated frontmatter")

    sections: dict[str, Any] = {}
    heading_to_key = {heading: key for key, heading in SECTION_ORDER}
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current is not None:
            sections[current] = "\n".join(buffer).strip()

    for line in lines[body_start:]:
        if line.startswith("## "):
            flush()
            current = heading_to_key.get(line[3:].strip())
            buffer = []
        elif current is not None:
            buffer.append(line)
    flush()
    return meta, sections


def validate_slug(slug: str) -> str:
    """Reject slugs that could escape ``docs/handoffs/``."""
    if not slug or "/" in slug or "\\" in slug or ".." in slug or slug.startswith("."):
        raise PacketError(f"invalid handoff slug: {slug!r}")
    return slug


def packet_path(repo_root: Path, slug: str) -> Path:
    """Validated packet location under the contract's handoffs dir."""
    validate_slug(slug)
    root = repo_root.resolve()
    path = (root / "docs" / "handoffs" / f"{slug}.md").resolve()
    if root not in path.parents:
        raise PacketError(f"packet path escapes repo root: {path}")
    return path


def write_packet(
    repo_root: Path, slug: str, meta: dict[str, Any], sections: dict[str, Any]
) -> dict[str, Any]:
    """Render and durably write the packet; truthful on failure (R1).

    Overwrites in place (one packet per branch, D4); a previous
    packet's ``created_at`` is preserved as ``superseded_at``.
    """
    try:
        path = packet_path(repo_root, slug)
    except PacketError as exc:
        return {"ok": False, "reason": "invalid_slug", "detail": str(exc)}

    if path.exists():
        try:
            old_meta, _ = parse(path.read_text(encoding="utf-8"))
            if old_meta.get("created_at"):
                meta = {**meta, "superseded_at": old_meta["created_at"]}
        except (OSError, PacketError):
            logger.warning("handoff_previous_packet_unreadable", path=str(path))

    rendered = render(meta, sections)
    if len(rendered.encode("utf-8")) > PACKET_CAP_BYTES:
        return {
            "ok": False,
            "reason": "packet_over_cap",
            "limit": PACKET_CAP_BYTES,
        }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        logger.warning("handoff_write_denied", path=str(path), error=str(exc))
        return {"ok": False, "reason": "write_denied", "detail": str(exc)}
    return {"ok": True, "path": str(path)}


def assemble_sections(fields: dict[str, Any]) -> dict[str, Any]:
    """Build the ASSERTED body sections from caller fields."""
    sections: dict[str, Any] = {}
    for name in _ASSERTED_TEXT_FIELDS:
        if fields.get(name):
            sections[name] = str(fields[name])
    rows = _normalize_verification(fields.get("verification"))
    if rows:
        sections["verification"] = rows
    return sections
