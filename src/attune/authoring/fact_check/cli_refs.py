"""Check CLI flag references against locally-installed CLI help.

For each ``attune <subcommand> --flag`` pattern referenced in
the polished file, run ``attune <subcommand> --help`` once,
parse the flag set, and assert the referenced flag appears.
Findings carry a "version coupling" disclaimer block per spec
§1.4 so consumers know which attune-ai version was probed and
how to override.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .report import CHECK_CLI_REFS, Finding

#: Match prose like ``attune ops --read-only`` or
#: ``attune workflow run security-audit --path src/``. Captures
#: the subcommand chain and the flag separately. ``cli`` is
#: parameterized so the same module works for non-attune
#: consumers in future phases.
_FLAG_PATTERN_TMPL = (
    r"`\s*(?P<cli>{cli})" r"(?P<sub>(?:\s+[a-z][a-z0-9-]*)*?)" r"\s+(?P<flag>--[a-z][a-z0-9-]*)"
)

_FLAG_IN_HELP = re.compile(r"--[a-z][a-z0-9-]*")


def _resolve_cli_name(project_root: Path) -> str:
    """Pick the consumer CLI name. Defaults to ``attune``.

    Hook point for future phases — for now we read from
    ``[tool.attune-author.fact-check].cli_name`` if present.
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return "attune"
    try:
        import tomllib
    except ImportError:  # pragma: no cover - Py <3.11 fallback
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "attune"
    return (
        data.get("tool", {})
        .get("attune-author", {})
        .get("fact-check", {})
        .get("cli_name", "attune")
    )


def _installed_version(cli: str) -> str:
    """Return the installed package version for ``cli``.

    Attempts ``importlib.metadata.version`` against a best-guess
    package name, then falls back to running ``<cli> --version``,
    then to ``"unknown"`` if both fail.
    """
    pkg_guess = "attune-ai" if cli == "attune" else cli
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version(pkg_guess)
    except PackageNotFoundError:
        pass
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any metadata-system error falls through to
        # the CLI probe; we don't want to fail the whole check on
        # a deformed dist-info.
        pass
    try:
        result = subprocess.run(
            [cli, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        out = (result.stdout or result.stderr).strip()
        if out:
            return out.splitlines()[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _help_text(cli: str, subcommand_chain: list[str], timeout: int = 5) -> str | None:
    """Run ``<cli> <chain...> --help`` and return stdout, or None."""
    if shutil.which(cli) is None:
        return None
    try:
        result = subprocess.run(
            [cli, *subcommand_chain, "--help"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # ``--help`` typically exits 0; if it didn't, the chain was
    # likely invalid — treat as "no flags found" so the chain
    # itself becomes the finding.
    if result.returncode != 0:
        return None
    return result.stdout or ""


def _extract_flags(help_text: str) -> set[str]:
    """Return the set of flag names that appear in ``help_text``."""
    return set(_FLAG_IN_HELP.findall(help_text))


def _version_block(cli: str, version: str, finding_path: str) -> str:
    """Build the per-finding version-coupling messaging block."""
    return (
        f"\n\nDetected against {cli} {version} (installed in active venv). "
        "If you are regenerating against a different version, verify the "
        f"flag exists in that version's `{cli} --help`.\n"
        "To override:\n"
        f"  - One-off:  attune-author generate FEATURE --skip-check {CHECK_CLI_REFS}\n"
        "  - Per file: [tool.attune-author.fact-check.skip]\n"
        f'              "{finding_path}" = ["{CHECK_CLI_REFS}"]'
    )


def check(polished_path: Path, project_root: Path) -> list[Finding]:
    """Run the cli-refs check on ``polished_path``.

    Returns findings for any ``<cli> <sub> --flag`` reference
    whose flag does not appear in the cached ``--help`` output
    for that subcommand chain.
    """
    cli = _resolve_cli_name(project_root)
    if shutil.which(cli) is None:
        # No CLI to probe against — skip silently. The check is
        # opportunistic; raising on a missing dev dep would be
        # worse than the false positives we're trying to prevent.
        return []
    pattern = re.compile(_FLAG_PATTERN_TMPL.format(cli=re.escape(cli)))
    text = polished_path.read_text(encoding="utf-8")

    try:
        rel_path = polished_path.relative_to(project_root).as_posix()
    except ValueError:
        rel_path = polished_path.name

    # Cache: (chain-tuple) -> set of flags. None means the chain
    # itself was rejected; we surface that as a separate finding.
    flag_cache: dict[tuple[str, ...], set[str] | None] = {}
    version: str | None = None
    findings: list[Finding] = []
    seen: set[tuple[tuple[str, ...], str]] = set()

    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            sub_raw = (match.group("sub") or "").strip()
            chain = tuple(sub_raw.split()) if sub_raw else ()
            flag = match.group("flag")

            key = (chain, flag)
            if key in seen:
                continue
            seen.add(key)

            if chain not in flag_cache:
                help_text = _help_text(cli, list(chain))
                flag_cache[chain] = _extract_flags(help_text) if help_text is not None else None

            flag_set = flag_cache[chain]
            if flag_set is None:
                if version is None:
                    version = _installed_version(cli)
                chain_str = " ".join([cli, *chain]).strip()
                findings.append(
                    Finding(
                        check=CHECK_CLI_REFS,
                        severity="error",
                        location=f"Line {lineno}",
                        message=(
                            f"`{chain_str}` — subcommand not found"
                            + _version_block(cli, version, rel_path)
                        ),
                    )
                )
                continue
            if flag not in flag_set:
                if version is None:
                    version = _installed_version(cli)
                chain_str = " ".join([cli, *chain]).strip()
                findings.append(
                    Finding(
                        check=CHECK_CLI_REFS,
                        severity="error",
                        location=f"Line {lineno}",
                        message=(
                            f"`{chain_str} {flag}` — flag not found in `{chain_str} --help`"
                            + _version_block(cli, version, rel_path)
                        ),
                    )
                )

    return findings


__all__ = ["check"]
