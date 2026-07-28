"""Tests for ``scripts/extract_contributing_setup.py`` (G4c lane).

The extractor is the drift-guard seam between CONTRIBUTING.md and
the clean-venv CI lane: it must execute the doc's LITERAL commands,
rewrite only the three contracted line classes (clone / cd / bare
pytest verification), and fail LOUDLY when the doc restructures.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "extract_contributing_setup.py"
_spec = importlib.util.spec_from_file_location("extract_contributing_setup", _SCRIPT)
ecs = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ecs
_spec.loader.exec_module(ecs)

DOC = (
    "# Contributing\n\n"
    "### Setup Development Environment\n\n"
    "```bash\n"
    "# Clone the repository\n"
    "git clone https://github.com/Smart-AI-Memory/attune-ai.git\n"
    "cd attune-ai\n\n"
    "python3 -m venv venv\n"
    "source venv/bin/activate\n\n"
    'pip install -e ".[dev]"\n\n'
    "pytest tests/\n"
    "```\n"
)


def test_extracts_and_rewrites_contracted_lines():
    script = ecs.extract(DOC)
    assert script.startswith("set -euo pipefail")
    assert "# [g4c: runs in the checkout under test] git clone" in script
    assert "# [g4c: runs in the checkout under test] cd attune-ai" in script
    assert 'pip install -e ".[dev]"' in script
    assert f"pytest tests/ {ecs.SMOKE_ARGS}" in script


def test_verbatim_lines_untouched():
    script = ecs.extract(DOC)
    assert "python3 -m venv venv" in script
    assert "source venv/bin/activate" in script


def test_missing_heading_fails_loudly():
    with pytest.raises(ValueError, match="heading"):
        ecs.extract("# Contributing\n\nno setup section here\n")


def test_missing_fence_fails_loudly():
    with pytest.raises(ValueError, match="no bash fence"):
        ecs.extract("### Setup Development Environment\n\nprose only\n")


def test_missing_pytest_line_fails_loudly():
    doc = DOC.replace("pytest tests/\n", "echo done\n")
    with pytest.raises(ValueError, match="pytest"):
        ecs.extract(doc)


def test_real_contributing_doc_satisfies_the_contract():
    """The repo's actual CONTRIBUTING.md must extract cleanly."""
    real = (_SCRIPT.parent.parent / "CONTRIBUTING.md").read_text(encoding="utf-8")
    script = ecs.extract(real)
    assert f"pytest tests/ {ecs.SMOKE_ARGS}" in script
    assert '".[dev]"' in script
