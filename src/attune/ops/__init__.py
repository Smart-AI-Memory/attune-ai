"""attune ops — operations dashboard for the AI Workflow-harness.

Exposes a local FastAPI app served at 127.0.0.1:8765 by default. Run via
``attune ops`` (preferred) or ``python -m attune.ops``.

The dashboard surfaces workflow registry, telemetry/cost data, personal memory,
release status, and environment health. It reads attune state from
``~/.attune/`` (or ``$ATTUNE_HOME``) and the current project root.
"""

__all__ = ["create_app", "build_config", "Config"]

# ``Config`` is deliberately NOT bound at module scope: PEP 562
# ``__getattr__`` only fires for missing attributes, so a module-level
# ``Config = None`` placeholder shadowed the lazy resolver and every
# ``from attune.ops import Config`` silently imported ``None``
# (caught 2026-07-30, Tier 3 corrections — see COVERAGE_BUG_LOG.md).


def create_app(*args, **kwargs):
    """Lazy-import the FastAPI factory so importing attune doesn't pull FastAPI."""
    from attune.ops.server import create_app as _create_app

    return _create_app(*args, **kwargs)


def build_config(*args, **kwargs):
    """Lazy import of the config builder."""
    from attune.ops.config import build_config as _build

    return _build(*args, **kwargs)


def __getattr__(name: str):  # pragma: no cover — re-export shim
    if name == "Config":
        from attune.ops.config import Config

        return Config
    raise AttributeError(name)
