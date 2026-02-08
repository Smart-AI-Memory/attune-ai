"""Comprehensive tests for keyboard shortcut generators.

Tests cover:
- VSCode keybindings.json generation
- CLI alias script generation
- Markdown documentation generation
- Multi-layout support
- Error handling and edge cases
"""

import json
from pathlib import Path

import pytest

from attune.workflows.keyboard_shortcuts.generators import (
    CLIAliasGenerator,
    ComprehensiveGenerator,
    MarkdownDocGenerator,
    VSCodeKeybindingsGenerator,
)
from attune.workflows.keyboard_shortcuts.schema import (
    Category,
    Feature,
    FeatureManifest,
    FrequencyTier,
    GeneratedShortcuts,
    KeyboardLayout,
    LayoutShortcuts,
    ScaleAssignments,
    ShortcutAssignment,
)


@pytest.fixture
def sample_manifest():
    """Create a sample feature manifest for testing."""
    features = [
        Feature(
            id="morning",
            name="Morning Briefing",
            description="Daily morning status",
            command="empathy.morning",
            cli_alias="empathy morning",
            frequency=FrequencyTier.DAILY,
        ),
        Feature(
            id="ship",
            name="Ship Check",
            description="Check if ready to ship",
            command="empathy.ship",
            cli_alias="empathy ship",
            frequency=FrequencyTier.DAILY,
        ),
        Feature(
            id="dashboard",
            name="Dashboard",
            description="View dashboard",
            command="empathy.dashboard",
            frequency=FrequencyTier.FREQUENT,
        ),
    ]

    categories = [
        Category(
            name="Quick Actions",
            tier=FrequencyTier.DAILY,
            features=features[:2],
        ),
        Category(
            name="Views",
            tier=FrequencyTier.FREQUENT,
            features=features[2:],
        ),
    ]

    return FeatureManifest(
        project_name="empathy-framework",
        project_type="vscode-extension",
        prefix="ctrl+shift+e",
        categories=categories,
    )


@pytest.fixture
def sample_generated_shortcuts(sample_manifest):
    """Create sample generated shortcuts for testing."""
    qwerty_shortcuts = [
        ShortcutAssignment(
            feature_id="morning",
            key="m",
            mnemonic="M = Morning",
            layout=KeyboardLayout.QWERTY,
        ),
        ShortcutAssignment(
            feature_id="ship",
            key="s",
            mnemonic="S = Ship",
            layout=KeyboardLayout.QWERTY,
        ),
        ShortcutAssignment(
            feature_id="dashboard",
            key="d",
            mnemonic="D = Dashboard",
            layout=KeyboardLayout.QWERTY,
        ),
    ]

    qwerty_layout = LayoutShortcuts(
        layout=KeyboardLayout.QWERTY,
        shortcuts=qwerty_shortcuts,
        scale_assignments=ScaleAssignments(
            daily=["m", "s"],
            frequent=["d"],
            advanced=[],
        ),
        phrase_mnemonic="My Ship Docks",
    )

    generated = GeneratedShortcuts(manifest=sample_manifest)
    generated.layouts[KeyboardLayout.QWERTY] = qwerty_layout

    return generated


