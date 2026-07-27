#!/usr/bin/env python3
"""Pre-commit hook: WARN when `.help/templates/<feature>/` lags changed source.

Detects which features' source globs match the files in the current
commit and prints the list. Check-only — this hook never regenerates
and never spends LLM budget. Polish-bearing regeneration happens at
RELEASE-PREP cadence instead (`/coach maintain`, backed by the absorbed
`attune.authoring` generator), per the polish-cost-reduction spec
(lever 1, ratified 2026-06-10): per-commit auto-regen re-polished whole
features on every source touch, which is exactly the repeat-API-spend
the spec eliminates.

Failure modes never block the commit:

- `attune.authoring` not importable → silent exit 0
- `.help/features.yaml` missing → silent exit 0

Pre-commit passes changed file paths on argv. Empty argv → exit 0.

Specs: docs/specs/polish-cost-reduction/ (lever 1);
docs/specs/ops-specs-completion-candidates/ (original hook).
"""

from __future__ import annotations

import re
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

    ``manifest_features`` is ``FeatureManifest.features`` from
    :mod:`attune.authoring.manifest` —
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


def main(argv: list[str]) -> int:
    if not argv:
        return 0  # No matching files in commit; nothing to do.

    repo_root = Path(__file__).resolve().parent.parent
    help_dir = repo_root / ".help"
    if not (help_dir / "features.yaml").is_file():
        return 0

    try:
        from attune.authoring.manifest import load_manifest
    except ImportError:
        return 0  # attune not importable in this env; skip silently.

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

    feat_list = ", ".join(sorted(affected))
    print(f"attune: {len(affected)} .help/templates feature(s) lag this change: {feat_list}")
    print("  (check-only — polish-bearing regen runs at release-prep")
    print("   via `/coach maintain`)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
