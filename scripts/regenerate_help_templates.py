#!/usr/bin/env python3
"""Pre-commit hook: regenerate `.help/templates/<feature>/` for changed source.

Runs `attune-author generate <feature> --all-kinds` for every feature
whose source files were modified in the current commit, then stages
the regenerated template directories so they land in the same commit
as the source change.

Gated on `ATTUNE_DOCS_AUTOREGEN=1` (matching the precedent set by
`scripts/check_docs_freshness.py`). Default mode is warn-only — the
hook prints which features are stale and exits 0 without modifying
the tree. Users opt in by setting the env var (typically in shell
profile) so the auto-regen is per-user, not per-repo.

Failure modes never block the commit:

- `attune-author` not installed → silent exit 0
- `.help/features.yaml` missing → silent exit 0
- Per-feature regen failure → log to stderr, continue with others
- `git add` failure → log to stderr, continue

Pre-commit passes changed file paths on argv. Empty argv → exit 0.

Spec: docs/specs/ops-specs-completion-candidates/ — companion to the
post-merge follow-up captured in PR #400's process notes.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a POSIX-style glob to a fullmatch regex.

    Per the existing CLAUDE.md ``_glob_match`` lesson:
    ``**`` → ``.*`` (cross-segment); ``*`` → ``[^/]*`` (single segment);
    ``?`` → ``[^/]``. Other characters escaped. Stricter than fnmatch
    which lets ``*`` greedily cross segments.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if i + 1 < len(pattern) and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out))


def _affected_features(changed_paths: list[Path], manifest_features: dict) -> set[str]:
    """Return the names of features whose source globs match any changed path.

    ``manifest_features`` is ``Manifest.features`` from attune_author —
    a dict[str, Feature] where each Feature has a ``files`` list of
    glob patterns relative to the repo root.
    """
    affected: set[str] = set()
    # Pre-compile every pattern once per run.
    compiled: list[tuple[str, list[re.Pattern[str]]]] = [
        (name, [_glob_to_regex(g) for g in getattr(feat, "files", []) or []])
        for name, feat in manifest_features.items()
    ]
    for path in changed_paths:
        path_str = path.as_posix()
        for feature_name, patterns in compiled:
            if feature_name in affected:
                continue
            for pat in patterns:
                if pat.fullmatch(path_str):
                    affected.add(feature_name)
                    break
    return affected


def _regen_one(feature: str, help_dir: Path, repo_root: Path) -> tuple[bool, str | None]:
    """Run ``attune-author generate <feature> --all-kinds``.

    Returns (success, error_message). On non-zero exit / timeout /
    missing binary, returns (False, <error>) — never raises.
    """
    try:
        result = subprocess.run(
            [
                "attune-author",
                "generate",
                feature,
                "--help-dir",
                str(help_dir),
                "--project-root",
                str(repo_root),
                "--all-kinds",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(repo_root),
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        # stderr first, fall back to stdout — attune-author errors land
        # in stderr but some failure modes still print to stdout.
        msg = (result.stderr or result.stdout or "").strip()
        return False, msg or f"exit {result.returncode}"
    return True, None


def _summarize_error(err: str | None) -> str:
    """Reduce a multi-line subprocess error to a compact one-liner.

    Tracebacks dumped by `attune-author` (or any subprocess) on
    failure are useful for debugging but noisy in commit-cycle
    output. Returns the LAST non-blank line (typically the actual
    exception message after a long traceback), capped at 200 chars.
    """
    if not err:
        return "(no error message)"
    last_line = next(
        (line for line in reversed(err.splitlines()) if line.strip()),
        err.strip(),
    )
    if len(last_line) > 200:
        return last_line[:197] + "..."
    return last_line


def _stage_dir(dir_path: Path, repo_root: Path) -> bool:
    """``git add <dir_path>``; return True on success."""
    try:
        result = subprocess.run(
            ["git", "add", str(dir_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            cwd=str(repo_root),
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0


def main(argv: list[str]) -> int:
    if not argv:
        return 0  # No matching files in commit; nothing to do.

    repo_root = Path(__file__).resolve().parent.parent
    help_dir = repo_root / ".help"
    if not (help_dir / "features.yaml").is_file():
        return 0

    try:
        from attune_author import load_manifest
    except ImportError:
        return 0  # attune-author not installed; skip silently.

    try:
        manifest = load_manifest(help_dir)
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a corrupt manifest shouldn't block commits.
        # The freshness nudge surfaces this elsewhere.
        print(f"attune: skipping help-regen — manifest load failed: {exc}", file=sys.stderr)
        return 0

    changed_paths = [Path(p) for p in argv]
    affected = _affected_features(changed_paths, manifest.features)
    if not affected:
        return 0

    autoregen = os.environ.get("ATTUNE_DOCS_AUTOREGEN", "0") == "1"
    feat_list = ", ".join(sorted(affected))

    if not autoregen:
        # Warn-only mode (default). Matches `check_docs_freshness.py`
        # precedent — the user opts in by setting the env var.
        print(f"attune: {len(affected)} .help/templates feature(s) need regen: {feat_list}")
        print(
            "  run: ATTUNE_DOCS_AUTOREGEN=1 git commit --amend --no-edit"
            "  (or `attune-author generate <feat> --all-kinds`)"
        )
        return 0

    print(f"attune: auto-regenerating {len(affected)} feature(s): {feat_list}")

    regenerated: list[str] = []
    for feature in sorted(affected):
        ok, err = _regen_one(feature, help_dir, repo_root)
        if ok:
            regenerated.append(feature)
        else:
            # Trim to first line + 200 char cap — full tracebacks are
            # noise in the commit output; the user can re-run manually
            # for the full error.
            summary = _summarize_error(err)
            print(
                f"  WARN: attune-author generate {feature} failed: {summary}",
                file=sys.stderr,
            )

    for feature in regenerated:
        template_dir = help_dir / "templates" / feature
        if not template_dir.is_dir():
            continue
        if not _stage_dir(template_dir, repo_root):
            print(
                f"  WARN: git add {template_dir} failed; stage it manually",
                file=sys.stderr,
            )

    if regenerated:
        print(f"attune: regenerated and staged {len(regenerated)} feature(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
