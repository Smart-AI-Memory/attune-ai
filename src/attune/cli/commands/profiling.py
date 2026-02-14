"""Profiling commands for Attune AI CLI.

Performance profiling and memory analysis commands.

Usage:
    attune profile memory-scan         # Scan for memory leaks
    attune profile memory-scan --json  # JSON output for CI
    attune profile memory-test         # Profile memory module

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

# Create the profile command group
profile_app = typer.Typer(
    name="profile",
    help="Performance profiling and memory analysis",
    no_args_is_help=True,
)


@profile_app.command("memory-scan")
def memory_scan(
    path: Path = typer.Argument(
        Path("src"),
        help="Directory to scan for memory issues",
    ),
    feature: str = typer.Option(
        None,
        "--feature",
        "-f",
        help="Scan files related to a specific feature",
    ),
    min_severity: str = typer.Option(
        "MEDIUM",
        "--min-severity",
        "-s",
        help="Minimum severity to report (HIGH, MEDIUM, LOW)",
    ),
    top: int = typer.Option(
        10,
        "--top",
        "-t",
        help="Number of hot files to show",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output in JSON format",
    ),
    run_profile: bool = typer.Option(
        False,
        "--profile",
        "-p",
        help="Run dynamic memory profiling on hot files",
    ),
) -> None:
    """Scan codebase for memory leak patterns.

    Detects common memory issues like:
    - sorted()[:N] patterns (should use heapq)
    - get_all_* methods that load entire datasets
    - Unbounded caches without eviction
    - Large list comprehensions that could be generators

    Examples:
        attune profile memory-scan                    # Scan src/
        attune profile memory-scan src/attune     # Scan specific dir
        attune profile memory-scan --feature "cache"  # Scan cache-related files
        attune profile memory-scan --json > report.json  # CI integration
    """
    scanner_path = (
        Path(__file__).parent.parent.parent.parent.parent / "benchmarks" / "memory_leak_scanner.py"
    )

    if not scanner_path.exists():
        console.print("[red]Error:[/red] Memory leak scanner not found at expected path")
        console.print(f"Expected: {scanner_path}")
        console.print("\nThe scanner script may have been moved or renamed.")
        console.print("Check the scripts/ directory or reinstall the package.")
        raise typer.Exit(1)

    args = [sys.executable, str(scanner_path), "--path", str(path)]

    if feature:
        args.extend(["--feature", feature])
    if min_severity:
        args.extend(["--min-severity", min_severity])
    if top:
        args.extend(["--top", str(top)])
    if json_output:
        args.append("--json")
    if run_profile:
        args.append("--profile")

    subprocess.run(args, check=False)


@profile_app.command("memory-test")
def memory_test(
    module: str = typer.Argument(
        "unified",
        help="Memory module to profile (unified, short_term, graph)",
    ),
) -> None:
    """Run memory profiling tests on memory modules.

    Profiles the specified memory module and reports memory usage
    for key operations like search, store, and retrieve.

    Examples:
        attune profile memory-test          # Profile unified memory
        attune profile memory-test unified  # Same as above
    """
    try:
        import memory_profiler  # noqa: F401 - check if installed
    except ImportError:
        console.print("[yellow]Installing memory_profiler...[/yellow]")
        subprocess.run([sys.executable, "-m", "pip", "install", "memory_profiler"], check=True)

    profile_script = (
        Path(__file__).parent.parent.parent.parent.parent
        / "benchmarks"
        / "profile_unified_memory.py"
    )

    if not profile_script.exists():
        console.print("[red]Error:[/red] Memory profiling script not found")
        console.print(f"Expected: {profile_script}")
        console.print("\nInstall memory_profiler with: pip install memory-profiler")
        console.print("Or check that the benchmarks directory exists.")
        raise typer.Exit(1)

    console.print(f"[bold]Profiling memory module: {module}[/bold]\n")
    subprocess.run([sys.executable, "-m", "memory_profiler", str(profile_script)], check=False)


@profile_app.command("hot-files")
def hot_files(
    path: Path = typer.Argument(
        Path("src"),
        help="Directory to analyze",
    ),
    top: int = typer.Option(
        15,
        "--top",
        "-t",
        help="Number of files to show",
    ),
) -> None:
    """Show files most likely to have memory issues.

    Quick scan that ranks files by risk score based on
    detected memory leak patterns.

    Examples:
        attune profile hot-files             # Scan src/
        attune profile hot-files --top 20    # Show top 20
    """
    scanner_path = (
        Path(__file__).parent.parent.parent.parent.parent / "benchmarks" / "memory_leak_scanner.py"
    )

    if not scanner_path.exists():
        console.print("[red]Error:[/red] Memory leak scanner not found")
        raise typer.Exit(1)

    args = [
        sys.executable,
        str(scanner_path),
        "--path",
        str(path),
        "--min-severity",
        "MEDIUM",
        "--top",
        str(top),
    ]
    subprocess.run(args, check=False)


@profile_app.callback()
def callback() -> None:
    """Performance profiling and memory analysis tools.

    Use these commands to identify memory leaks, inefficient patterns,
    and performance bottlenecks in your codebase.

    [bold]Quick Start:[/bold]
        attune profile memory-scan      Scan for memory issues
        attune profile hot-files        Show riskiest files
        attune profile memory-test      Profile memory module
    """