class TestVSCodeKeybindingsGenerator:
    """Tests for VSCode keybindings.json generator."""

    def test_generate_creates_output_directory(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates output directory if missing."""
        generator = VSCodeKeybindingsGenerator()
        output_dir = tmp_path / "keybindings"

        assert not output_dir.exists()

        generator.generate(sample_generated_shortcuts, output_dir)

        assert output_dir.exists()

    def test_generate_creates_file_per_layout(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates one file per layout."""
        generator = VSCodeKeybindingsGenerator()
        output_dir = tmp_path / "keybindings"

        generated_files = generator.generate(sample_generated_shortcuts, output_dir)

        assert "qwerty" in generated_files
        assert generated_files["qwerty"].exists()

    def test_generate_creates_valid_json(self, tmp_path, sample_generated_shortcuts):
        """Test that generated keybindings are valid JSON."""
        generator = VSCodeKeybindingsGenerator()
        output_dir = tmp_path / "keybindings"

        generated_files = generator.generate(sample_generated_shortcuts, output_dir)

        qwerty_file = generated_files["qwerty"]
        content = json.loads(qwerty_file.read_text(encoding="utf-8"))

        assert isinstance(content, list)

    def test_generate_includes_all_shortcuts(self, tmp_path, sample_generated_shortcuts):
        """Test that all shortcuts are included in output."""
        generator = VSCodeKeybindingsGenerator()
        output_dir = tmp_path / "keybindings"

        generated_files = generator.generate(sample_generated_shortcuts, output_dir)

        qwerty_file = generated_files["qwerty"]
        bindings = json.loads(qwerty_file.read_text(encoding="utf-8"))

        assert len(bindings) == 3

    def test_generate_bindings_format(self, sample_manifest, sample_generated_shortcuts):
        """Test keybinding entry format."""
        generator = VSCodeKeybindingsGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        bindings = generator._generate_bindings(sample_manifest, layout_shortcuts)

        assert len(bindings) == 3
        assert bindings[0]["key"] == "ctrl+shift+e m"
        assert bindings[0]["mac"] == "cmd+shift+e m"
        assert bindings[0]["command"] == "empathy.morning"
        assert bindings[0]["// mnemonic"] == "M = Morning"

    def test_generate_bindings_converts_ctrl_to_cmd_for_mac(
        self, sample_manifest, sample_generated_shortcuts
    ):
        """Test that ctrl is converted to cmd for Mac shortcuts."""
        generator = VSCodeKeybindingsGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        bindings = generator._generate_bindings(sample_manifest, layout_shortcuts)

        for binding in bindings:
            assert "ctrl" in binding["key"]
            assert "cmd" in binding["mac"]
            assert "ctrl" not in binding["mac"]

    def test_generate_bindings_skips_missing_commands(self, sample_manifest):
        """Test that shortcuts with missing commands are skipped."""
        generator = VSCodeKeybindingsGenerator()

        layout_shortcuts = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[
                ShortcutAssignment(
                    feature_id="nonexistent",
                    key="x",
                    mnemonic="X = Unknown",
                ),
            ],
        )

        bindings = generator._generate_bindings(sample_manifest, layout_shortcuts)

        assert len(bindings) == 0

    def test_find_command_returns_correct_command(self, sample_manifest):
        """Test finding command for a feature ID."""
        generator = VSCodeKeybindingsGenerator()

        command = generator._find_command(sample_manifest, "morning")

        assert command == "empathy.morning"

    def test_find_command_returns_none_for_missing_feature(self, sample_manifest):
        """Test finding command for non-existent feature."""
        generator = VSCodeKeybindingsGenerator()

        command = generator._find_command(sample_manifest, "nonexistent")

        assert command is None

    def test_generate_multiple_layouts(self, tmp_path, sample_manifest):
        """Test generating keybindings for multiple layouts."""
        generator = VSCodeKeybindingsGenerator()

        # Create shortcuts for multiple layouts
        generated = GeneratedShortcuts(manifest=sample_manifest)

        for layout in [KeyboardLayout.QWERTY, KeyboardLayout.DVORAK]:
            generated.layouts[layout] = LayoutShortcuts(
                layout=layout,
                shortcuts=[
                    ShortcutAssignment(
                        feature_id="morning",
                        key="m",
                        mnemonic="M = Morning",
                        layout=layout,
                    ),
                ],
            )

        output_dir = tmp_path / "keybindings"
        generated_files = generator.generate(generated, output_dir)

        assert len(generated_files) == 2
        assert "qwerty" in generated_files
        assert "dvorak" in generated_files


