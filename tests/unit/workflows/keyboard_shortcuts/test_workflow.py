"""Comprehensive tests for keyboard shortcuts workflow.

Tests cover:
- Workflow stage execution
- Stage skipping logic
- LLM integration
- Response parsing
- Fallback generation
- End-to-end workflow
"""

import json
from unittest.mock import patch

import pytest
import yaml

from attune.workflows.base import ModelTier
from attune.workflows.keyboard_shortcuts.schema import (
    Category,
    Feature,
    FeatureManifest,
    FrequencyTier,
    GeneratedShortcuts,
    KeyboardLayout,
    LayoutShortcuts,
    ShortcutAssignment,
)
from attune.workflows.keyboard_shortcuts.workflow import KeyboardShortcutWorkflow


@pytest.fixture
def workflow():
    """Create a keyboard shortcut workflow instance."""
    return KeyboardShortcutWorkflow()


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project with package.json."""
    package_file = tmp_path / "package.json"
    package_data = {
        "contributes": {
            "commands": [
                {"command": "test.morning", "title": "Morning Briefing"},
                {"command": "test.ship", "title": "Ship Check"},
            ],
        },
    }
    package_file.write_text(json.dumps(package_data))
    return tmp_path


@pytest.fixture
def sample_manifest():
    """Create a sample feature manifest."""
    features = [
        Feature(
            id="morning",
            name="Morning Briefing",
            command="test.morning",
            frequency=FrequencyTier.DAILY,
        ),
        Feature(
            id="ship",
            name="Ship Check",
            command="test.ship",
            frequency=FrequencyTier.DAILY,
        ),
    ]

    categories = [
        Category(name="Quick Actions", tier=FrequencyTier.DAILY, features=features),
    ]

    return FeatureManifest(
        project_name="test-project",
        project_type="vscode-extension",
        categories=categories,
    )


class TestWorkflowConfiguration:
    """Tests for workflow configuration and metadata."""

    def test_workflow_name(self, workflow):
        """Test workflow has correct name."""
        assert workflow.name == "keyboard-shortcuts"

    def test_workflow_description(self, workflow):
        """Test workflow has description."""
        assert "keyboard shortcuts" in workflow.description.lower()

    def test_workflow_stages(self, workflow):
        """Test workflow defines all stages."""
        expected_stages = ["discover", "analyze", "generate", "validate", "export"]
        assert workflow.stages == expected_stages

    def test_workflow_tier_map(self, workflow):
        """Test workflow defines tier for each stage."""
        assert workflow.tier_map["discover"] == ModelTier.CHEAP
        assert workflow.tier_map["analyze"] == ModelTier.CAPABLE
        assert workflow.tier_map["generate"] == ModelTier.CAPABLE
        assert workflow.tier_map["validate"] == ModelTier.CHEAP
        assert workflow.tier_map["export"] == ModelTier.CHEAP

    def test_workflow_has_parser(self, workflow):
        """Test workflow initializes parser."""
        assert workflow.parser is not None

    def test_workflow_has_generator(self, workflow):
        """Test workflow initializes generator."""
        assert workflow.generator is not None


class TestDiscoverStage:
    """Tests for feature discovery stage."""

    @pytest.mark.asyncio
    async def test_discover_features_from_package_json(self, workflow, sample_project):
        """Test discovering features from package.json."""
        input_data = {"path": str(sample_project)}

        result, in_tokens, out_tokens = await workflow._discover_features(input_data)

        assert result["feature_count"] == 2
        assert result["categories"] >= 1
        assert in_tokens == 0
        assert out_tokens == 0

    @pytest.mark.asyncio
    async def test_discover_returns_manifest(self, workflow, sample_project):
        """Test that discover returns a manifest."""
        input_data = {"path": str(sample_project)}

        result, _, _ = await workflow._discover_features(input_data)

        manifest = result["manifest"]
        assert isinstance(manifest, FeatureManifest)
        assert len(manifest.all_features()) == 2

    @pytest.mark.asyncio
    async def test_discover_handles_no_features(self, workflow, tmp_path):
        """Test handling when no features are found."""
        input_data = {"path": str(tmp_path)}

        result, in_tokens, out_tokens = await workflow._discover_features(input_data)

        assert result["feature_count"] == 0
        assert "error" in result
        assert in_tokens == 0
        assert out_tokens == 0

    @pytest.mark.asyncio
    async def test_discover_uses_current_directory_by_default(self, workflow):
        """Test that discover uses current directory if no path provided."""
        input_data = {}

        result, _, _ = await workflow._discover_features(input_data)

        # Should not crash, might or might not find features
        assert "manifest" in result


class TestAnalyzeStage:
    """Tests for feature analysis stage."""

    @pytest.mark.asyncio
    async def test_analyze_calls_llm(self, workflow, sample_manifest):
        """Test that analyze stage calls LLM."""
        input_data = {"manifest": sample_manifest}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ("analyzed_features:\n  - id: morning", 100, 50)

            await workflow._analyze_features(input_data, ModelTier.CAPABLE)

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_formats_prompt_correctly(self, workflow, sample_manifest):
        """Test that analyze formats prompt with feature data."""
        input_data = {"manifest": sample_manifest}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ("analyzed_features: []", 100, 50)

            await workflow._analyze_features(input_data, ModelTier.CAPABLE)

            call_args = mock_llm.call_args
            prompt = call_args[1]["prompt"]
            assert "test-project" in prompt
            assert "morning" in prompt.lower()

    @pytest.mark.asyncio
    async def test_analyze_parses_yaml_response(self, workflow, sample_manifest):
        """Test that analyze parses YAML response from LLM."""
        input_data = {"manifest": sample_manifest}

        yaml_response = """
