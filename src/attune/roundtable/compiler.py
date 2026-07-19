"""Artifact compiler + proposal ledger — round-table V2-P2.

Codifies what the first real spec-authoring loop (thread
``mem-signal-001``, ``docs/specs/memory-feedback-signal/``) did by
hand: typed round contracts the moderator can LINT before posting
(TR-4's mechanical gate applied to spec loops), a deterministic
parser from the drafter's final document into per-item structures,
an objection ledger linking critique items to the requirements they
attack, and a deterministic assembly step that turns chair rulings
into a tracked ``requirements.md`` — models produce content, the
compiler produces the file.

Field-note fix carried from V2-P1: output budgets are ROLE-AWARE
(:data:`ROLE_REPLY_CHARS`) — a drafter's document and a critic's
position have different size envelopes; the flat per-seat cap
truncated the first live revision mid-document.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Role-aware output budgets (chars) for seat invocations in a spec
#: loop. The runner's flat seat cap suits routine positions; spec
#: loops pass the role's budget instead.
ROLE_REPLY_CHARS = {
    "position": 8_000,
    "critic": 16_000,
    "drafter": 40_000,
}

#: Convergence tags the round-3 contract admits, in the normalized
#: form the V2-P1 loop settled on (``(table: ...)``) and the raw
#: bracket form the drafter emits (``[tag: ...]``).
_TAG_RE = re.compile(
    r"^[\[(](?:table:|tag:)\s*(?P<tag>agreed[^\])]*|2-1[^\])]*|contested[^\])]*)[\])]",
    re.IGNORECASE,
)

#: A requirement heading: ``**MI-1 — title...**`` (any 2+ uppercase
#: prefix; the id grammar is shared by draft and final contracts).
_ITEM_RE = re.compile(r"^\*\*(?P<id>[A-Z]{2,}-\d+)\s*—\s*(?P<title>.+?)\*\*$")

#: A critique line naming its target: ``**MI-3:**`` / ``**MI-1 —``,
#: or the explicit gap marker ``**MISSING``.
_CRITIQUE_TARGET_RE = re.compile(r"\*\*(?P<id>[A-Z]{2,}-\d+|MISSING)\b")

_VERDICT_RE = re.compile(r"^VERDICT:\s*(?P<verdict>ready-with-edits|needs-revision)", re.MULTILINE)


@dataclass
class SpecItem:
    """One parsed requirement item from a drafter document."""

    item_id: str
    title: str
    body: str
    tag: str = ""  # agreed | 2-1 ... | contested ... (final round only)
    objections: list[str] = field(default_factory=list)
    chair_status: str = "pending"  # pending | approved | declined


@dataclass
class SpecDraft:
    """A parsed drafter document (round 1 or round 3)."""

    items: list[SpecItem]
    non_goals: str = ""
    dissent_register: str = ""
    open_questions: str = ""

    def item(self, item_id: str) -> SpecItem | None:
        """Return the item with ``item_id``, or None."""
        return next((i for i in self.items if i.item_id == item_id), None)


def _sections(text: str) -> dict[str, str]:
    """Split a document on ``## `` headings; keys are lowered titles."""
    out: dict[str, str] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            out[current] = ""
        elif current:
            out[current] += line + "\n"
    return out


def _section(sections: dict[str, str], prefix: str) -> str:
    """First section whose title starts with ``prefix`` (else '')."""
    return next((v.strip() for k, v in sections.items() if k.startswith(prefix)), "")


def parse_draft(text: str) -> SpecDraft:
    """Parse a drafter document into items + sections.

    Works for both the round-1 draft and the round-3 final: items are
    ``**XX-N — title**`` blocks; a trailing tag line (``[tag: ...]``
    or ``(table: ...)``) is captured when present.
    """
    sections = _sections(text)
    req_text = _section(sections, "requirements") or text
    items: list[SpecItem] = []
    current: SpecItem | None = None
    body_lines: list[str] = []

    def _flush() -> None:
        if current is not None:
            current.body = "\n".join(body_lines).strip()
            items.append(current)

    for line in req_text.splitlines():
        stripped = line.strip()
        m = _ITEM_RE.match(stripped)
        if m:
            _flush()
            current = SpecItem(item_id=m.group("id"), title=m.group("title").strip(), body="")
            body_lines = []
            continue
        t = _TAG_RE.match(stripped)
        if t and current is not None:
            current.tag = t.group("tag").strip()
            continue
        if current is not None:
            body_lines.append(line)
    _flush()

    return SpecDraft(
        items=items,
        non_goals=_section(sections, "non-goals"),
        dissent_register=_section(sections, "dissent register"),
        open_questions=_section(sections, "open questions"),
    )


def lint_draft(text: str) -> list[str]:
    """Round-1 contract: numbered items with acceptance bullets."""
    problems: list[str] = []
    draft = parse_draft(text)
    if not draft.items:
        problems.append("no requirement items found (expected **XX-N — title** blocks)")
    for item in draft.items:
        if "- " not in item.body:
            problems.append(f"{item.item_id}: no acceptance-criteria bullets")
    if not draft.non_goals:
        problems.append("missing '## Non-goals' section")
    return problems


