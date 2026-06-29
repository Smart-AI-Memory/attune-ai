"""Feedback and confidence scoring for help templates.

Records user ratings (good/bad) and computes confidence
scores. Also provides usage-weight integration, tag search,
workflow chain prediction, and precursor warnings.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from attune.help.templates import (
    _DEFAULT_GENERATED_DIR,
    AudienceProfile,
    PopulatedTemplate,
    _load_cross_links,
    populate,
)

logger = logging.getLogger(__name__)

_FEEDBACK_FILE = "feedback.json"


# ------------------------------------------------------------------
# Feedback recording
# ------------------------------------------------------------------


def _load_feedback(generated_dir: Path) -> dict[str, dict]:
    """Load feedback data from feedback.json.

    Args:
        generated_dir: Path to generated/ directory.

    Returns:
        Dict of template_id -> {good: int, bad: int}.
    """
    path = generated_dir / _FEEDBACK_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load feedback.json: %s", e)
        return {}


def _save_feedback(generated_dir: Path, data: dict) -> None:
    """Save feedback data atomically.

    Args:
        generated_dir: Path to generated/ directory.
        data: Feedback dict to save.
    """
    path = generated_dir / _FEEDBACK_FILE
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)  # replace() is cross-platform; rename() fails on Windows


def record_template_feedback(
    template_id: str,
    rating: str,
    *,
    generated_dir: str | Path | None = None,
) -> float:
    """Record user feedback on a template.

    Args:
        template_id: Template to rate.
        rating: "good" or "bad".
        generated_dir: Override generated/ directory.

    Returns:
        Updated confidence score (0.0-1.0).
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    feedback = _load_feedback(gen_dir)

    if template_id not in feedback:
        feedback[template_id] = {"good": 0, "bad": 0}

    if rating == "good":
        feedback[template_id]["good"] += 1
    elif rating == "bad":
        feedback[template_id]["bad"] += 1

    _save_feedback(gen_dir, feedback)
    return get_template_confidence(
        template_id,
        generated_dir=generated_dir,
    )


def get_template_confidence(
    template_id: str,
    *,
    generated_dir: str | Path | None = None,
) -> float:
    """Get confidence score based on feedback.

    Returns good / (good + bad), or 1.0 if no feedback.

    Args:
        template_id: Template to check.
        generated_dir: Override generated/ directory.

    Returns:
        Confidence score 0.0-1.0.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    feedback = _load_feedback(gen_dir)

    entry = feedback.get(template_id)
    if not entry:
        return 1.0

    good = entry.get("good", 0)
    bad = entry.get("bad", 0)
    total = good + bad
    if total == 0:
        return 1.0
    return good / total


# ------------------------------------------------------------------
# Usage weights
# ------------------------------------------------------------------


def get_usage_weights(days: int = 30) -> dict[str, float]:
    """Get template relevance weights from usage telemetry.

    Args:
        days: Number of days to look back.

    Returns:
        Dict of template_id -> weight (0.0-1.0).
    """
    try:
        from attune.telemetry.usage_tracker import UsageTracker

        # Use the singleton — a fresh UsageTracker() re-pays constructor I/O
        # (mkdir + summary load/scan) on every search_by_tag/list_tags call
        # that sorts by usage.
        tracker = UsageTracker.get_instance()
        stats = tracker.get_stats(days=days)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: telemetry is optional
        return {}

    by_workflow = stats.get("by_workflow", {})
    if not by_workflow:
        return {}

    costs: dict[str, float] = {}
    for wf_name, val in by_workflow.items():
        if isinstance(val, dict):
            costs[wf_name] = float(val.get("total_cost", 0))
        else:
            costs[wf_name] = float(val)

    max_cost = max(costs.values(), default=0)
    if max_cost <= 0:
        return {}

    wf_weights = {name: cost / max_cost for name, cost in costs.items()}

    cross_links = _load_cross_links(_DEFAULT_GENERATED_DIR)
    workflow_map = cross_links.get("workflow_map", {})

    template_weights: dict[str, float] = {}
    for wf_name, weight in wf_weights.items():
        for tid in workflow_map.get(wf_name, []):
            template_weights[tid] = max(
                template_weights.get(tid, 0),
                weight,
            )

    return template_weights


# ------------------------------------------------------------------
# Tag search
# ------------------------------------------------------------------


def search_by_tag(
    tag: str,
    *,
    generated_dir: str | Path | None = None,
    sort_by_usage: bool = False,
) -> list[str]:
    """Find template IDs matching a tag.

    Args:
        tag: Tag to search for.
        generated_dir: Override generated/ directory.
        sort_by_usage: Sort by usage frequency.

    Returns:
        List of matching template IDs.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    results = cross_links.get("tag_index", {}).get(tag, [])

    if sort_by_usage and results:
        weights = get_usage_weights()
        if weights:
            results = sorted(
                results,
                key=lambda tid: weights.get(tid, 0),
                reverse=True,
            )
    return results