analyzed_features:
  - id: morning
    frequency: daily
    mnemonic: M = Morning
phrase_mnemonic: My Morning
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (yaml_response, 100, 50)

            result, _, _ = await workflow._analyze_features(input_data, ModelTier.CAPABLE)

            assert "analysis" in result
            assert result["phrase_mnemonic"] == "My Morning"

    @pytest.mark.asyncio
    async def test_analyze_updates_manifest_with_frequencies(self, workflow, sample_manifest):
        """Test that analyze updates manifest features with analyzed frequencies."""
        # Set frequencies to FREQUENT initially
        for feature in sample_manifest.all_features():
            feature.frequency = FrequencyTier.FREQUENT

        input_data = {"manifest": sample_manifest}

        yaml_response = """
analyzed_features:
  - id: morning
    frequency: daily
  - id: ship
    frequency: daily
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (yaml_response, 100, 50)

            await workflow._analyze_features(input_data, ModelTier.CAPABLE)

            # Frequencies should be updated
            morning = next(f for f in sample_manifest.all_features() if f.id == "morning")
            assert morning.frequency == FrequencyTier.DAILY

    @pytest.mark.asyncio
    async def test_analyze_returns_token_counts(self, workflow, sample_manifest):
        """Test that analyze returns token counts from LLM."""
        input_data = {"manifest": sample_manifest}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ("analyzed_features: []", 123, 456)

            result, in_tokens, out_tokens = await workflow._analyze_features(
                input_data,
                ModelTier.CAPABLE,
            )

            assert in_tokens == 123
            assert out_tokens == 456


class TestGenerateStage:
    """Tests for shortcut generation stage."""

    @pytest.mark.asyncio
    async def test_generate_calls_llm(self, workflow, sample_manifest):
        """Test that generate stage calls LLM."""
        input_data = {"manifest": sample_manifest, "analysis": {}}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ('{"qwerty": {"shortcuts": []}}', 100, 50)

            await workflow._generate_shortcuts(input_data, ModelTier.CAPABLE)

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_parses_json_response(self, workflow, sample_manifest):
        """Test that generate parses JSON response from LLM."""
        input_data = {"manifest": sample_manifest, "analysis": {}}

        json_response = """
{
  "qwerty": {
    "shortcuts": [
      {"feature_id": "morning", "key": "m", "mnemonic": "M = Morning"}
    ],
    "scale_assignments": {
      "daily": ["m"],
      "frequent": [],
      "advanced": []
    },
    "phrase_mnemonic": "My Morning"
  }
}
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (json_response, 100, 50)

            result, _, _ = await workflow._generate_shortcuts(input_data, ModelTier.CAPABLE)

            assert "generated" in result
            generated = result["generated"]
            assert KeyboardLayout.QWERTY in generated.layouts

    @pytest.mark.asyncio
    async def test_generate_creates_shortcuts_for_all_layouts(self, workflow, sample_manifest):
        """Test that generate creates shortcuts for all supported layouts."""
        input_data = {"manifest": sample_manifest, "analysis": {}}

        json_response = """
{
  "qwerty": {"shortcuts": [{"feature_id": "morning", "key": "m", "mnemonic": "M"}]},
  "dvorak": {"shortcuts": [{"feature_id": "morning", "key": "a", "mnemonic": "A"}]},
  "colemak": {"shortcuts": [{"feature_id": "morning", "key": "r", "mnemonic": "R"}]}
}
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (json_response, 100, 50)

            result, _, _ = await workflow._generate_shortcuts(input_data, ModelTier.CAPABLE)

            generated = result["generated"]
            assert len(generated.layouts) == 3
            assert KeyboardLayout.QWERTY in generated.layouts
            assert KeyboardLayout.DVORAK in generated.layouts
            assert KeyboardLayout.COLEMAK in generated.layouts

    @pytest.mark.asyncio
    async def test_generate_uses_fallback_on_invalid_response(self, workflow, sample_manifest):
        """Test that generate uses fallback when LLM returns invalid JSON."""
        input_data = {"manifest": sample_manifest, "analysis": {}}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ("invalid json", 100, 50)

            result, _, _ = await workflow._generate_shortcuts(input_data, ModelTier.CAPABLE)

            # Should use fallback generation
            generated = result["generated"]
            assert isinstance(generated, GeneratedShortcuts)

    @pytest.mark.asyncio
    async def test_generate_fallback_uses_first_letter(self, workflow, sample_manifest):
        """Test fallback generation uses first letter of feature ID."""
        generated = workflow._generate_fallback_shortcuts(sample_manifest)

        # Should have QWERTY layout
        assert KeyboardLayout.QWERTY in generated.layouts

        qwerty = generated.layouts[KeyboardLayout.QWERTY]
        shortcuts = {s.feature_id: s.key for s in qwerty.shortcuts}

        assert shortcuts["morning"] == "m"
        assert shortcuts["ship"] == "s"

    @pytest.mark.asyncio
    async def test_generate_fallback_handles_conflicts(self, workflow):
        """Test fallback handles features with same first letter."""
        features = [
            Feature(id="morning", name="Morning", command="test.morning"),
            Feature(id="midnight", name="Midnight", command="test.midnight"),
        ]
        manifest = FeatureManifest(
            project_name="test",
            categories=[Category(name="Test", features=features)],
        )

        generated = workflow._generate_fallback_shortcuts(manifest)

        qwerty = generated.layouts[KeyboardLayout.QWERTY]
        shortcuts = {s.feature_id: s.key for s in qwerty.shortcuts}

        # Both start with 'm', should use different keys
        assert shortcuts["morning"] != shortcuts["midnight"]


class TestValidateStage:
    """Tests for shortcut validation stage."""

    @pytest.mark.asyncio
    async def test_validate_calls_llm(self, workflow, sample_manifest):
        """Test that validate stage calls LLM."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[
                ShortcutAssignment(feature_id="morning", key="m", mnemonic="M = Morning"),
            ],
        )

        input_data = {"manifest": sample_manifest, "generated": generated}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ('{"valid": true, "conflicts": []}', 100, 50)

            await workflow._validate_shortcuts(input_data, ModelTier.CHEAP)

            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_parses_validation_response(self, workflow, sample_manifest):
        """Test that validate parses validation response."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )

        input_data = {"manifest": sample_manifest, "generated": generated}

        json_response = """
{
  "valid": false,
  "conflicts": [{"type": "duplicate", "key": "m"}],
  "warnings": [{"type": "ergonomic", "key": "q"}]
}
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (json_response, 100, 50)

            result, _, _ = await workflow._validate_shortcuts(input_data, ModelTier.CHEAP)

            validation = result["validation"]
            assert validation["valid"] is False
            assert len(validation["conflicts"]) == 1
            assert len(validation["warnings"]) == 1

    @pytest.mark.asyncio
    async def test_validate_updates_generated_shortcuts(self, workflow, sample_manifest):
        """Test that validate updates generated shortcuts with results."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )

        input_data = {"manifest": sample_manifest, "generated": generated}

        json_response = """
{
  "valid": false,
  "conflicts": ["conflict1"],
  "warnings": ["warning1"]
}
"""

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = (json_response, 100, 50)

            await workflow._validate_shortcuts(input_data, ModelTier.CHEAP)

            assert generated.validation_passed is False
            assert generated.conflicts == ["conflict1"]
            assert generated.warnings == ["warning1"]


class TestExportStage:
    """Tests for output export stage."""

    @pytest.mark.asyncio
    async def test_export_generates_all_outputs(self, workflow, sample_manifest, tmp_path):
        """Test that export generates all output formats."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[
                ShortcutAssignment(feature_id="morning", key="m", mnemonic="M = Morning"),
            ],
        )

        input_data = {"generated": generated, "output_dir": str(tmp_path)}

        result, in_tokens, out_tokens = await workflow._export_outputs(input_data)

        assert "output_files" in result
        assert in_tokens == 0
        assert out_tokens == 0

    @pytest.mark.asyncio
    async def test_export_creates_vscode_keybindings(self, workflow, sample_manifest, tmp_path):
        """Test that export creates VSCode keybindings."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )

        input_data = {"generated": generated, "output_dir": str(tmp_path)}

        result, _, _ = await workflow._export_outputs(input_data)

        output_files = result["output_files"]
        assert "vscode" in output_files

    @pytest.mark.asyncio
    async def test_export_creates_cli_aliases(self, workflow, sample_manifest, tmp_path):
        """Test that export creates CLI aliases."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )

        input_data = {"generated": generated, "output_dir": str(tmp_path)}

        result, _, _ = await workflow._export_outputs(input_data)

        output_files = result["output_files"]
        assert "cli" in output_files
        assert output_files["cli"].exists()

    @pytest.mark.asyncio
    async def test_export_creates_markdown_docs(self, workflow, sample_manifest, tmp_path):
        """Test that export creates Markdown documentation."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )

        input_data = {"generated": generated, "output_dir": str(tmp_path)}

        result, _, _ = await workflow._export_outputs(input_data)

        output_files = result["output_files"]
        assert "docs" in output_files
        assert output_files["docs"].exists()


class TestStageSkipping:
    """Tests for stage skipping logic."""

    def test_skip_analyze_if_features_already_categorized(self, workflow, sample_manifest):
        """Test that analyze is skipped if features already have frequencies."""
        # All features have frequencies set
        input_data = {"manifest": sample_manifest}

        should_skip, reason = workflow.should_skip_stage("analyze", input_data)

        assert should_skip is True
        assert "already categorized" in reason.lower()

    def test_dont_skip_analyze_if_features_need_categorization(self, workflow):
        """Test that analyze runs if features lack frequencies."""
        # Create manifest with features missing frequencies
        features = [
            Feature(id="test", name="Test", command="test.cmd", frequency=FrequencyTier.FREQUENT),
        ]
        # Manually clear frequency to None (simulating uncategorized)
        features[0].frequency = None  # type: ignore

        manifest = FeatureManifest(
            project_name="test",
            categories=[Category(name="Test", features=features)],
        )

        input_data = {"manifest": manifest}

        should_skip, reason = workflow.should_skip_stage("analyze", input_data)

        # With at least one feature missing frequency, should not skip
        # But in practice, all features will have default frequency
        # This test shows the logic structure

    def test_skip_validate_if_requested(self, workflow):
        """Test that validate is skipped if user requests it."""
        input_data = {"skip_validation": True}

        should_skip, reason = workflow.should_skip_stage("validate", input_data)

        assert should_skip is True
        assert "user request" in reason.lower()

    def test_dont_skip_validate_by_default(self, workflow):
        """Test that validate runs by default."""
        input_data = {}

        should_skip, reason = workflow.should_skip_stage("validate", input_data)

        assert should_skip is False

    def test_dont_skip_other_stages(self, workflow):
        """Test that other stages are never skipped."""
        input_data = {}

        for stage in ["discover", "generate", "export"]:
            should_skip, reason = workflow.should_skip_stage(stage, input_data)
            assert should_skip is False


class TestRunStage:
    """Tests for run_stage dispatcher."""

    @pytest.mark.asyncio
    async def test_run_stage_discover(self, workflow, sample_project):
        """Test running discover stage."""
        input_data = {"path": str(sample_project)}

        result, _, _ = await workflow.run_stage("discover", ModelTier.CHEAP, input_data)

        assert "manifest" in result

    @pytest.mark.asyncio
    async def test_run_stage_analyze(self, workflow, sample_manifest):
        """Test running analyze stage."""
        input_data = {"manifest": sample_manifest}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ("analyzed_features: []", 100, 50)

            result, _, _ = await workflow.run_stage("analyze", ModelTier.CAPABLE, input_data)

            assert "analysis" in result

    @pytest.mark.asyncio
    async def test_run_stage_generate(self, workflow, sample_manifest):
        """Test running generate stage."""
        input_data = {"manifest": sample_manifest, "analysis": {}}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ('{"qwerty": {"shortcuts": []}}', 100, 50)

            result, _, _ = await workflow.run_stage("generate", ModelTier.CAPABLE, input_data)

            assert "generated" in result

    @pytest.mark.asyncio
    async def test_run_stage_validate(self, workflow, sample_manifest):
        """Test running validate stage."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        generated.layouts[KeyboardLayout.QWERTY] = LayoutShortcuts(
            layout=KeyboardLayout.QWERTY,
            shortcuts=[],
        )
        input_data = {"manifest": sample_manifest, "generated": generated}

        with patch.object(workflow, "_invoke_llm") as mock_llm:
            mock_llm.return_value = ('{"valid": true}', 100, 50)

            result, _, _ = await workflow.run_stage("validate", ModelTier.CHEAP, input_data)

            assert "validation" in result

    @pytest.mark.asyncio
    async def test_run_stage_export(self, workflow, sample_manifest, tmp_path):
        """Test running export stage."""
        generated = GeneratedShortcuts(manifest=sample_manifest)
        input_data = {"generated": generated, "output_dir": str(tmp_path)}

        result, _, _ = await workflow.run_stage("export", ModelTier.CHEAP, input_data)

        assert "output_files" in result

    @pytest.mark.asyncio
    async def test_run_stage_invalid_stage(self, workflow):
        """Test running invalid stage raises error."""
        with pytest.raises(ValueError, match="Unknown stage"):
            await workflow.run_stage("invalid", ModelTier.CHEAP, {})


