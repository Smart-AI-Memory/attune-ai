"""Core utilities for Attune AI CLI.

Shared utilities, console configuration, and helper functions used across
all CLI command modules.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from importlib.metadata import version as get_version

import typer
from rich.console import Console

# Shared Rich console instance for all CLI commands
console = Console()


def get_attune_version() -> str:
    """Get the installed version of attune-ai."""
    try:
        return get_version("attune-ai")
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Version detection fallback for dev installs
        return "dev"


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold blue]Attune AI[/bold blue] v{get_attune_version()}")
        raise typer.Exit()
