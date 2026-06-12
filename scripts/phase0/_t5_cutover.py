"""One-shot T5 cutover executor (lessons-corpus-rag T5).

Moves the full Lessons corpus from .claude/CLAUDE.md to
.claude/lessons.md and rewrites CLAUDE.md with a mirrored
"Lessons — core" section (Patrick-ratified 20 items / 22 blocks).

Deleted after the cutover PR merges — kept in the PR for review of
exactly how the move was performed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO / ".claude" / "CLAUDE.md"
LESSONS_MD = REPO / ".claude" / "lessons.md"

# First-line anchors for the ratified core (distinctive substrings of
# each lesson's opening line). 20 ratified items; items 10 and 18 are
# explicitly two-facet -> 22 blocks.
CORE_ANCHORS = [
    # Tier 1 — high-severity
    "Read/head/cat on untracked",
    "Editor settings-sync is a silent",
    "A repo CI secret becoming VALID",
    "Keyless-CI-faithful local runs",
    "interrupted/rejected compound Bash",
    "user-rejected Edit tool call",
    "Branch-vs-worktree commit tangle",
    "to an absolute `/Users/patrickroebuck",
    "git stash pop` gotchas",
    "Admin-merging a deletion PR",
    "Admin-merging a PR before Windows lanes",
    # Tier 2 — session mechanics
    "The editable install's MAPPING",
    "Create a new worktree to continue last session",
    "pre-commit hook blocks",  # security_guard lesson
    "Harness safety classifier blocks bundled-destructive",
    "Pre-commit black/ruff/detect-secrets auto-fix",
    "regen pre-commit hook does a full LLM",
    # Tier 3 — kept fire-frequency
    'Diagnosing "this branch cannot be merged"',
    "Diagnosing CI from the `gh` CLI",
    "Verify-first applies to infra/config",
    "Registered ≠ working",
    "Spec-named work-scope drifts",
]

LESSONS_PREAMBLE = """# Lessons

The complete engineering-lessons corpus for attune-ai. This file is
deliberately NOT auto-loaded into Claude Code sessions; it is served
on demand by `attune.lessons.LessonsIndex` via `/recall <topic>`, the
UserPromptSubmit lesson-recall hook, and jit-recall `lesson_ref`s.

APPEND NEW LESSONS HERE (same `- **title**:` bullet format). The
~20 always-loaded core lessons in `.claude/CLAUDE.md` are verbatim
MIRRORS of entries in this file — this file is canonical; a
drift-guard test (`tests/unit/lessons/test_core_mirror.py`) fails if
a core mirror diverges. If you edit a core lesson, edit it in BOTH
files.
"""

CORE_HEADER = """## Lessons — core

The always-loaded core (Patrick-ratified 2026-06-12): high-severity
classes, session mechanics that fire before retrieval could, and the
highest fire-frequency judgment rules. The FULL corpus (380+ lessons)
lives in [.claude/lessons.md](lessons.md) — canonical source; these
entries are verbatim mirrors, drift-guarded by
`tests/unit/lessons/test_core_mirror.py`.

Query the tail with `/recall <topic>`; relevant lessons also surface
automatically at prompt time and at tool-call decision points.
APPEND NEW LESSONS to `.claude/lessons.md`, not here — mirror into
this section only if core-worthy (and then keep both copies in sync).
"""


def split_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Return (start, end) line-index ranges of top-level lesson blocks."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith("- **")]
    blocks = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(lines)
        # a block also ends at an intervening ### heading
        for j in range(s + 1, e):
            if lines[j].startswith("### "):
                e = j
                break
        blocks.append((s, e))
    return blocks


def main() -> int:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Locate the section: orphan marker line, then "## Lessons Learned".
    marker_idx = next(
        i for i, ln in enumerate(lines) if ln.strip() == "<!-- attune-lessons-start -->"
    )
    heading_idx = next(i for i, ln in enumerate(lines) if ln.strip() == "## Lessons Learned")
    assert heading_idx > marker_idx, "unexpected layout"

    head = lines[:marker_idx]  # everything before the orphan marker
    body = lines[heading_idx + 1 :]  # the corpus, sans heading

    blocks = split_blocks(body)
    print(f"corpus blocks found: {len(blocks)}")

    # Match each anchor to exactly one block (by its first line).
    core: list[tuple[int, int]] = []
    for anchor in CORE_ANCHORS:
        hits = [b for b in blocks if anchor in body[b[0]]]
        if len(hits) != 1:
            print(f"ANCHOR FAIL: {anchor!r} -> {len(hits)} hits", file=sys.stderr)
            return 1
        core.append(hits[0])
    # de-dup + keep corpus order
    core = sorted(set(core))
    print(f"core blocks selected: {len(core)}")

    # lessons.md: preamble + the full body verbatim.
    body_text = "\n".join(body).strip("\n")
    LESSONS_MD.write_text(
        LESSONS_PREAMBLE + "\n## Lessons Learned\n\n" + body_text + "\n",
        encoding="utf-8",
    )

    # CLAUDE.md: head + core section.
    core_texts = []
    for s, e in core:
        block = "\n".join(body[s:e]).rstrip("\n")
        core_texts.append(block)
    new_claude = (
        "\n".join(head).rstrip("\n") + "\n\n" + CORE_HEADER + "\n" + "\n\n".join(core_texts) + "\n"
    )
    # normalize: no triple blank lines
    new_claude = re.sub(r"\n{3,}", "\n\n", new_claude)
    CLAUDE_MD.write_text(new_claude, encoding="utf-8")

    print(f"lessons.md lines: {len(LESSONS_MD.read_text().splitlines())}")
    print(f"CLAUDE.md lines:  {len(new_claude.splitlines())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
