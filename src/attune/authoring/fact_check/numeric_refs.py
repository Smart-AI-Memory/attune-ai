"""Check numeric claims in prose against verifiable counts.

For each sentence matching ``<digits> <noun>`` where the noun
is in our verifier map, compare the stated count against a
filesystem or manifest derived ground truth. Unverifiable
nouns surface as ``warning`` so the human can confirm.

The noun-to-resolver map is intentionally small and extensible
— per spec §1.5.1, additional resolvers can be added per
consumer without touching this module's structure.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from .report import CHECK_NUMERIC_REFS, Finding

#: Match ``<digits>[, suffix] <noun>`` constructions like
#: ``259 templates``, ``11 kinds``, ``26 features``. Captures
#: the integer and the noun.
_CLAIM = re.compile(
    r"\b(?P<count>\d{1,6})\s+"
    r"(?P<noun>templates?|features?|kinds?|workflows?|skills?|agents?)\b",
    re.IGNORECASE,
)

#: Nouns we know how to resolve but don't have a verifier
#: registered for in the consumer's project root. Surfaced as
#: warnings to nudge the human to verify rather than silently
#: passing.
_AMBIGUOUS_NOUNS = {"workflow", "workflows", "skill", "skills", "agent", "agents"}


def _count_templates(project_root: Path) -> int | None:
    """Count ``.help/templates/**/*.md`` files."""
    templates_dir = project_root / ".help" / "templates"
    if not templates_dir.is_dir():
        return None
    return sum(1 for _ in templates_dir.rglob("*.md"))


def _count_features(project_root: Path) -> int | None:
    """Count top-level features in ``.help/features.yaml``."""
    features_yaml = project_root / ".help" / "features.yaml"
    if not features_yaml.is_file():
        return None
    try:
        import yaml
    except ImportError:  # pragma: no cover - pyyaml is a core dep
        return None
    try:
        data = yaml.safe_load(features_yaml.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        # yaml.YAMLError is NOT a ValueError subclass: without it a
        # syntactically-broken features.yaml aborts the whole
        # fact-check run instead of leaving this count unverifiable
        # (library-review F1).
        return None
    if not isinstance(data, dict):
        return None
    features = data.get("features", data)
    if isinstance(features, dict):
        return len(features)
    if isinstance(features, list):
        return len(features)
    return None


def _count_kinds(_project_root: Path) -> int | None:
    """Return the canonical attune-author kind count.

    Read lazily so import order doesn't depend on the consumer's
    site-packages state at fact-check-package import time.
    """
    try:
        from attune.authoring.source_introspection import KINDS  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        # INTENTIONAL: if the consumer is running fact-check
        # against a different attune-author build, fall through.
        return None
    try:
        return len(KINDS)
    except TypeError:
        return None


#: Mapping of normalized (singular, lowercase) noun → resolver.
_RESOLVERS: dict[str, Callable[[Path], int | None]] = {
    "template": _count_templates,
    "feature": _count_features,
    "kind": _count_kinds,
}


def _normalize_noun(noun: str) -> str:
    """Lowercase and naive-singularize for the resolver lookup."""
    lowered = noun.lower()
    if lowered.endswith("s") and lowered[:-1] in _RESOLVERS:
        return lowered[:-1]
    return lowered


def check(polished_path: Path, project_root: Path) -> list[Finding]:
    """Run the numeric-refs check on ``polished_path``."""
    text = polished_path.read_text(encoding="utf-8")
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()

    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _CLAIM.finditer(line):
            try:
                count = int(match.group("count"))
            except ValueError:
                continue
            noun = match.group("noun")
            key = (noun.lower(), count)
            if key in seen:
                continue
            seen.add(key)

            normalized = _normalize_noun(noun)
            resolver = _RESOLVERS.get(normalized)
            if resolver is not None:
                actual = resolver(project_root)
                if actual is None:
                    # Couldn't resolve in this project; treat as
                    # ambiguous so the human verifies.
                    findings.append(
                        Finding(
                            check=CHECK_NUMERIC_REFS,
                            severity="warning",
                            location=f"Line {lineno}",
                            message=(
                                f"`{count} {noun}` — unable to verify against "
                                "project state; please confirm manually"
                            ),
                        )
                    )
                    continue
                if count != actual:
                    findings.append(
                        Finding(
                            check=CHECK_NUMERIC_REFS,
                            severity="error",
                            location=f"Line {lineno}",
                            message=(f"`{count} {noun}` — actual count is {actual}"),
                        )
                    )
            elif normalized in _AMBIGUOUS_NOUNS:
                findings.append(
                    Finding(
                        check=CHECK_NUMERIC_REFS,
                        severity="warning",
                        location=f"Line {lineno}",
                        message=(
                            f"`{count} {noun}` — no deterministic verifier; "
                            "please confirm manually"
                        ),
                    )
                )

    return findings


__all__ = ["check"]
