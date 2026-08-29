"""Tests for scripts/normalize_website_tsconfig.py (retro 6a).

The pre-commit hook auto-reverts next-dev's ``jsx: preserve`` flip
in ``website/tsconfig.json``. Pin both directions: the flip is
reverted (with an accurate count — a zero-count silent no-op is the
masking-lesson failure mode), and an already-canonical file is left
byte-identical.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "normalize_website_tsconfig.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_normalize_tsconfig", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_flip_is_reverted_with_count(mod):
    fixed, count = mod.normalize('{\n  "jsx": "preserve",\n}')
    assert count == 1
    assert '"jsx": "react-jsx"' in fixed
    assert "preserve" not in fixed


def test_canonical_file_untouched(mod):
    text = '{\n  "jsx": "react-jsx",\n}'
    fixed, count = mod.normalize(text)
    assert count == 0
    assert fixed == text


def test_whitespace_variant_matched(mod):
    fixed, count = mod.normalize('{"jsx" : "preserve"}')
    assert count == 1
    assert fixed == '{"jsx": "react-jsx"}'


def test_live_tsconfig_is_canonical(mod):
    """The tracked website/tsconfig.json must not carry the flip."""
    text = (REPO / "website" / "tsconfig.json").read_text(encoding="utf-8")
    _, count = mod.normalize(text)
    assert count == 0, "website/tsconfig.json carries next-dev's jsx flip — revert it"