def list_tags(
    *,
    generated_dir: str | Path | None = None,
    sort_by_usage: bool = False,
) -> dict[str, int]:
    """List all tags with their template counts.

    Args:
        generated_dir: Override generated/ directory.
        sort_by_usage: Sort by aggregate usage weight.

    Returns:
        Dict of tag -> count.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    tag_index = cross_links.get("tag_index", {})

    if sort_by_usage:
        weights = get_usage_weights()
        if weights:

            def tag_weight(item: tuple[str, list[str]]) -> float:
                _, tids = item
                return sum(weights.get(tid, 0) for tid in tids)

            return {
                tag: len(ids)
                for tag, ids in sorted(
                    tag_index.items(),
                    key=tag_weight,
                    reverse=True,
                )
            }

    return dict(
        sorted(
            ((tag, len(ids)) for tag, ids in tag_index.items()),
            key=lambda x: x[1],
            reverse=True,
        )
    )


# ------------------------------------------------------------------
# Workflow chain prediction
# ------------------------------------------------------------------


def get_workflow_help(
    workflow_name: str,
    *,
    generated_dir: str | Path | None = None,
    max_results: int = 3,
) -> list[PopulatedTemplate]:
    """Get help templates relevant after a workflow completes.

    Args:
        workflow_name: Workflow slug (e.g. "code-review").
        generated_dir: Override generated/ directory.
        max_results: Maximum templates to return.

    Returns:
        List of PopulatedTemplate at compact verbosity.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    workflow_map = cross_links.get("workflow_map", {})

    template_ids = workflow_map.get(workflow_name, [])
    if not template_ids:
        return []

    audience = AudienceProfile(verbosity="compact")
    results: list[PopulatedTemplate] = []
    for tid in template_ids[:max_results]:
        result = populate(tid, audience=audience, generated_dir=generated_dir)
        if result:
            results.append(result)
    return results


# ------------------------------------------------------------------
# Error precursor detection
# ------------------------------------------------------------------

_EXTENSION_TAG_MAP: dict[str, list[str]] = {
    ".py": ["python", "imports", "testing"],
    ".yml": ["ci"],
    ".yaml": ["ci"],
    ".json": ["packaging"],
    ".toml": ["packaging", "python"],
    ".md": ["claude-code"],
}


def get_precursor_warnings(
    file_path: str,
    *,
    generated_dir: str | Path | None = None,
    max_results: int = 3,
) -> list[PopulatedTemplate]:
    """Get warnings relevant to a file being edited.

    Args:
        file_path: Path to the file being edited.
        generated_dir: Override generated/ directory.
        max_results: Maximum templates to return.

    Returns:
        List of PopulatedTemplate at compact verbosity.
    """
    gen_dir = Path(generated_dir) if generated_dir else _DEFAULT_GENERATED_DIR
    cross_links = _load_cross_links(gen_dir)
    tag_index = cross_links.get("tag_index", {})

    ext = Path(file_path).suffix.lower()
    relevant_tags = _EXTENSION_TAG_MAP.get(ext, [])
    if not relevant_tags:
        return []

    candidates: dict[str, int] = {}
    for tag in relevant_tags:
        for tid in tag_index.get(tag, []):
            if tid.startswith(("war-", "err-")):
                candidates[tid] = candidates.get(tid, 0) + 1

    if not candidates:
        return []

    sorted_ids = sorted(
        candidates,
        key=lambda t: candidates[t],
        reverse=True,
    )

    audience = AudienceProfile(verbosity="compact")
    results: list[PopulatedTemplate] = []
    for tid in sorted_ids[:max_results]:
        result = populate(tid, audience=audience, generated_dir=generated_dir)
        if result:
            results.append(result)
    return results
