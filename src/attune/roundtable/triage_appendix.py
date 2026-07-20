"""Briefing→table triage appendix to the weekly clean-run (T4, armed).

Chartered in q-briefing-triage-001 (T4: appendix, not a new routine),
validated manually n=1 (2026-07-19) and n=2 (2026-07-20), armed
headless by chair ruling 2026-07-20 ("T4 y"). Contract details in
docs/specs/roundtable-triage/requirements.md; rulings in its
decisions.md.

Shape per the ruled contract:

- Briefing pull is READ-ONLY and free — the curator source readers,
  the gate verdict ledger, and usage.jsonl freshness. NO LLM curation
  pass (T3: no standing scheduled LLM spend); empty sources render
  "dark" honestly instead of being refreshed with paid sweeps.
- Distillation is DETERMINISTIC, capped at 5 items; anything dropped
  by the cap is named in the brief (no silent caps).
- The appendix posts to the SAME clean-run thread (one weekly ruling
  sitting) with its own seat round + synthesis, under its own
  invocation sub-cap (the combined run stays under the chair-ruled
  R5 ceiling of 10).
- Auto-demote (T4): after two consecutive digests whose RECORDED
  ruling count is zero, the appendix stops running headless and
  reports itself demoted to chair-invoked. Unrecorded outcomes never
  demote (conservative).
- The runner never promotes (R8).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import datetime
import importlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: Deterministic distillation cap (T4).
MAX_ITEMS = 5

#: Appendix invocation sub-cap: 3 seats + 1 synthesis.
APPENDIX_MAX_INVOCATIONS = 4

#: Kill switch — set to "off" to skip the appendix without editing code.
KILL_SWITCH_ENV = "ATTUNE_TRIAGE_APPENDIX"

#: Curator sources pulled for the briefing (read-only, no LLM).
SOURCE_NAMES = (
    "bulletin",
    "diagnoses",
    "git_state",
    "recommendations",
    "spec_drift",
    "specs",
    "sweep",
    "telemetry",
)

#: Sources whose emptiness is rendered as "dark" (T3) rather than
#: treated as a decidable item.
DARK_RENDER_SOURCES = frozenset({"bulletin", "git_state", "recommendations", "sweep", "telemetry"})


@dataclass
class TriageItem:
    """One decidable briefing item put to the table."""

    title: str
    evidence: str
    question: str


def _state_path() -> Path:
    attune_dir = Path(os.environ.get("ATTUNE_HOME", str(Path.home() / ".attune")))
    return attune_dir / "ops" / "triage_appendix.json"


def _load_state(path: Path | None = None) -> dict[str, object]:
    p = path or _state_path()
    if not p.is_file():
        return {"digests": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("triage appendix: unreadable state %s: %s", p, exc)
        return {"digests": []}
    return data if isinstance(data, dict) else {"digests": []}


def _save_state(state: dict[str, object], path: Path | None = None) -> None:
    p = path or _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def is_demoted(path: Path | None = None) -> bool:
    """T4 auto-demote: two consecutive RECORDED zero-ruling digests."""
    digests = _load_state(path).get("digests")
    if not isinstance(digests, list) or len(digests) < 2:
        return False
    last_two = digests[-2:]
    return all(isinstance(d, dict) and d.get("rulings") == 0 for d in last_two)


def record_digest(thread: str, items: int, *, path: Path | None = None) -> None:
    """Append one digest record with an unrecorded (null) ruling count."""
    state = _load_state(path)
    digests = state.setdefault("digests", [])
    assert isinstance(digests, list)
    digests.append(
        {
            "thread": thread,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "items": items,
            "rulings": None,
        }
    )
    _save_state(state, path)


def record_rulings(thread: str, rulings: int, *, path: Path | None = None) -> bool:
    """Record the chair's ruling count for a digest (the demotion input).

    Called by the interactive ruling session when promoting. Returns
    True when the thread's record was found and updated.
    """
    state = _load_state(path)
    digests = state.get("digests")
    if not isinstance(digests, list):
        return False
    for record in reversed(digests):
        if isinstance(record, dict) and record.get("thread") == thread:
            record["rulings"] = rulings
            _save_state(state, path)
            return True
    return False


def pull_briefing(project_root: Path) -> tuple[list[TriageItem], list[str], list[str]]:
    """Read-only briefing pull: (candidate items, dark sources, extra evidence).

    Sources must not raise (their contract); a reader that does is
    reported as unreadable evidence rather than crashing the routine.
    """
    candidates: list[TriageItem] = []
    dark: list[str] = []
    extra: list[str] = []
    for name in SOURCE_NAMES:
        try:
            mod = importlib.import_module(f"attune.curator.sources.{name}")
            summary = mod.read(project_root=project_root)
            items = list(summary.items)
        except Exception as exc:  # noqa: BLE001 — appendix must not kill the routine
            logger.warning("triage appendix: source %s failed: %s", name, exc)
            extra.append(f"source {name}: UNREADABLE ({exc})")
            continue
        if not items:
            if name in DARK_RENDER_SOURCES:
                dark.append(name)
            continue
        if name in ("spec_drift", "diagnoses"):
            for item in items:
                candidates.append(
                    TriageItem(
                        title=str(getattr(item, "title", item)),
                        evidence=str(getattr(item, "detail", "")),
                        question="Recommend a disposition with a one-line rationale.",
                    )
                )
    extra.extend(_gate_ledger_evidence())
    extra.append(_usage_freshness_evidence())
    return candidates, dark, extra


def _gate_ledger_evidence() -> list[str]:
    """Gate-verdict input: local ledger read; honest darkness otherwise.

    Per the A4 ruling the durable input is a CI-artifact fetch at
    render time; until that follow-on lands, the local ledger (dark by
    construction — D7 runs the gates CI-only) is rendered honestly.
    """
    try:
        from attune.gates.lifecycle import ledger  # noqa: PLC0415

        path = ledger.ledger_path()
        if not path.is_file():
            return [f"gate verdict ledger: dark (no local ledger at {path}; A4 CI fetch pending)"]
        unresolved = ledger.unresolved_chair_required()
        if unresolved:
            return [
                "gate verdict ledger: "
                f"{len(unresolved)} unresolved CHAIR_REQUIRED receipt(s): "
                + "; ".join(f"{r.gate_id}:{r.target}" for r in unresolved[:5])
            ]
        return ["gate verdict ledger: present, no unresolved CHAIR_REQUIRED receipts"]
    except Exception as exc:  # noqa: BLE001 — evidence, not a crash point
        return [f"gate verdict ledger: UNREADABLE ({exc})"]


def _usage_freshness_evidence() -> str:
    """Local spend/freshness line: usage.jsonl last-write age."""
    attune_dir = Path(os.environ.get("ATTUNE_HOME", str(Path.home() / ".attune")))
    usage = attune_dir / "telemetry" / "usage.jsonl"
    if not usage.is_file():
        return "local spend: dark (no usage.jsonl)"
    age_h = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.datetime.fromtimestamp(usage.stat().st_mtime, tz=datetime.timezone.utc)
    ).total_seconds() / 3600
    return f"local spend: usage.jsonl last write {age_h:.0f}h ago"


def distill(candidates: list[TriageItem]) -> tuple[list[TriageItem], int]:
    """Deterministic cap at MAX_ITEMS; returns (kept, dropped_count)."""
    return candidates[:MAX_ITEMS], max(0, len(candidates) - MAX_ITEMS)


def compose_brief(
    items: list[TriageItem],
    dark: list[str],
    extra: list[str],
    dropped: int,
    stamp: str,
) -> str:
    """The n=1/n=2 brief shape, composed deterministically."""
    lines = [
        "APPENDIX — briefing triage (T4 headless; the chair rules "
        "per-item after your deliberation; recommend, do not execute; "
        "compress his decisions, do not multiply them). Standing "
        "rulings in docs/specs/roundtable-triage/decisions.md are "
        "NOT to be re-litigated. For EACH item give a concrete "
        "recommendation with a one-line rationale, then the main "
        "RISK of your triage.",
        "",
        f"Briefing evidence gathered read-only {stamp}.",
        "Dark sources (T3, rendered honestly, no refresh spend): "
        + (", ".join(dark) if dark else "none"),
        *extra,
        "",
    ]
    for i, item in enumerate(items, 1):
        lines += [
            f"ITEM {i} — {item.title}",
            f"  evidence: {item.evidence[:500]}",
            f"  QUESTION: {item.question}",
            "",
        ]
    if dropped:
        lines.append(f"(cap: {dropped} further candidate item(s) dropped — named, not silent)")
    return "\n".join(lines)


def run_triage_appendix(
    board,
    thread: str,
    project_root: Path,
    invoke_seat,
    seat_recipes,
    *,
    state_path: Path | None = None,
) -> int:
    """Run the appendix on an existing clean-run thread; return invocations used.

    Returns 0 without any board write or LLM invocation when the kill
    switch is off, the appendix is demoted, or the briefing has zero
    decidable items (each is printed, so a silent skip is impossible).
    """
    if os.environ.get(KILL_SWITCH_ENV, "").lower() == "off":
        print("  appendix: skipped (kill switch)", flush=True)
        return 0
    if is_demoted(state_path):
        print(
            "  appendix: DEMOTED to chair-invoked (two consecutive "
            "zero-ruling digests, T4) — not running",
            flush=True,
        )
        return 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    candidates, dark, extra = pull_briefing(project_root)
    items, dropped = distill(candidates)
    if not items:
        print("  appendix: 0 decidable items — skipped (no spend)", flush=True)
        record_digest(thread, 0, path=state_path)
        board.post_message(
            thread,
            "moderator",
            "appendix",
            f"Triage appendix {stamp}: 0 decidable items in the briefing "
            f"(dark: {', '.join(dark) if dark else 'none'}). No seats convened.",
            appendix="triage",
        )
        return 0
    brief = compose_brief(items, dark, extra, dropped, stamp)
    board.post_message(thread, "moderator", "question", brief, appendix="triage")

    invocations = 0
    positions: list[tuple[str, str]] = []
    for seat, recipe in seat_recipes:
        if invocations >= APPENDIX_MAX_INVOCATIONS - 1:
            board.post_message(
                thread,
                "moderator",
                "halt",
                f"appendix invocation sub-cap before seat {seat!r}",
                appendix="triage",
            )
            break
        invocations += 1
        print(f"  appendix seat {seat} ... briefing", flush=True)
        code, reply = invoke_seat(recipe, brief)
        if code != 0 or not reply.strip():
            print(f"  appendix seat {seat}: ABSENT (exit {code})", flush=True)
            board.post_message(
                thread,
                seat,
                "position",
                f"ABSENT — exit {code}: {reply[:200]}",
                absent=True,
                appendix="triage",
            )
            continue
        print(f"  appendix seat {seat}: position posted", flush=True)
        board.post_message(thread, seat, "position", reply, appendix="triage")
        positions.append((seat, reply))

    if positions:
        invocations += 1
        synthesis_brief = (
            "You are the moderator of the triage appendix. Synthesize the "
            "seat positions below per item: agreement counts, divergences "
            "with the recorded evidence that resolves them, and a "
            "per-item recommendation line the chair can rule on with "
            "shorthand. Compact. Text only.\n\n"
            + "\n\n".join(f"## {seat}\n{reply}" for seat, reply in positions)
        )
        print("  appendix synthesis ... running", flush=True)
        code, digest = invoke_seat(("claude", "-p", "{brief}"), synthesis_brief)
        if code == 0 and digest.strip():
            board.post_message(thread, "moderator", "synthesis", digest, appendix="triage")
            print("  appendix synthesis: posted", flush=True)
        else:
            board.post_message(
                thread,
                "moderator",
                "halt",
                f"appendix synthesis failed (exit {code}): {digest[:200]}",
                appendix="triage",
            )
            print(f"  appendix synthesis: FAILED (exit {code})", flush=True)

    record_digest(thread, len(items), path=state_path)
    print(
        f"  appendix complete: {len(items)} item(s), {invocations} invocation(s); "
        "record rulings with attune.roundtable.triage_appendix.record_rulings() "
        "when promoting (T4 demotion input).",
        flush=True,
    )
    return invocations
