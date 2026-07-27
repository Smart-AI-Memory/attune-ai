"""Load faithfulness-judge configuration from ``pyproject.toml``.

Reads the ``[tool.attune-author.fact-check.faithfulness]``
sub-table. Defaults match :class:`FaithfulnessConfig`'s defaults
(enabled=False — opt-in only since the judge makes real API
calls).
"""

from __future__ import annotations

from pathlib import Path

from attune.model_tiers import resolve_model

from . import FaithfulnessConfig


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        import tomllib
    except ImportError:  # pragma: no cover - Py <3.11 fallback
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_config(project_root: Path) -> FaithfulnessConfig:
    """Build a :class:`FaithfulnessConfig` from the project's pyproject.

    Reads ``[tool.attune-author.fact-check.faithfulness]`` so the
    faithfulness section sits alongside (and inside) the existing
    fact-check table. Unknown keys are ignored so adjacent phases
    can grow their own sub-tables.
    """
    data = _read_toml(project_root / "pyproject.toml")
    tool = data.get("tool", {}) if isinstance(data, dict) else {}
    author = tool.get("attune-author", {}) if isinstance(tool, dict) else {}
    fact_check = author.get("fact-check", {}) if isinstance(author, dict) else {}
    section = fact_check.get("faithfulness", {}) if isinstance(fact_check, dict) else {}

    if not isinstance(section, dict):
        return FaithfulnessConfig()

    def _bool(key: str, default: bool) -> bool:
        value = section.get(key, default)
        return bool(value)

    def _float(key: str, default: float) -> float:
        value = section.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _str(key: str, default: str) -> str:
        value = section.get(key, default)
        return str(value) if value else default

    return FaithfulnessConfig(
        enabled=_bool("enabled", False),
        threshold=_float("threshold", 0.95),
        budget_per_file_usd=_float("budget_per_file_usd", 0.10),
        # Premium tier resolved at load time (env pin respected); an
        # explicit pyproject `model` value still wins.
        model=_str("model", resolve_model("premium")),
        block_polish_on_unavailable=_bool("block_polish_on_unavailable", False),
    )


__all__ = ["load_config"]
