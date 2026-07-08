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
    # Roots to scan for spec directories. Defaults to empty here; the specs
    # route resolves an empty tuple to `<project_root>/docs/specs/`. Multiple
    # roots supported for federated listing across project boundaries.
    specs_roots: tuple[Path, ...] = ()
    # User-supplied additions to the Host: header allowlist. The default
    # allowlist always includes `host:port` and loopback aliases; this lets
    # users widen for tunneled / proxied setups (Cloudflare Tunnel,
    # Tailscale, ssh -L, etc.). See docs/specs/ops-security-hardening/.
    trusted_hosts: tuple[str, ...] = ()
    # How many days of completed runs to keep on disk under
    # ``<attune_home>/ops/runs/``. The startup sweep deletes anything
    # older. 30 days is enough to span a typical sprint; bump via
    # ``--runs-retention-days`` if you want longer history.
    runs_retention_days: int = 30
    # Whether the Specs page surfaces "Ready to close?" completion
    # candidates. Opt-in default-off per
    # ``docs/specs/ops-specs-completion-candidates/`` (Q6). Toggled
    # via ``--specs-candidates`` / ``--no-specs-candidates`` and
    # persisted to ``<attune_home>/ops/config.json``.
    specs_candidates_enabled: bool = False

    @property
    def telemetry_path(self) -> Path:
        return self.attune_home / "telemetry" / "usage.jsonl"

    @property
    def memory_events_path(self) -> Path:
        """Local event log written by the short-term memory hooks.

        Produced by ``plugin/hooks/_memory_telemetry.py``; one JSON line
        per hook fire (session_recall / jit_recall / session_stash).
        """
        return self.attune_home / "telemetry" / "memory_events.jsonl"

    @property
    def runs_dir(self) -> Path:
        """Disk root for persisted ops runs. May not exist until first write."""
        return self.attune_home / "ops" / "runs"

    @property
    def memory_dir(self) -> Path:
        return self.attune_home / "memory"

    @property
    def sessions_dir(self) -> Path:
        return self.attune_home / "sessions"

    @property
    def bulletin_dir(self) -> Path:
        """Directory for the multi-actor bulletin's active log + archive."""
        return self.attune_home / "bulletin"


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
    specs_roots: tuple[Path, ...] | None = None,
    trusted_hosts: tuple[str, ...] | None = None,
    runs_retention_days: int = 30,
    specs_candidates_enabled: bool = False,
) -> Config:
    """Build a Config from inputs and environment defaults.

    ``specs_roots`` defaults to ``()``; the specs route resolves an empty
    tuple to ``<project_root>/docs/specs/`` so unconfigured installs pick up
    the standard layout automatically.

    ``trusted_hosts`` defaults to ``()``; the middleware always includes
    ``host:port`` and loopback aliases in its allowlist, so the default
    works for local development without configuration.

    ``specs_candidates_enabled`` defaults to False; the CLI resolver
    (:func:`attune.ops.ops_config_store.resolve_specs_candidates_enabled`)
    overlays persisted state when the caller has computed it.
    """
    root = (project_root or Path.cwd()).expanduser().resolve()
    return Config(
        project_root=root,
        attune_home=attune_home(),
        host=host,
        port=port,
        allow_run=allow_run,
        specs_roots=tuple(specs_roots or ()),
        trusted_hosts=tuple(trusted_hosts or ()),
        runs_retention_days=max(0, int(runs_retention_days)),
        specs_candidates_enabled=specs_candidates_enabled,
    )