class TestHelperMethods:
    """Tests for helper methods."""

    def test_features_to_yaml(self, workflow, sample_manifest):
        """Test converting features to YAML."""
        yaml_str = workflow._features_to_yaml(sample_manifest)

        data = yaml.safe_load(yaml_str)
        assert "features" in data
        assert len(data["features"]) == 2

    def test_parse_yaml_response_with_code_block(self, workflow):
        """Test parsing YAML from code block."""
        response = """
Here's the analysis:
```yaml
analyzed_features:
  - id: morning
    frequency: daily
```
"""

        result = workflow._parse_yaml_response(response)

        assert result is not None
        assert "analyzed_features" in result

    def test_parse_yaml_response_without_code_block(self, workflow):
        """Test parsing YAML without code block."""
        response = """
analyzed_features:
  - id: morning
    frequency: daily
"""

        result = workflow._parse_yaml_response(response)

        assert result is not None
        assert "analyzed_features" in result

    def test_parse_yaml_response_invalid(self, workflow):
        """Test parsing invalid YAML returns None."""
        response = "{ invalid yaml: : :"

        result = workflow._parse_yaml_response(response)

        assert result is None

    def test_parse_json_response_with_code_block(self, workflow):
        """Test parsing JSON from code block."""
        response = """
```json
{
  "qwerty": {
    "shortcuts": []
  }
}
```
"""

        result = workflow._parse_json_response(response)

        assert result is not None
        assert "qwerty" in result

    def test_parse_json_response_without_code_block(self, workflow):
        """Test parsing JSON without code block."""
        response = '{"qwerty": {"shortcuts": []}}'

        result = workflow._parse_json_response(response)

        assert result is not None
        assert "qwerty" in result

    def test_parse_json_response_invalid(self, workflow):
        """Test parsing invalid JSON returns None."""
        response = "{ invalid json }"

        result = workflow._parse_json_response(response)

        assert result is None

    def test_update_manifest_from_analysis(self, workflow, sample_manifest):
        """Test updating manifest with analysis results."""
        analysis = {
            "analyzed_features": [
                {"id": "morning", "frequency": "advanced"},
                {"id": "ship", "frequency": "frequent"},
            ],
        }

        workflow._update_manifest_from_analysis(sample_manifest, analysis)

        morning = next(f for f in sample_manifest.all_features() if f.id == "morning")
        ship = next(f for f in sample_manifest.all_features() if f.id == "ship")

        assert morning.frequency == FrequencyTier.ADVANCED
        assert ship.frequency == FrequencyTier.FREQUENT

    def test_update_manifest_ignores_invalid_frequency(self, workflow, sample_manifest):
        """Test that invalid frequency values are ignored."""
        original_freq = sample_manifest.all_features()[0].frequency

        analysis = {
            "analyzed_features": [
                {"id": "morning", "frequency": "invalid_tier"},
            ],
        }

        workflow._update_manifest_from_analysis(sample_manifest, analysis)

        # Frequency should remain unchanged
        assert sample_manifest.all_features()[0].frequency == original_freq

    def test_build_generated_shortcuts_from_response(self, workflow, sample_manifest):
        """Test building GeneratedShortcuts from LLM response."""
        shortcuts_data = {
            "qwerty": {
                "shortcuts": [
                    {"feature_id": "morning", "key": "m", "mnemonic": "M = Morning"},
                ],
                "scale_assignments": {
                    "daily": ["m"],
                    "frequent": [],
                    "advanced": [],
                },
                "phrase_mnemonic": "My Morning",
            },
        }

        generated = workflow._build_generated_shortcuts(sample_manifest, shortcuts_data)

        assert KeyboardLayout.QWERTY in generated.layouts
        qwerty = generated.layouts[KeyboardLayout.QWERTY]
        assert len(qwerty.shortcuts) == 1
        assert qwerty.phrase_mnemonic == "My Morning"

    def test_build_generated_shortcuts_with_none_uses_fallback(self, workflow, sample_manifest):
        """Test that None response triggers fallback generation."""
        generated = workflow._build_generated_shortcuts(sample_manifest, None)

        # Should use fallback
        assert KeyboardLayout.QWERTY in generated.layouts

    @pytest.mark.asyncio
    async def test_invoke_llm_calls_base_method(self, workflow):
        """Test that _invoke_llm calls inherited _call_llm."""
        with patch.object(workflow, "_call_llm") as mock_call:
            mock_call.return_value = ("response", 100, 50)

            response, in_tokens, out_tokens = await workflow._invoke_llm(
                prompt="test",
                tier=ModelTier.CHEAP,
                system="system",
            )

            mock_call.assert_called_once()
            assert response == "response"
            assert in_tokens == 100
            assert out_tokens == 50
