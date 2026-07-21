"""mkdocs ``on_config`` hook — build the "Features" nav section.

Implements decision **D12** of the help-docs-single-source spec: the
per-feature hub page (``docs/features/<F>.md``, emitted by the
``attune.authoring`` projector) is the single nav entry per feature. This hook
scans ``docs/features/*.md`` at build time and injects one top-level
``Features`` nav section listing every hub — so the ~270-feature rollout
never edits ``mkdocs.yml`` per feature.

Scope is intentionally narrow: this hook owns **only** nav injection.
Dropping the blanket ``architecture/`` / ``features/`` exclusions is a
static ``mkdocs.yml`` edit (see spec task T3), not a runtime mutation of
the parsed ``exclude_docs`` PathSpec — separating the two keeps the hook
robust and side-effect-free beyond ``config["nav"]``.

Wire it in ``mkdocs.yml``::

    hooks:
      - docs/hooks/feature_nav.py

Spec: docs/specs/help-docs-single-source/ (decisions.md D11/D12,
r7-rollout-playbook.md).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("mkdocs.hooks.feature_nav")

FEATURES_DIRNAME = "features"
SECTION_TITLE = "Features"


def _title_for(hub_path: Path) -> str:
    """Derive a nav label from a hub page's first ``# `` H1, else its stem.

    Args:
        hub_path: Path to ``docs/features/<feature>.md``.

    Returns:
        The H1 text when present, otherwise a humanized feature stem
        (``spec-engine`` -> ``Spec Engine``).
    """
    try:
        for line in hub_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except OSError as exc:
        logger.warning("feature_nav: cannot read %s: %s", hub_path, exc)
    return hub_path.stem.replace("-", " ").replace("_", " ").title()


def _build_features_section(docs_dir: Path) -> dict[str, list[Any]] | None:
    """Build the ``Features`` nav node from ``docs/features/*.md``.

    Args:
        docs_dir: The mkdocs ``docs/`` directory.

    Returns:
        A ``{"Features": [...]}`` nav node, or ``None`` when there is no
        ``docs/features/`` directory (nothing to wire).
    """
    features_dir = docs_dir / FEATURES_DIRNAME
    if not features_dir.is_dir():
        logger.info("feature_nav: no %s/ directory; nav unchanged", FEATURES_DIRNAME)
        return None

    children: list[Any] = []
    index_path = features_dir / "index.md"
    if index_path.is_file():
        children.append({"Overview": f"{FEATURES_DIRNAME}/index.md"})

    hubs = sorted(p for p in features_dir.glob("*.md") if p.name != "index.md")
    for hub in hubs:
        children.append({_title_for(hub): f"{FEATURES_DIRNAME}/{hub.name}"})

    if not children:
        logger.info("feature_nav: %s/ is empty; nav unchanged", FEATURES_DIRNAME)
        return None

    logger.info("feature_nav: wired %d feature hub(s) into nav", len(hubs))
    return {SECTION_TITLE: children}


def on_config(config: Any, **kwargs: Any) -> Any:
    """Inject (or replace) the top-level ``Features`` nav section.

    Idempotent: removes any existing top-level ``Features`` node first
    (e.g. a static ``- Features: FEATURES.md`` placeholder) before
    appending the generated section, so a re-run never duplicates it.

    Args:
        config: The mkdocs config being built. Mutated in place.

    Returns:
        The same config, per the mkdocs hook contract.
    """
    section = _build_features_section(Path(config["docs_dir"]))
    if section is None:
        return config

    nav = config.get("nav")
    if not isinstance(nav, list):
        # INTENTIONAL: this site declares an explicit nav; without one
        # there is nothing to attach a Features section to. Warn and
        # leave config untouched rather than fabricate a full nav.
        logger.warning("feature_nav: no explicit nav: list; Features section skipped")
        return config

    pruned = [item for item in nav if not (isinstance(item, dict) and SECTION_TITLE in item)]
    pruned.append(section)
    config["nav"] = pruned
    return config
