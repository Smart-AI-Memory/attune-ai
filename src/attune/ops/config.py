"""Runtime configuration for attune ops."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Where attune ops reads project + attune state from."""

    project_root: Path
    attune_home: Path
    host: str = "127.0.0.1"
    port: int = 8765
    allow_run: bool = False

    @property
    def telemetry_path(self) -> Path:
        return self.attune_home / "telemetry" / "usage.jsonl"

    @property
    def memory_dir(self) -> Path:
        return self.attune_home / "memory"

    @property
    def sessions_dir(self) -> Path:
        return self.attune_home / "sessions"


def attune_home() -> Path:
    """Resolve the user's attune home dir (env override -> ~/.attune)."""
    override = os.environ.get("ATTUNE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".attune"


def build_config(
    project_root: Path | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    allow_run: bool = False,
) -> Config:
    """Build a Config from inputs and environment defaults."""
    root = (project_root or Path.cwd()).expanduser().resolve()
    return Config(
        project_root=root,
        attune_home=attune_home(),
        host=host,
        port=port,
        allow_run=allow_run,
    )
