#!/usr/bin/env python3
"""Generate Troubleshooting templates — symptom, diagnosis, fix.

Sources:
  1. Common failure patterns from Lessons Learned
  2. Environment/setup issues

Usage:
    python scripts/generate_troubleshooting_templates.py           # Generate
    python scripts/generate_troubleshooting_templates.py --check   # Verify
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from template_utils import render_and_output


@dataclass
class TroubleshootingTemplate:
    """Populated Troubleshooting template."""

    name: str
    title: str
    symptom: str
    diagnosis_steps: list[str]
    fix: str
    prevention: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = ""
    related_topics: list[dict[str, str]] = field(default_factory=list)


# Common troubleshooting scenarios derived from
# Lessons Learned and support patterns
_TROUBLESHOOTING: list[dict] = [
    {
        "name": "workflow-not-running",
        "title": "Workflow won't run",
        "symptom": "Running `attune workflow run <name>` produces no output or an authentication error.",
        "diagnosis_steps": [
            "Check if ANTHROPIC_API_KEY is set: `echo $ANTHROPIC_API_KEY`",
            "Verify the workflow name exists: `attune workflow list`",
            "Run `attune auth status` to check authentication strategy",
            "Run `attune doctor` for a full environment check",
        ],
        "fix": "Set your API key: `export ANTHROPIC_API_KEY=your-key`. If using subscription auth, run `attune auth setup`.",
        "prevention": "Add `ANTHROPIC_API_KEY` to your shell profile (`.zshrc` or `.bashrc`).",
        "tags": ["workflow", "auth", "setup"],
        "source": "common support pattern",
    },
    {
        "name": "mcp-server-not-responding",
        "title": "MCP server not responding",
        "symptom": "Claude Code skills don't trigger or show 'MCP server unavailable'.",
        "diagnosis_steps": [
            "Check `.mcp.json` exists in the project root",
            "Verify the command resolves: `which uv` or `which python`",
            "Check if the MCP process is running: `ps aux | grep attune`",
            "Test the server manually: `uv run python -m attune.mcp.server`",
        ],
        "fix": "Ensure `.mcp.json` uses `uv run` (not bare `python`) to resolve the correct venv. Restart Claude Code after fixing.",
        "prevention": "Use `uv run --from attune-ai` in .mcp.json to guarantee correct package resolution.",
        "tags": ["mcp", "claude-code", "setup"],
        "source": "CLAUDE.md Lessons Learned",
        "related_topics": [
            {"type": "Error", "description": "Custom MCP stdio loop fails Claude Code handshake"},
            {"type": "Error", "description": ".mcp.json python resolves to pyenv shim"},
        ],
    },
    {
        "name": "import-error-attune",
        "title": "ModuleNotFoundError for attune submodules",
        "symptom": "`ModuleNotFoundError: No module named 'attune.workflows'` or similar.",
        "diagnosis_steps": [
            "Check for a shadow `attune/` directory at the repo root: `ls -d attune/ 2>/dev/null`",
            "Verify installation: `pip show attune-ai`",
            "Check Python path: `python -c 'import attune; print(attune.__file__)'`",
        ],
        "fix": "Remove any `attune/` directory at the repo root that shadows the installed package. Reinstall: `pip install -e .`",
        "prevention": "Never create prototype directories matching the package name at the repo root.",
        "tags": ["imports", "python", "setup"],
        "source": "CLAUDE.md Lessons Learned",
        "related_topics": [
            {"type": "Error", "description": "Shadow directories at repo root break imports"},
        ],
    },
    {
        "name": "pre-commit-infinite-loop",
        "title": "Pre-commit hooks fail in a loop",
        "symptom": "Git commit fails repeatedly with black/ruff auto-fix, even after re-staging.",
        "diagnosis_steps": [
            "Check for unstaged tracked files: `git status`",
            "Look for stash conflicts: pre-commit stashes unstaged changes before running hooks",
            "Verify black/ruff are formatting the staged files: `uv run black --check <files>`",
        ],
        "fix": "Stash or add ALL unstaged tracked files before committing: `git stash push -- <unstaged files>`, then commit, then `git stash pop`.",
        "prevention": "Run `uv run ruff check --fix <files> && uv run black <files>` before staging. Commit with no unstaged tracked files.",
        "tags": ["git", "python", "ci"],
        "source": "CLAUDE.md Lessons Learned",
        "related_topics": [
            {"type": "Error", "description": "Pre-commit stash conflict with auto-fix hooks"},
            {
                "type": "Warning",
                "description": "Any unstaged file triggers pre-commit stash conflicts",
            },
        ],
    },
    {
        "name": "plugin-not-found",
        "title": "Claude Code plugin skills not available",
        "symptom": "Typing `/attune` or other skill commands shows no matches in Claude Code.",
        "diagnosis_steps": [
            "Check if plugin is installed: `claude plugin list`",
            "Verify the marketplace was added: `claude plugin marketplace list`",
            "Check for duplicate plugins that may conflict",
        ],
        "fix": "Reinstall: `claude plugin marketplace add Smart-AI-Memory/attune-ai && claude plugin install attune-ai@attune-ai`. Remove any conflicting plugins.",
        "prevention": "Only install one attune plugin (either attune-lite or attune-ai, not both).",
        "tags": ["claude-code", "plugin", "setup"],
        "source": "CLAUDE.md Lessons Learned",
        "related_topics": [
            {"type": "Error", "description": "Duplicate plugins cause conflicting skill triggers"},
        ],
    },
    {
        "name": "ci-tests-timeout",
        "title": "CI tests timing out",
        "symptom": "GitHub Actions test matrix fails with timeout on one or more platforms.",
        "diagnosis_steps": [
            "Check which platform timed out (Windows is ~3x slower)",
            "Look at `timeout-minutes` in the workflow YAML",
            "Check if new tests were added that significantly increase runtime",
        ],
        "fix": "Increase `timeout-minutes` in the workflow YAML. Windows needs ~45-60 min for the full suite. Update `test_timeout_values_are_reasonable` test if the upper bound changed.",
        "prevention": "Set Windows timeout to 60 min. Run targeted coverage (`pytest tests/unit/module/`) during development.",
        "tags": ["ci", "testing", "windows"],
        "source": "CLAUDE.md Lessons Learned",
    },
    {
        "name": "gpg-signing-fails",
        "title": "GPG signing fails in VSCode/Claude Code",
        "symptom": "Commits fail with `error: gpg failed to sign the data` in non-interactive terminals.",
        "diagnosis_steps": [
            "Check if `pinentry-mac` is installed: `which pinentry-mac`",
            "Verify `gpg-agent.conf` has the right pinentry-program (first line wins)",
            "Check if the GPG agent has a cached passphrase: `echo test | gpg --clearsign`",
        ],
        "fix": "Install `pinentry-mac` (`brew install pinentry-mac`). Set `pinentry-program /opt/homebrew/bin/pinentry-mac` as the FIRST line in `~/.gnupg/gpg-agent.conf`. Kill agent: `gpgconf --kill gpg-agent`.",
        "prevention": "Cache the passphrase by running `echo unlock | gpg --clearsign` in a real terminal before using VSCode.",
        "tags": ["git", "macos", "setup"],
        "source": "CLAUDE.md Lessons Learned",
    },
]


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Troubleshooting template generator."""
    if argv is None:
        argv = sys.argv[1:]

    check = "--check" in argv

    repo_root = Path(__file__).resolve().parent.parent
    templates_dir = repo_root / "plugin" / "help" / "templates"
    output_dir = repo_root / "plugin" / "help" / "generated" / "troubleshooting"

    if not templates_dir.exists():
        print(f"ERROR: {templates_dir} not found")
        return 1

    templates = [TroubleshootingTemplate(**t) for t in _TROUBLESHOOTING]
    print(f"  Troubleshooting guides: {len(templates)} found")

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    mode = "Checking" if check else "Generating"
    print(f"\n{mode} Troubleshooting templates from {len(templates)} entries\n")

    items = [
        {
            "name": t.name,
            "title": t.title,
            "symptom": t.symptom,
            "diagnosis_steps": t.diagnosis_steps,
            "fix": t.fix,
            "prevention": t.prevention,
            "tags": t.tags,
            "source": t.source,
            "related_topics": t.related_topics,
        }
        for t in templates
    ]

    successes, failures = render_and_output(
        env,
        "troubleshooting.md.jinja2",
        items,
        output_dir,
        check,
    )

    print(f"\n{'Checked' if check else 'Generated'}: {successes} ok, {failures} failed")
    print(f"Output: {output_dir}")

    if check and failures > 0:
        print("\nRun 'python scripts/generate_troubleshooting_templates.py' to regenerate.")

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
