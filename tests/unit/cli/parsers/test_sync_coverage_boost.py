"""Tests for sync CLI parsers.

Module: cli/parsers/sync.py (31 lines)
"""

from argparse import ArgumentParser

import pytest

from attune.cli.parsers.sync import register_parsers

# ============================================================================
# register_parsers Tests
# ============================================================================


@pytest.mark.unit
class TestRegisterParsers:
    """Test suite for sync parser registration."""

    def test_register_parsers_adds_sync_claude(self):
        """Test that register_parsers adds sync-claude command."""
        # Given
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # When
        register_parsers(subparsers)

        # Then
        # Parse with sync-claude to verify it was registered
        args = parser.parse_args(["sync-claude"])
        assert hasattr(args, "func")

    def test_sync_claude_has_patterns_dir_arg(self):
        """Test that sync-claude has --patterns-dir argument."""
        # Given
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()
        register_parsers(subparsers)

        # When
        args = parser.parse_args(["sync-claude", "--patterns-dir", "custom/patterns"])

        # Then
        assert args.patterns_dir == "custom/patterns"

    def test_sync_claude_has_output_dir_arg(self):
        """Test that sync-claude has --output-dir argument."""
        # Given
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()
        register_parsers(subparsers)

        # When
        args = parser.parse_args(["sync-claude", "--output-dir", "custom/output"])

        # Then
        assert args.output_dir == "custom/output"

    def test_sync_claude_default_patterns_dir(self):
        """Test that sync-claude has correct default for patterns-dir."""
        # Given
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()
        register_parsers(subparsers)

        # When
        args = parser.parse_args(["sync-claude"])

        # Then
        assert args.patterns_dir == "patterns"

    def test_sync_claude_default_output_dir(self):
        """Test that sync-claude has correct default for output-dir."""
        # Given
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()
        register_parsers(subparsers)

        # When
        args = parser.parse_args(["sync-claude"])

        # Then
        assert args.output_dir == ".claude/rules/attune"
