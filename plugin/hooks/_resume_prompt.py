"""Resume-prompt builder — single source of truth for the format.

Both the Stop-hook compact warning and the ``/handoff`` slash
command call ``build_resume_prompt`` so the user sees identical
output whether the prompt was triggered automatically or on
demand.

Format: a Markdown blockquote that the user can paste into a
fresh Claude Code session to pick up where they left off.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import sys
from pathlib import Path

# Hooks are invoked as standalone scripts; ensure sibling helpers
# resolve regardless of how this module was loaded (script vs.
# pytest import vs. importlib).
_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _state import GitState, SpecInfo  # noqa: E402 — sys.path bootstrap above

# Hard cap on the rendered prompt — protects against pathological
# uncommitted-file lists or oversized commit subjects.
_MAX_PROMPT_BYTES = 4096

# Cap on the number of uncommitted files listed before truncation.
_MAX_UNCOMMITTED = 20


def _format_uncommitted(uncommitted: tuple[str, ...]) -> list[str]:
    """Render the uncommitted-file lines with truncation footer."""
    if not uncommitted:
        return []
    visible = list(uncommitted[:_MAX_UNCOMMITTED])
    lines = [f">   - {path}" for path in visible]
    leftover = len(uncommitted) - len(visible)
    if leftover > 0:
        lines.append(f">   - +{leftover} more")
    return lines


def _format_phase(spec: SpecInfo) -> str:
    """Human-readable ``Phase X (status)`` blurb for the spec."""
    phase_label = {
        "requirements": "Phase 1 (Requirements)",
        "design": "Phase 2 (Design)",
        "tasks": "Phase 3 (Tasks)",
    }.get(spec.phase, spec.phase)
    status = spec.status or "unknown"
    return f"{phase_label} — Status: {status}"


def _truncate(text: str) -> str:
    """Truncate to the byte cap with a footer, only if needed."""
    encoded = text.encode("utf-8")
    if len(encoded) <= _MAX_PROMPT_BYTES:
        return text
    footer = "\n> …(truncated)\n"
    budget = _MAX_PROMPT_BYTES - len(footer.encode("utf-8"))
    if budget <= 0:
        return text[:_MAX_PROMPT_BYTES]
    truncated = encoded[:budget].decode("utf-8", errors="ignore")
    return truncated + footer


def _read_current_task(spec: SpecInfo) -> str:
    """Pick a one-line ``current task`` derived from tasks.md.

    Strategy: scan ``tasks.md`` for the most-recent
    ``Status: completed`` row in the implementation table and
    quote the row's task description. Caller may override with a
    live TodoWrite snapshot via ``todo_summary`` when available.

    Returns an empty string when no completed task is found
    (e.g. spec is at requirements/design phase).
    """
    tasks_file = spec.path / "tasks.md"
    if not tasks_file.is_file():
        return ""
    try:
        text = tasks_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    last_completed = ""
    for line in text.splitlines():
        if "completed" not in line.lower():
            continue
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        # Expected layout: | # | Task | Status | Notes |
        status_cell = cells[2].lower() if len(cells) > 2 else ""
        if "completed" not in status_cell and "complete" not in status_cell:
            continue
        task_cell = cells[1]
        # Strip leading bold/markdown formatting for readability.
        task_cell = task_cell.replace("**", "").strip()
        if task_cell:
            last_completed = task_cell
    return last_completed


def build_resume_prompt(
    spec_info: SpecInfo | None,
    git_state: GitState,
    *,
    workspace_path: str = "~/attune",
    todo_summary: str | None = None,
) -> str:
    """Render the user-facing resume prompt body.

    Args:
        spec_info: Most-recent in-flight spec, or ``None`` for a
            generic fallback that points at the last commit.
        git_state: Branch / last-commit / uncommitted snapshot
            from ``_state.git_state``.
        workspace_path: Display path for the worktree (purely
            cosmetic — what the user pastes into a fresh session).
        todo_summary: Optional one-line ``current task`` override.
            When provided, takes precedence over the
            tasks.md-derived fallback.

    Returns:
        Markdown blockquote ending with a ``Pick up …`` line.
        Always under 4 kB.
    """
    branch = git_state.branch or "<unknown>"
    last_commit = ""
    if git_state.last_sha:
        subject = git_state.last_subject or "(no subject)"
        last_commit = f"`{git_state.last_sha} {subject}`"

    lines: list[str] = ["**Resume prompt for a fresh session:**", ""]
    blockquote: list[str] = [
        f"> Resume work in worktree `{workspace_path}` on branch `{branch}`.",
    ]
    if last_commit:
        blockquote.append(f"> Last commit: {last_commit}.")

    if spec_info is not None:
        blockquote.append(">")
        spec_relative = _spec_display_path(spec_info)
        blockquote.append(f"> Active spec: `{spec_relative}` — {_format_phase(spec_info)}.")
        current_task = todo_summary or _read_current_task(spec_info)
        if current_task:
            blockquote.append(f"> Current task: {current_task}")
        uncommitted_lines = _format_uncommitted(git_state.uncommitted)
        if uncommitted_lines:
            blockquote.append(">")
            blockquote.append("> Uncommitted:")
            blockquote.extend(uncommitted_lines)
        blockquote.append(">")
        blockquote.append(f"> Pick up where the spec left off in `{spec_relative}tasks.md`.")
    else:
        if todo_summary:
            blockquote.append(">")
            blockquote.append(f"> Current task: {todo_summary}")
        blockquote.append(">")
        blockquote.append("> No active spec; pick up from the last commit's diff.")

    lines.extend(blockquote)
    lines.append("")
    lines.append("(Copy the block above into a fresh Claude Code session.)")
    return _truncate("\n".join(lines))


def _spec_display_path(spec_info: SpecInfo) -> str:
    """Pretty-relative display path for a spec.

    Aims for ``specs/<slug>/`` (workspace) or
    ``<layer>/specs/<slug>/`` (layer-scoped). Falls back to the
    absolute path if the layout doesn't match.
    """
    parts = spec_info.path.parts
    try:
        idx = parts.index("specs")
    except ValueError:
        return str(spec_info.path)
    relative = "/".join(parts[idx:]) + "/"
    if spec_info.layer != "workspace":
        relative = f"{spec_info.layer}/{relative}"
        # Avoid duplicating the layer if it was already in parts.
        if Path(relative).parts.count(spec_info.layer) > 1:
            relative = "/".join(parts[idx:]) + "/"
    return relative
