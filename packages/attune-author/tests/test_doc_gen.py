"""Tests for attune_author.doc_gen pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune_author.doc_gen import DocGenConfig, DocGenResult, generate_docs
from attune_author.doc_gen.stages import (
    build_outline,
    parse_outline_sections,
    review_content,
    write_content,
)


class TestDocGenConfig:
    """Tests for DocGenConfig."""

    def test_defaults(self) -> None:
        """Test default config values."""
        cfg = DocGenConfig()
        assert cfg.doc_type == "api-reference"
        assert cfg.audience == "developers"
        assert cfg.max_outline_tokens == 1000
        assert cfg.section_focus == []

    def test_overrides(self) -> None:
        """Test custom config values."""
        cfg = DocGenConfig(
            doc_type="guide",
            audience="beginners",
            max_outline_tokens=2000,
            section_focus=["intro", "setup"],
        )
        assert cfg.doc_type == "guide"
        assert cfg.section_focus == ["intro", "setup"]


class TestParseOutlineSections:
    """Tests for parse_outline_sections()."""

    def test_parses_numbered_sections(self) -> None:
        """Test parsing top-level numbered sections."""
        outline = "1. Introduction\n" "   1.1 Background\n" "2. Setup\n" "3. API Reference\n"
        sections = parse_outline_sections(outline)
        assert sections == ["Introduction", "Setup", "API Reference"]

    def test_strips_subtitles(self) -> None:
        """Test that subtitles after dashes are stripped."""
        outline = "1. Quick Start - Get up and running\n2. Reference\n"
        sections = parse_outline_sections(outline)
        assert sections == ["Quick Start", "Reference"]

    def test_empty_outline(self) -> None:
        """Test empty outline returns empty list."""
        assert parse_outline_sections("") == []

    def test_no_numbered_lines(self) -> None:
        """Test outline without numbered lines returns empty."""
        assert parse_outline_sections("Just some text\nMore text\n") == []


class TestStages:
    """Tests for the three stages: outline, write, review."""

    def _mock_client(self, response_text: str) -> MagicMock:
        """Build a mock Anthropic client."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=response_text)]
        client = MagicMock()
        client.messages.create.return_value = mock_response
        return client

    def test_build_outline(self) -> None:
        """Test outline generation."""
        client = self._mock_client("1. Intro\n2. API\n3. Examples")
        result = build_outline(
            client=client,
            source_content="def foo(): pass",
            doc_type="api-reference",
            audience="developers",
            model="claude-sonnet-4",
            max_tokens=1000,
        )
        assert "1. Intro" in result
        client.messages.create.assert_called_once()

    def test_write_content(self) -> None:
        """Test content writing."""
        client = self._mock_client("# Documentation\n\nDetails...")
        result = write_content(
            client=client,
            outline="1. Intro\n2. API",
            source_content="def foo(): pass",
            doc_type="api-reference",
            audience="developers",
            model="claude-sonnet-4",
            max_tokens=4000,
        )
        assert "# Documentation" in result

    def test_write_content_with_section_focus(self) -> None:
        """Test write with section focus instructions."""
        client = self._mock_client("# Section A only\n")
        result = write_content(
            client=client,
            outline="1. A\n2. B",
            source_content="code",
            doc_type="guide",
            audience="developers",
            model="claude-sonnet-4",
            max_tokens=2000,
            section_focus=["A"],
        )
        assert result == "# Section A only\n"

        # Verify focus instruction was passed in system prompt
        call_args = client.messages.create.call_args
        system = call_args.kwargs["system"]
        assert "A" in system

    def test_review_content(self) -> None:
        """Test review and polish."""
        client = self._mock_client("# Polished\n\nClean docs.")
        result = review_content(
            client=client,
            draft="# Draft\n\nRough.",
            source_content="def foo(): pass",
            doc_type="api-reference",
            audience="developers",
            model="claude-sonnet-4",
            max_tokens=4000,
        )
        assert "Polished" in result

    def test_review_falls_back_to_draft_on_empty_response(self) -> None:
        """Test review returns draft if response is empty."""
        client = MagicMock()
        client.messages.create.return_value = MagicMock(content=None)

        result = review_content(
            client=client,
            draft="# Original draft",
            source_content="code",
            doc_type="guide",
            audience="devs",
            model="claude-sonnet-4",
            max_tokens=1000,
        )
        assert result == "# Original draft"


class TestGenerateDocs:
    """Tests for the generate_docs pipeline orchestrator."""

    def test_raises_without_api_key(self) -> None:
        """Test that missing API key raises RuntimeError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                generate_docs("def foo(): pass")

    def test_runs_three_stages(self, tmp_path: Path) -> None:
        """Test that all three stages run in order."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="stage output")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = generate_docs("def foo(): pass")

        assert isinstance(result, DocGenResult)
        assert result.stages_completed == ["outline", "write", "review"]
        assert mock_client.messages.create.call_count == 3

    def test_reads_target_file(self, tmp_path: Path) -> None:
        """Test that file paths are read."""
        source_file = tmp_path / "source.py"
        source_file.write_text("def my_function(): return 42\n")

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="docs")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("anthropic.Anthropic", return_value=mock_client):
                result = generate_docs(str(source_file))

        assert result.source_path == str(source_file)
        # The first call (outline) should have received the file content
        first_call = mock_client.messages.create.call_args_list[0]
        user_msg = first_call.kwargs["messages"][0]["content"]
        assert "my_function" in user_msg

    def test_writes_output_file(self, tmp_path: Path) -> None:
        """Test that output is written when output_path is given."""
        out = tmp_path / "out" / "docs.md"

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="final docs")]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake"}):  # pragma: allowlist secret
            with patch("anthropic.Anthropic", return_value=mock_client):
                generate_docs("source", output_path=str(out))

        assert out.exists()
        assert out.read_text() == "final docs"
