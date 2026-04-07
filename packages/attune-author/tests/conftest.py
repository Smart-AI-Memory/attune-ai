"""Shared test fixtures for attune-author."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def help_dir(tmp_path: Path) -> Path:
    """Create a .help/ directory with a features.yaml."""
    help = tmp_path / ".help"
    help.mkdir()

    features_yaml = help / "features.yaml"
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
    return help


@pytest.fixture
def project_root(tmp_path: Path, help_dir: Path) -> Path:
    """Create a minimal project structure."""
    # Source files
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
