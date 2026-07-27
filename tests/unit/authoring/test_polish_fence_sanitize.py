"""Regression tests for the fence-wrap sanitization (2026-06-11).

The polish LLM occasionally returns the whole template wrapped in
a ```markdown fence. Unstripped, the fence defeats the generator's
frontmatter merge (its regex anchors at ``\\A---``), which then
prepends a SECOND frontmatter block and ships the fenced duplicate
as the body — the malformed shape observed live on 2026-06-11.
Poisoned responses were also cached, replaying the corruption on
keyless cache hits.
"""

from __future__ import annotations

import pytest

from attune.authoring.generator import _replace_polished_frontmatter
from attune.authoring.polish import (
    _sanitize_output,
    _strip_wrapping_fence,
    polish_template,
)

_CANONICAL = """---
type: concept
name: demo-concept
feature: demo
depth: concept
source_hash: abc123
---

# Demo

Deterministic body.
"""

_FENCED_ECHO = """```markdown
---
type: concept
name: demo-concept
feature: demo
depth: concept
source_hash: WRONGHASH
---

# Demo

Polished body prose.
```"""


class TestStripWrappingFence:
    def test_strips_markdown_fence_wrap(self) -> None:
        out = _strip_wrapping_fence(_FENCED_ECHO)
        assert out.startswith("---\n")
        assert "```" not in out

    def test_strips_bare_fence_wrap(self) -> None:
        out = _strip_wrapping_fence("```\n# Title\n\nBody.\n```")
        assert out == "# Title\n\nBody."

    def test_no_fence_unchanged(self) -> None:
        text = "# Title\n\nBody.\n"
        assert _strip_wrapping_fence(text) == text

    def test_interior_code_blocks_preserved(self) -> None:
        text = "# Title\n\n```python\nprint('hi')\n```\n\nMore.\n"
        assert _strip_wrapping_fence(text) == text

    def test_unclosed_fence_unchanged(self) -> None:
        text = "```markdown\n# Title\n\nBody without closing fence.\n"
        assert _strip_wrapping_fence(text) == text

    def test_wrap_around_interior_blocks(self) -> None:
        text = "```markdown\n# T\n\n```python\nx = 1\n```\n\nTail.\n```"
        out = _strip_wrapping_fence(text)
        assert out.startswith("# T")
        assert "```python" in out
        assert not out.rstrip().endswith("```\n```")


class TestSanitizeOutput:
    def test_fenced_response_sanitizes_to_frontmatter_start(self) -> None:
        assert _sanitize_output(_FENCED_ECHO).startswith("---\n")

    def test_frontmatter_merge_after_sanitize_yields_single_block(self) -> None:
        # End-to-end reproduction of the 2026-06-11 malformed shape:
        # without sanitization the merge prepends a second
        # frontmatter block above the fenced echo.
        merged = _replace_polished_frontmatter(_sanitize_output(_FENCED_ECHO), _CANONICAL)
        assert merged.count("type: concept") == 1
        assert "```" not in merged
        # Deterministic field restored from canonical, not the echo.
        assert "source_hash: abc123" in merged
        assert "WRONGHASH" not in merged
        # The polished body survived.
        assert "Polished body prose." in merged


class TestCacheReadHealing:
    def test_poisoned_cache_hit_is_sanitized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pre-fix cache entries carrying the fence heal on read."""
        import attune.authoring.polish as polish_mod

        monkeypatch.setattr(polish_mod, "_cache_get", lambda key: _FENCED_ECHO)

        def _no_llm(*args, **kwargs):  # pragma: no cover - guard
            raise AssertionError("cache hit must not call the LLM")

        monkeypatch.setattr(polish_mod, "_call_llm", _no_llm)
        out = polish_template(
            content=_CANONICAL,
            feature_name="demo",
            source_summary="src",
            template_type="concept",
        )
        assert out.startswith("---\n")
        assert "```" not in out
