"""Code inspection commands.

Commands for scanning and inspecting codebases for issues.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import subprocess
from pathlib import Path

from attune.cli.core import console


def scan(
    path: Path = Path("."),
    format_out: str = "text",
    fix: bool = False,
    staged: bool = False,
) -> None:
    """Scan codebase for issues using ruff and bandit."""
    console.print(f"[bold blue]Scanning {path}...[/bold blue]\n")

    # Run ruff for linting
    console.print("[bold]Running ruff (linting)...[/bold]")
    ruff_args = ["ruff", "check", str(path)]
    if fix:
        ruff_args.append("--fix")
    subprocess.run(ruff_args, check=False)

    # Run bandit for security (if available)
    console.print("\n[bold]Running bandit (security)...[/bold]")
    bandit_args = ["bandit", "-r", str(path), "-q"]
    if format_out == "json":
        bandit_args.extend(["-f", "json"])
    result = subprocess.run(bandit_args, check=False, capture_output=True)
    if result.returncode == 0:
        console.print("[green]No security issues found[/green]")
    elif result.stdout:
        console.print(result.stdout.decode())

    console.print("\n[bold green]Scan complete![/bold green]")


def inspect_cmd(
    path: Path = Path("."),
    format_out: str = "text",
) -> None:
    """Deep inspection with code analysis."""
    args = ["attune-inspect", str(path)]
    if format_out != "text":
        args.extend(["--format", format_out])

    result = subprocess.run(args, check=False, capture_output=False)
    if result.returncode != 0:
        console.print("[yellow]Note: attune-inspect may not be installed[/yellow]")
        console.print("Install with: pip install attune-framework[software]")
