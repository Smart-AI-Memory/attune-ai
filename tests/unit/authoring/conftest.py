"""Shared fixtures for the absorbed authoring (LLM polish) tests.

Adapted from attune-author's tests/conftest.py during the T3 absorb
(docs/specs/attune-author-consolidation/, ruling D10). The isolation
fixtures are the load-bearing part: without them a dev machine's real
polish cache or ambient credentials would leak into the suite.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _lenient_polish_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[None]:
    """Disable strict polish mode and isolate cache/credentials.

    Polish is strict in production (a missing API key raises), but
    the suite deliberately runs without credentials and mocks the
    LLM call where needed. The polish cache is pointed at a per-test
    tmp dir so a previous live regen run can't make golden tests
    silently observe LLM-rewritten content. Credentials and the
    ambient Claude Code session are hidden so un-mocked polish calls
    can never route to a REAL subscription or API call.
    """
    monkeypatch.setenv("ATTUNE_AUTHOR_STRICT_POLISH", "false")
    monkeypatch.setenv(
        "ATTUNE_AUTHOR_POLISH_CACHE",
        str(tmp_path_factory.mktemp("polish_cache")),
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Pin LLM auth routing to the API path and hide any ambient
    # Claude Code session (CLAUDECODE=1 would auto-route un-mocked
    # polish calls to REAL subscription calls via the Agent SDK).
    monkeypatch.setenv("ATTUNE_AUTH_MODE", "api")
    monkeypatch.delenv("ATTUNE_AUTHOR_AUTH_MODE", raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    yield


@pytest.fixture(autouse=True)
def _reset_rag_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset the module-level RagPipeline singleton before each test.

    ground_polish_context() caches the pipeline after first
    construction; tests that patch attune_rag.RagPipeline need the
    singleton to be None so the patch intercepts construction.
    """
    import attune.authoring.rag_hook as _rh  # noqa: PLC0415

    monkeypatch.setattr(_rh, "_PIPELINE", None)


@pytest.fixture
def help_dir(tmp_path: Path) -> Path:
    """Create a .help/ directory with a features.yaml."""
    help_root = tmp_path / ".help"
    help_root.mkdir()

    features_yaml = help_root / "features.yaml"
    features_yaml.write_text(
        "version: 1\n"
        "\n"
        "features:\n"
        "  auth:\n"
        "    description: Authentication and authorization\n"
        "    files:\n"
        "      - src/auth/**\n"
        "    tags: [security, users]\n"
        "  cli:\n"
        "    description: Command-line interface\n"
        "    files:\n"
        "      - src/cli.py\n"
        "    tags: [cli, commands]\n",
        encoding="utf-8",
    )
    return help_root


@pytest.fixture
def project_root(tmp_path: Path, help_dir: Path) -> Path:
    """Create a minimal project structure."""
    src = tmp_path / "src"
    src.mkdir()

    auth_dir = src / "auth"
    auth_dir.mkdir()

    (auth_dir / "__init__.py").write_text(
        '"""Authentication module."""\n',
        encoding="utf-8",
    )
    (auth_dir / "login.py").write_text(
        '"""Login handler."""\n\n\n'
        "def authenticate(username: str, password: str) -> bool:\n"
        '    """Authenticate a user.\n\n'
        "    Args:\n"
        "        username: The username.\n"
        "        password: The password.\n\n"
        "    Returns:\n"
        "        True if authenticated.\n"
        '    """\n'
        "    return True\n",
        encoding="utf-8",
    )

    (src / "cli.py").write_text(
        '"""CLI entry point."""\n\n\n'
        "def main() -> None:\n"
        '    """Run the CLI."""\n'
        "    pass\n",
        encoding="utf-8",
    )

    return tmp_path
