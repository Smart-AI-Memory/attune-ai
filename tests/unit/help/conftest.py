"""Shared fixtures for help system tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_polish_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable the LLM polish pass in all help tests.

    Generator tests verify Jinja2 rendering, not LLM output.
    The polish pass is tested separately.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