class TestCLIAliasGenerator:
    """Tests for CLI alias script generator."""

    def test_generate_creates_parent_directory(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates parent directory if missing."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "subdir" / "aliases.sh"

        assert not output_file.parent.exists()

        generator.generate(sample_generated_shortcuts, output_file)

        assert output_file.parent.exists()

    def test_generate_creates_file(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates output file."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        result = generator.generate(sample_generated_shortcuts, output_file)

        assert result == output_file
        assert output_file.exists()

    def test_generate_includes_header(self, tmp_path, sample_generated_shortcuts):
        """Test that generated script includes header."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "#!/bin/bash" in content
        assert "Keyboard Conductor CLI Aliases" in content
        assert "empathy-framework" in content

    def test_generate_includes_mnemonic_in_header(self, tmp_path, sample_generated_shortcuts):
        """Test that mnemonic phrase is included in header."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "My Ship Docks" in content

    def test_generate_creates_short_aliases(self, tmp_path, sample_generated_shortcuts):
        """Test that short aliases are created (e.g., 'em' for empathy morning)."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert 'alias em="empathy morning"' in content
        assert 'alias es="empathy ship"' in content

    def test_generate_includes_mnemonic_comments(self, tmp_path, sample_generated_shortcuts):
        """Test that mnemonic comments are included for each alias."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "# M = Morning" in content
        assert "# S = Ship" in content

    def test_generate_skips_features_without_cli_alias(self, tmp_path, sample_generated_shortcuts):
        """Test that features without CLI alias are skipped."""
        generator = CLIAliasGenerator()
        output_file = tmp_path / "aliases.sh"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        # Dashboard has no cli_alias, should not appear
        assert "ed=" not in content or "dashboard" not in content.lower()

    def test_generate_uses_qwerty_layout_by_default(self, tmp_path, sample_manifest):
        """Test that QWERTY layout is used for CLI by default."""
        generator = CLIAliasGenerator()

        # Create shortcuts with only DVORAK
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.DVORAK] = LayoutShortcuts(
            layout=KeyboardLayout.DVORAK,
            shortcuts=[
                ShortcutAssignment(
                    feature_id="morning",
                    key="a",
                    mnemonic="A = Morning (Dvorak)",
                    layout=KeyboardLayout.DVORAK,
                ),
            ],
            phrase_mnemonic="Dvorak phrase",
        )

        output_file = tmp_path / "aliases.sh"
        generator.generate(generated, output_file)

        content = output_file.read_text(encoding="utf-8")

        # Should use Dvorak since QWERTY not available
        assert "Dvorak phrase" in content

    def test_generate_handles_no_shortcuts(self, tmp_path, sample_manifest):
        """Test handling when no shortcuts are generated."""
        generator = CLIAliasGenerator()

        generated = GeneratedShortcuts(manifest=sample_manifest)
        output_file = tmp_path / "aliases.sh"

        generator.generate(generated, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "# No shortcuts generated" in content

    def test_find_cli_alias_returns_correct_alias(self, sample_manifest):
        """Test finding CLI alias for a feature."""
        generator = CLIAliasGenerator()

        cli_alias = generator._find_cli_alias(sample_manifest, "morning")

        assert cli_alias == "empathy morning"

    def test_find_cli_alias_returns_none_for_missing_feature(self, sample_manifest):
        """Test finding CLI alias for non-existent feature."""
        generator = CLIAliasGenerator()

        cli_alias = generator._find_cli_alias(sample_manifest, "nonexistent")

        assert cli_alias is None


class TestMarkdownDocGenerator:
    """Tests for Markdown documentation generator."""

    def test_generate_creates_parent_directory(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates parent directory if missing."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "subdir" / "SHORTCUTS.md"

        assert not output_file.parent.exists()

        generator.generate(sample_generated_shortcuts, output_file)

        assert output_file.parent.exists()

    def test_generate_creates_file(self, tmp_path, sample_generated_shortcuts):
        """Test that generator creates output file."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        result = generator.generate(sample_generated_shortcuts, output_file)

        assert result == output_file
        assert output_file.exists()

    def test_generate_includes_project_name(self, tmp_path, sample_generated_shortcuts):
        """Test that project name is included in documentation."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "empathy-framework" in content

    def test_generate_includes_phrase_mnemonic(self, tmp_path, sample_generated_shortcuts):
        """Test that phrase mnemonic is included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "My Ship Docks" in content

    def test_generate_includes_prefix_instructions(self, tmp_path, sample_generated_shortcuts):
        """Test that prefix key instructions are included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "ctrl+shift+e" in content.lower()
        assert "cmd+shift+e" in content.lower()  # Mac version

    def test_generate_includes_keyboard_diagram(self, tmp_path, sample_generated_shortcuts):
        """Test that ASCII keyboard diagram is included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        # Should contain keyboard layout characters
        assert "[Q][W][E]" in content or "Q][W][E" in content

    def test_generate_includes_scales_section(self, tmp_path, sample_generated_shortcuts):
        """Test that learning scales section is included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "Scale 1" in content or "The Basics" in content
        assert "Scale 2" in content or "The Workflows" in content
        assert "Scale 3" in content or "Full Orchestra" in content

    def test_generate_includes_full_table(self, tmp_path, sample_generated_shortcuts):
        """Test that full shortcuts table is included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        # Should contain table headers
        assert "| Key |" in content or "|Key|" in content
        assert "Morning" in content
        assert "Ship" in content

    def test_generate_includes_empathy_attribution(self, tmp_path, sample_generated_shortcuts):
        """Test that Empathy Framework attribution is included."""
        generator = MarkdownDocGenerator()
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(sample_generated_shortcuts, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "Empathy Framework" in content

    def test_generate_handles_no_shortcuts(self, tmp_path, sample_manifest):
        """Test handling when no shortcuts are generated."""
        generator = MarkdownDocGenerator()

        generated = GeneratedShortcuts(manifest=sample_manifest)
        output_file = tmp_path / "SHORTCUTS.md"

        generator.generate(generated, output_file)

        content = output_file.read_text(encoding="utf-8")

        assert "# No shortcuts generated" in content

    def test_generate_cheatsheet_groups_by_scale(self, sample_manifest, sample_generated_shortcuts):
        """Test that cheatsheet groups shortcuts by scale."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        cheatsheet = generator._generate_cheatsheet(sample_manifest, layout_shortcuts)

        assert "Daily" in cheatsheet or "daily" in cheatsheet.lower()
        assert "Frequent" in cheatsheet or "frequent" in cheatsheet.lower()

    def test_generate_keyboard_diagram_highlights_active_keys(self, sample_generated_shortcuts):
        """Test that keyboard diagram highlights used keys."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        diagram = generator._generate_keyboard_diagram(layout_shortcuts)

        # Should contain highlighted keys
        assert "M" in diagram or "m" in diagram
        assert "S" in diagram or "s" in diagram

    def test_generate_scales_section_shows_progression(
        self, sample_manifest, sample_generated_shortcuts
    ):
        """Test that scales section shows learning progression."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        scales = generator._generate_scales_section(sample_manifest, layout_shortcuts)

        # Should show scale 1 and scale 2
        assert "m" in scales.lower() or "M" in scales
        assert "s" in scales.lower() or "S" in scales

    def test_generate_full_table_includes_all_shortcuts(
        self, sample_manifest, sample_generated_shortcuts
    ):
        """Test that full table includes all shortcuts."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        table = generator._generate_full_table(sample_manifest, layout_shortcuts)

        assert "Morning" in table
        assert "Ship" in table
        assert "Dashboard" in table

    def test_find_shortcut_by_key_returns_correct_shortcut(self, sample_generated_shortcuts):
        """Test finding shortcut by key."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        shortcut = generator._find_shortcut_by_key(layout_shortcuts, "m")

        assert shortcut is not None
        assert shortcut.feature_id == "morning"

    def test_find_shortcut_by_key_case_insensitive(self, sample_generated_shortcuts):
        """Test that key search is case-insensitive."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        shortcut = generator._find_shortcut_by_key(layout_shortcuts, "M")

        assert shortcut is not None
        assert shortcut.feature_id == "morning"

    def test_find_shortcut_by_key_returns_none_for_missing(self, sample_generated_shortcuts):
        """Test finding non-existent shortcut."""
        generator = MarkdownDocGenerator()

        layout_shortcuts = sample_generated_shortcuts.layouts[KeyboardLayout.QWERTY]
        shortcut = generator._find_shortcut_by_key(layout_shortcuts, "z")

        assert shortcut is None

    def test_find_feature_returns_correct_feature(self, sample_manifest):
        """Test finding feature by ID."""
        generator = MarkdownDocGenerator()

        feature = generator._find_feature(sample_manifest, "morning")

        assert feature is not None
        assert feature.name == "Morning Briefing"

    def test_find_feature_returns_none_for_missing(self, sample_manifest):
        """Test finding non-existent feature."""
        generator = MarkdownDocGenerator()

        feature = generator._find_feature(sample_manifest, "nonexistent")

        assert feature is None


class TestComprehensiveGenerator:
    """Tests for comprehensive generator that creates all formats."""

    def test_initialization(self):
        """Test comprehensive generator initializes all sub-generators."""
        generator = ComprehensiveGenerator()

        assert isinstance(generator.vscode_gen, VSCodeKeybindingsGenerator)
        assert isinstance(generator.cli_gen, CLIAliasGenerator)
        assert isinstance(generator.markdown_gen, MarkdownDocGenerator)

    def test_generate_all_creates_output_directory(self, tmp_path, sample_generated_shortcuts):
        """Test that generate_all creates output directory."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        assert not output_dir.exists()

        generator.generate_all(sample_generated_shortcuts, output_dir)

        assert output_dir.exists()

    def test_generate_all_creates_all_formats(self, tmp_path, sample_generated_shortcuts):
        """Test that all output formats are created."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        assert "vscode" in generated
        assert "cli" in generated
        assert "docs" in generated

    def test_generate_all_creates_vscode_keybindings(self, tmp_path, sample_generated_shortcuts):
        """Test that VSCode keybindings are created."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        vscode_files = generated["vscode"]
        assert "qwerty" in vscode_files
        assert vscode_files["qwerty"].exists()

    def test_generate_all_creates_cli_aliases(self, tmp_path, sample_generated_shortcuts):
        """Test that CLI aliases are created."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        cli_file = generated["cli"]
        assert cli_file.exists()
        assert cli_file.name == "aliases.sh"

    def test_generate_all_creates_markdown_docs(self, tmp_path, sample_generated_shortcuts):
        """Test that Markdown documentation is created."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        docs_file = generated["docs"]
        assert docs_file.exists()
        assert docs_file.name == "KEYBOARD_SHORTCUTS.md"

    def test_generate_all_organizes_keybindings_in_subdirectory(
        self, tmp_path, sample_generated_shortcuts
    ):
        """Test that keybindings are organized in subdirectory."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        vscode_files = generated["vscode"]
        for path in vscode_files.values():
            assert "keybindings" in str(path)

    def test_generate_all_returns_all_paths(self, tmp_path, sample_generated_shortcuts):
        """Test that all generated file paths are returned."""
        generator = ComprehensiveGenerator()
        output_dir = tmp_path / "output"

        generated = generator.generate_all(sample_generated_shortcuts, output_dir)

        # VSCode returns dict of layouts
        assert isinstance(generated["vscode"], dict)
        # CLI and docs return single paths
        assert isinstance(generated["cli"], Path)
        assert isinstance(generated["docs"], Path)
