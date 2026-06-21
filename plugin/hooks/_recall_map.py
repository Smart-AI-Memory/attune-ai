"""Curated decision-point -> rule map for just-in-time recall.

The single reviewable source for which durable rules surface at which
tool-call decision points (docs/specs/just-in-time-recall/, decision
D3). Keyed by tool name; valued by short ``{rule_id, text}`` entries.

Authoring rules:

- ``text`` is a distilled ONE-LINER nudge (decision D4) — the full
  lesson stays in ``.claude/CLAUDE.md`` / the ``feedback_*`` memories
  as the source of truth.
- Only instrument genuine, observed slip-points (R3: low noise).
  Growing this map is deliberate, diff-reviewed work — not a dumping
  ground for every lesson.
- ``rule_id`` is stable and filesystem-safe (it keys the per-session
  surface-once sentinel).
- Optional ``match_substring`` scopes a rule to tool calls whose
  serialized ``tool_input`` contains the substring — REQUIRED for
  broad tools like ``Bash`` so the rule fires only at the actual
  decision point, not on the session's first bash call.
- Optional ``lesson_ref`` names a lessons-corpus slug (an
  ``attune.lessons`` entry path like ``tag-mechanics-….md``); the
  hook resolves it through ``LessonsIndex`` at fire time and appends
  an excerpt of the CURRENT lesson body below the one-liner, so the
  nudge never drifts from the corpus. Resolution is best-effort —
  older installs without ``attune.lessons`` fall back to the
  one-liner alone. Slugs derive from lesson titles: a title edit
  changes the slug (the drift-guard test in
  ``test_jit_recall.py`` catches a dangling ref).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

RECALL_MAP: dict[str, list[dict[str, str]]] = {
    # Proof case (R6): the question-shape rule was stored in two places
    # on 2026-06-03 and still slipped three times mid-session.
    "AskUserQuestion": [
        {
            "rule_id": "question-shape",
            "text": (
                "Question-shape rule: ask ONE question per turn; lead with "
                "your recommendation as the FIRST option, its label ending "
                "in '(Recommended)'; options concise and directly "
                "selectable — no and/or bundles, no buried prose."
            ),
        },
    ],
    # Release tagging (added 2026-06-10): tags cut from the wrong ref
    # have shipped before (attune-rag 0.5.0 — a late branch push missed
    # the merge SHA and auto-published unpolished content).
    "Bash": [
        {
            "rule_id": "release-verify-merge-sha",
            "match_substring": "gh release create",
            "lesson_ref": (
                "tag-mechanics-push-protection-squash-timing-" "and-the-auto-release-body.md"
            ),
            "text": (
                "Before `gh release create`: verify the release content "
                "is IN the target commit (`git show <sha>:pyproject.toml "
                "| grep version`; changelog section present) and pass the "
                "FULL 40-char merge SHA via --target, never a branch name."
            ),
        },
        # Commit-didn't-land dance (T2.1, added 2026-06-20): pre-commit
        # auto-fixers re-stage files and `commit -q` can exit 0 yet skip
        # the commit — a repeated, silent slip across release sessions.
        {
            "rule_id": "git-commit-verify-landed",
            "match_substring": "git commit",
            "text": (
                "After `git commit`, verify it LANDED (`git log --oneline "
                "-1` / `git status --short`) — pre-commit auto-fixers can "
                "leave files re-staged and `git commit -q` can exit 0 yet "
                "SKIP the commit. Pre-flight the PINNED black/ruff before "
                "`git add` so the hooks see already-clean files."
            ),
        },
        # Admin-merge already-merged trap (T2.1, added 2026-06-20): the
        # local post-merge step errors even when the remote merge
        # succeeded; a blind retry 404s because the PR is already merged.
        {
            "rule_id": "admin-merge-verify-remote",
            "match_substring": "pr merge",
            "text": (
                "`gh pr merge --admin` can error from the LOCAL post-merge "
                "step even when the REMOTE merge SUCCEEDED — verify `gh pr "
                "view <n> --json state,mergedAt,mergeCommit` before "
                "retrying; a retry 404s because it is already merged."
            ),
        },
        # Rebase drops GPG signatures (T2.1, added 2026-06-20): replayed
        # commits come back unsigned; pushing them loses the signature.
        {
            "rule_id": "rebase-resigns-gpg",
            "match_substring": "rebase",
            "text": (
                "Rebase (and `git pull --rebase`) REPLAYS commits "
                "UNSIGNED — re-sign with `git commit --amend -S "
                "--no-edit` (or re-sign the replayed range) before "
                "pushing, or the pushed commits lose their GPG signature."
            ),
        },
    ],
}
