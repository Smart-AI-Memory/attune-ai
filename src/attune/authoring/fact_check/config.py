"""Load fact-check configuration from ``pyproject.toml``.

Reads the ``[tool.attune-author.fact-check]`` table. Missing
sections fall back to :class:`FactCheckConfig` defaults — which
match the spec's "all checks on, soft-fail" Phase 1 defaults.
"""

from __future__ import annotations

from pathlib import Path

from .report import FactCheckConfig


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


def load_config(project_root: Path) -> FactCheckConfig:
    """Build a :class:`FactCheckConfig` from the project's pyproject.

    Unknown keys are ignored — the goal is forward-compat with
    future phases that add their own toggles under the same table.
    """
    data = _read_toml(project_root / "pyproject.toml")
    tool = data.get("tool", {}) if isinstance(data, dict) else {}
    author = tool.get("attune-author", {}) if isinstance(tool, dict) else {}
    section = author.get("fact-check", {}) if isinstance(author, dict) else {}
    skip = section.get("skip", {}) if isinstance(section, dict) else {}

    def _bool(key: str, default: bool) -> bool:
        value = section.get(key, default) if isinstance(section, dict) else default
        return bool(value)

    cfg = FactCheckConfig(
        enabled=_bool("enabled", True),
        soft_fail=_bool("soft_fail", True),
        check_python_refs=_bool("check_python_refs", True),
        check_cli_refs=_bool("check_cli_refs", True),
        check_md_links=_bool("check_md_links", True),
        check_numeric_refs=_bool("check_numeric_refs", True),
        check_tutorial_static=_bool("check_tutorial_static", True),
        check_doc_examples=_bool("check_doc_examples", True),
    )
    if isinstance(skip, dict):
        cfg.skip = {
            str(k): [str(c) for c in v] if isinstance(v, list) else [] for k, v in skip.items()
        }
    return cfg


__all__ = ["load_config"]