def lint_critique(text: str) -> list[str]:
    """Round-2 contract: targeted, cited items plus a VERDICT line.

    The citation check is TR-4's mechanical floor: every critique
    item must reference the grounding pack or a concrete path — an
    item with neither is rejected before posting.
    """
    problems: list[str] = []
    item_blocks = re.split(r"\n(?=\d+\.\s)", text.strip())
    targeted = [b for b in item_blocks if _CRITIQUE_TARGET_RE.search(b)]
    if not targeted:
        problems.append("no critique items naming an item id or MISSING")
    for block in targeted:
        head = block.strip().splitlines()[0][:60]
        if not re.search(r"\bpack\b|\bpack item\b|[\w/]+\.(?:py|md)\b", block, re.IGNORECASE):
            problems.append(f"uncited critique item (no pack/file reference): {head!r}")
    if not _VERDICT_RE.search(text):
        problems.append("missing 'VERDICT: ready-with-edits | needs-revision' line")
    return problems


def lint_final(text: str) -> list[str]:
    """Round-3 contract: every item tagged; dissent present or attested."""
    problems: list[str] = []
    draft = parse_draft(text)
    if not draft.items:
        problems.append("no requirement items found")
    for item in draft.items:
        if not item.tag:
            problems.append(f"{item.item_id}: missing convergence tag (agreed / 2-1 / contested)")
    register = draft.dissent_register.lower()
    if not register:
        problems.append("missing '## Dissent register' section")
    elif "empty" in register and "attested" not in register:
        problems.append("dissent register claims empty without attestation")
    has_dissent_tag = any(i.tag and not i.tag.lower().startswith("agreed") for i in draft.items)
    if has_dissent_tag and (not register or len(register) < 40):
        problems.append("2-1/contested items present but the dissent register is empty")
    return problems


def critique_verdict(text: str) -> str | None:
    """Return the critique's VERDICT value, or None when absent."""
    m = _VERDICT_RE.search(text)
    return m.group("verdict") if m else None


def link_critiques(draft: SpecDraft, critiques: dict[str, str]) -> SpecDraft:
    """Attach each critique item to the requirement it targets (ledger).

    Args:
        draft: The parsed draft whose items receive objections.
        critiques: Mapping of critic seat name to critique text.

    Returns:
        The same draft, with ``item.objections`` populated as
        ``"<seat>: <first line of the critique item>"`` entries.
        ``MISSING``-targeted items have no owning requirement and are
        skipped here — they surface via the critique text itself.
    """
    for seat, text in critiques.items():
        for block in re.split(r"\n(?=\d+\.\s)", text.strip()):
            m = _CRITIQUE_TARGET_RE.search(block)
            if not m or m.group("id") == "MISSING":
                continue
            item = draft.item(m.group("id"))
            if item is None:
                continue
            first_line = block.strip().splitlines()[0].strip()
            item.objections.append(f"{seat}: {first_line}")
    return draft


def compile_requirements(
    draft: SpecDraft,
    *,
    spec_title: str,
    thread: str,
    rulings: dict[str, str],
    ruling_note: str = "",
) -> str:
    """Deterministically assemble the chair-ruled ``requirements.md``.

    Only ``approved`` items land in the Requirements section;
    declined items are recorded by id in the provenance header so
    the file is honest about what the chair rejected (the ledger's
    chair-status column, materialized).

    Args:
        draft: Parsed (and optionally critique-linked) final draft.
        spec_title: Human title for the H1.
        thread: Board thread id (provenance — TR/R10).
        rulings: ``item_id -> "approved" | "declined"``; missing ids
            stay ``pending`` and are excluded with a warning line.
        ruling_note: Optional chair-ruling sentence for the header.
    """
    for item in draft.items:
        item.chair_status = rulings.get(item.item_id, "pending")
    approved = [i for i in draft.items if i.chair_status == "approved"]
    declined = [i.item_id for i in draft.items if i.chair_status == "declined"]
    pending = [i.item_id for i in draft.items if i.chair_status == "pending"]

    lines = [
        f"# {spec_title} — Requirements",
        "",
        "**Status: requirements chair-ruled per item** — authored by the",
        f"round table (thread `{thread}`); compiled deterministically by",
        "`attune.roundtable.compiler` (V2-P2). Approved items only;",
        f"declined: {', '.join(declined) if declined else 'none'};",
        f"unruled: {', '.join(pending) if pending else 'none'}.",
    ]
    if ruling_note:
        lines += ["", ruling_note]
    lines += ["", "## Requirements", ""]
    for item in approved:
        lines.append(f"**{item.item_id} — {item.title}**")
        if item.body:
            lines.append(item.body)
        lines.append(f"(table: {item.tag or 'untagged'}; chair: approved)")
        lines.append("")
    if draft.non_goals:
        lines += ["## Non-goals", "", draft.non_goals, ""]
    if draft.dissent_register:
        lines += ["## Dissent register", "", draft.dissent_register, ""]
    return "\n".join(lines).rstrip() + "\n"
