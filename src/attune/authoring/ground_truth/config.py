"""Load ground-truth context-injection configuration from pyproject.

Reads ``[tool.attune-author.context-injection]``. Missing sections
fall back to defaults: all three sources enabled, 5KB budget, consumer
CLI executable ``attune`` (matches the most common case in this repo
ecosystem; configurable for other consumers).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: Default total context budget in characters. Empirically the
#: ops-dashboard fixture renders ~5KB across cli_help + public_api +
#: dataclasses, so this sits at the comfortable upper edge of the
#: real-world distribution.
_DEFAULT_BUDGET_BYTES = 5 * 1024

#: Default consumer CLI executable. Configurable for consumers whose
#: CLI is not named ``attune`` (e.g., a project using attune-author
#: against its own CLI).
_DEFAULT_CLI_EXECUTABLE = "attune"


@dataclass
class GroundTruthConfig:
    """Ground-truth context-injection configuration.

    Attributes:
        enabled: Master switch. ``False`` returns ``None`` from
            :func:`attune.authoring.ground_truth.build_context` so the
            polish proceeds with no ground-truth block at all.
        inject_cli_help: Include ``<cli> <subcommand> --help`` block.
        inject_public_api: Include ``<public_api>`` block.
        inject_dataclasses: Include ``<dataclasses>`` block.
        budget_bytes: Maximum rendered byte size for the combined
            block list. Non-positive disables enforcement.
        cli_executable: Consumer CLI to invoke for the ``--help``
            block. Resolved against PATH at subprocess time.
    """

    enabled: bool = True
    inject_cli_help: bool = True
    inject_public_api: bool = True
    inject_dataclasses: bool = True
    budget_bytes: int = _DEFAULT_BUDGET_BYTES
    cli_executable: str = _DEFAULT_CLI_EXECUTABLE


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


def load_config(project_root: Path) -> GroundTruthConfig:
    """Build a :class:`GroundTruthConfig` from the project's pyproject.

    Unknown keys are ignored so future phases can extend this table
    without breaking older callers.
    """
    data = _read_toml(project_root / "pyproject.toml")
    tool = data.get("tool", {}) if isinstance(data, dict) else {}
    author = tool.get("attune-author", {}) if isinstance(tool, dict) else {}
    section = author.get("context-injection", {}) if isinstance(author, dict) else {}

    def _bool(key: str, default: bool) -> bool:
        value = section.get(key, default) if isinstance(section, dict) else default
        return bool(value)

    def _int(key: str, default: int) -> int:
        value = section.get(key, default) if isinstance(section, dict) else default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _str(key: str, default: str) -> str:
        value = section.get(key, default) if isinstance(section, dict) else default
        return str(value) if value else default

    return GroundTruthConfig(
        enabled=_bool("enabled", True),
        inject_cli_help=_bool("inject_cli_help", True),
        inject_public_api=_bool("inject_public_api", True),
        inject_dataclasses=_bool("inject_dataclasses", True),
        budget_bytes=_int("budget_bytes", _DEFAULT_BUDGET_BYTES),
        cli_executable=_str("cli_executable", _DEFAULT_CLI_EXECUTABLE),
    )


__all__ = ["GroundTruthConfig", "load_config"]
