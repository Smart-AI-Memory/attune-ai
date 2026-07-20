"""G2 — advertised-command reference validation (claim-drift-gates).

Every ``/command`` token printed by the CLI's user-facing surfaces —
``create_parser()``'s epilog, ``_show_welcome``, and ``cmd_setup`` —
must resolve to a real command file (``src/attune/commands/<name>.md``
or ``plugin/commands/<name>.md``). The advertised set is extracted by
CALLING the render surfaces, not by grepping source, so refactors
can't bypass the gate.

The inverse direction (commands that exist but are advertised
nowhere) is a REPORT-ONLY warning tier per D8 (ruled 2026-07-20) —
non-gating, reassess after a month of output.

CI-only per D7. Keyless, no network. Run me serially:
    pytest tests/unit/gates/test_advertised_commands.py -p no:xdist
"""

from __future__ import annotations

import re
import warnings
from argparse import Namespace
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

#: Line-leading slash tokens ("  /dev   Developer tools"). Anchored to
#: line start so URLs (https://...) and path fragments never match.
_TOKEN_RE = re.compile(r"(?m)^\s+/([a-z][a-z0-9-]*)\b")


def _existing_commands() -> set[str]:
    names = {p.stem for p in (REPO / "src" / "attune" / "commands").glob("*.md")}
    names |= {p.stem for p in (REPO / "plugin" / "commands").glob("*.md")}
    return names


def _advertised(capsys, monkeypatch, tmp_path) -> dict[str, set[str]]:
    """Render each surface for real and extract its advertised tokens."""
    from attune.cli_commands.utility_commands import cmd_setup
    from attune.cli_minimal import _show_welcome, create_parser

    surfaces: dict[str, set[str]] = {}

    surfaces["epilog"] = set(_TOKEN_RE.findall(create_parser().epilog or ""))

    _show_welcome()
    surfaces["welcome"] = set(_TOKEN_RE.findall(capsys.readouterr().out))

    # cmd_setup installs into Path.home()/.claude/commands — point home
    # at tmp so the REAL renderer runs without touching the user's home.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    cmd_setup(Namespace())
    surfaces["setup"] = set(_TOKEN_RE.findall(capsys.readouterr().out))

    return surfaces


def test_every_advertised_command_resolves(capsys, monkeypatch, tmp_path):
    surfaces = _advertised(capsys, monkeypatch, tmp_path)
    existing = _existing_commands()
    assert any(surfaces.values()), "no advertised tokens extracted — renderers changed shape"
    ghosts = {
        surface: sorted(tokens - existing)
        for surface, tokens in surfaces.items()
        if tokens - existing
    }
    assert not ghosts, (
        f"advertised commands with no command file: {ghosts} — retarget the "
        "line to a real command in src/attune/commands/ (or delete it)"
    )


def test_unadvertised_commands_report_only(capsys, monkeypatch, tmp_path):
    """D8 (ruled): the inverse direction is a non-gating discoverability
    report — commands that exist but no CLI surface mentions."""
    surfaces = _advertised(capsys, monkeypatch, tmp_path)
    advertised = set().union(*surfaces.values())
    unadvertised = sorted(_existing_commands() - advertised)
    if unadvertised:
        warnings.warn(
            "commands that exist but are advertised on no CLI surface "
            f"(D8 report-only): {unadvertised}",
            UserWarning,
            stacklevel=1,
        )
